"""
@summary:       Python attribute editor template extending Maya's
                Some methods have been re-implemented to have better control
                Coding convention assimilates Maya's camelCase on purpose
@run:           import coop.ae as cae (suggested)
@license:       MIT
@repository:    https://github.com/artineering-io/maya-coop
"""
from __future__ import print_function
from __future__ import unicode_literals
import maya.cmds as cmds
import maya.mel as mel
from . import lib as clib
from . import qt as cqt
from . import logger as clog
from PySide2 import QtWidgets, QtCore

LOG = clog.logger("coop.ae")

from maya.internal.common.ae.template import Template
import maya.internal.common.ae.custom as ae_custom


# For more options e.g., dragCallback, createDraggable, please refer
# to the source file this library bases on:
# Python/Lib/site-packages/maya/internal/common/ae/template.py


class AETemplate(Template):
    # We explicitly include ALL methods of Template to simplify autocomplete and
    # provide documentation over these methods.

    def __init__(self, node_name, extra_attributes=True):
        """
        Template constructor
        Args:
            node_name (unicode): Node name passed from mel template
            extra_attributes (bool): If 'Extra Attributes' should be automatically added
        """
        if extra_attributes:
            super(AETemplate, self).__init__(node_name)
        else:
            self.nodeName = node_name
            cmds.editorTemplate(beginScrollLayout=True)
            self.buildUI(node_name)
            cmds.editorTemplate(endScrollLayout=True)

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
        # control_name = cmds.editorTemplate(queryName=[self.nodeName, control[0]])
        # Note: the command above returns None until the AE is shown, so we can't query this here

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
        If using widget objects, use customControl() instead
        Calls a custom command to generate custom UIs in the attribute editor.
        The callCustom flag of editorTemplate only works with mel commands, this method creates a mel wrapper to
        call Python functions within the module.
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
        mel_fmt_args = ""

        # build callCustom commands and procedures
        for i, arg in enumerate(args):
            mel_fmt_args += "-stringArg $arg{} ".format(i + 1)
            if clib.is_string(arg):
                mel_cmd += '"{}" '.format(arg)
                py_args += "'^{}s', ".format(i + 1)
                new_proc_cmd += "string $arg{}, ".format(i + 1)
                replace_proc_cmd += "string $arg{}, ".format(i + 1)
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
        new_proc_cmd = new_proc_cmd[:-2] + ') { python('
        replace_proc_cmd = replace_proc_cmd[:-2] + ') { python('
        if mel_fmt_args:
            new_proc_cmd += "`format " + mel_fmt_args
            replace_proc_cmd += "`format " + mel_fmt_args
        new_proc_cmd += '"{}.{}('.format(module, new_proc)
        replace_proc_cmd += '"{}.{}('.format(module, replace_proc)
        new_proc_cmd += py_args[:-2]
        replace_proc_cmd += py_args[:-2]
        new_proc_cmd += ')"'
        replace_proc_cmd += ')"'
        if mel_fmt_args:
            new_proc_cmd += '`'
            replace_proc_cmd += '`'
        new_proc_cmd += ');}'
        replace_proc_cmd += ');}'

        # debug mel commands
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

    @staticmethod
    def customControl(custom_obj, attrs):
        """
        Adds a custom control to the template.
        Args:
            custom_obj (class): The custom control object,
                                A class with buildControlUI() and replaceControlUI()
            attrs (unicode, list): The attributes that this control manages
        """

        def create(*args):
            custom_obj.onCreate(args)  # calls buildControlUI()

        def replace(*args):
            custom_obj.onReplace(args)  # calls replaceControlUI()

        cmds.editorTemplate(attrs, callCustom=[create, replace])

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


##################################################################################
class CustomControl(ae_custom.CustomControl):
    # inherits from Maya/Python/Lib/site-packages/maya/internal/common/ae/common.py
    # This virtual class helps generate custom Maya control objects.
    # It has intrinsic members and the 'build' and 'replace' methods, which need to be
    # overwritten for it to work as intended

    def __init__(self, *args, **kwargs):
        self.nodeName = None
        self.plugName = None
        self.build_args = args
        self.build_kwargs = kwargs

    def buildControlUI(self):
        pass

    def replaceControlUI(self):
        pass


