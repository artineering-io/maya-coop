"""
@summary:       Python attribute editor template extending Maya's
@run:           import coop.ae as cae (suggested)
@license:       MIT
@repository:    https://github.com/artineering-io/maya-coop
"""
from __future__ import print_function
from __future__ import unicode_literals
import maya.cmds as cmds
import maya.mel as mel
import coop.lib as clib
from maya.internal.common.ae.template import Template
# For more options e.g., dragCallback, createDraggable, please refer
# to the source file this one bases on
# Python/Lib/site-packages/maya/internal/common/ae/template


class AETemplate(Template):
    # We explicitly include ALL methods of Template to simplify autocomplete and
    # provide documentation over these methods.

    def __init__(self, node_name):
        super(AETemplate, self).__init__(node_name)

    def suppress(self, control):
        """
        Supress control (attribute) from appearing in the attribute editor
        Args:
            control (unicode): Name of control (attribute) to suppress
        """
        super(AETemplate, self).suppress(control)

    def addControl(self, control, ann="", lab="", callback=None):
        """
        Adds a named control
        Args:
            control (unicode): Name of control (attribute) to add
            ann (unicode): Annotation to appear in the tooltip (if any)
            lab (unicode): Nice name of attribute (if any)
            callback (func): Function to call if something happens
        """
        control = [control]
        if callback:
            control.append(callback)
        if lab:
            cmds.editorTemplate(label=lab, addControl=control, ann=ann)
        else:
            cmds.editorTemplate(addControl=control, ann=ann)

    def addControls(self, controls):
        """
        Adds a list of controls
        Args:
            controls (list): List of controls to add (string names)
        """
        super(AETemplate, self).addControls(controls)

    def buildUI(self, node_name):
        """
        This method needs to be overriden to create the custom UI
        Args:
            node_name (unicode): Name of the node to build UI for
        """
        super(AETemplate, self).buildUI(node_name)

    def suppressAll(self):
        """ Suppresses all attributes from appearing in the Attribute Editor """
        super(AETemplate, self).suppressAll()

    def suppressCachingFrozenNodeState(self):
        """ Suppresses the caching, frozen and nodeState attributes from appearing in the Attribute Editor """
        self.suppress("caching")
        self.suppress("frozen")
        self.suppress("nodeState")

    def callTemplate(self, template_name):
        """
        Appends an attribute editor template
        Args:
            template_name (unicode): Node name of the attribute editor template
        """
        super(AETemplate, self).callTemplate(template_name)

    def callCustom(self, new_proc, replace_proc, module, *args):
        """
        Calls a custom command to generate custom UIs in the attribute editor
        Args:
            new_proc (unicode): Procedure to add a new UI item
            replace_proc (unicode): Procedure to edit a UI item depending on selection
            module (unicode):  Module where the python versions of the new and replace functions are
            *args (any): Arguments to pass onto the procedure
        """
        import_cmd = 'python("import {}");'.format(module)  # importing the module where the python functions are
        new_proc_cmd = 'global proc {}('.format(new_proc)
        replace_proc_cmd = 'global proc {}('.format(replace_proc)
        mel_cmd = 'editorTemplate -callCustom "{}" "{}" '.format(new_proc, replace_proc)
        py_args = ""

        # build callCustom commands and procedures
        for i, arg in enumerate(args):
            if clib.is_string(arg):
                mel_cmd += '"{}" '.format(arg)
                py_args += "'{}', ".format(arg)
                new_proc_cmd += "string $arg{}, ".format(i)
                replace_proc_cmd += "string $arg{}, ".format(i)
            else:
                mel_cmd += '{} '.format(arg)
                py_args = '{}, '.format(arg)
                if isinstance(arg, int):
                    new_proc_cmd += "int $arg{}, ".format(i)
                    replace_proc_cmd += "int $arg{}, ".format(i)
                elif isinstance(arg, float):
                    new_proc_cmd += "float $arg{}, ".format(i)
                    replace_proc_cmd += "float $arg{}, ".format(i)
                else:
                    cmds.error("Variable of type '{}' has not been implemented yet in callCustom".format(type(arg)))
        mel_cmd = mel_cmd[:-1] + ";"
        new_proc_cmd = new_proc_cmd[:-2] + ') { '
        new_proc_cmd += 'python("{}.{}('.format(module, new_proc)
        new_proc_cmd += py_args[:-2]
        new_proc_cmd += ')"); }'
        replace_proc_cmd = replace_proc_cmd[:-2] + ') { '
        replace_proc_cmd += 'python("{}.{}('.format(module, replace_proc)
        replace_proc_cmd += py_args[:-2]
        replace_proc_cmd += ')"); }'

        # debug mel commands
        # print(import_cmd)
        # print(new_proc_cmd)
        # print(replace_proc_cmd)
        # print(mel_cmd)

        # evaluate mel commands
        mel.eval(import_cmd)
        mel.eval(new_proc_cmd)
        mel.eval(replace_proc_cmd)
        mel.eval(mel_cmd)

    @staticmethod
    def separator(add=True):
        """
         Adds a separator to the template.
        Args:
            add (bool): If separator should be added or not
        """
        if add:
            cmds.editorTemplate(addSeparator=True)

    class Layout:
        """ Editor template layout """
        def __init__(self, template, name, collapse=False):
            self.template = template
            self.collapse = collapse
            self.name = name

        def __enter__(self):
            cmds.editorTemplate(beginLayout=self.name, collapse=self.collapse)
            return self.template

        def __exit__(self, mytype, value, tb):
            cmds.editorTemplate(endLayout=True)
