"""
@license:       MIT
@repository:    https://github.com/artineering-io/maya-coop
#                           ___  _
#     ___ ___   ___  _ __  / _ \| |_
#    / __/ _ \ / _ \| '_ \| | | | __|
#   | (_| (_) | (_) | |_) | |_| | |_
#    \___\___/ \___/| .__/ \__\_\\__|
#                   |_|
@summary:       Maya cooperative qt library
@run:           import coop.coopQt as qt (suggested)
"""
from __future__ import print_function
from __future__ import unicode_literals
import logging, time, threading, os
import maya.mel as mel
import maya.cmds as cmds
import maya.OpenMayaUI as omUI
from PySide2 import QtCore, QtGui, QtWidgets
from shiboken2 import wrapInstance
# Qt Web stuff
from PySide2.QtCore import QUrl
try:
    from PySide2.QtWebEngineWidgets import QWebEngineView, QWebEnginePage  # Doesn't work with Maya 2017
except ImportError:
    from PySide2.QtWebKitWidgets import QWebView as QWebEngineView


try:
    basestring  # Python 2
except NameError:
    basestring = (str,)  # Python 3

try:
    long        # Python 2
except NameError:
    long = int  # Python 3

# LOGGING
logging.basicConfig()  # errors and everything else (2 separate log groups)
logger = logging.getLogger("coopQt")  # create a logger for this file
logger.setLevel(logging.DEBUG)  # defines the logging level (INFO for releases)


# STYLES
fontHeader = QtGui.QFont('MS Shell dlg 2', 15);
fontFooter = QtGui.QFont('MS Shell dlg 2', 8);
# button.setStyleSheet("background-color: rgb(0,210,255); color: rgb(0,0,0);")
# imagePath = cmds.internalVar(upd = True) + 'icons/background.png')
# button.setStyleSheet("background-image: url(" + imagePath + "); border:solid black 1px;")
# self.setStyleSheet("QLabel { color: rgb(50, 50, 50); font-size: 11px; background-color: rgba(188, 188, 188, 50); border: 1px solid rgba(188, 188, 188, 250); } QSpinBox { color: rgb(50, 50, 50); font-size: 11px; background-color: rgba(255, 188, 20, 50); }")


PPI = cmds.mayaDpiSetting(realScaleValue=True, q=True)

# WINDOW
def getMayaWindow():
    """
    Get the pointer to a maya window and wrap the instance as a QWidget
    Returns:
        Maya Window as a QWidget instance
    """
    ptr = omUI.MQtUtil.mainWindow()  # pointer to main window
    return wrapInstance(long(ptr), QtWidgets.QWidget)  # wrapper

def isWindowMinimized(window):
    """ Returns True if window is minimized """
    if cmds.window(window, exists=True, query=True):
        ptr = omUI.MQtUtil.findWindow(window)  # pointer to window
        qWindow = wrapInstance(long(ptr), QtWidgets.QWidget)  # wrapper
        return qWindow.windowState() == QtCore.Qt.WindowMinimized

def getDock(name=''):
    """
    Get pointer to a dock pane
    Args:
        name: Name of the dock

    Returns:
        ptr: pointer to the created dock
    """
    if not name:
        cmds.error("No name for dock was specified")
    deleteDock(name)
    # used to be called dockControl
    # ctrl = cmds.workspaceControl(name, dockToMainWindow=('left', True), label=name)
    ctrl = cmds.dockControl(name, con=name, area='left', label=name)
    qtCtrl = omUI.MQtUtil.findControl(ctrl)
    ptr = wrapInstance(long(qtCtrl), QtWidgets.QWidget)
    return ptr


def deleteDock(name=''):
    """
    Deletes a docked UI
    Args:
        name: Name of the dock to delete
    """
    if cmds.dockControl(name, query=True, exists=True):  # workspaceControl on 2017
        logger.debug("The dock should be deleted next")
        cmds.deleteUI(name)


