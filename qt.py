"""
@summary:       Maya cooperative qt library
@run:           import coop.coopQt as qt (suggested)
@license:       MIT
@repository:    https://github.com/artineering-io/maya-coop
"""
from __future__ import print_function
from __future__ import unicode_literals
import time, datetime, threading, os
import maya.cmds as cmds
import maya.OpenMayaUI as omUI
from PySide2 import QtCore, QtGui, QtWidgets
from shiboken2 import wrapInstance, getCppPointer
from . import lib as clib
from . import logger as clog

# Python 2-3 checks
try:
    from PySide2.QtWebEngineWidgets import QWebEngineView, QWebEnginePage  # Doesn't work with Maya 2017
except ImportError:
    from PySide2.QtWebKitWidgets import QWebView as QWebEngineView

try:
    long  # Python 2
except NameError:
    long = int  # Python 3

LOG = clog.logger("coop.qt")
FONT_HEADER = QtGui.QFont('MS Shell dlg 2', 15)
FONT_FOOTER = QtGui.QFont('MS Shell dlg 2', 8)


# WINDOW
def get_maya_window():
    """
    Get the pointer to a maya window and wrap the instance as a QWidget
    Returns:
        (QWidget): Maya window as a QWidget instance
    """
    ptr = omUI.MQtUtil.mainWindow()  # pointer to main window
    return wrap_instance(ptr)


def wrap_instance(qt_ptr, q_widget=None):
    """
    Wrap pointer as a QWidget
    Args:
        qt_ptr (ptr): Pointer to QWidget
        q_widget (class): Class to wrap pointer as

    Returns:
        (QWidget): QWidget
    """
    if q_widget is None:
        q_widget = QtWidgets.QWidget
    return wrapInstance(long(qt_ptr), q_widget)


def wrap_ctrl(qt_ctrl, qt_base=None):
    """
    Wrap pointer as a QWidget
    Args:
        qt_ctrl (unicode): Name of Qt Control
        qt_base (class): Class to wrap pointer as

    Returns:
        (QWidget): QWidget
    """
    # find pointer
    qt_ptr = omUI.MQtUtil.findControl(qt_ctrl)
    if qt_ptr is None:
        qt_ptr = omUI.MQtUtil.findLayout(qt_ctrl)
    if qt_ptr is None:
        qt_ptr = omUI.MQtUtil.findMenuItem(qt_ctrl)
    if qt_ptr is None:
        return None
    # find base if unspecified
    if qt_base is None:
        q_obj = wrapInstance(long(qt_ptr), QtCore.QObject)
        if qt_base is None:
            meta_obj = q_obj.metaObject()
            cls = meta_obj.className()
            # print("Methods of class {} are:".format(cls))
            # for i in range(meta_obj.methodCount()):
            #     print(meta_obj.method(i).name())
            # print("Properties of class {} are:".format(cls))
            # for i in range(meta_obj.propertyCount()):
            #     print(meta_obj.property(i).name())
            # print("---")
            if hasattr(QtWidgets, cls):
                qt_base = getattr(QtWidgets, cls)
            else:
                super_cls = meta_obj.superClass().className()
                if hasattr(QtWidgets, super_cls):
                    qt_base = getattr(QtWidgets, super_cls)
                else:
                    qt_base = QtWidgets.QWidget
    return wrapInstance(long(qt_ptr), qt_base)  # wrap instance


def ctrl_exists(qt_ctrl):
    """
    Returns True if qt_ctrl exists
    Args:
        qt_ctrl (unicode): Full path to Qt Control within Maya

    Returns:
        (bool): True if qt_ctrl exists
    """
    if omUI.MQtUtil.findControl(qt_ctrl) is None:
        return False
    return True


def get_full_name(qt_ptr):
    """
    Get full name of qt widget from pointer
    Args:
        qt_ptr (ptr): Pointer to QWidget

    Returns:
        (unicode): full name of qt widget
    """
    full_name = omUI.MQtUtil.fullName(long(qt_ptr))
    if full_name:
        if full_name[-1] == "|":
            # Sometimes the command returns the full name with '|' in the end
            full_name = full_name[:-1]
    return full_name


