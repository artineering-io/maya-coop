"""
@summary:       Python attribute editor template extending Maya's
@run:           import coop.ae as cae (suggested)
@license:       MIT
@repository:    https://github.com/artineering-io/maya-coop
"""
import maya.cmds as cmds
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

    @staticmethod
    def separator():
        """ Adds a separator to the template. """
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
