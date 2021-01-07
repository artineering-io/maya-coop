from __future__ import print_function
from __future__ import unicode_literals
from PySide2 import QtWidgets, QtCore, QtGui
import lib as clib
import qt as cqt
import setup


class SetupUI(cqt.CoopMayaUI):
    """ Cross platform plugin setup """

    def __init__(self, title, module_name="", install_dir="", brand="Coop Installer",
                 supported_os=None, rebuild=True):
        self.module_name = module_name
        self.module_path = clib.get_module_path(module_name)
        self.install_dir = install_dir
        self.reinstall = False

        self.supported_os = supported_os
        if self.supported_os is None:
            self.supported_os = ["win", "mac", "linux"]

        super(SetupUI, self).__init__(title, dock=False, rebuild=rebuild, brand=brand, show=False)

    def buildUI(self):
        """ This method builds the UI """

        # check supported OS
        if clib.get_local_os() not in self.supported_os:
            error_layout = QtWidgets.QVBoxLayout()
            error_layout.setAlignment(QtCore.Qt.AlignCenter)
            not_supported_lbl = QtWidgets.QLabel("{} doesn't work on this operating system.".format(self.module_name))
            not_supported_lbl.setStyleSheet("font-weight: bold; color: #ff5b5b")
            error_layout.addWidget(not_supported_lbl)
            self.layout.addLayout(error_layout)
            self.layout.addWidget(self.brand)
            self.resize(400, 150)
            return

        # main layout
        setup_layout = QtWidgets.QHBoxLayout(self)
        self.layout.addLayout(setup_layout)
        setup_layout.setContentsMargins(20, 20, 20, 20)

        # left pane
        img_label = QtWidgets.QLabel()
        icon_path = clib.Path(__file__).parent().child("icons/install.png")
        pixmap = QtGui.QPixmap(icon_path.path)
        img_label.setPixmap(pixmap)
        img_label.setScaledContents(True)
        img_label.setFixedSize(100, 90)
        img_label.setContentsMargins(0, 10, 20, 0)
        left_grp = cqt.WidgetGroup([img_label, "stretch"])
        setup_layout.addWidget(left_grp)

        # right pane
        method_box = QtWidgets.QGroupBox("Installation options")
        method_layout = QtWidgets.QVBoxLayout(method_box)
        setup_layout.addWidget(method_box)
        self.button_grp = QtWidgets.QButtonGroup()  # button group

        install_txt = "Install"

        # uninstall
        if self.module_path:
            installed_lbl = QtWidgets.QLabel("{} already installed in {}".format(self.module_name, self.module_path))
            installed_lbl.setStyleSheet("font-weight: bold; color: yellow")
            method_layout.addWidget(installed_lbl)
            uninstall_rad = QtWidgets.QRadioButton("Uninstall {}".format(self.module_name))
            self.button_grp.addButton(uninstall_rad, 0)
            method_layout.addWidget(uninstall_rad)
            method_layout.addWidget(cqt.HLine())
            install_txt = "Re-install"
            self.reinstall = True
            self.resize(600, 250)
        else:
            self.resize(600, 200)

        # install
        install_lbl = QtWidgets.QLabel("{} {} from {}".format(install_txt, self.module_name, self.install_dir))
        install_lbl.setStyleSheet("font-weight: bold; color: #add8e6")
        method_layout.addWidget(install_lbl)

        user_install_rad = QtWidgets.QRadioButton("Install only for me")
        user_install_rad.setChecked(True)
        self.button_grp.addButton(user_install_rad, 1)
        method_layout.addWidget(user_install_rad)

        all_users_install_rad = QtWidgets.QRadioButton("Install for all users")
        all_users_install_rad.setDisabled(True)
        self.button_grp.addButton(all_users_install_rad, 2)
        method_layout.addWidget(all_users_install_rad)

        dialog_buttons = QtWidgets.QDialogButtonBox()
        dialog_buttons.setOrientation(QtCore.Qt.Horizontal)
        dialog_buttons.addButton("Cancel", QtWidgets.QDialogButtonBox.RejectRole)
        dialog_buttons.addButton("Accept", QtWidgets.QDialogButtonBox.AcceptRole)
        dialog_buttons.accepted.connect(self.process)
        dialog_buttons.rejected.connect(self.reject)
        method_layout.addWidget(dialog_buttons)

        self.layout.addWidget(self.brand)

    def process(self):
        options = ["Uninstall", "Install", "Install for all"]
        option = options[self.button_grp.checkedId()]
        if option == "Uninstall":
            print("Uninstalling {}".format(self.module_name))
            setup.uninstall(self.module_path, self.module_name)
        elif option == "Install":
            print("Installing {} for current user".format(self.module_name))
            if self.reinstall:
                setup.uninstall(self.module_path, self.module_name, self.reinstall)
            setup.install(self.install_dir, all_users=False)
        else:
            print("Installing {} for all users".format(self.module_name))

        self.accept()