def get_maya_layout(ui_path=""):
    """
    Get Maya's internal layout where ui_path is being placed or the current parent
    where the UI is being currently modified
    Args:
        ui_path (unicode): UI path of Maya control or layout

    Returns:
        (QLayout): Maya's parent layout wrapped in a QLayout
    """
    if ui_path:
        parent = wrap_instance(omUI.MQtUtil.findLayout(ui_path), QtCore.QObject)
    else:
        parent = wrap_instance(omUI.MQtUtil.getCurrentParent(), QtCore.QObject)
    # Note: Maya layouts are explicit in the UI path.
    #       As Qt doesn't do this by default, Maya includes a dummy widget with the same name
    #       We can use this knowledge to extract the actual layout
    parent_layout = parent.children()[-1].layout()
    return parent_layout


def get_cpp_pointer(qobject):
    """
    Get the C++ pointer of any QObject
    Args:
        qobject (QObject): QObject to get C++ pointer from
    Returns:
        C++ pointer
    """
    return getCppPointer(qobject)[0]


class UIPath:
    def __init__(self, path):
        if isinstance(path, str):
            self.path = clib.u_decode(path)
        elif clib.get_py_version() < 3:
            if isinstance(path, unicode):
                self.path = path
        else:
            clib.print_error("{} is not a string".format(path), True)

    def root(self):
        """
        Gets the root name of the UI path
        Returns:
            (unicode): Root name of UI path
        """
        idx = self.path.find('|')
        if idx != -1:
            return self.path[:idx]
        return ""


def is_minimized(window):
    """
    Returns True if window is minimized
    Args:
        window (unicode):  Window title

    Returns:
        (bool): True if window is minimized
    """
    if cmds.window(window, exists=True, query=True):
        ptr = omUI.MQtUtil.findWindow(window)  # pointer to window
        q_window = wrap_instance(ptr)
        return q_window.windowState() == QtCore.Qt.WindowMinimized


def get_dock(name=''):
    """
    Get pointer to a dock pane
    Args:
        name (unicode): Name of the dock

    Returns:
        (raw): Raw pointer to the created dock
    """
    if not name:
        cmds.error("No name for dock was specified")
    delete_dock(name)
    # used to be called dockControl
    # ctrl = cmds.workspaceControl(name, dockToMainWindow=('left', True), label=name)
    ctrl = cmds.dockControl(name, con=name, area='left', label=name)
    ptr = omUI.MQtUtil.findControl(ctrl)
    return wrap_instance(ptr)


def delete_dock(name=''):
    """
    Deletes a docked UI
    Args:
        name (unicode): Name of the dock to delete
    """
    if cmds.dockControl(name, query=True, exists=True):  # workspaceControl on 2017
        LOG.debug("The dock should be deleted next")
        cmds.deleteUI(name)


def get_dpi_scale():
    """
    Gets the dpi scale of the Maya window
    Returns:
        (float): DPI scaling factor of the Maya interface
    TODO: MacOS and Linux version
    """
    if clib.get_local_os() == "win":
        return cmds.mayaDpiSetting(realScaleValue=True, q=True)
    return 1.0


def read_python(file_path):
    """
    Reads python file and evaluates it
    Args:
        file_path (unicode): File path to *.py file
    """
    with open(file_path, 'r') as f:
        raw_data = f.read()
    return eval(raw_data)


