"""
@summary:       Module setup
@run:           Refer to setup_view
@license:       MIT
@repository:    https://github.com/artineering-io/maya-coop
"""
from __future__ import print_function
from __future__ import unicode_literals
import os, shutil, io, pprint
import maya.cmds as cmds
import coopLib as clib


# SETTLE OS DEPENDENT CASES
SEP = ':'         # separator
if clib.localOS() == "win":
    SEP = ';'


def install(install_dir, all_users=False):
    """
    Install the module
    Args:
        install_dir (unicode): Root directory of the module file
        all_users (bool): If the installation should be for all users
    """
    unicode_dir = install_dir.decode('unicode-escape')  # convert to unicode
    if not all_users:
        print("-> Installing module for current user")
        new_variables = {'MAYA_MODULE_PATH': [os.path.abspath(unicode_dir)]}
        maya_env_path = _check_maya_env()

        # get and merge environment variables
        env_variables, env_variables_order = parse_environment_variables(maya_env_path)
        merge_variables(new_variables, env_variables, env_variables_order)

        # write environment variables
        temp_file_path = clib.Path(maya_env_path).parent().child("maya.tmp")
        write_variables(temp_file_path.path, env_variables, env_variables_order)

        # replace environment file
        shutil.move(temp_file_path.path, maya_env_path)

    clib.displayInfo("-> Installation complete <-")
    _restart_dialog()


def uninstall(install_dir, module_name):
    """
    Uninstalls the module
    Args:
        install_dir (unicode): Root directory of the module file
        module_name (unicode): Name of the module
    """
    maya_env_path = _check_maya_env()
    env_variables, env_variables_order = parse_environment_variables(maya_env_path)

    if "MAYA_MODULE_PATH" in env_variables:
        module_paths = list(env_variables["MAYA_MODULE_PATH"])
        for path in module_paths:
            if os.path.abspath(path) == os.path.abspath(install_dir):
                env_variables["MAYA_MODULE_PATH"].remove(path)
                break

    # write environment variables
    temp_file_path = clib.Path(maya_env_path).parent().child("maya.tmp")
    write_variables(temp_file_path.path, env_variables, env_variables_order)

    # replace environment file
    shutil.move(temp_file_path.path, maya_env_path)

    # delete shelves
    clib.deleteShelves({"{}".format(module_name): "{}.mel".format(module_name)}, False)
    _restart_dialog()


def parse_environment_variables(maya_env_path):
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
    with io.open(maya_env_path, mode='r') as f:
        for line in f:
            # get rid of new line chars
            line = line.replace("\n", "").replace("\r", "")

            # separate into variable and value
            breakdown = line.split('=')
            if len(breakdown) == 1:  # no equal sign could be used
                breakdown = line.split(' ')  # split by empty spaces
                breakdown = filter(None, breakdown)  # get rid of empty string list elements
            if len(breakdown) != 2:
                if not breakdown:
                    cmds.warning("Empty line found in Maya.env file, skipping line")
                else:
                    cmds.warning("Maya.env file has unrecognizable variables:\n{0}".format(breakdown))
                continue

            # get values of variable
            values = breakdown[1].split(SEP)
            values = filter(None, values)
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

    print("USER ENVIRONMENT VARIABLES:")
    pprint.pprint(env_variables)
    print("")
    return env_variables, env_variables_order


def merge_variables(new_variables, env_variables, env_variables_order):
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

    print("MERGED VARIABLES:")
    pprint.pprint(env_variables)
    print("")  # new line


def write_variables(file_path, variables, variables_order):
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
            line += "{}{}".format(value, SEP)
        return line[0:-1] + "\n"

    with io.open(file_path, mode='a') as tmp:
        # the shelf environment variable must be the first
        shelf_variable = "MAYA_SHELF_PATH"
        if shelf_variable in variables:
            # make sure that we are not saving an empty variable
            if variables[shelf_variable]:
                if shelf_variable in variables_order:
                    variables_order.remove(shelf_variable)
                tmp.write(format_variable(shelf_variable, variables.pop(shelf_variable, [])))
        # write the variables in a sorted fashion
        for var in variables_order:
            # check if no sorted variables have been deleted
            if var in variables:
                # make sure that we are not saving an empty variable
                if variables[var]:
                    tmp.write(format_variable(var, variables[var]))


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
    cmds.confirmDialog(title='Restart Maya',
                       message='Installation successful!\nPlease restart Maya to make sure everything loads correctly',
                       icn='information', button='OK', ma='center')
