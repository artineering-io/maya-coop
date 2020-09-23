"""
@license:       MIT
@repository:    https://github.com/artineering-io/maya-coop
#                         ____       _               
#     ___ ___   ___  _ __/ ___|  ___| |_ _   _ _ __  
#    / __/ _ \ / _ \| '_ \___ \ / _ \ __| | | | '_ \ 
#   | (_| (_) | (_) | |_) |__) |  __/ |_| |_| | |_) |
#    \___\___/ \___/| .__/____/ \___|\__|\__,_| .__/ 
#                   |_|                       |_|    
@summary:       This file installs plugins by adding file directories into the Maya.env file
@run:           Drag and drop the install.mel file which runs coopSetup
"""
from __future__ import print_function
import os, shutil, urllib, pprint
import maya.cmds as cmds
import maya.mel as mel
import coopLib as lib


# SETTLE OS DEPENDENT CASES
localOS = lib.localOS()
sep = ':'         # separator
if localOS == "win":
    sep = ';'


def run(root):
    """
    Insert system paths in the Maya.env
    Args:
        root: root directory of the plugin hierarchy
    """
    print("-> Installing plugin")
    variables = {'MAYA_MODULE_PATH': [os.path.abspath(root)]}

    # get Maya.env file
    mayaEnvFilePath = cmds.about(env=True, q=True)
    # check if Maya env exists (some users have reported that the Maya.env file did not exist in their environment dir)
    if not os.path.isfile(mayaEnvFilePath):
        tempFileDir = os.path.join(os.path.dirname(mayaEnvFilePath), "Maya.env")
        with open(tempFileDir, 'ab') as tmp:
            tmp.write("")

    # get Maya environment variables
    envVariables, envVariablesOrder, envCleanup = getEnvironmentVariables(mayaEnvFilePath)
    print("ENVIRONMENT VARIABLES:")
    pprint.pprint(envVariables)

    # merge environment variables
    envVariables = mergeVariables(variables, envVariables)
    print("MODIFIED VARIABLES:")
    pprint.pprint(envVariables)

    # write environment variables
    tempFilePath = os.path.join(os.path.dirname(mayaEnvFilePath), "maya.tmp")
    writeVariables(tempFilePath, envVariables, envVariablesOrder)

    # replace environment file
    shutil.move(tempFilePath, mayaEnvFilePath)

    lib.printInfo("-> Installation complete")

    # restart maya (we make sure everything will load correctly once maya is restarted)
    cmds.confirmDialog(title='Restart Maya',
                       message='Installation successful!\nPlease restart Maya to make sure everything loads correctly',
                       icn='information', button='OK', ma='center')


def getEnvironmentVariables(mayaEnvFilePath):
    """
    Get the environment variables found at the Maya.env file
    Args:
        mayaEnvFilePath (str): Path of the Maya.env file
    Returns:
        envVariables (dict)
        envVariablesOrder (list)
        envCleanup (bool)
    """
    # read Maya environment variables
    envVariables = dict()
    envVariablesOrder = []
    envCleanup = False
    with open(mayaEnvFilePath, 'rb') as f:
        for line in f:
            # get rid of new line chars
            line = line.replace("\n", "")
            line = line.replace("\r", "")

            # separate into variable and value
            breakdown = line.split('=')
            if len(breakdown) == 1:
                # no equal sign was used
                breakdown = line.split(' ')  # get rid of empty spaces at the beginning and end of the string
                breakdown = filter(None, breakdown)  # get rid of empty string list elements
            if len(breakdown) != 2:
                if not breakdown:
                    cmds.warning("Empty line found in Maya.env file, skipping line")
                    envCleanup = True  # need to cleanup the environment file, as Maya doesn't support empty lines
                    continue
                else:
                    cmds.warning("Your Maya.env file has unrecognizable variables:\n{0}".format(breakdown))
                    continue

            # get values of variable
            vals = breakdown[1].split(sep)
            vals = filter(None, vals)
            values = list()
            for val in vals:
                try:
                    val = int(val)
                    values.append(val)
                except ValueError:
                    # string value
                    values.append(val.strip(' '))
            # get variable name and save
            varName = breakdown[0].strip(' ')
            envVariables[varName] = values
            envVariablesOrder.append(varName)

    return envVariables, envVariablesOrder, envCleanup


def mergeVariables(variables, envVariables):
    """
    Merge new variables with existing environment variables
    Args:
        variables (dict): variables to merge
        envVariables (dict): existing environment variables
    Returns:
        envVariables (dict)
    """
    print("")
    for var in variables:
        if var not in envVariables:
            # no variable existed, add
            envVariables[var] = variables[var]
        else:
            # variable already existed
            for varValue in variables[var]:
                # for each variable value to add
                if varValue in envVariables[var]:
                    print("{0}={1} is already set as an environment variable.".format(var, varValue))
                else:
                    # variable did not exist, insert in front
                    envVariables[var].insert(0, varValue)
                    # (optional) check for clashes of files with other variables
    print("Variables successfully updated.\n")
    return envVariables


def writeVariables(filePath, variables, sortedVariables):
    """
    Write environment variables to file path
    Args:
        filePath (str): path to save variables to
        variables (dict): environment variables to save
    """
    with open(filePath, 'ab') as tmp:
        # the shelf environment variable must be the first
        shelfVariable = "MAYA_SHELF_PATH"
        if shelfVariable in variables:
            # make sure that we are not saving an empty variable
            if variables[shelfVariable]:
                if shelfVariable in sortedVariables:
                    sortedVariables.remove(shelfVariable)
                outLine = "{0}=".format(shelfVariable)
                for v in variables.pop(shelfVariable, None):
                    outLine += "{0}{1}".format(v, sep)
                tmp.write(outLine + "\n")
        # add new variables in sortedVariables
        for var in variables:
            if var not in sortedVariables:
                sortedVariables.append(var)
        # write the variables in a sorted fashion
        for var in sortedVariables:
            # check if no sorted variables have been deleted
            if var in variables:
                # make sure that we are not saving an empty variable
                if variables[var]:
                    outLine = "{0}=".format(var)
                    for v in variables[var]:
                        outLine += "{0}{1}".format(v, sep)
                    tmp.write(outLine + "\n")