class PlainAttrGrp(CustomControl):
    """
    The default Maya attribute but without the  texture map button
    """

    def buildControlUI(self):
        node, attr = clib.split_node_attr(self.plugName)
        if not cmds.attributeQuery(attr, n=node, ex=True):
            LOG.error("{} doesn't exist".format(self.plugName))

        cmds.setUITemplate("attributeEditorTemplate", pushTemplate=True)
        lab = cmds.attributeQuery(attr, n=node, niceName=True)
        if "lab" in self.build_kwargs:
            lab = self.build_kwargs['lab']
        ann = ""
        if "ann" in self.build_kwargs:
            ann = self.build_kwargs['ann']
        callback = None
        if "callback" in self.build_kwargs:
            callback = self.build_kwargs['callback']
        attr_type = cmds.attributeQuery(attr, n=node, attributeType=True)
        if attr_type == "float":
            cmds.attrFieldSliderGrp(at=self.plugName, label=lab, ann=ann, hideMapButton=True)
        elif attr_type == "float3":
            cmds.attrColorSliderGrp(at=self.plugName, label=lab, ann=ann, showButton=False,
                                    cw=[4, 0], columnAttach4=["right", "both", "right", "both"],
                                    columnOffset4=[6, 1, -3, 0])
        elif attr_type == "bool":
            if callback is None:
                ctrl = cmds.attrControlGrp(attribute=self.plugName, label=lab, ann=ann)
            else:
                ctrl = cmds.attrControlGrp(attribute=self.plugName, label=lab, ann=ann,
                                           changeCommand=lambda: callback(node))
            widget = cqt.wrap_ctrl(ctrl, QtWidgets.QWidget)
            # widget.setLayoutDirection(QtCore.Qt.RightToLeft)  # move checkbox to the right
            label = widget.findChildren(QtWidgets.QLabel)[0]
            label.setText(lab)
            checkbox = widget.findChildren(QtWidgets.QCheckBox)[0]
            checkbox.setText("           ")
        else:
            LOG.error("{} UI could not be generated."
                      "Attributes of type {} have not been implemented in PlainAttrGrp())".format(self.plugName,
                                                                                                  attr_type))
        cmds.setUITemplate(popTemplate=True)

    def replaceControlUI(self):
        pass  # the attrFieldSliderGrp is in charge of replacing/setting whatever value is in there


