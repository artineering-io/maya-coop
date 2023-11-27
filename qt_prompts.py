"""
@summary:       Cooperative qt prompts library
@run:           import coop.qt_prompts as cqtp (suggested)
@license:       MIT
@repository:    https://github.com/artineering-io/maya-coop
"""
from __future__ import print_function
from PySide2 import QtCore, QtWidgets, QtGui
import coop.qt as cqt


class PromptUI(cqt.CoopMayaUI):
    """ Base class for UI prompts """
    windowTitle = "Basic Prompt"

    def __init__(self, window_title=windowTitle, message="", tooltip="", parent=""):
        self.windowTitle = window_title
        self.message = message
        self.tooltip = tooltip

        super(PromptUI, self).__init__(self.windowTitle, tooltip=self.tooltip, center=True, show=False, parent=parent)

    def buildUI(self):
        spacing = 10
        self.layout.setContentsMargins(spacing, spacing, spacing, spacing)
        self.layout.setSpacing(spacing)

        if self.message:
            message_label = QtWidgets.QLabel(self.message)
            self.layout.addWidget(message_label)

        self.create_connections()

    def sizeHint(self):
        return QtCore.QSize(800, 800)

    def create_connections(self):
        self.accepted.connect(self.on_accept)
        self.rejected.connect(self.on_reject)

    def on_reject(self):
        self.deleteLater()

    def on_accept(self):
        self.deleteLater()

    def keyPressEvent(self, key_event):
        """ Handles when enter is pressed when the dialog is used """
        if (key_event.key() == QtCore.Qt.Key_Enter) or key_event.key() == QtCore.Qt.Key_Return:
            self.accept()

    def showEvent(self, event):
        """ Activates the window upon showing it """
        self.activateWindow()


class PickerUI(PromptUI):
    """ UI class for the object picker """
    windowTitle = "Option Picker"
    options = []

    def __init__(self, options, message="", multi_select=False, parent=""):
        """
        Shows an option picker prompt asking for user input
        Args:
            options (list): List of options to pick from
            message (unicode): Message of the prompt
            multi_select (bool): If the option picker should allow multi-selection
            parent (QWidget): If the prompt has custom parenting
        """
        self.options = options
        self.multi_select = multi_select
        self.message = message

        super(PickerUI, self).__init__(self.windowTitle, self.message, tooltip="Option picker", parent=parent)

    def buildUI(self):
        super(PickerUI, self).buildUI()
        self.options_list = QtWidgets.QListWidget()
        if self.multi_select:
            self.options_list.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        else:
            self.options_list.itemDoubleClicked.connect(self.accept)
        self.layout.addWidget(self.options_list)

        self.select_btn = QtWidgets.QPushButton("Select")
        self.select_btn.clicked.connect(self.accept)
        self.layout.addWidget(self.select_btn)

        self.options_list.setFocus()

    def populateUI(self):
        idx = 0
        if not self.multi_select:
            row = self.options_list.currentRow()
            if row > 0:
                idx = row
        self.options_list.clear()
        self.options_list.addItems(self.options)
        if not self.multi_select:
            self.options_list.setCurrentRow(idx)

    def get_selection(self):
        """ Gets the selected rows in the option picker """
        indices = []
        sel_rows = self.options_list.selectionModel().selectedRows()
        for row in sel_rows:
            indices.append(row.row())
        return indices


class RenameUI(PromptUI):
    """ UI class for the object picker """
    windowTitle = "Rename Element"

    def __init__(self, message="", prev_name="", parent=""):
        """
        Shows a rename prompt asking for user input
        Args:
            message (unicode): Message of the rename prompt
            prev_name (unicode): Previous name
            parent (QWidget): If the prompt has custom parenting
        """
        self.message = message
        self.prev_name = prev_name

        super(RenameUI, self).__init__(self.windowTitle, self.message, tooltip="Rename element", parent=parent)

    def buildUI(self):
        super(RenameUI, self).buildUI()
        self.rename_edit = QtWidgets.QLineEdit(self.prev_name)
        self.rename_edit.returnPressed.connect(self.accept)
        self.layout.addWidget(self.rename_edit)

        rename_btn = QtWidgets.QPushButton("Rename")
        rename_btn.clicked.connect(self.accept)
        self.layout.addWidget(rename_btn)

        self.resize(200, 100)

        self.rename_edit.setFocus()

    def get_name(self):
        """ Gets the new name defined in the prompt """
        return self.rename_edit.text()