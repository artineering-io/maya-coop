"""
@summary:       Module setup
@run:           Refer to setup_view
@license:       MIT
@repository:    https://github.com/artineering-io/maya-coop
"""
from __future__ import print_function
from __future__ import unicode_literals
import os, shutil, pprint, ctypes, sys
import maya.cmds as cmds
import maya.mel as mel
import lib as clib
import logger as clog

LOG = clog.logger("coop.setup")


def install(install_dir, all_users=False, maya_versions=None):
    """
    Install the module
    Args:
        install_dir (unicode): Root directory of the module file
        all_users (bool): If the installation should be for all users
        maya_versions (list): Maya versions to install onto
    """
    install_dir = clib.u_decode(install_dir)
    maya_versions = clib.u_enlist(maya_versions)
    if not all_users:
        LOG.info("-> Installing module for current user")
        new_variables = {'MAYA_MODULE_PATH': [os.path.abspath(install_dir)]}
        maya_env_path = _check_maya_env()

        # get and merge environment variables
        env_variables, env_variables_order = _parse_environment_variables(maya_env_path)
        _merge_variables(new_variables, env_variables, env_variables_order)

        # write environment variables
        temp_file_path = clib.Path(maya_env_path).parent().child("maya.tmp")
        _write_variables(temp_file_path.path, env_variables, env_variables_order)

        # replace environment file
        shutil.move(temp_file_path.path, maya_env_path)
    else:
        LOG.info("-> Installing module for all users")
        _install_all_users(install_dir, maya_versions)

    clib.display_info("-> Installation complete <-")
    _restart_dialog()


def uninstall(install_dir, module_name, reinstall=False):
    """
    Uninstalls the module
    Args:
        install_dir (unicode): Root directory of the module file
        module_name (unicode): Name of the module
        reinstall (bool): If uninstalling happens because of a re-install
    """
    if _is_installed_per_user(module_name):
        maya_env_path = _check_maya_env()
        env_variables, env_variables_order = _parse_environment_variables(maya_env_path)

        if "MAYA_MODULE_PATH" in env_variables:
            module_paths = list(env_variables["MAYA_MODULE_PATH"])
            for path in module_paths:
                if os.path.abspath(path) == os.path.abspath(install_dir):
                    env_variables["MAYA_MODULE_PATH"].remove(path)
                    break

        # write environment variables
        temp_file_path = clib.Path(maya_env_path).parent().child("maya.tmp")
        _write_variables(temp_file_path.path, env_variables, env_variables_order)

        # replace environment file
        shutil.move(temp_file_path.path, maya_env_path)
    elif not reinstall:
        t = "Heads-up"
        m = "Are you sure you wish to uninstall {} for ALL users?".format(module_name)
        reply = cmds.confirmDialog(title=t, message=m, button=['Yes', 'No'],
                                   defaultButton='Yes', cancelButton='No', dismissString='No', icn="warning")
        # don't do anything
        if reply == "No":
            LOG.info("Nothing will be uninstalled")
            return
        _uninstall_all_users(module_name)

    if not reinstall:
        clib.delete_shelves({"{}".format(module_name): "{}.mel".format(module_name)}, False)
        _restart_dialog()


def get_common_module_dir():
    """
    Get Maya's common module dir
    Returns:
        (unicode): Directory to common modules
    """
    module_dirs = mel.eval("getenv MAYA_MODULE_PATH;").split(clib.get_os_separator())
    for module_dir in module_dirs:
        if clib.get_local_os() == "win":
            if "Common Files" in module_dir:
                return clib.Path(module_dir).parent().path
        # TODO: Other OS
    return ""


def is_admin():
    """
    Returns true if script is run as admin
    Returns:
        (bool)
    """
    try:
        return os.getuid() == 0  # if Unix
    except AttributeError:
        return ctypes.windll.shell32.IsUserAnAdmin()  # if Windows