class CoopMayaUI(QtWidgets.QDialog):

    def __init__(self, title, dock=False, rebuild=False, brand="studio.coop", tooltip="", show=True,
                 parent=""):

        if cmds.window(title, exists=True):
            if not rebuild:
                cmds.showWindow(title)
                return
            cmds.deleteUI(title, wnd=True)

        if parent == "":
            parent = get_maya_window()
        elif cmds.window(clib.u_stringify(parent), exists=True, query=True):
            ptr = omUI.MQtUtil.findWindow(parent)
            parent = wrap_instance(ptr)
        else:
            if parent is None:
                # this is intended, do not parent to anything
                pass

        if clib.get_py_version() > 3:
            super().__init__(parent)
        else:
            super(CoopMayaUI, self).__init__(parent)

        # create window
        self.setWindowTitle(title)
        self.setObjectName(title)
        self.setWindowFlags(QtCore.Qt.Tool)  # always on top (multiplatform)
        self.dpi = get_dpi_scale()

        # check if the ui is dockable
        if cmds.dockControl(title, query=True, exists=True):
            print("dock under this name exists")
            cmds.deleteUI("watercolorFX", ctl=True)
            cmds.deleteUI("watercolorFX", lay=True)
        if dock:
            cmds.dockControl(title, con=title, area='left', label=title)
        else:
            self.setGeometry(250, 250, 0, 0)  # default position when built

        # default UI elements (keeping it simple)
        self.layout = QtWidgets.QVBoxLayout(self)  # self -> apply to QDialog
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        # self.layout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)

        header_margin = 10 * self.dpi
        self.header = QtWidgets.QLabel(title)
        self.header.setAlignment(QtCore.Qt.AlignHCenter)
        self.header.setFont(FONT_HEADER)
        self.header.setContentsMargins(header_margin, header_margin, header_margin, header_margin)

        self.brand = QtWidgets.QLabel(brand)
        self.brand.setAlignment(QtCore.Qt.AlignHCenter)
        self.brand.setToolTip(tooltip)
        self.brand.setStyleSheet("background-color: rgb(40,40,40); color: rgb(180,180,180); border:solid black 1px;")
        self.brand.setFont(FONT_FOOTER)
        self.brand.setFixedHeight(15*self.dpi)

        self.buildUI()
        self.populateUI()
        if not dock and show:
            self.show()

        LOG.debug("{0} was successfully generated".format(title))

    def populateUI(self):
        pass

    def buildUI(self):
        pass

    def refresh(self):
        # if refresh is not overriden, then its going to rebuild the UI
        clear_layout(self.layout)
        self.buildUI()
        self.populateUI()


def refresh_window(window_title_or_class, quiet=True):
    """
    Refresh the UI elements by deleting all widgets and rebuilding it
    Args:
        window_title_or_class (unicode or class): Title of the window to refresh
        quiet (bool): If messages should be printed
    """
    if clib.is_string(window_title_or_class):
        window_title = window_title_or_class
        if cmds.window(window_title, exists=True):
            ptr = omUI.MQtUtil.findWindow(window_title)  # pointer to main window
            window = wrap_instance(ptr)
            main_layout = window.layout()
            clear_layout(main_layout)  # delete all widgets within main layout
            window.window().buildUI()
    else:
        window_title = window_title_or_class.windowTitle
        if cmds.window(window_title, exists=True):
            ptr = omUI.MQtUtil.findWindow(window_title)  # pointer to main window
            window_title_or_class = wrap_instance(ptr, window_title_or_class)
            window_title_or_class.refresh()


def repopulate_window(window_title):
    """
    Repopulates the window by running the populateUI method
    Args:
         window_title (unicode): Title of the window to repopulate
    """
    if cmds.window(window_title, exists=True, query=True):
        if cmds.window(window_title, visible=True, q=True):
            ptr = omUI.MQtUtil.findWindow(window_title)
            wrap_instance(ptr).window().populateUI()


def clear_layout(layout):
    """
    Delete all widgets within a layout
    Args:
        layout (QLayout): layout to clear
    """
    # delete all widgets within main layout
    index = layout.count() - 1
    while index >= 0:
        widget = layout.itemAt(index).widget()
        widget.setParent(None)
        index -= 1


class IconButton(QtWidgets.QLabel):
    """
    Icon Button class object
    """
    clicked = QtCore.Signal()
    active = False

    def __init__(self, image, tooltip='', size=None, parent=None, b_color=(68, 68, 68), h_color=(200, 200, 200)):
        """
        Icon Button constructor
        Args:
            image (unicode): relative image path ("images/butIcon.png")
            tooltip (unicode): tooltip of button (default -> "")
            size {lst): List of unsigned integers -> size of button in pixels (default -> [25, 25])
            parent (QWidget): Parent widget (default -> None)
        """
        super(IconButton, self).__init__(parent)
        if size is None:
            size = [25, 25]
        self.setFixedSize(size[0], size[1])
        self.setScaledContents(True)
        self.setToolTip(tooltip)
        self.setPixmap(image)
        self.b_color = b_color
        self.h_color = h_color
        self.set_colors()

    def mouseReleaseEvent(self, event):
        self.toggle()
        self.clicked.emit()

    def change_icon(self, image):
        self.setPixmap(image)

    def toggle(self):
        if not self.active:
            self.active = True
        else:
            self.active = False

    def set_colors(self):
        style_sheet = "QLabel{background-color: rgb" + "{0}".format(self.b_color) + \
                      ";} QLabel:hover{background-color: rgb" + "{0}".format(self.h_color) + ";}"
        self.setStyleSheet(style_sheet)

    def set_active_colors(self):
        """ Sets an active background color """
        style_sheet = "QLabel{background-color: rgb" + "{0}".format(self.h_color) + \
                      ";} QLabel:hover{background-color: rgb" + "{0}".format(self.h_color) + ";}"
        self.setStyleSheet(style_sheet)