def relativePath(path):
    """
    Returns the relative path, if any, compared to the project path
    Args:
        path (str): path of current file or directory
    Returns:
        relPath (str): relative path to project, if available (with forward slashes)
    """
    projectPath = os.path.abspath(cmds.workspace(q=True, rootDirectory=True))
    newPath = os.path.abspath(path)
    if projectPath in newPath:
        newPath = newPath[newPath.find(projectPath)+len(projectPath):]
        return newPath.replace(os.sep, '/')
    return path


class MayaUI(QtWidgets.QDialog):
    """
    DEPRECATED - USE CoopMayaUI instead
    Creates a QDialog and parents it to the main Maya window
    """
    def __init__(self, parent=getMayaWindow()):
        super(MayaUI, self).__init__(parent)


class CoopMayaUI(QtWidgets.QDialog):

    def __init__(self, title, dock=False, rebuild=False, brand="studio.coop", tooltip="", show=True, parent=getMayaWindow()):

        # check if parent is given, otherwise, get Maya
        if isinstance(parent, basestring):
            if cmds.window(parent, exists=True, query=True):
                ptr = omUI.MQtUtil.findWindow(parent)
                parent = wrapInstance(long(ptr), QtWidgets.QWidget)  # wrapper
            else:
                cmds.warning("No window with name {} was found, parenting to Maya window")
                parent = getMayaWindow()

        super(CoopMayaUI, self).__init__(parent)
        # check if window exists
        if cmds.window(title, exists=True):
            if not rebuild:
                cmds.showWindow(title)
                return
            cmds.deleteUI(title, wnd=True)  # delete old window

        # create window
        self.setWindowTitle(title)
        self.setObjectName(title)
        self.setWindowFlags(QtCore.Qt.Tool)  # always on top (multiplatform)
        self.dpiS = cmds.mayaDpiSetting(realScaleValue=True, q=True)
        """
        if cmds.about(mac=True):
            self.dpiS = 1
        else:
            self.dpiS = cmds.mayaDpiSetting(systemDpi=True, q=True)/96.0
        """

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

        headerMargin = 10 * self.dpiS
        self.header = QtWidgets.QLabel(title)
        self.header.setAlignment(QtCore.Qt.AlignHCenter)
        self.header.setFont(fontHeader)
        self.header.setContentsMargins(headerMargin, headerMargin, headerMargin, headerMargin)

        self.brand = QtWidgets.QLabel(brand)
        self.brand.setAlignment(QtCore.Qt.AlignHCenter)
        self.brand.setToolTip(tooltip)
        self.brand.setStyleSheet("background-color: rgb(40,40,40); color: rgb(180,180,180); border:solid black 1px;")
        self.brand.setFont(fontFooter)
        self.brand.setFixedHeight(15)

        self.buildUI()
        self.populateUI()
        if not dock and show:
            self.show()

        logger.debug("{0} was successfully generated".format(title))

    def populateUI(self):
        pass

    def buildUI(self):
        pass


def refreshUI(windowTitle, quiet=True):
    """
    Refresh the UI elements by deleting all widgets and rebuilding it
    Args:
        windowTitle (str): Title of the window to refresh
    """
    if cmds.window(windowTitle, exists=True):
        ptr = omUI.MQtUtil.findWindow(windowTitle)  # pointer to main window
        window = wrapInstance(long(ptr), QtWidgets.QWidget)  # wrapper
        mainLayout = window.layout()
        clearLayout(mainLayout)  # delete all widgets within main layout
        window.window().buildUI()
    else:
        if not quiet:
            logger.debug("{0} window doesn't exist".format(windowTitle))


def clearLayout(layout):
    """
    Delete all widgets within a layout
    Args:
        layout (str): layout to clear
    """
    # delete all widgets within main layout
    index = layout.count() - 1
    while index >= 0:
        widget = layout.itemAt(index).widget()
        widget.setParent(None)
        index -= 1


def getCoopIconPath():
    """
    Get the coop icon path
    Returns:
        iconPath (str): the coop icon path
    """
    iconPaths = mel.eval('getenv("XBMLANGPATH")')
    for iconPath in iconPaths.split(';'):
        if "coop/maya/icons" in iconPath:
            return iconPath