def _parse_environment_variables(maya_env_path):
    """
    Get the environment variables found in the Maya.env file
    Args:
        maya_env_path (unicode): Path of the Maya.env file
    Returns:
        env_variables (dict): dictionary with environment variables
        env_variables_order (list): list with the existing order of variables
    """
    # read Maya environment variables
    env_variables = dict()
    env_variables_order = []
    with open(maya_env_path, mode='r') as f:
        for line in f:
            # get rid of new line chars
            line = line.replace("\n", "").replace("\r", "")

            # separate into variable and value
            breakdown = line.split('=')
            if len(breakdown) == 1:  # no equal sign could be used
                breakdown = line.split(' ')  # split by empty spaces
                breakdown = list(filter(None, breakdown))  # get rid of empty string list elements
            if len(breakdown) != 2:
                if not breakdown:
                    cmds.warning("Empty line found in Maya.env file, skipping line")
                else:
                    cmds.warning("Maya.env file has unrecognizable variables:\n{0}".format(breakdown))
                continue

            # get values of variable
            values = breakdown[1].split(clib.get_os_separator())
            values = list(filter(None, values))
            stored_values = list()
            for val in values:
                try:
                    val = int(val)
                    stored_values.append(val)
                except ValueError:
                    stored_values.append(val.strip(' '))  # string value

            # get variable name and save
            var_name = breakdown[0].strip(' ')
            env_variables[var_name] = stored_values
            env_variables_order.append(var_name)

    LOG.debug("USER ENVIRONMENT VARIABLES:")
    pprint.pprint(env_variables)
    print("")
    return env_variables, env_variables_order


def _merge_variables(new_variables, env_variables, env_variables_order):
    """
    Merge new variables with existing environment variables
    Args:
        new_variables (dict): Variables to merge
        env_variables (dict): Existing environment variables
        env_variables_order (list): Order of environment variables
    Returns:
        env_variables (dict)
    """
    for var in new_variables:
        if var not in env_variables:
            # no variable existed, add
            env_variables[var] = new_variables[var]
            env_variables_order.append(var)
        else:
            # variable already existed
            for var_value in new_variables[var]:
                # for each variable value to add
                if var_value in env_variables[var]:
                    print("{0}={1} is already set as an environment variable.".format(var, var_value))
                else:
                    # variable did not exist, insert in front
                    env_variables[var].insert(0, var_value)
                    # (optional) check for clashes of files with other variables

    LOG.debug("MERGED VARIABLES:")
    pprint.pprint(env_variables)
    print("")  # new line


def _write_variables(file_path, variables, variables_order):
    """
    Write environment variables to file path
    Args:
        file_path (unicode): Path to save variables to
        variables (dict): Environment variables to save
        variables_order (list): List of environment variables in the right order
    """

    def format_variable(variable, values):
        line = "{}=".format(variable)
        for value in values:
            line += "{}{}".format(value, clib.get_os_separator())
        return line[0:-1] + "\n"

    with open(file_path, mode='a') as tmp:
        # the shelf environment variable must be the first
        shelf_variable = "MAYA_SHELF_PATH"
        if shelf_variable in variables:
            # make sure that we are not saving an empty variable
            if variables[shelf_variable]:
                if shelf_variable in variables_order:
                    variables_order.remove(shelf_variable)
                tmp.write(str(format_variable(shelf_variable, variables.pop(shelf_variable, []))))
        # write the variables in a sorted fashion
        for var in variables_order:
            # check if no sorted variables have been deleted
            if var in variables:
                # make sure that we are not saving an empty variable
                if variables[var]:
                    tmp.write(str(format_variable(var, variables[var])))


def _install_all_users(install_dir, maya_versions):
    """
    Installs modules at install_dir for all users
    Args:
        install_dir (unicode): Directory where the .mod files are
        maya_versions (list): List of Maya versions to install modules in
    """
    install_dir = clib.Path(install_dir)
    modules = [module for module in install_dir.list_dir() if module.endswith(".mod")]

    # create temporary .mod files
    new_modules = []
    for module in modules:
        old_path = clib.Path(install_dir.path).child(module)
        temp_path = clib.Path(install_dir.path).child("{}_temp".format(module))
        modified_module = ""
        with open(old_path.path, 'r') as mod_file:
            for line in mod_file:
                modified_module += line.replace('./', install_dir.slash_path())
        with open(temp_path.path, 'w') as new_mod_file:
            new_mod_file.write(str(modified_module))
        new_modules.append(temp_path.path)

    if is_admin():
        py_cmd = _py_cmd_install_all_users(maya_versions, new_modules)
        eval(py_cmd)
    elif clib.get_local_os() == "win":
        py_cmd = _py_cmd_install_all_users(maya_versions, new_modules, close=True)
        import subprocess
        mayapy = clib.Path(sys.executable).parent().child("mayapy.exe").path
        ctypes.windll.shell32.ShellExecuteW(None, "runas", mayapy,
                                            subprocess.list2cmdline([str("-i"), str("-c"), py_cmd]), None, 1)
    else:
        # TODO: MacOS and Linux versions
        clib.print_error("OS ({}) is not supported yet".format(clib.get_local_os()), True)

    LOG.info("Installation finished")