class HLine(QtWidgets.QFrame):
    """
    Horizontal line class object
    """

    def __init__(self, width=0, height=5):
        """
        Horizontal line constructor
        Args:
            width (int):  Width of horizontal line
            height (int): Height of widget (line thickness won't change)
        """
        super(HLine, self).__init__()
        self.setFrameShape(QtWidgets.QFrame.HLine)
        self.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.height = height
        self.width = width

    def sizeHint(self):
        return QtCore.QSize(self.width, self.height)


class RelativeSlider(QtWidgets.QSlider):
    """
    Relative slider class object
    A slider that slides back to it's 0 position after sliding, giving relative values to it's previous position
    """

    def __init__(self, direction=QtCore.Qt.Horizontal):
        """
        Relative slider constructor
        Args:
            direction: QtCore.Qt.Horizontal or QtCore.Qt.Vertical
        """
        super(RelativeSlider, self).__init__(direction)
        self.prevValue = 0
        self.sliderReleased.connect(self.release)
        self.installEventFilter(self)

    def release(self):
        self.prevValue = 0
        self.slide_back(time.time() + 0.05)

    def rel_value(self):
        """
        Get the relative value
        Returns:
            (int): relative value
        """
        rel_value = self.value() - self.prevValue
        self.prevValue = self.value()
        return rel_value

    def slide_back(self, end_time):
        self.blockSignals(True)
        if time.time() < end_time:
            self.setValue(self.value() * 0.9)
            threading.Timer(0.01, self.slide_back, [end_time]).start()
        else:
            self.setValue(0)
        self.blockSignals(False)

    def eventFilter(self, object, event):
        """ Event filter to ignore mouse wheel on slider """
        if event.type() == QtCore.QEvent.Wheel:
            return True  # blocking the event
        else:
            return False