##################################################################################
class AEControlIndexer:
    """
    Indexes specific attribute editor controls of a node type in a dictionary
    within the entire Maya UI
    """
    index = dict()

    def __init__(self, node_name, ui_ctrls):
        """
        Args:
            node_name (uniform): Node name to index attribute from
            ui_ctrls (list, unicode): Controls to index e.g., "frameLayout"
        """
        if not cmds.objExists(node_name):
            clib.print_error("{} doesn't exist".format(node_name))
            return
        node_type = cmds.objectType(node_name)
        # initialize instance variables
        self.index = dict()
        self.ui_ctrls = clib.u_enlist(ui_ctrls)
        for ui_ctrl in self.ui_ctrls:
            self.index[ui_ctrl] = dict()
        # iterate through all ui paths
        self.ui_paths = cmds.lsUI(controlLayouts=True, l=True)
        for ui_path in self.ui_paths:
            if node_type in ui_path:
                if ui_path.startswith("window"):
                    # there is a window with the node_type in its widget name (most likely copy tab of the AE)
                    window_name = ui_path[:ui_path.find('|')]
                    if cmds.window(window_name, title=True, query=True) == node_name:
                        self.index_window(window_name)
                elif ui_path.startswith("AttributeEditor"):
                    if mel.eval('$tempMelVar=$gAECurrentTab') == node_name:
                        self.index_ui_ctrls(ui_path)
                elif ui_path.startswith("hyperShadePanel"):
                    if mel.eval('$tempMelVar=$gPropertyPanelActiveNode;') == node_name:
                        self.index_ui_ctrls(ui_path)

    def index_window(self, window_name):
        """
        Indexes any windows that might be related to the node type
        Args:
            window_name (unicode): name of the window
        """
        for ui_path in self.ui_paths:
            if window_name in ui_path:
                self.index_ui_ctrls(ui_path)

    def index_ui_ctrls(self, ui_path):
        """
        Indexes the AE controls if the ui_path is one
        Args:
            ui_path (unicode): ui path to index if it is a frame layout
        """
        for ui_ctrl in self.ui_ctrls:
            ui_ctrl_widget = self.is_ui_ctrl(ui_path, ui_ctrl)
            if ui_ctrl_widget:
                ui_name = ui_ctrl_widget.accessibleName()
                if ui_name not in self.index[ui_ctrl]:
                    self.index[ui_ctrl][ui_name] = [ui_ctrl_widget]
                else:
                    self.index[ui_ctrl][ui_name].append(ui_ctrl_widget)

    @staticmethod
    def is_ui_ctrl(ui_path, ui_ctrl, widget=True):
        """
        Check if the ui path is the exact ui path of a desired control and return it if it is
        Args:
            ui_path (unicode): UI path of a control or layout
            ui_ctrl (unicode): Name of control or layout to verify
            widget (bool): If the QWidget or the path should be returned
        Returns:
            (QWidget, unicode): A QWidget or the path to the exact control (None if not found)
        """
        idx = ui_path.rfind("|{}".format(ui_ctrl))
        if idx != -1:
            r_idx = ui_path.find("|", idx + 1)
            if r_idx == -1:  # it is the path of the searched for layout
                # print("---> {}".format(ui_path))
                if widget:
                    return cqt.wrap_ctrl(ui_path)
                return ui_path
        return None

    def get_ctrls(self, ui_ctrl):
        """
        Get controls of a specific type from the index
        Args:
            ui_ctrl (unicode): control type to get index from
        Returns:
            (dict): Dictionary of control names and their existing QWidgets
        """
        if ui_ctrl in self.index:
            return self.index[ui_ctrl]
        clib.print_error("Index doesn't have {} controls".format(ui_ctrl))
        return None


def toggle_frame(node_name, attribute, ctrls, frame_layout):
    """
    Toggles the frame layout of attributes depending on the state of the setting
    Args:
        node_name (unicode): Name of the node to check
        attribute (unicode): Setting attribute
        ctrls (dict): Dictionary of frame layout controls
        frame_layout (unicode): Title of the frame layout
    """
    if frame_layout in ctrls:
        if cmds.getAttr("{}.{}".format(node_name, attribute)):
            for widget in ctrls[frame_layout]:
                widget.setVisible(True)
        else:
            for widget in ctrls[frame_layout]:
                widget.setVisible(False)


def toggle_attributes(node_name, driving_attribute, ctrls, shown_attributes, strict=True):
    """
    Toggles shown_attributes depending on the enum of the driving attribute
    Example:
        There are two "enum" options for drivers, driver A and driver B
        When driver A is active [0], we want to show his attributes (0 element in shown_attributes) and hide the rest
        When driver B is active [1], we want to show his attributes (1 element in shown_attributes) and hide the rest
    Args:
        node_name (unicode): Name of the node to check
        driving_attribute (unicode): name of the driving attribute
        ctrls (dict): Dictionary of frame layout controls
        shown_attributes (unicode, list): attributes that need to be shown depending on driving attribute
        strict (bool): If error messages should be displayed when a widget can't be found in the Attribute Editor
    """
    if not cmds.attributeQuery(driving_attribute, n=node_name, ex=True):
        LOG.error("No driving attribute '{}' found in node '{}'".format(driving_attribute, node_name))
        return
    option = int(cmds.getAttr("{}.{}".format(node_name, driving_attribute)))  # make sure its an "enum"
    shown_attributes = clib.u_enlist(shown_attributes)

    for i, toggle in enumerate(shown_attributes):
        toggle = clib.u_enlist(toggle)  # make sure they are in a list so we can loop through them
        for t in toggle:
            if t in ctrls:
                if i == option:
                    for widget in ctrls[t]:
                        widget.setVisible(True)
                else:
                    for widget in ctrls[t]:
                        widget.setVisible(False)
            else:
                if strict:
                    LOG.error("{} widgets are not found in the Attribute Editor".format(t))
