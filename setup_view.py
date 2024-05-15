"""
@summary:       Module setup view
@run:           SetupUI(title, module, root_dir, brand, supported_os, rebuild=True)
@license:       MIT
@repository:    https://github.com/artineering-io/maya-coop
"""
from __future__ import print_function
from __future__ import unicode_literals
try:
    from PySide6 import QtWidgets, QtGui, QtCore
except ImportError:
    from PySide2 import QtWidgets, QtGui, QtCore
from . import lib as clib
from . import qt as cqt
from . import setup
from . import logger as clog
LOG = clog.logger("coop.setup_view")


class SetupUI(cqt.CoopMayaUI):
    """ Cross platform plugin setup """

    def __init__(self, title, module_name="", install_dir="", brand="Coop Installer",
                 supported_os=None, supported_maya_versions=None, env_variables=None, custom_install_func=None,
                 custom_uninstall_func=None, license_path="", rebuild=True):
        self.module_name = module_name
        self.module_path = clib.get_module_path(module_name)
        self.install_dir = install_dir
        self.supported_os = supported_os or ["win", "mac", "linux"]
        self.supported_maya_versions = supported_maya_versions or [clib.get_maya_version()]
        self.reinstall = False
        self.env_variables = env_variables
        self.custom_install_func = custom_install_func
        self.custom_uninstall_func = custom_uninstall_func
        self.license_path = clib.Path(license_path)
        self.license_deletion_checked = False

        self.options = ["Uninstall", "Install", "Install for all"]

        super(SetupUI, self).__init__(title, center=True, rebuild=rebuild, brand=brand, show=False)
        self.layout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
        self.brand.setMinimumWidth(600)

    def buildUI(self):
        """ This method builds the UI """
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

        # right pane (content)
        content_box = QtWidgets.QGroupBox("")
        self.content_layout = QtWidgets.QVBoxLayout(content_box)
        self.content_layout.setSpacing(2*self.dpi)
        setup_layout.addWidget(content_box, stretch=1)

        self.layout.addWidget(self.brand)

    def populateUI(self):
        if clib.get_local_os() not in self.supported_os:
            return self.unsupported_os()

        self.install_options_grp = QtWidgets.QButtonGroup()
        self.install_txt = "Install"

        # populate options
        if self.module_path:
            self.uninstall_option()
        self.install_options()

        dialog_buttons = QtWidgets.QDialogButtonBox()
        dialog_buttons.setOrientation(QtCore.Qt.Horizontal)
        dialog_buttons.addButton("Cancel", QtWidgets.QDialogButtonBox.RejectRole)
        dialog_buttons.addButton("Accept", QtWidgets.QDialogButtonBox.AcceptRole)
        dialog_buttons.accepted.connect(self.process)
        dialog_buttons.rejected.connect(self.reject)
        self.content_layout.addWidget(dialog_buttons)

    def unsupported_os(self):
        self.content_layout.setAlignment(QtCore.Qt.AlignCenter)
        not_supported_lbl = QtWidgets.QLabel("{} doesn't work on this operating system.".format(self.module_name))
        not_supported_lbl.setStyleSheet("font-weight: bold; color: #ff5b5b")
        self.content_layout.addWidget(not_supported_lbl)
        self.layout.addWidget(self.brand)

    def uninstall_option(self):
        """ Populates the uninstallation option """
        installed_lbl = QtWidgets.QLabel("{} already installed in {}".format(self.module_name, self.module_path))
        installed_lbl.setStyleSheet("font-weight: bold; color: #E6E2AC;")
        self.content_layout.addWidget(installed_lbl)
        uninstall_rad = QtWidgets.QRadioButton("Uninstall {}".format(self.module_name))
        self.install_options_grp.addButton(uninstall_rad, 0)
        self.install_options_grp.buttonReleased.connect(self.install_method_changed)
        self.content_layout.addWidget(uninstall_rad)

        self.delete_everything_cbox = QtWidgets.QCheckBox("Delete everything {}-related".format(self.module_name))
        self.delete_everything_cbox.setStyleSheet("margin-left: {}px;".format(20 * self.dpi))
        self.delete_everything_cbox.stateChanged.connect(self.delete_everything_changed)
        self.content_layout.addWidget(self.delete_everything_cbox)
        self.delete_everything_cbox.hide()

        self.content_layout.addWidget(cqt.HLine(height=15*self.dpi))
        self.install_txt = "Re-install"
        self.reinstall = True

    def install_options(self):
        """ Populates the installation options """
        install_lbl = QtWidgets.QLabel("{} {} from {}".format(self.install_txt, self.module_name, self.install_dir))
        install_lbl.setStyleSheet("font-weight: bold; color: #add8e6")
        self.content_layout.addWidget(install_lbl)

        user_install_rad = QtWidgets.QRadioButton("Install only for me")
        user_install_rad.setChecked(True)
        user_install_rad.setToolTip("Local installation from current folder")
        self.install_options_grp.addButton(user_install_rad, 1)
        self.content_layout.addWidget(user_install_rad)

        self.all_users_install_rad = QtWidgets.QRadioButton("Install for all users")
        self.all_users_install_rad.setAccessibleName("Install for all users")
        self.all_users_install_rad.setToolTip("System-wide installation")
        self.install_options_grp.addButton(self.all_users_install_rad, 2)
        self.content_layout.addWidget(self.all_users_install_rad)

        self.delete_license_cbox = QtWidgets.QCheckBox("Delete existing license")
        delete_license_grp = cqt.WidgetGroup([cqt.HLine(height=15*self.dpi), self.delete_license_cbox])
        self.delete_license_cbox.setStyleSheet("font-weight: bold; color: #E6ACBB;")
        self.delete_license_cbox.released.connect(self.cache_license_choice)
        self.content_layout.addWidget(delete_license_grp)
        if not self.license_path.exists():
            delete_license_grp.hide()

    def process(self):
        """ Processes the selected options to install """
        delete_everything = self.delete_everything_cbox.isChecked()
        if self.delete_license_cbox.isChecked() or delete_everything:
            setup.delete_license(self.license_path)

        option = self.options[self.install_options_grp.checkedId()]
        if option == "Uninstall":
            LOG.info("Uninstalling {}".format(self.module_name))
            setup.uninstall(self.module_path, self.module_name, shelves=self.module_name, no_trace=delete_everything,
                            env_vars_to_delete=self.env_variables, custom_uninstall_func=self.custom_uninstall_func)
        elif option == "Install":
            LOG.info("Installing {} for current user".format(self.module_name))
            if self.reinstall:
                setup.uninstall(self.module_path, self.module_name, self.reinstall,
                                custom_uninstall_func=self.custom_uninstall_func)
            setup.install(self.install_dir, all_users=False, env_variables=self.env_variables,
                          custom_install_func=self.custom_install_func)
        else:
            setup.install(self.install_dir, all_users=True, maya_versions=self.supported_maya_versions,
                          custom_install_func=self.custom_install_func)
            LOG.info("Installing {} for all users".format(self.module_name))

        self.accept()

    def install_method_changed(self):
        """ Toggles the preferences for all user installations """
        option = self.options[self.install_options_grp.checkedId()]
        if option == "Uninstall":
            self.delete_everything_cbox.show()
            if self.delete_everything_cbox.isChecked():
                self.delete_license_cbox.setChecked(True)
        else:
            self.delete_everything_cbox.hide()
            self.delete_license_cbox.setChecked(self.license_deletion_checked)

    def cache_license_choice(self):
        """ Caches the user made decision regarding licensing """
        self.license_deletion_checked = self.delete_license_cbox.isChecked()

    def delete_everything_changed(self, state):
        """
        Enables/Disables the license deletion option
        """
        if state > 0:
            self.delete_license_cbox.setChecked(True)
        else:
            self.delete_license_cbox.setChecked(self.license_deletion_checked)