class LabeledFieldSliderGroup(QtWidgets.QWidget):
    """
    Create a labeled field slider group
    """
    valueChanged = QtCore.Signal()  # value changed signal of custom widget

    def __init__(self, label="", value=0.0, soft_minv=0.0, soft_maxv=1.0, minv=None, maxv=None):
        super(LabeledFieldSliderGroup, self).__init__()
        self.dpiS = get_dpi_scale()
        self._set_slider_members(label, soft_minv, soft_maxv, minv, maxv)

        # create layout
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # create label
        label = QtWidgets.QLabel(label)
        label.setMinimumWidth(140 * self.dpiS)
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.layout.addWidget(label)

        # create field
        self.field = QtWidgets.QDoubleSpinBox()
        self.field.setDecimals(3)
        self.field.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.field.setFixedWidth(60 * self.dpiS)
        self.field.setStyleSheet("border: 0; border-radius: {0}px".format(2 * self.dpiS))
        self.field.setAlignment(QtCore.Qt.AlignVCenter)
        self.field.setMinimum(-999999999)
        if self.min is not None:
            self.field.setMinimum(self.min)
        self.field.setMaximum(999999999)
        if self.max is not None:
            self.field.setMaximum(self.max)

        self.field.setSingleStep(0.01 * pow(10, len(str(int(value)))))  # step depends on how many digits value has
        self.field.setObjectName("{0} field".format(label))
        self.layout.addWidget(self.field)

        # create slider
        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.installEventFilter(self)
        self.slider.setMinimumWidth(200 * self.dpiS)
        self.slider.setObjectName("{0} slider".format(label))
        self.slider.setSingleStep(10 * pow(10, len(str(int(value)))))  # step depends on how many digits value has
        self.slider.setPageStep(10 * pow(10, len(str(int(value)))))  # step depends on how many digits value has
        self.layout.addWidget(self.slider)

        # save data variables
        self.set_range(self.soft_min, self.soft_max)

        # set values
        self.field.setValue(value)
        self.slider.setValue(value * 1000)  # sliders only operate on integers
        self.internalValue = value

        # create connections
        self.slider.valueChanged.connect(self.update_value)
        self.field.valueChanged.connect(self.update_value)

    def _set_slider_members(self, label, soft_minv, soft_maxv, minv, maxv):
        """
        Sets the slider members and verifies that everything is in order
        Args:
            label (unicode): Label of slider widget
            soft_minv (float): Soft min of slider
            soft_maxv (float): Soft max of slider
            minv (float): Absolute min of slider
            maxv (float): Absolute max of slider
        """
        self.label = label
        self.min = minv
        self.soft_min = soft_minv
        if minv is not None:
            if soft_minv < self.min:
                self.soft_min = self.min
        self.max = maxv
        self.soft_max = soft_maxv
        if maxv is not None:
            if soft_maxv > self.max:
                self.soft_max = self.max


    def set_range(self, minv, maxv):
        """
        Sets the range of the slider to min and max
        Args:
            minv (float): Minimum value of slider
            maxv (float): Maximum value of slider
        """
        # check minimum
        if minv < maxv:
            if self.min is None:
                self.soft_min = minv
            else:
                if minv >= self.min:
                    self.soft_min = minv
                else:
                    LOG.warning("Soft minimum value of {} not less than minimum value of {} in {}"
                                .format(minv, self.min, self.label))
        else:
            LOG.warning("Minimum value of {} not less than maximum value of {} in {}"
                        .format(minv, maxv, self.label))
        self.slider.setMinimum(self.soft_min * 1000)
        # check maximum
        if maxv > self.soft_min:
            if self.max is None:
                self.soft_max = maxv
            else:
                if maxv <= self.max:
                    self.soft_max = maxv
                else:
                    LOG.warning("Soft maximum value {} is not more than maximum value of {} in {}"
                                .format(maxv, self.max, self.label))
        else:
            LOG.warning("Maximum value {} is not more than minimum value of {} in {}"
                        .format(maxv, self.soft_min, self.label))
        self.slider.setMaximum(self.soft_max * 1000)

    def update_value(self):
        """ Update and synchronize the value between the spinbox and slider """
        value = self.sender().value()
        if self.sender() == self.slider:
            value /= 1000.0
            # print("{0} with value: {1}".format(self.sender().objectName(), value))
            self.field.setValue(value)
        if self.sender() == self.field:
            # print("{0} with value: {1}".format(self.sender().objectName(), value))
            self.slider.blockSignals(True)
            # check if slider needs to be changed
            if value < self.soft_min:
                self.set_range(value, self.soft_max)
            if value > self.soft_max:
                self.set_range(self.soft_min, value)
            # set value
            self.slider.setValue(value * 1000)
            self.slider.blockSignals(False)
        self.internalValue = value
        self.valueChanged.emit()

    def value(self):
        """
        Get the internal value of the LabeledFieldSliderGroup
        Returns:
            float: the shared value between the spinbox and the slider
        """
        return self.internalValue

    def set_field_width(self, width):
        """
        Set a custom width for field spinbox
        Args:
            width (int): New width of the field spinbox
        """
        self.field.setFixedWidth(width * self.dpiS)

    def eventFilter(self, object, event):
        """ Event filter to ignore mouse wheel on slider """
        if event.type() == QtCore.QEvent.Wheel and object is self.slider:
            return True
        else:
            return False