def _uninstall_all_users(module_name):
    """
    Uninstalls module for all users
    Args:
        module_name (unicode): Name of the module to uninstall
    """
    module_dir = get_common_module_dir()
    modules = clib.Path(module_dir).find_all("{}.mod".format(module_name), relative=False)
    if is_admin():
        py_cmd = _py_cmd_uninstall_all_users(modules)
        eval(py_cmd)
    else:
        py_cmd = _py_cmd_uninstall_all_users(modules, close=True)
        import subprocess
        mayapy = clib.Path(sys.executable).parent().child("mayapy.exe").path
        ctypes.windll.shell32.ShellExecuteW(None, "runas", mayapy,
                                            subprocess.list2cmdline([str("-i"), str("-c"), py_cmd]), None, 1)


def _py_cmd_install_all_users(maya_versions, modules, close=False):
    """
    Creates the Python command to run with elevated permissions
    Args:
        maya_versions (list): List of Maya versions to install onto i.e., [2019, 2020]
        modules (list): List of module paths
        close (bool): If the application running this command should close
    Returns:
        (unicode): Python command
    """
    module_dir = get_common_module_dir()
    py_cmd = "import shutil; "
    for v in maya_versions:
        shared_module_dir = clib.Path(module_dir).child(v)
        if not shared_module_dir.exists():
            py_cmd += "import os; os.makedirs('{}'); ".format(shared_module_dir.slash_path())
        for module in modules:
            mod = clib.Path(module).slash_path()
            module_name = clib.Path(module).swap_extension(".mod").basename()
            shared_module_path = clib.Path(shared_module_dir.path).child(module_name).slash_path()
            py_cmd += "shutil.copyfile('{}', '{}'); ".format(mod, shared_module_path)
    py_cmd += "import os; "
    for temp in modules:
        py_cmd += "os.remove('{}'); ".format(temp)
    if close:
        py_cmd += "os.kill(os.getpid(), 9);"
    return py_cmd


def _py_cmd_uninstall_all_users(modules, close=False):
    """
    Creates the Python command to run with elevated permissions
    Args:
        modules (list): List of module file paths to delete
        close (bool): If the application running this command should close
    Returns:
        (unicode): Python command
    """
    py_cmd = "import os; "
    for module in modules:
        py_cmd += "os.remove('{}'); ".format(clib.Path(module).slash_path())
    if close:
        py_cmd += "import os; os.kill(os.getpid(), 9);"
    return py_cmd


def _check_maya_env():
    """
    Checks that the Maya.env file exists in the user directory
    Note: some users have reported that the Maya.env file did not exist in their user environment dir

    Returns:
        (unicode): Path to the Maya.env file
    """
    maya_env_path = clib.Path(cmds.about(env=True, q=True))
    if not maya_env_path.exists():
        with open(maya_env_path.path, 'ab') as tmp:
            tmp.write(str(""))
    return maya_env_path.path


def _restart_dialog():
    """ A Restart dialog to fully load the installed module """
    cmds.confirmDialog(title='Restart Maya',
                       message='Installation successful!\nPlease restart Maya to make sure everything loads correctly',
                       icn='information', button='OK', ma='center')


def _is_installed_per_user(module_name):
    """
    Checks if the module is installed per user or all users
    Args:
        module_name (unicode): Name of the module to check
    Returns:
        (bool): If the module is installed per user
    """
    installed_path = clib.Path(clib.get_module_path(module_name)).slash_path()
    module_paths = mel.eval("getenv MAYA_MODULE_PATH;").split(clib.get_os_separator())
    for path in module_paths:
        if clib.Path(path).slash_path() == installed_path:
            return True
    return False
