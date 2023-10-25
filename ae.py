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
import maya.OpenMayaUI as omUI
from . import lib as clib
from . import qt as cqt
from . import logger as clog
from PySide2 import QtCore, QtWidgets, QtGui
from functools import partial

LOG = clog.logger("coop.ae")
ATTR_WIDGETS = dict()  # Index of Custom Attribute Widgets
PLAIN_ATTR_DATA = dict()

maya_useNewAPI = True

try:
    long  # Python 2
except NameError:
    long = int  # Python 3


class BaseAttr(object):
    def __init__(self, attr_name, label="", tooltip="", callback=None, enable=True,
                 range_label=None, label_width=-1, custom_replace=None):
        """
        Base attribute class containing attribute GUI data
        Args:
            attr_name (unicode): Name of the attribute
            label (unicode): Label ot the attribute in the AE
            tooltip (unicode): Tooltip to appear when hovering over the attribute
            callback (func): Callback triggered upon attribute change
            enable (bool): If the attribute is enabled or disabled
            range_label (unicode): Range label in case of a float2 attribute
            label_width (int): Custom label width
            custom_replace (func): Custom replace function for attribute
        """
        self.name = attr_name
        self.label = label
        self.tooltip = tooltip
        self.callback = callback
        self.enable = enable
        self.range_label = range_label
        if label_width == -1:
            label_width = int(mel.eval('$tempMelVar=$gTextColumnWidthIndex'))
        self.label_width = label_width
        self.custom_replace = custom_replace