class FileBrowserGrp(QtWidgets.QWidget):
    """
    Create a line edit file browser group
    """
    valueChanged = QtCore.Signal()  # value changed signal of custom widget

    def __init__(self, file_path='', placeholder='', button='...', relative=True, relative_root='',
                 dialog_start_dir='', dialog_title="Select texture file:",
                 dialog_filter="All Files (*.*)"):
        super(FileBrowserGrp, self).__init__()
        self.dpi = get_dpi_scale()
        self.internal_value = file_path
        self.relative = relative
        self.relative_root = relative_root
        self.dialog_title = dialog_title
        self.dialog_filter = dialog_filter
        self.dialog_start_dir = dialog_start_dir
        if not dialog_start_dir:
            self.dialog_start_dir = cmds.workspace(q=True, rootDirectory=True)

        # create layout
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(2 * self.dpi)

        # create line edit
        self.line_edit = QtWidgets.QLineEdit(file_path)
        self.line_edit.setPlaceholderText(placeholder)
        self.line_edit.returnPressed.connect(self.update_path)
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        size_policy.setHorizontalStretch(1)
        self.line_edit.setSizePolicy(size_policy)

        self.layout.addWidget(self.line_edit)
        self.layout.addStretch()

        # create browse button
        push_button = QtWidgets.QPushButton(button)
        push_button.setMaximumWidth(len(str(button)) * 10 * self.dpi)
        push_button.released.connect(self.browse_dialog)
        self.layout.addWidget(push_button)
        self.layout.addStretch()

    def browse_dialog(self):
        """ Runs when the file browse button is released """
        start_dir = self.line_edit.text()
        if not start_dir or not os.path.isfile(start_dir):
            start_dir = self.dialog_start_dir
        path = clib.dialog_open(starting_directory=start_dir, title=self.dialog_title,
                                file_filter=self.dialog_filter)
        if self.relative:
            path = clib.make_path_relative(path, self.relative_root)
        self.internal_value = path
        self.line_edit.setText(path)
        self.valueChanged.emit()

    def update_path(self):
        """ Runs when the line edit field is updated """
        self.internal_value = self.line_edit.text()
        self.valueChanged.emit()

    def value(self):
        """
        Get the internal value of the FileBrowserGrp
        Returns:
            str: the current path to a file
        """
        return self.internal_value


class WidgetGroup(QtWidgets.QWidget):
    """
    Simple widget group class object with embedded layout and batch widget assignment
    """

    def __init__(self, q_widgets=None, q_layout=None, parent=None, margins=0):
        """
        Widget Group constructor
        Args:
            q_widgets (list): List of widgets to group (default: [])
            q_layout (QLayout): Layout object -> layout of group (default: QtWidgets.QVBoxLayout())
            parent (QWidget): Parent object (default: None)
        """
        super(WidgetGroup, self).__init__(parent)
        if q_widgets is None:
            q_widgets = []
        if not q_layout:
            q_layout = QtWidgets.QVBoxLayout()
        self.group_layout = q_layout
        self.setLayout(self.group_layout)
        self.group_layout.setContentsMargins(margins, margins, margins, margins)
        self.add_widgets(q_widgets)

    def add_widget(self, widget):
        """
        Add a single widget to the group
        Args:
            widget (QWidget): Widget to be added
        """
        self.group_layout.addWidget(widget)

    def add_widget_into(self, widget, row, column):
        """
        Add a single widget into (row, column) of the group (has to be a QGridLayout)
        Args:
            widget (QWidget): Widget to be added
            row (int): row to insert into
            column (int): column to insert into
        """
        self.group_layout.addWidget(widget, row, column)

    def add_widgets(self, widgets):
        """
        Adds a list of widgets to the group
        Args:
            widgets (list): List of QWidgets to be added
        """
        for widget in widgets:
            if widget == "stretch":
                self.group_layout.addStretch()
            else:
                self.group_layout.addWidget(widget)


