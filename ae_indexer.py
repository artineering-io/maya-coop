"""
@summary:       Python attribute editor indexer
@run:           import coop.ae_indexer (suggested)
@license:       MIT
@repository:    https://github.com/artineering-io/maya-coop
"""
from collections import OrderedDict
try:
    from PySide6 import QtCore
except ImportError:
    from PySide2 import QtCore
import maya.mel as mel
import maya.cmds as cmds

from . import lib as clib
from . import qt as cqt
from . import logger as clog
from . import materials as cmat
from . import ae as cae


LOG = clog.logger("coop.ae")


class AEControls:
    controls = OrderedDict()
    node_name = ""
    supported_controls = ["frameLayout",  # drop-down group layouts
                          "attrFieldSliderGrp",  # float sliders
                          "attrColorSliderGrp",  # color sliders
                          "checkBoxGrp",  # check boxes
                          "attrNavigationControlGrp",  # textures
                          "attrEnumOptionMenuGrp",  # combo box
                          "separator",  # separator
                          "attrFieldGrp"  # vec2 vec3 vec4
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
        if not self.from_window:  # show ae by selecting the node
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
            elif self.ae_window[self.node_name][0] != cqt.UIPath(ui_path).root():
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
            cqt.get_maya_window().activateWindow()  # remove focus
        else:
            # print("Window for {} already created as {}".format(self.node_name, self.ae_window))
            pass

    @staticmethod
    def delete_ae_temp_windows():
        for window in cmds.lsUI(windows=True):
            if window.startswith("windowTEMP"):
                cmds.deleteUI(window, window=True)
                cmds.windowPref(window, remove=True)

    def _parse_ae_children(self, parent_path, parent_object):
        """
        Parse supported children widgets recursively
        Args:
            parent_path (unicode): Parent ui path
            parent_object (QObject): Parent object to traverse
        """
        children = parent_object.children() or []
        # print("--> Parent {}".format(parent_path))
        for child in children:
            child_path = cqt.get_full_name(cqt.get_cpp_pointer(child))
            # print(child_path)
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
            widget = cae.AEControlIndexer.is_ui_ctrl(ui_path, ctrl_type)
            if widget:
                ctrl_name = widget.accessibleName()
                if ctrl_type == "" and ctrl_type == "checkBoxGrp":
                    cmds.attrControlGrp(ui_path, label=True, q=True)
                ctrl_data = OrderedDict()
                ctrl_data['__type__'] = ctrl_type
                ctrl_data['__lvl__'] = ui_path.count('|')
                ctrl_data['__visible__'] = widget.isVisible()
                if ctrl_type not in self.layout_controls:  # widget from attribute
                    attribute = self._query_attribute_of_ctrl(self.node_name, ctrl_name, ctrl_type, ui_path)
                    ctrl_data['__attr__'] = attribute
                    self._store_ctrl_data(ctrl_type, attribute, ctrl_data)
                else:
                    if ctrl_type == "frameLayout":
                        ctrl_data['__collapse__'] = cmds.frameLayout(ui_path, collapse=True, q=True)
                        # if ctrl_data['__collapse__']:
                        #     print("Should open {}".format(ui_path))
                        # cmds.frameLayout(ui_path, collapse=False, e=True)
                        # QtTest.QTest.mouseClick(widget, QtCore.Qt.LeftButton)
                        # print("Collapse script is {}".format(cmds.frameLayout(ui_path, collapse=True, q=True)))
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

    def _store_ctrl_data(self, control, attr, ctrl_data):
        """
        Store values of a maya controls
        Args:
            control (unicode): Maya's internal control to get values from
            attr (unicode): Attribute to get values from
            ctrl_data (OrderedDict): Dictionary of control data
        """
        if control == "attrColorSliderGrp":
            self._store_color_slider_data(attr, ctrl_data)
        else:
            # store ctrl data
            if control == "attrFieldSliderGrp":
                self._store_slider_data(attr, ctrl_data)
            elif control == "attrEnumOptionMenuGrp":
                self._store_enum_data(attr, ctrl_data)
            elif control == "attrFieldGrp":
                self._store_field_grp_data(attr, ctrl_data)
            # store values
            if control == "attrNavigationControlGrp":
                self._store_texture_data(attr, ctrl_data)
            elif control == "attrFieldGrp":
                ctrl_data['__value__'] = cmds.getAttr("{}.{}".format(self.node_name, attr))[0]
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
        elif control_type == "attrFieldGrp":
            attribute = clib.split_node_attr(cmds.attrFieldGrp(control_path, attribute=True, q=True))[-1]
        elif control_type == "attrEnumOptionMenuGrp":
            # Note: We can't query the attribute though the "cmds.attrEnumOptionMenuGrp"
            attribute = _compare_nice_names_of_each_attr(cmds.attributeInfo(node_name, enumerated=True))
        elif control_type == "attrNavigationControlGrp":
            # Note: we can't query the attribute though the "cmds.attrNavigationControlGrp"
            attribute = _compare_nice_names_of_each_attr(cmds.listAttr(node_name, usedAsFilename=True))
        return attribute

    def _store_color_slider_data(self, attr, ctrl_data):
        """
        Store color slider data
        Returns:
            attr (unicode): Attribute to get values from
            ctrl_data (OrderedDict): Dictionary of control data
        """
        ctrl_data['__value__'] = cmds.getAttr("{}.{}".format(self.node_name, attr))[0]
        if cmds.attributeQuery(attr, n=self.node_name, usedAsFilename=True):
            ctrl_data['__lvl__'] += 1  # offset the level by one to be in the same depth as other controls
            ctrl_data['__texture__'] = True
            texture = cmat.get_texture(self.node_name, attr)
            if texture:
                ctrl_data['__value__'] = texture
            else:
                connected_node = cmat.get_connected_node(self.node_name, attr, prefix="n|")
                if connected_node:
                    ctrl_data['__value__'] = connected_node

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

    def _store_enum_data(self, attr, ctrl_data):
        """
        Store combo box data
        Returns:
            attr (unicode): Attribute to get values from
            ctrl_data (OrderedDict): Dictionary of control data
        """
        enum_list = cmds.attributeQuery(attr, n=self.node_name, listEnum=True)[0]
        ctrl_data['__options__'] = enum_list.split(':')

    def _store_field_grp_data(self, attr, ctrl_data):
        """
        Store field group data
        Returns:
            attr (unicode): Attribute to get values from
            ctrl_data (OrderedDict): Dictionary of control data
        """
        if cmds.attributeQuery(attr, n=self.node_name, minExists=True):
            ctrl_data['__min__'] = cmds.attributeQuery(attr, n=self.node_name, minimum=True)
        if cmds.attributeQuery(attr, n=self.node_name, maxExists=True):
            ctrl_data['__max__'] = cmds.attributeQuery(attr, n=self.node_name, maximum=True)
        if cmds.attributeQuery(attr, n=self.node_name, numberOfChildren=True):
            ctrl_data['__children__'] = cmds.attributeQuery(attr, n=self.node_name, listChildren=True)

    def _store_texture_data(self, attr, ctrl_data):
        """
        Store slider data
        Returns:
            attr (unicode): Attribute to get values from
            ctrl_data (OrderedDict): Dictionary of control data
        """
        ctrl_data['__value__'] = ""
        node_attr = "{}.{}".format(self.node_name, attr)
        connections = cmds.listConnections(node_attr, s=True, d=False) or []
        if connections:
            in_node = connections[0]
            if cmds.objectType(in_node) == "file":
                ctrl_data['__value__'] = cmds.getAttr("{}.{}".format(in_node, "fileTextureName"))
            else:
                ctrl_data['__value__'] = "n|{}".format(in_node)


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