def labeledComboBox(label, options):
    """
    Creates and returns a labeled combobox
    Args:
        label (str): String containing label text
        options (lst): List of options to display in combo box e.g. ['.png', '.jpg', '.tif']

    Returns:
        labeledComboBox (QWidget): QWidget with the labeled combo box
    TODO:
        Convert to CLASS
    """
    w = QtWidgets.QWidget()
    wLayout = QtWidgets.QHBoxLayout()
    labelW = QtWidgets.QLabel(label)
    comboW = QtWidgets.QComboBox()
    comboW.addItems(options)
    wLayout.addWidget(labelW)
    wLayout.addWidget(comboW)
    w.setLayout(wLayout)
    return w


class IconButton(QtWidgets.QLabel):
    """
    Icon Button class object
    """
    clicked = QtCore.Signal(str)
    active = False

    def __init__(self, image, tooltip='', size=[25, 25], parent=None, bColor=(68, 68, 68), hColor=(200, 200, 200)):
        """
        Icon Button constructor
        Args:
            image (str): relative image path ("images/butIcon.png")
            tooltip (str): tooltip of button (default -> "")
            size {lst): List of unsigned integers -> size of button in pixels (default -> [25, 25])
            parent (QWidget): Parent widget (default -> None)
        """
        super(IconButton, self).__init__(parent)
        self.setFixedSize(size[0], size[1])
        self.setScaledContents(True)
        self.setToolTip(tooltip)
        self.setPixmap(image)
        self.bColor = bColor
        self.hColor = hColor
        self.setColors()

    def mouseReleaseEvent(self, event):
        self.toggle()
        self.clicked.emit("emit the signal")

    def changeIcon(self, image):
        self.setPixmap(image)

    def toggle(self):
        if not self.active:
            self.active = True
        else:
            self.active = False

    def setColors(self):
        styleSheet = "QLabel{background-color: rgb" + "{0}".format(self.bColor) + \
                     ";} QLabel:hover{background-color: rgb" + "{0}".format(self.hColor) + ";}"
        self.setStyleSheet(styleSheet)

    def setActiveColors(self):
        """ Sets an active background color """
        styleSheet = "QLabel{background-color: rgb" + "{0}".format(self.hColor) + \
                     ";} QLabel:hover{background-color: rgb" + "{0}".format(self.hColor) + ";}"
        self.setStyleSheet(styleSheet)