class CollapsibleGrp(QtWidgets.QWidget):
    """
    Create a collapsible group similar to what you can find in the attribute editor
    """
    collapsed = {
        True: u'  \u2BC8   ',
        False: u'  \u2BC6   '
    }
    w_height = 0

    def __init__(self, title='', collapsed=False):
        super(CollapsibleGrp, self).__init__()
        self.dpi = get_dpi_scale()
        self.title = title

        # create layout
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # create toggle button
        self.toggle_button = QtWidgets.QPushButton("{}{}".format(self.collapsed[collapsed], self.title))
        self.toggle_button.setObjectName("toggler")
        self.setStyleSheet('QPushButton#toggler {'
                           'text-align: left;'
                           'font-weight: bold;'
                           'background-color: #5d5d5d;'
                           'padding: 0.3em;'
                           'border-radius: 0.2em;}')
        self.toggle_button.released.connect(self.toggle_content)
        self.layout.addWidget(self.toggle_button)

        # content widget
        self.content = QtWidgets.QGroupBox()
        self.content_layout = QtWidgets.QVBoxLayout(self.content)
        self.layout.addWidget(self.content)
        self.content.setVisible(not collapsed)

    def add_widget(self, widget):
        """ Adds a widget to the content of the collapsible group """
        self.content_layout.addWidget(widget)

    def toggle_content(self):
        """ Toggles the content of the collapsible group """
        if self.content.isVisible():
            self.content.setVisible(False)
            self.toggle_button.setText("{}{}".format(self.collapsed[True], self.title))
            if self.w_height:
                self.window().resize(self.window().width(), self.w_height)  # TODO: make this somehow work
        else:
            self.w_height = self.window().height()
            self.content.setVisible(True)
            self.toggle_button.setText("{}{}".format(self.collapsed[False], self.title))


class SplashView(QWebEngineView):
    """ SplashView is a QWebEngineView that opens links in a browser instead of in the QWebEngineView"""
    def __init__(self, *args, **kwargs):
        QWebEngineView.__init__(self, *args, **kwargs)
        self.setPage(WebEnginePage(self))


class WebEnginePage(QWebEnginePage):
    def acceptNavigationRequest(self, url, _type, is_main_frame):
        if _type == QWebEnginePage.NavigationTypeLinkClicked:
            print("Opening: {}".format(url.toString()))
            QtGui.QDesktopServices.openUrl(url)
            return False
        return True


class ProgressDialog(QtWidgets.QProgressDialog):
    """ Simple progress dialog """
    def __init__(self, window_title, parent="", prefix="Processing", time_remaining=False):
        self.prefix = prefix
        self.float_value = 0
        self.start_time = time.time()
        self.time_elapsed = 0
        self.time_remaining = time_remaining
        if cmds.about(batch=True):
            print("Initializing {}".format(window_title))
        else:
            if parent == "":
                parent = get_maya_window()
            super(ProgressDialog, self).__init__(parent)
            self.setWindowModality(QtCore.Qt.WindowModal)
            self.setWindowTitle(window_title)
            self.setMinimumWidth(600)
            self.setAutoClose(True)
            self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
            self.setAutoReset(True)
            self.setRange(0, 100)
            self.setValue(int(self.float_value))
            self.show()
            process_events()

    def add(self, v, item):
        self.float_value += v
        if self.time_remaining:
            self.calculate_time()
        if cmds.about(batch=True):
            self.log_progress(item)
        else:
            if self.wasCanceled():
                return False
            self.setValue(int(self.float_value))
            label = "{} {}".format(self.prefix, item)
            if self.time_remaining:
                label += "\nElapsed time {}".format(self.time_elapsed)
                label += "\nRemaining time {}".format(self.time_remaining)
            self.setLabelText(label)
            process_events()
        return True

    def log_progress(self, item):
        print("{}% / 100%".format(round(self.float_value)))
        log_info = "{} {}".format(self.prefix, item)
        if self.time_remaining:
            log_info += " | elapsed: {} | remaining: {}".format(self.time_elapsed, self.time_remaining)
        print(log_info)

    def calculate_time(self):
        self.time_elapsed = time.time() - self.start_time
        self.time_remaining = (100.0 - self.float_value) * (self.time_elapsed / self.float_value)
        # format to HH:MM:SS
        self.time_elapsed = str(datetime.timedelta(seconds=int(self.time_elapsed)))
        self.time_remaining = str(datetime.timedelta(seconds=int(self.time_remaining)))

    def finish(self):
        if cmds.about(batch=True):
            print("100% - COMPLETED")
        else:
            self.setValue(100)
            self.close()


def process_events():
    """ Processes all queued Qt events """
    QtCore.QCoreApplication.processEvents()


# DEBUG


def print_children(qobject):
    """
    Prints all the children of qobject recursively
    Args:
        qobject (QObject, unicode): The QObject object or path to inspect
    """
    if clib.is_string(qobject):
        qobject = wrap_ctrl(qobject)
    children = qobject.children()
    for child in children:
        print(get_full_name(get_cpp_pointer(child)))
        print_children(child)