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
from collections import OrderedDict
import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om  # python api 2.0
from . import lib as clib
from . import api as capi
from . import qt as cqt
from . import logger as clog
from PySide2 import QtCore, QtWidgets
from functools import partial

LOG = clog.logger("coop.ae")
ATTR_WIDGETS = dict()  # Index of Custom Attribute Widgets
PLAIN_ATTR_DATA = dict()


def maya_useNewAPI():
    pass


class AETemplate(object):
    """
    Base class for python Attribute Editor templates.
    Based on the Template object from:
    Python/Lib/site-packages/maya/internal/common/ae/template.py
    Extended for actual production usage
    """

    def __init__(self, node_name, extra_attributes=True):
        """
        Template constructor
        Args:
            node_name (unicode): Node name passed from mel template
            extra_attributes (bool): If 'Extra Attributes' should be automatically added
        """
        self.nodeName = node_name
        cmds.editorTemplate(beginScrollLayout=True)
        self.build_ui(node_name)
        if extra_attributes:
            cmds.editorTemplate(addExtraControls=True)
        cmds.editorTemplate(endScrollLayout=True)

    @staticmethod
    def suppress(control):
        """
        Supress control (attribute) from appearing in the attribute editor
        Args:
            control (unicode): Name of control (attribute) to suppress
        """
        cmds.editorTemplate(suppress=control)

    @staticmethod
    def add_control(control, ann="", lab="", callback=None):
        """
        Adds a named control
        Args:
            control (unicode): Name of control (attribute) to add
            ann (unicode): Annotation to appear in the tooltip (if any)
            lab (unicode): Nice name of attribute (if any)
            callback (func): Function to call if something happens
        """
        # print("add_control('{}', '{}', '{}', {})".format(control, ann, lab, callback))
        if clib.get_maya_version() > 2020:
            control = clib.u_enlist(control)
            if callback:
                control.append(callback)
            if lab:
                cmds.editorTemplate(label=lab, ann=ann, addControl=control)
            else:
                cmds.editorTemplate(ann=ann, addControl=control)
        else:
            # mel as cmds.editorTemplate doesn't work below 2022
            cmd = 'editorTemplate -ann "{}"'.format(ann)
            if lab:
                cmd += ' -label "{}"'.format(lab)
            cmd += ' -addControl "{}"'.format(control)
            if callback:
                clib.print_warning("Callbacks are not supported by add_control() on Maya < 2022")
                clib.print_info("Use custom_control(PlainAttrGrp()) instead")
            mel.eval(cmd)
        # control_name = cmds.editorTemplate(queryName=[self.nodeName, control[0]])
        # Note: the command above returns None until the AE is shown, so we can't query this here

    def add_controls(self, controls):
        """
        Adds a list of controls
        Args:
            controls (list): List of controls to add (string names)
        """
        for c in controls:
            self.add_control(c)

    @staticmethod
    def separator(add=True):
        """
        Adds a separator to the template.
        Args:
            add (bool): If separator should be added or not
        """
        if add:
            cmds.editorTemplate(addSeparator=True)

    def build_ui(self, node_name):
        """
        This method needs to be overriden to create the custom UI
        Args:
            node_name (unicode): Name of the node to build UI for
        """
        raise NotImplementedError("build_ui() has not been implemented")

    def suppress_caching_frozen_node_state(self):
        """ Suppresses the caching, frozen and nodeState attributes from appearing in the Attribute Editor """
        self.suppress("caching")
        self.suppress("frozen")
        self.suppress("nodeState")

    def call_template(self, template_name):
        """
        Appends an attribute editor template
        Args:
            template_name (unicode): Node name of the attribute editor template
        """
        mel.eval(u'AE{0}Template {1}'.format(template_name, self.nodeName))

    @staticmethod
    def call_custom(new_proc, replace_proc, module, *args):
        """
        If targeting only Maya 2022+. use custom_control() instead
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
                    cmds.error("Variable of type '{}' has not been implemented yet in call_custom".format(type(arg)))
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
    def custom_control(custom_obj, attrs):
        """
        Adds a custom control to the template.
        Args:
            custom_obj (class): The custom control object,
                                A class with buildControlUI() and replaceControlUI()
            attrs (unicode, list): The attributes that this control manages
        """
        # print("custom_control({}, {})".format(custom_obj, attrs))
        if clib.get_maya_version() > 2020:
            def create(*args):
                custom_obj.on_create(args)  # calls build_control_ui()

            def replace(*args):
                custom_obj.on_replace(args)  # calls replace_control_ui()

            cmds.editorTemplate(attrs, callCustom=[create, replace])
        else:
            # mel wrapping it is because cmds.editorTemplate doesn't work properly prior Maya 2022
            global PLAIN_ATTR_DATA
            PLAIN_ATTR_DATA[attrs] = custom_obj.build_kwargs  # we store the widget format data in a global
            AETemplate.call_custom("_ae_plain_attr_new", "_ae_plain_attr_replace", __name__,
                                   attrs)

    class Layout:
        """
        Editor template layout which enables the use of:
        with self.Layout(name, collapse):
            pass
        """

        def __init__(self, name, collapse=False):
            self.collapse = collapse
            self.name = name

        def __enter__(self):
            cmds.editorTemplate(beginLayout=self.name, collapse=self.collapse)

        def __exit__(self, mytype, value, tb):
            cmds.editorTemplate(endLayout=True)


##################################################################################
class CustomControl(object):
    """
    Base class for custom controls within the attribute editor.
    Based on the CustomControl object from:
    Python/Lib/site-packages/maya/internal/common/ae/common.py
    Extended for actual production usage

    This virtual class helps generate custom Maya control objects.
    It has intrinsic members and the 'build' and 'replace' methods, which need to be
    overwritten for it to work as intended
    """

    def __init__(self, *args, **kwargs):
        """
        Constructor of Custom Control initializing class variables
        Args:
            *args: Arguments that were passed to the custom control
            **kwargs: Keyword arguments (dict) that were passed to the custom control
        """
        self.node_name = None
        self.plug_name = None
        self.attr_name = None
        self.build_args = args
        self.build_kwargs = kwargs

    # args will collect all attributes that connected to this custom control
    def on_create(self, *args):
        """
        Run when the Custom Control is created
        Args:
            *args: Arguments that were passed to the control (usually node.attr it controls)
        """
        control_args = args[0]
        self.plug_name = control_args[0] if control_args else ""
        self.node_name, self.attr_name = clib.split_node_attr(self.plug_name)
        parent_name = cmds.setParent(q=True)
        cmds.scriptJob(uiDeleted=[parent_name, self.on_close], runOnce=True)
        self.build_control_ui()

    def on_replace(self, *args):
        """
        Run when the Custom Control is replaced/updated as the context has changed
        Args:
            *args:  Arguments that were passed to the control (usually new node.attr it controls)
        """
        control_args = args[0]
        self.plug_name = control_args[0] if control_args else ""
        self.node_name, self.attr_name = clib.split_node_attr(self.plug_name)
        self.replace_control_ui()

    def on_close(self):
        """ Override this class with the commands to 'close' the UI """
        pass

    def build_control_ui(self):
        """ Override this class with the commands to 'build' the UI """
        pass

    def replace_control_ui(self):
        """ Override this class with the commands to 'replace' the UI """
        pass

    def set_enable(self, enable):
        """ Override this class with the commands to 'enable/disable' the UI """
        pass


class PlainAttrGrp(CustomControl):
    """ Maya attribute controls created depending on the type of the attribute """

    def build_control_ui(self):
        """ Builds the custom control UI """
        node, attr = clib.split_node_attr(self.plug_name)
        if not cmds.attributeQuery(attr, n=node, ex=True):
            LOG.error("{} doesn't exist".format(self.plug_name))
            return

        cmds.setUITemplate("attributeEditorTemplate", pushTemplate=True)
        try:
            _plain_attr_widget(self.plug_name, self.build_kwargs)
        finally:
            cmds.setUITemplate(popTemplate=True)

    def replace_control_ui(self):
        """ Updates/replaces the custom control UI """
        _plain_attr_widget_update(self.plug_name, self.build_kwargs.get('callback', None))


def _plain_attr_widget(node_attr, kwargs):
    """
    Creates a plain attribute widget depending on the type of attribute
    Args:
        node_attr (unicode): The plug name in the form of 'node.attr'
        kwargs (dict): Keyword arguments that were passed to the custom control
    """
    global ATTR_WIDGETS  # keeps track of the created controls for the different node attributes
    node, attr = clib.split_node_attr(node_attr)
    lab = kwargs.get('lab', cmds.attributeQuery(attr, n=node, niceName=True))
    ann = kwargs.get('ann', "")
    callback = kwargs.get('callback', None)
    if callback:
        callback = partial(callback, node)  # better than using lambdas
    obj_type = cmds.objectType(node)
    widget_name = "{}{}".format(obj_type, attr)
    _check_attr_widgets(widget_name)
    attr_type = cmds.attributeQuery(attr, n=node, attributeType=True)
    ctrl = ""
    if attr_type == "float":
        if "map" not in kwargs:
            ctrl = cmds.attrFieldSliderGrp(at=node_attr, label=lab, ann=ann, hideMapButton=True)
        else:
            ctrl = cmds.attrNavigationControlGrp(at=node_attr, label=lab, ann=ann)
    elif attr_type == "float3":
        ctrl = cmds.attrColorSliderGrp(at=node_attr, label=lab, ann=ann, showButton=False,
                                       cw=[4, 0], columnAttach4=["right", "both", "right", "both"],
                                       columnOffset4=[6, 1, -3, 0])
    elif attr_type == "bool":
        ctrl = cmds.attrControlGrp(attribute=node_attr, label=lab, ann=ann)
        if callback:  # manage callbacks manually to guarantee their existence
            cmds.scriptJob(attributeChange=[node_attr, callback], parent=ctrl, replacePrevious=True)
        widget = cqt.wrap_ctrl(ctrl, QtWidgets.QWidget)
        widget.setAccessibleName(lab)
        # widget.setLayoutDirection(QtCore.Qt.RightToLeft)  # move checkbox to the right
        label = widget.findChildren(QtWidgets.QLabel)[0]
        label.setText(lab)
        checkbox = widget.findChildren(QtWidgets.QCheckBox)[0]
        checkbox.setText("           ")
    elif attr_type == "enum":
        ctrl = cmds.attrEnumOptionMenuGrp(at=node_attr, label=lab, ann=ann)
        if callback:  # manage callbacks manually to guarantee their existence
            cmds.scriptJob(attributeChange=[node_attr, callback], parent=ctrl, replacePrevious=True)
    else:
        LOG.error("{} UI could not be generated. Attributes of type {} "
                  "have not been implemented for _plain_attr_widget())".format(node_attr, attr_type))
        return
    if not ctrl.startswith("window"):  # do not updates/replace attributes that are in external windows
        if ctrl not in ATTR_WIDGETS[widget_name]:
            ATTR_WIDGETS[widget_name].append(ctrl)


def _check_attr_widgets(widget_name):
    """
    Verifies the integrity of the controls associated with widget_name
    in the ATTR_WIDGETS global
    Args:
        widget_name (unicode): Widget name to verify i.e., obj_type.attr
    """
    global ATTR_WIDGETS
    if widget_name not in ATTR_WIDGETS:
        ATTR_WIDGETS[widget_name] = []
    else:
        ctrls = ATTR_WIDGETS[widget_name]
        for i, ctrl in enumerate(ctrls):
            if not cqt.ctrl_exists(ctrl):
                ATTR_WIDGETS[widget_name].pop(i)


def _plain_attr_widget_update(node_attr, callback):
    """
    Updates/replaces a plain attribute to work with the new node
    Args:
        node_attr (unicode): The plug name in the form of 'node.attr'
        callback (function): Callback function
    """
    node, attr = clib.split_node_attr(node_attr)
    obj_type = cmds.objectType(node)
    widget_name = "{}{}".format(obj_type, attr)
    if not cmds.attributeQuery(attr, n=node, ex=True):
        return
    attr_type = cmds.attributeQuery(attr, n=node, attributeType=True)
    if callback:
        callback = partial(callback, node)
    ctrls = ATTR_WIDGETS.get(widget_name, [])
    for ctrl in ctrls:
        if not cqt.ctrl_exists(ctrl):  # cleanup
            ATTR_WIDGETS[widget_name].remove(ctrl)
            continue
        # update existing controls
        if attr_type == "float":
            try:
                if ctrl.rfind("attrFieldSliderGrp") > 0:
                    cmds.attrFieldSliderGrp(ctrl, at=node_attr, e=True)
                else:
                    cmds.attrNavigationControlGrp(ctrl, at=node_attr, e=True)
            except RuntimeError:
                LOG.error("Error updating attribute: {}".format(ctrl))
        elif attr_type == "float3":
            cmds.attrColorSliderGrp(ctrl, at=node_attr, e=True)
        elif attr_type == "bool":
            cmds.attrControlGrp(ctrl, attribute=node_attr, e=True)
            _check_script_jobs(node_attr, ctrl, callback)
        elif attr_type == "enum":
            cmds.attrEnumOptionMenuGrp(ctrl, at=node_attr, e=True)
            _check_script_jobs(node_attr, ctrl, callback)
        else:
            LOG.error("{} UI could not be generated."
                      "Attributes of type {} have not been implemented for "
                      "_plain_attr_widget_update())".format(node_attr, attr_type))


def _check_script_jobs(node_attr, ctrl, callback):
    """
    Checks for callbacks and creates/updates the script job associated with ctrl
    Args:
        node_attr (unicode): The plug name in the form of 'node.attr'
        ctrl (unicode): The full path/name of the control to attach callback onto
        callback (partial): Function to attach to control
    """
    if callback:
        # print("Callback of {}: {}".format(node_attr, callback))
        cmds.scriptJob(attributeChange=[node_attr, callback], parent=ctrl, replacePrevious=True)
        callback()  # run callback (default behavior)


def _ae_plain_attr_new(node_attr):
    """
    Builds the custom control UI for node_attr
    Deprecated: Use PlainAttrGrp class instead on Maya 2022+
    Args:
        node_attr (unicode): The plug name in the form of 'node.attr'
    """
    # print("ae_plain_attr_new_('{}')".format(node_attr))
    node, attr = clib.split_node_attr(node_attr)
    if not cmds.attributeQuery(attr, n=node, ex=True):
        LOG.error("{} doesn't exist".format(node_attr))
        return
    cmds.setUITemplate("attributeEditorTemplate", pushTemplate=True)
    try:
        _plain_attr_widget(node_attr, PLAIN_ATTR_DATA[attr])
    finally:
        cmds.setUITemplate(popTemplate=True)


def _ae_plain_attr_replace(node_attr):
    """
    Updates/replaces the custom control UI for node_attr
    Deprecated: Use PlainAttrGrp class instead on Maya 2022+
    Args:
        node_attr (unicode): The plug name in the form of 'node.attr'
    """
    # print("ae_plain_attr_replace_('{}')".format(node_attr))
    node, attr = clib.split_node_attr(node_attr)
    _plain_attr_widget_update(node_attr, PLAIN_ATTR_DATA[attr].get('callback', None))  # update widget


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
                    if mel.eval('$aeTab=$gAECurrentTab') == node_name:
                        self.index_ui_ctrls(ui_path)
                elif ui_path.startswith("hyperShadePanel"):
                    if mel.eval('$ppTab=$gPropertyPanelActiveNode;') == node_name:
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
            if r_idx == -1:  # it is the exact path of the searched control
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
    # print("toggle_frame('{}', '{}', {}, '{}'".format(node_name, attribute, ctrls, frame_layout))
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


def search_for_node_ae_windows(node_names):
    """
    Returns a dictionary of all ae windows associated with the nodes
    Args:
        node_names (unicode, list): Node names to search for windows
    Returns:
        (OrderedDict): Dictionary of window names that show the attribute of the node
    """
    windows = OrderedDict()
    ui_paths = cmds.lsUI(controlLayouts=True, l=True)
    node_names = clib.u_enlist(node_names)
    for node_name in node_names:
        if cmds.objExists(node_name):
            for ui_path in ui_paths:
                if ui_path.startswith("window"):
                    window_name = ui_path[:ui_path.find('|')]
                    if cmds.window(window_name, t=True, q=True) == node_name:
                        if node_name in windows:
                            if window_name not in windows[node_name]:
                                windows[node_name].append(window_name)
                        else:
                            windows[node_name] = [window_name]
        else:
            LOG.error("{} does not exist".format(node_name))
    return windows


class AEControls:
    controls = OrderedDict()
    node_name = ""
    supported_controls = ["frameLayout",  # drop-down group layouts
                          "attrFieldSliderGrp",  # float sliders
                          "attrColorSliderGrp",  # color sliders
                          "checkBoxGrp",  # check boxes
                          "attrNavigationControlGrp",  # textures
                          "attrEnumOptionMenuGrp",  # combo box
                          "separator"  # separator
                          # spinbox  # TODO?
                          ]
    layout_controls = ["frameLayout", "separator"]
    ae_path = ''
    ae_object = ''

    def __init__(self, node_name, from_window=True):
        self.from_window = from_window
        self._check_node_name(node_name)
        self.node_type = cmds.objectType(self.node_name)
        self._get_ae_qobject()
        self.controls = OrderedDict()
        self._parse_ae_children(self.ae_path, self.ae_object)

    def _check_node_name(self, node_name):
        """
        Check if everything is in order with the node name
        Args:
            node_name (unicode): Name of the node to get AE controls of
        """
        # check that everything is right
        if not cmds.objExists(node_name):
            clib.print_error("{} doesn't exist".format(node_name), True)
        self.node_name = clib.u_stringify(cmds.ls(node_name, l=True))
        if not self.from_window:   # show ae by selecting the node
            selection = cmds.ls(sl=True, l=True)
            if node_name != selection[-1]:
                cmds.select(node_name, r=True)

    def _get_ae_qobject(self):
        """
        Find attribute editor widget to get available widgets from
        Example path: AttributeEditor|MainAttributeEditorLayout|formLayout1|AEmenuBarLayout|AErootLayout
        |AEStackLayout|AErootLayoutPane|AEbaseFormLayout|AEcontrolFormLayout|AttrEdflairShaderFormLayout
        |scrollLayout50|columnLayout1759|frameLayout614|columnLayout1801|columnLayout1803|attrFieldSliderGrp902
        """
        def _parse_ae_path(ui_path):
            path = ""
            scroll_idx = ui_path.find("|scrollLayout")
            if scroll_idx > 0:
                column_idx = ui_path[scroll_idx:].find('|columnLayout') + 1
                if column_idx > 0:
                    frame_idx = ui_path[scroll_idx + column_idx:].find('|')
                    if frame_idx > 0:
                        path = ui_path[:scroll_idx + column_idx + frame_idx]
            return path

        if self.from_window:
            self._create_ae_window()

        ui_paths = cmds.lsUI(controlLayouts=True, l=True)
        self.ae_path = ""
        for ui_path in ui_paths:
            if not self.from_window:  # from open attribute editor
                if self.node_type not in ui_path:
                    continue
            elif self.ae_window[self.node_name][0] not in ui_path:  # from open ae window
                continue
            ae_path = _parse_ae_path(ui_path)
            if cqt.ctrl_exists(ae_path):
                self.ae_path = ae_path
                break
        self.ae_object = cqt.wrap_ctrl(self.ae_path, QtCore.QObject)

    def _create_ae_window(self):
        self.ae_window = search_for_node_ae_windows(self.node_name)
        # create ae window in case it was not opened already
        if self.node_name not in self.ae_window:
            short_node_name = cmds.ls(self.node_name, shortNames=True)[0]
            window_name = "windowTEMP_{}".format(short_node_name)
            window_name = cmds.window(window_name, title=self.node_name,
                                      widthHeight=(1, 1), topLeftCorner=(-5000, 0))
            mel_cmd = 'createAETabInWindow(\"{}\", \"{}\");'.format(self.node_name, window_name)
            mel.eval(mel_cmd)
            self.ae_window[self.node_name] = [window_name]
        else:
            print("Window for {} already created as {}".format(self.node_name, self.ae_window))

    @staticmethod
    def delete_ae_temp_windows():
        for window in cmds.lsUI(windows=True):
            if window.startswith("windowTEMP"):
                cmds.deleteUI(window, window=True)

    def _parse_ae_children(self, parent_path, parent_object):
        """
        Parse supported children widgets recursively
        Args:
            parent_path (unicode): Parent ui path
            parent_object (QObject): Parent object to traverse
        """
        children = parent_object.children() or []
        #print("--> Parent {}".format(parent_path))
        for child in children:
            child_path = cqt.get_full_name(cqt.get_cpp_pointer(child))
            #print(child_path)
            if child_path == parent_path:
                continue  # children may have the same ui_path as the parent
            self._store_supported_ctrls(child_path)
            try:
                self._parse_ae_children(child_path, child)
            except AttributeError:
                clib.print_warning("Couldn't parse children of {}".format(child_path))

    def _store_supported_ctrls(self, ui_path):
        """
        Get and store supported widgets from the path
        Note: Control metadata is also stored with '__' as prefix and suffix
        Args:
            ui_path (unicode): Maya's UI path of the widget
        """
        for ctrl_type in self.supported_controls:
            widget = AEControlIndexer.is_ui_ctrl(ui_path, ctrl_type)
            if widget:
                ctrl_name = widget.accessibleName()
                ctrl_data = OrderedDict()
                ctrl_data['__type__'] = ctrl_type
                ctrl_data['__lvl__'] = ui_path.count('|')
                ctrl_data['__visible__'] = widget.isVisible()
                if ctrl_type not in self.layout_controls:  # widget from attribute
                    attribute = self._query_attribute_of_ctrl(self.node_name, ctrl_name, ctrl_type, ui_path)
                    ctrl_data['__attr__'] = attribute
                    self._store_ctrl_data(ctrl_type, ui_path, attribute, ctrl_data)
                self._build_ctrls_data(self.controls, ctrl_name, ctrl_data)
                break

    def _build_ctrls_data(self, controls, ctrl_name, ctrl_data):
        """
        Store control data recursively in the right hierarchy
        Args:
            controls (OrderedDict): Current OrderedDict to embed the control to
            ctrl_name (unicode): Name of the control to potentially store
            ctrl_data (OrderedDict): Data of the control to potentially store
        """
        ctrls = list(controls.keys())
        if ctrls:
            if not ctrls[-1].startswith('__'):
                if (controls[ctrls[-1]]['__lvl__'] < ctrl_data['__lvl__']) \
                        and (controls[ctrls[-1]]['__type__'] != "separator"):
                    # child of previously parsed control, proceed to check if it's grandchild
                    self._build_ctrls_data(controls[ctrls[-1]], ctrl_name, ctrl_data)
                    return
        controls[ctrl_name] = ctrl_data

    def _store_ctrl_data(self, control, control_path, attr, ctrl_data):
        """
        Store values of a maya controls
        Args:
            control (unicode): Maya's internal control to get values from
            control_path (unicode): Maya's internal control path to get values from
            attr (unicode): Attribute to get values from
            ctrl_data (OrderedDict): Dictionary of control data
        """
        if control == "attrColorSliderGrp":
            ctrl_data['__value__'] = cmds.attrColorSliderGrp(control_path, rgbValue=True, q=True)
            if cmds.attributeQuery(attr, n=self.node_name, usedAsFilename=True):
                ctrl_data['__lvl__'] += 1  # offset the level by one to be in the same depth as other controls
        else:
            if control == "attrFieldSliderGrp":
                self._store_slider_data(attr, ctrl_data)
            elif control == "attrEnumOptionMenuGrp":
                enum_list = cmds.attributeQuery(attr, n=self.node_name, listEnum=True)[0]
                ctrl_data['__options__'] = enum_list.split(':')
            if control == "attrNavigationControlGrp":
                ctrl_data['__value__'] = ""  # TODO query textures of file nodes, and set afterwards...
            else:
                ctrl_data['__value__'] = cmds.getAttr("{}.{}".format(self.node_name, attr))

    def _query_attribute_of_ctrl(self, node_name, control_name, control_type, control_path):
        def _compare_nice_names_of_each_attr(attrs):
            for attr in attrs:
                nice_name = cmds.attributeQuery(attr, n=node_name, niceName=True)
                if control_name == nice_name:
                    return attr

        attribute = ""
        if control_type == "attrFieldSliderGrp":
            attribute = clib.split_node_attr(cmds.attrFieldSliderGrp(control_path, attribute=True, q=True))[-1]
        elif control_type == "attrColorSliderGrp":
            attribute = clib.split_node_attr(cmds.attrColorSliderGrp(control_path, attribute=True, q=True))[-1]
        elif control_type == "checkBoxGrp":
            attribute = clib.split_node_attr(cmds.attrControlGrp(control_path, attribute=True, q=True))[-1]
        elif control_type == "attrEnumOptionMenuGrp":
            # Note: We can't query the attribute though the "cmds.attrEnumOptionMenuGrp"
            attribute = _compare_nice_names_of_each_attr(cmds.attributeInfo(node_name, enumerated=True))
        elif control_type == "attrNavigationControlGrp":
            # Note: we can't query the attribute though the "cmds.attrNavigationControlGrp"
            attribute = _compare_nice_names_of_each_attr(cmds.listAttr(node_name, usedAsFilename=True))
        return attribute

    def _store_slider_data(self, attr, ctrl_data):
        """
        Store slider data
        Returns:
            attr (unicode): Attribute to get values from
            ctrl_data (OrderedDict): Dictionary of control data
        """
        if cmds.attributeQuery(attr, n=self.node_name, minExists=True):
            ctrl_data['__min__'] = cmds.attributeQuery(attr, n=self.node_name, minimum=True)[0]
        if cmds.attributeQuery(attr, n=self.node_name, softMinExists=True):
            ctrl_data['__softMin__'] = cmds.attributeQuery(attr, n=self.node_name, softMin=True)[0]
        if cmds.attributeQuery(attr, n=self.node_name, maxExists=True):
            ctrl_data['__max__'] = cmds.attributeQuery(attr, n=self.node_name, maximum=True)[0]
        if cmds.attributeQuery(attr, n=self.node_name, softMaxExists=True):
            ctrl_data['__softMax__'] = cmds.attributeQuery(attr, n=self.node_name, softMax=True)[0]
        # old method based solely on ctrl data
        # ctrl_data['__max__'] = cmds.attrFieldSliderGrp(control_path, sliderMaxValue=True, q=True)
        # ctrl_data['__min__'] = cmds.attrFieldSliderGrp(control_path, sliderMinValue=True, q=True)