class HLine(QtWidgets.QFrame):
    """
    Horizontal line class object
    """
    def __init__(self, width=0, height=5*PPI):
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
        self.slideBack(time.time()+0.05)

    def relValue(self):
        """
        Get the relative value
        Returns:
            (int): relative value
        """
        relValue = self.value() - self.prevValue
        self.prevValue = self.value()
        return relValue

    def slideBack(self, endTime):
        self.blockSignals(True)
        if time.time() < endTime:
            self.setValue(self.value() * 0.9)
            threading.Timer(0.01, self.slideBack, [endTime]).start()
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

    def __init__(self, label="", value=0.0, min=0.0, max=1.0):
        super(LabeledFieldSliderGroup, self).__init__()
        self.dpiS = cmds.mayaDpiSetting(realScaleValue=True, q=True)

        # create layout
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # create label
        l = QtWidgets.QLabel(label)
        l.setMinimumWidth(140 * self.dpiS)
        l.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.layout.addWidget(l)

        # create field
        self.field = QtWidgets.QDoubleSpinBox()
        self.field.setDecimals(3)
        self.field.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.field.setFixedWidth(60 * self.dpiS)
        self.field.setStyleSheet("border: 0; border-radius: {0}px".format(2 * self.dpiS))
        self.field.setAlignment(QtCore.Qt.AlignVCenter)
        self.field.setMinimum(-999999999)
        self.field.setMaximum(999999999)
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
        self.setRange(min, max)

        # set values
        self.field.setValue(value)
        self.slider.setValue(value * 1000)  # sliders only operate on integers
        self.internalValue = value

        # create connections
        self.slider.valueChanged.connect(self.updateValue)
        self.field.valueChanged.connect(self.updateValue)


    def setRange(self, min='', max=''):
        """
        Sets the range of the slider to min and max
        Args:
            min (float): Minimum value of slider
            max (float): Maximum value of slider
        """
        import numbers
        if isinstance(min, numbers.Number):
            if isinstance(max, numbers.Number):
                if min < max:
                    self.min = min
                else:
                    logger.warning("Minimum value is not less than maximum value")
            else:
                if min < self.max:
                    self.min = min
                else:
                    logger.warning("Minimum value is not less than maximum value")
            self.slider.setMinimum(self.min * 1000)
        if isinstance(max, numbers.Number):
            if max > self.min:
                self.max = max
            else:
                logger.warning("Maximum value is not more than minimum value")
            self.slider.setMaximum(self.max * 1000)

    def updateValue(self):
        """ Update and synchronize the value between the spinbox and slider """
        if self.sender() == self.slider:
            value = self.sender().value() / 1000.0
            # print("{0} with value: {1}".format(self.sender().objectName(), value))
            self.field.setValue(value)
        if self.sender() == self.field:
            value = self.sender().value()
            # print("{0} with value: {1}".format(self.sender().objectName(), value))
            self.slider.blockSignals(True)
            # check if slider needs to be changed
            if value < self.min:
                self.setRange(value, self.max)
            if value > self.max:
                self.setRange(self.min, value)
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

    def __init__(self, filePath='', placeholder='', button='...', startDir=''):
        super(FileBrowserGrp, self).__init__()
        self.dpiS = cmds.mayaDpiSetting(realScaleValue=True, q=True)
        self.internalValue = filePath
        self.startDir = startDir
        if not startDir:
            self.startDir = cmds.workspace(q=True, rootDirectory=True)

        # create layout
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(2 * self.dpiS)

        # create line edit
        self.lineEdit = QtWidgets.QLineEdit(filePath)
        self.lineEdit.setPlaceholderText(placeholder)
        self.lineEdit.returnPressed.connect(self.updatePath)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(1)
        self.lineEdit.setSizePolicy(sizePolicy)

        self.layout.addWidget(self.lineEdit)
        self.layout.addStretch()

        # create browse button
        pushButton = QtWidgets.QPushButton(button)
        pushButton.setMaximumWidth(len(str(button))*10*self.dpiS)
        pushButton.released.connect(self.browseDialog)
        self.layout.addWidget(pushButton)
        self.layout.addStretch()

    def browseDialog(self):
        """ Runs when the file browse button is released """
        startDir = self.lineEdit.text()
        if not startDir:
            # get project filepath
            startDir = self.startDir
        elif startDir[0] == '/':
            # relative path, make absolute
            startDir = os.path.join(self.startDir, startDir[1:])
        saveDir = cmds.fileDialog2(dir=startDir, fileMode=1, cap="Select texture file:", dialogStyle=2)
        if not saveDir:
            cmds.error("Filename not specified")
            return
        saveDir = relativePath(saveDir[0])
        self.internalValue = saveDir
        self.lineEdit.setText(saveDir)
        self.valueChanged.emit()

    def updatePath(self):
        """ Runs when the line edit field is updated """
        self.internalValue = self.lineEdit.text()
        self.valueChanged.emit()

    def value(self):
        """
        Get the internal value of the FileBrowserGrp
        Returns:
            str: the current path to a file
        """
        return self.internalValue