class ShortAttr(BaseAttr):
    def __init__(self, attr_name, label="", tooltip="", callback=None, enable=True, custom_replace=None):
        """
        Convenience attribute class containing GUI data for short attributes (used for responsive grid layouts)
        Args:
            attr_name (unicode): Name of the attribute
            label (unicode): Label ot the attribute in the AE
            tooltip (unicode): Tooltip to appear when hovering over the attribute
            callback (func): Callback triggered upon attribute change
            enable (bool): If the attribute is enabled or disabled
        """
        super(ShortAttr, self).__init__(attr_name, label, tooltip, callback, enable, custom_replace=custom_replace)
        self.label_width *= 0.8


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
    def custom_control(custom_obj, attrs=""):
        """
        Adds a custom control to the template.
        Args:
            custom_obj (class): The custom control object,
                                A class with build_control_ui() and replace_control_ui()
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


##################################################################################
class ResponsiveGridLayout(CustomControl):
    """ Creates a responsive grid layout in the AE
    Args:
        attrs (list): A list of BaseAttr to include in the responsive grid
        title (unicode): If the Grid layout should have a title (frameLayout)
        spacing (int): Spacing between the grid elements
        columns (int): Specifies how many columns the grid layout will have
    """
    def build_control_ui(self):
        # print(self.build_args)
        # print(self.build_kwargs)
        self.attrs = self.build_args[0]
        bg_color = []
        if "bg_color" in self.build_kwargs:
            bg_color = self.build_kwargs["bg_color"]
        cmds.setUITemplate("attributeEditorTemplate", pushTemplate=True)
        try:
            # build frame
            frame_title = self.build_kwargs.get('title', '')
            if frame_title:
                frame_path = cmds.frameLayout(label=frame_title, collapse=False)
                if bg_color:
                    cmds.frameLayout(frame_path, backgroundColor=[bg_color[0], bg_color[1], bg_color[2]], edit=True)
            else:
                frame_path = cmds.columnLayout()
            # build grid
            self.grid = QtWidgets.QWidget()
            self.grid_layout = QtWidgets.QGridLayout(self.grid)
            self.grid_layout.setContentsMargins(0, 0, 0, 0)
            self.grid_layout.setSpacing(self.build_kwargs.get("spacing", 0))
            self.populate_widgets()
            # add grid to frame
            frame_widget = omUI.MQtUtil.findControl(frame_path)
            omUI.MQtUtil.addWidgetToMayaLayout(cqt.get_cpp_pointer(self.grid), long(frame_widget))
        finally:
            cmds.setUITemplate(popTemplate=True)

    def replace_control_ui(self):
        # as ctrls are parented on QT element, existence is managed by us
        for i, attr in enumerate(self.attrs):
            node_attr = "{}.{}".format(self.node_name, attr.name)
            ctrl_path = cqt.get_full_name(cqt.get_cpp_pointer(self.ctrl_widgets[i]))
            callback = None
            if attr.callback:
                callback = partial(attr.callback, self.node_name)
            _update_ctrl(ctrl_path, node_attr, callback)
            if attr.custom_replace:  # run custom replace function if specified
                attr.custom_replace(node_attr, ctrl_path)

    def populate_widgets(self):
        self.ctrl_widgets = []
        row = 0
        column = 0
        for attr in self.attrs:
            node_attr = "{}.{}".format(self.node_name, attr.name)
            ctrl = _plain_attr_widget(node_attr, attr)
            if ctrl:
                ctrl_widget = cqt.wrap_ctrl(ctrl, QtWidgets.QWidget)
                self.ctrl_widgets.append(ctrl_widget)
                self.grid_layout.addWidget(ctrl_widget, row, column, 1, 1)
                column += 1
                if column == self.build_kwargs.get("columns", 2):
                    row += 1
                    column = 0


##################################################################################
class PlainAttrGrp(CustomControl):
    """ Maya attribute controls created depending on the type of the attribute 
    Args:
        attr (BaseAttr): A BaseAttr object containing attribute information
        attr_data (kwargs): The attribute data as keyword arguments
    """

    def build_control_ui(self):
        """ Builds the custom control UI """
        node, attr = clib.split_node_attr(self.plug_name)
        if not cmds.attributeQuery(attr, n=node, ex=True):
            LOG.error("{} doesn't exist".format(self.plug_name))
            return

        cmds.setUITemplate("attributeEditorTemplate", pushTemplate=True)
        try:
            if self.build_args:
                _plain_attr_widget(self.plug_name, self.build_args[0])
            else:
                _plain_attr_widget(self.plug_name, self.build_kwargs)
        finally:
            cmds.setUITemplate(popTemplate=True)

    def replace_control_ui(self):
        """ Updates/replaces the custom control UI """
        _plain_attr_widget_update(self.plug_name, self.build_kwargs.get('callback', None))


def _plain_attr_widget(node_attr, attr_data):
    """
    Creates a plain attribute widget depending on the type of attribute
    Args:
        node_attr (unicode): The plug name in the form of 'node.attr'
        attr_data (dict, BaseAttr): Keyword arguments that were passed to the custom control
    """
    global ATTR_WIDGETS  # keeps track of the created controls for the different node attributes

    def get_attr_data(base_attr):
        """
        Convert BaseAttr object to dictionary
        Args:
            base_attr (BaseAttr): Base attribute object
        """
        data = {
            'lab': base_attr.label,
            'ann': base_attr.tooltip,
            'callback': base_attr.callback,
            'enable': base_attr.enable,
            'range_label': base_attr.range_label,
            'label_width': base_attr.label_width
        }
        return data

    if isinstance(attr_data, BaseAttr):
        attr_data = get_attr_data(attr_data)

    node, attr = clib.split_node_attr(node_attr)
    lab = attr_data.get('lab', '')
    if not lab:
        lab = cmds.attributeQuery(attr, n=node, niceName=True)
    label_width = attr_data.get('label_width', int(mel.eval('$tempMelVar=$gTextColumnWidthIndex')))
    enabled = attr_data.get('enable', True)
    ann = attr_data.get('ann', "")
    callback = attr_data.get('callback', None)
    if callback:
        callback = partial(callback, node)  # better than using lambdas
    obj_type = cmds.objectType(node)
    widget_name = "{}{}".format(obj_type, attr)
    _check_attr_widgets(widget_name)
    attr_type = cmds.attributeQuery(attr, n=node, attributeType=True)
    if attr_type == "float" or attr_type == "long":
        if "map" not in attr_data:
            ctrl = cmds.attrFieldSliderGrp(at=node_attr, label=lab, ann=ann,
                                           hideMapButton=True, enable=enabled, columnWidth=[1, label_width])
        else:
            ctrl = cmds.attrNavigationControlGrp(at=node_attr, label=lab, ann=ann)
        if callback:  # manage callbacks manually to guarantee their existence
            cmds.scriptJob(attributeChange=[node_attr, callback], parent=ctrl, replacePrevious=True)
    elif attr_type == "float3":
        ctrl = cmds.attrColorSliderGrp(at=node_attr, label=lab, ann=ann, showButton=False,
                                       cw=[4, 0], columnAttach4=["right", "both", "right", "both"],
                                       columnOffset4=[6, 1, -3, 0])
    elif attr_type == "float2":
        ctrl = attr_range_grp(node_attr, lab=lab, tooltip=ann, range_label=attr_data.get('range_label', ""))
    elif attr_type == "long2" or attr_type == "double4":
        ctrl = cmds.attrFieldGrp(attribute=node_attr, label=lab, ann=ann, hideMapButton=True)
    elif attr_type == "bool":
        ctrl = attr_checkbox_grp(node_attr, lab, label_width, tooltip=ann, enable=enabled, callback=callback)
    elif attr_type == "enum":
        ctrl = cmds.attrEnumOptionMenuGrp(at=node_attr, label=lab, ann=ann, enable=enabled,
                                          columnWidth=[1, label_width])
        if callback:  # manage callbacks manually to guarantee their existence
            cmds.scriptJob(attributeChange=[node_attr, callback], parent=ctrl, replacePrevious=True)
    else:
        LOG.error("{} UI could not be generated. Attributes of type {} "
                  "have not been implemented for _plain_attr_widget())".format(node_attr, attr_type))
        return
    if not ctrl.startswith("window"):  # do not update/replace attributes that are in external windows
        if ctrl not in ATTR_WIDGETS[widget_name]:
            ATTR_WIDGETS[widget_name].append(ctrl)
    return ctrl


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
    # print("_plain_attr_widget_update({})".format(node_attr))
    node, attr = clib.split_node_attr(node_attr)
    obj_type = cmds.objectType(node)
    widget_name = "{}{}".format(obj_type, attr)
    if not cmds.attributeQuery(attr, n=node, ex=True):
        return
    if callback:
        callback = partial(callback, node)
    ctrls = ATTR_WIDGETS.get(widget_name, [])
    for ctrl in ctrls:
        if not cqt.ctrl_exists(ctrl):  # cleanup
            ATTR_WIDGETS[widget_name].remove(ctrl)
            continue
        # update existing controls
        _update_ctrl(ctrl, node_attr, callback)


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


def _update_ctrl(ctrl, node_attr, callback=None):
    node, attr = clib.split_node_attr(node_attr)
    attr_type = cmds.attributeQuery(attr, n=node, attributeType=True)
    if attr_type == "float":
        try:
            if ctrl.rfind("attrFieldSliderGrp") > 0:
                cmds.attrFieldSliderGrp(ctrl, at=node_attr, e=True)
            else:
                cmds.attrNavigationControlGrp(ctrl, at=node_attr, e=True)
        except RuntimeError:
            LOG.error("Error updating attribute: {}".format(ctrl))
    elif attr_type == "long":
        cmds.attrFieldSliderGrp(ctrl, attribute=node_attr, e=True)
    elif attr_type == "long2" or attr_type == "double4":
        cmds.attrFieldGrp(ctrl, at=node_attr, e=True)
    elif attr_type == "float3":
        cmds.attrColorSliderGrp(ctrl, at=node_attr, e=True)
    elif attr_type == "float2":
        cmds.attrFieldGrp(ctrl, at=node_attr, e=True)
    elif attr_type == "bool":
        cmds.connectControl(ctrl, node_attr, index=2)
        _check_script_jobs(node_attr, ctrl, callback)
    elif attr_type == "enum":
        cmds.attrEnumOptionMenuGrp(ctrl, at=node_attr, e=True)
        _check_script_jobs(node_attr, ctrl, callback)
    else:
        LOG.error("{} UI could not be generated."
                  "Attributes of type {} have not been implemented for "
                  "_plain_attr_widget_update())".format(node_attr, attr_type))


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
        self.windows = []
        self.ui_ctrls = clib.u_enlist(ui_ctrls)
        for ui_ctrl in self.ui_ctrls:
            self.index[ui_ctrl] = dict()
        # iterate through all ui paths
        self.ui_paths = cmds.lsUI(controlLayouts=True, l=True)
        for ui_path in self.ui_paths:
            if node_type in ui_path:
                if ui_path.startswith("window"):
                    # there is a window with the node_type in its widget name (most likely copy tab of the AE)
                    window_name = cqt.UIPath(ui_path).root()
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
        if window_name not in self.windows:
            self.windows.append(window_name)
            for ui_path in self.ui_paths:
                if window_name == cqt.UIPath(ui_path).root():
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


def attr_range_grp(node_attr, lab, tooltip="", range_label="", enable=True):
    """
    Create a custom Attribute Range widget (float2) with a range label inbetween
    Args:
        node_attr (unicode): The attribute the control should change in the format node.attr
        lab (unicode): The label the control should have (can be different than attribute name)
        tooltip (unicode): Tooltip that appears when hovering over the control
        range_label (unicode): The range label that appears between the range fields
        enable (bool): If widget should be enabled or disabled
    Returns:
        (ui path): The UI path of the custom attribute control group
    """
    ctrl = cmds.attrFieldGrp(attribute=node_attr, label=lab, ann=tooltip, enable=enable)
    widget = cqt.get_maya_widget(ctrl)
    layout = widget.layout()
    line_edits = widget.findChildren(QtWidgets.QLineEdit)
    le_width = line_edits[0].width()
    spacer = QtWidgets.QLabel(range_label)
    spacer.setMinimumWidth(le_width * 2 + (10 * cqt.get_dpi_scale()))
    spacer.setAlignment(QtCore.Qt.AlignCenter)
    layout.insertWidget(2, spacer, 1)
    line_edits[-1].setMinimumWidth(le_width + 5)
    return ctrl


def attr_checkbox_grp(node_attr, lab, label_width=None, tooltip="", callback=None, enable=True):
    """
    Create a custom Attribute Checkbox Group widget that has the checkbox to the right
    Args:
        node_attr (unicode): The attribute the control should change in the format node.attr
        lab (unicode): The label the control should have (can be different than attribute name)
        label_width (int): The width available for the label
        tooltip (unicode): Tooltip that appears when hovering over the control
        callback (func): Function to call when the attribute is changed
        enable (bool): If widget should be enabled or disabled
    Returns:
        (ui path): The UI path of the custom attribute control group
    """
    ctrl = cmds.attrControlGrp(attribute=node_attr, label=lab, ann=tooltip, enable=enable)
    if callback:  # manage callbacks manually to guarantee their existence
        cmds.scriptJob(attributeChange=[node_attr, callback], parent=ctrl, replacePrevious=True)
    widget = cqt.wrap_ctrl(ctrl, QtWidgets.QWidget)
    widget.setAccessibleName(lab)
    widget.setLayoutDirection(QtCore.Qt.RightToLeft)  # move checkbox to the right
    cmds.checkBoxGrp(ctrl, columnWidth=[1, 0], e=True)  # hide empty label of ctrl group
    cbox = widget.findChildren(QtWidgets.QCheckBox)[0]
    if label_width is None:
        label_width = int(mel.eval('$tempMelVar=$gTextColumnWidthIndex'))
    dpi_scale = cqt.get_dpi_scale()
    cbox.setFixedWidth(dpi_scale * (label_width + 2))
    style_sheet = "margin-top: {0}px; margin-bottom: {0}px".format(dpi_scale * 2)
    cbox.setStyleSheet(style_sheet)
    return ctrl
