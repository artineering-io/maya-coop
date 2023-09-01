"""
@summary:       Module setup
@run:           Refer to setup_view
@license:       MIT
@repository:    https://github.com/artineering-io/maya-coop
"""
from __future__ import print_function
from __future__ import unicode_literals
import os, shutil, pprint

import maya.cmds as cmds
import maya.mel as mel
from . import lib as clib
from . import logger as clog
from . import shelves as cshelf

LOG = clog.logger("coop.setup")


def install(install_dir, all_users=False, maya_versions=None, env_variables=None, custom_install_func=None):
    """
    Install the module
    Args:
        install_dir (unicode): Root directory of the module file
        all_users (bool): If the installation should be for all users
        maya_versions (list): Maya versions to install onto
        env_variables (dict): Additional environment variables to inject to Maya.env
        custom_install_func (function): Custom partial install function to run
    """
    install_dir = clib.u_decode(install_dir)
    maya_versions = clib.u_enlist(maya_versions)
    if not all_users:
        LOG.info("-> Installing module for current user")
        _install_local(install_dir, env_variables)
    else:
        LOG.info("-> Installing module for all users")
        _install_all_users(install_dir, maya_versions)

    if custom_install_func:
        custom_install_func()

    clib.display_info("-> Installation complete <-")
    _restart_dialog()


def uninstall(install_dir, module_name, reinstall=False, shelves=None, background=False, env_vars_to_delete=None,
              custom_uninstall_func=None):
    """
    Uninstalls the module
    Args:
        install_dir (unicode): Root directory of the module file
        module_name (unicode): Name of the module
        reinstall (bool): If uninstalling happens because of a re-install
        shelves (unicode, list): Shelves to uninstall
        background (bool): If uninstalling should happen in the background (without user prompts)
        env_vars_to_delete (dict): Additional environment variables to delete from Maya.env
        custom_uninstall_func (function): Custom partial uninstall function to run
    """
    if is_installed_per_user(module_name):
        maya_env_path = _check_maya_env()
        env_variables, env_variables_order = _parse_environment_variables(maya_env_path)

        # delete environment variables
        if env_vars_to_delete is None:
            env_vars_to_delete = dict()
        if "MAYA_MODULE_PATH" in env_vars_to_delete:
            env_vars_to_delete["MAYA_MODULE_PATH"].append(install_dir)
        else:
            env_vars_to_delete["MAYA_MODULE_PATH"] = [install_dir]
        _delete_maya_env_vars(env_variables, env_vars_to_delete)

        LOG.debug("CLEANED VARIABLES:")
        pprint.pprint(env_variables)

        # write environment variables
        temp_file_path = clib.Path(maya_env_path).parent().child("maya.tmp")
        _write_variables(temp_file_path.path, env_variables, env_variables_order)

        # replace environment file
        shutil.move(temp_file_path.path, maya_env_path)
    elif not reinstall and not background:
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
        if shelves:
            cshelf.delete_shelves(shelves, False)
        if not background:
            _restart_dialog()

    if custom_uninstall_func:
        custom_uninstall_func()

    clib.print_info("{} successfully uninstalled".format(module_name.title()))


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
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()  # if Windows


def is_installed_per_user(module_name):
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


def _fmt_variables(env_variables):
    """
    Formats environment variables
    Args:
        env_variables (dict): Additional environment variables to inject into Maya.env
    Returns:
        (dict): Dictionary of formatted environment variables
    """
    new_variables = {}
    if env_variables:
        for var in env_variables:
            values = []
            for val in env_variables[var]:
                values.append(os.path.abspath(val))
            new_variables[var] = values
    return new_variables


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


def _install_local(install_dir, env_variables):
    """
    Installs module at install_dir for current local user.
    Local installations adds the module path to the Maya.env file, together with
    any other env_variables
    Args:
        install_dir (unicode): Directory where the .mod files are
        env_variables (dict): Additional environment variables to inject into Maya.env
    """
    # adding module to environment variables
    if 'MAYA_MODULE_PATH' in env_variables:
        env_variables['MAYA_MODULE_PATH'].append(install_dir)
    else:
        env_variables['MAYA_MODULE_PATH'] = [install_dir]

    new_variables = _fmt_variables(env_variables)
    maya_env_path = _check_maya_env()

    # get and merge environment variables
    env_variables, env_variables_order = _parse_environment_variables(maya_env_path)
    _merge_variables(new_variables, env_variables, env_variables_order)

    # write environment variables
    temp_file_path = clib.Path(maya_env_path).parent().child("maya.tmp")
    _write_variables(temp_file_path.path, env_variables, env_variables_order)

    # replace environment file
    shutil.move(temp_file_path.path, maya_env_path)


def _install_all_users(install_dir, maya_versions):
    """
    Installs modules from install_dir for all users in:
    Windows: C:/Program Files/Common Files/Autodesk Shared/Modules/maya
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

    # paste module files with elevated priviledges
    py_cmd = _py_cmd_install_all_users(maya_versions, new_modules)
    print(py_cmd)
    if is_admin():
        eval(py_cmd)
    elif clib.get_local_os() == "win":
        clib.run_python_as_admin(py_cmd, close=True)
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
    if not modules:  # in case module mod file is lowercase
        modules = clib.Path(module_dir).find_all("{}.mod".format(module_name.lower()), relative=False)
    py_cmd = _py_cmd_uninstall_all_users(modules)
    if is_admin():
        eval(py_cmd)
    else:
        clib.run_python_as_admin(py_cmd, close=True)


def _py_cmd_install_all_users(maya_versions, modules):
    """
    Creates the Python command to run with elevated permissions
    Args:
        maya_versions (list): List of Maya versions to install onto i.e., [2019, 2020]
        modules (list): List of module paths
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
        py_cmd += "os.remove('{}'); ".format(clib.Path(temp).slash_path())
    return py_cmd


def _py_cmd_uninstall_all_users(modules):
    """
    Creates the Python command to run with elevated permissions
    Args:
        modules (list): List of module file paths to delete
    Returns:
        (unicode): Python command
    """
    py_cmd = "import os; "
    for module in modules:
        py_cmd += "os.remove('{}'); ".format(clib.Path(module).slash_path())
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


def _delete_maya_env_vars(env_variables, env_vars_to_delete):
    """
    Delete environment variables from dictionary if they exist
    Args:
        env_variables (dict): Dictionary of environment variables
        env_vars_to_delete (dict): Dictionary of environment variables to delete
    """
    if not env_vars_to_delete:
        return

    for var_to_delete in env_vars_to_delete:
        if var_to_delete not in env_variables:
            continue
        var_paths_to_delete = list(env_vars_to_delete[var_to_delete])
        var_paths = list(env_variables[var_to_delete])
        for path_to_delete in var_paths_to_delete:
            for path in var_paths:
                if os.path.abspath(path_to_delete) == os.path.abspath(path):
                    env_variables[var_to_delete].remove(path)
                    break


def _restart_dialog():
    """ A Restart dialog to fully load the installed module """
    cmds.confirmDialog(title='Restart Maya',
                       message='Changes were successful!\nPlease restart Maya to make sure everything loads correctly',
                       icn='information', button='OK', ma='center')