class WidgetGroup(QtWidgets.QWidget):
    """
    Simple widget group class object with embedded layout and batch widget assignment
    """

    def __init__(self, qWidgets=[], qLayout=None, parent=None, margins=0):
        """
        Widget Group constructor
        Args:
            qWidgets (lst): List of QWidgets to group (default -> [])
            qLayout: QtWidgets Layout object -> layout of group (default -> QtWidgets.QVBoxLayout())
            parent: QtWidgets object -> parent QtWidgets object (default -> None)
        """
        super(WidgetGroup, self).__init__(parent)
        if not qLayout:
            qLayout = QtWidgets.QVBoxLayout()
        self.groupLayout = qLayout
        self.setLayout(self.groupLayout)
        self.groupLayout.setContentsMargins(margins, margins, margins, margins)
        self.addWidgets(qWidgets)

    def addWidget(self, widget):
        """
        Add a single widget to the group
        Args:
            widget (QWidget): Widget to be added
        """
        self.groupLayout.addWidget(widget)

    def addWidget(self, widget, row, column):
        """
        Add a single widget into (row, column) of the group (has to be a QGridLayout)
        Args:
            widget (QWidget): Widget to be added
            row (int): row to insert into
            column (int): column to insert into
        """
        self.groupLayout.addWidget(widget, row, column)

    def addWidgets(self, widgets):
        """
        Adds a list of widgets to the group
        Args:
            widgets (lst): List of QWidgets to be added
        """
        for widget in widgets:
            if widget == "stretch":
                self.groupLayout.addStretch()
            else:
                self.groupLayout.addWidget(widget)


class CollapsibleGrp(QtWidgets.QWidget):
    """
    Create a collapsible group similar to what you can find in the attribute editor
    """
    def __init__(self, title=''):
        super(CollapsibleGrp, self).__init__()
        self.dpiS = cmds.mayaDpiSetting(realScaleValue=True, q=True)
        self.title = title

        # create layout
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        # self.layout.setSpacing(2 * self.dpiS)

        # create toggle button
        self.toggleButton = QtWidgets.QPushButton(u'  \u25BC    ' + self.title)
        self.toggleButton.setObjectName("toggler")
        self.setStyleSheet('QPushButton#toggler {'
                           'text-align: left;'
                           'font-weight: bold;'
                           'background-color: #5d5d5d;'
                           'padding: 0.3em;'
                           'border-radius: 0.2em;}')
        self.toggleButton.released.connect(self.toggleContent)
        self.layout.addWidget(self.toggleButton)

        # content widget
        self.content = QtWidgets.QGroupBox()
        self.contentLayout = QtWidgets.QVBoxLayout(self.content)
        self.layout.addWidget(self.content)

    def addWidget(self, widget):
        """ Adds a widget to the content of the collapsible group """
        self.contentLayout.addWidget(widget)

    def toggleContent(self):
        """ Toggles the content of the collapsible group """
        if self.content.isVisible():
            self.content.setVisible(False)
            self.toggleButton.setText(u'  \u25B6    ' + self.title)
        else:
            self.content.setVisible(True)
            self.toggleButton.setText(u'  \u25BC    ' + self.title)


class SplashView(QWebEngineView):
    """ SplashView is a QWebEngineView that opens links in a browser instead of in the QWebEngineView"""
    def __init__(self, *args, **kwargs):
        QWebEngineView.__init__(self, *args, **kwargs)
        self.setPage(WebEnginePage(self))


class WebEnginePage(QWebEnginePage):
    def acceptNavigationRequest(self, url,  _type, isMainFrame):
        if _type == QWebEnginePage.NavigationTypeLinkClicked:
            print("Opening: {}".format(url.toString()))
            QtGui.QDesktopServices.openUrl(url)
            return False
        return True


class ProgressDialog(QtWidgets.QProgressDialog):
    """ Simple progress dialog """
    def __init__(self, parent, window_title):
        super(ProgressDialog, self).__init__(parent)
        self.setWindowModality(QtCore.Qt.WindowModal)
        self.setWindowTitle(window_title)
        self.setMinimumWidth(600)
        self.setAutoClose(True)
        self.setAutoReset(True)
        self.setRange(0, 100)
        self.floatValue = 0
        self.setValue(int(self.floatValue))
        self.show()
        processEvents()

    def add(self, v, item):
        if self.wasCanceled():
            return False
        self.floatValue += v
        self.setValue(int(self.floatValue))
        self.setLabelText("Processing {}".format(item))
        processEvents()
        return True

def processEvents():
    """ Processes all queued Qt events """
    QtCore.QCoreApplication.processEvents()
