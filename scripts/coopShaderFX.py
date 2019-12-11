"""
@license:       MIT
@repository:    https://github.com/artineering-io/maya-coop
#                         ____  _               _           _______  __
#     ___ ___   ___  _ __/ ___|| |__   __ _  __| | ___ _ __|  ___\ \/ /
#    / __/ _ \ / _ \| '_ \___ \| '_ \ / _` |/ _` |/ _ \ '__| |_   \  / 
#   | (_| (_) | (_) | |_) |__) | | | | (_| | (_| |  __/ |  |  _|  /  \ 
#    \___\___/ \___/| .__/____/|_| |_|\__,_|\__,_|\___|_|  |_|   /_/\_\
#                   |_|                                                
@summary:       Maya cooperative ShaderFX library
@run:           import coopShaderFX as csfx (suggested)
"""
import logging
import maya.cmds as cmds

# LOGGING
logging.basicConfig()  # errors and everything else (2 separate log groups)
logger = logging.getLogger("coopShaderFX")  # create a logger for this file
logger.setLevel(logging.DEBUG)  # defines the logging level (INFO for releases)

def getId(material, uniqueNodeName, quiet=False):
    """
    Utility function to get the id of uniqueNodeName within a shaderFX material
    Args:
        material (str): Material to get node id from
        uniqueNodeName (str): Unique node name in ShaderFX
        quiet (bool): If warnings should print or not
    Returns:
        (int): Node id in ShaderFX graph
    """
    nodeId = 0
    if cmds.objectType(material) == 'ShaderfxShader':
        try:
            nodeId = cmds.shaderfx(sfxnode=material, getNodeIDByName=uniqueNodeName)
        except RuntimeError:
            if not quiet:
                logger.warning("Node {0} was not found in the material {1}".format(uniqueNodeName, material))
    return nodeId


def setNodeValue(material, uniqueNodeName, value, quiet=False):
    """
    Utility function to set the node value within a shaderFX material
    Args:
        material (str): Material to get node id from
        uniqueNodeName (str): Unique node name in ShaderFX
        value (any): Value to set into node
        quiet (bool): If warnings should print or not
    """
    nodeId = getId(material, uniqueNodeName, quiet)
    if nodeId:
        selection = cmds.ls(sl=True, l=True)
        cmds.select(material, r=True)  # triggers are only made if material is selected
        if "value" in cmds.shaderfx(sfxnode=material, listProperties=nodeId):
            if isinstance(value, bool):
                cmds.shaderfx(sfxnode=material, edit_bool=(nodeId, "value", value))
            if isinstance(value, float):
                cmds.shaderfx(sfxnode=material, edit_float=(nodeId, "value", value))
        else:
            cmds.shaderfx(sfxnode=material, edit_stringlist=(nodeId, "options", value))
        cmds.select(selection, r=True)
    else:
        if not quiet:
            logger.warning("Setting of {0} node to {1} has failed".format(uniqueNodeName, value))
    return nodeId


def getNodeValue(material, uniqueNodeName, quiet=False):
    """
    Utility function to get the node value within a shaderFX material
    Args:
        material (str): Material to get node id from
        uniqueNodeName (str): Unique node name in ShaderFX
        quiet (bool): If warnings should print or not
    """
    value = -1
    nodeId = getId(material, uniqueNodeName, quiet)
    if nodeId:
        if "value" in cmds.shaderfx(sfxnode=material, listProperties=nodeId):
            value = cmds.shaderfx(sfxnode=material, getPropertyValue=(nodeId, "value"))
        else:
            value = cmds.shaderfx(sfxnode=material, getPropertyValue=(nodeId, "options"))[-1]
    return value
