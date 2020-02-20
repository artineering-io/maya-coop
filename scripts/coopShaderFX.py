"""
@license:       MIT
@repository:    https://github.com/artineering-io/maya-coop
#                              ____  _               _           _______  __
#     ___ ___   ___  _ __     / ___|| |__   __ _  __| | ___ _ __|  ___\ \/ /
#    / __/ _ \ / _ \| '_ \    \___ \| '_ \ / _` |/ _` |/ _ \ '__| |_   \  /
#   | (_| (_) | (_) | |_) |    ___) | | | | (_| | (_| |  __/ |  |  _|  /  \
#    \___\___/ \___/| .__/    |____/|_| |_|\__,_|\__,_|\___|_|  |_|   /_/\_\
#                   |_|
@summary:       Maya cooperative ShaderFX library
@run:           import coopShaderFX as csfx (suggested)
"""
import logging
import maya.cmds as cmds
import coopLib as lib

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
        cmds.select(material, r=True)  # triggers and scripts are only made if material is selected
        if "value" in cmds.shaderfx(sfxnode=material, listProperties=nodeId):
            if isinstance(value, bool):
                cmds.shaderfx(sfxnode=material, edit_bool=(nodeId, "value", value))
            elif isinstance(value, float):
                cmds.shaderfx(sfxnode=material, edit_float=(nodeId, "value", value))
            elif isinstance(value, int):
                cmds.shaderfx(sfxnode=material, edit_int=(nodeId, "value", value))
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


def referenceCheck(mat, promptViewed=False):
    """
    Checks if the material is referenced and processes it accordingly
    Args:
        mat (str): material to check
    """
    # check if material is referenced
    if cmds.referenceQuery(mat, isNodeReferenced=True) and not promptViewed:
        message = "Referenced ShaderFX materials may not save correctly\n" \
                  "Do you wish to convert them to local materials instead?"
        button = ['Yes', 'Yes, convert ALL', 'No']
        reply = cmds.confirmDialog(t="Referenced materials", m=message, b=button, icn="warning", ma="center")
        promptViewed = True
        if "Yes" in reply:
            if "Yes" == reply:
                if lib.getAssignedMeshes(mat):
                    mat = dereferenceMaterial(mat)
            else:
                materials = cmds.ls(type="ShaderfxShader")
                for m in materials:
                    if m != mat:
                        if lib.getAssignedMeshes(m):
                            dereferenceMaterial(m)
                if lib.getAssignedMeshes(mat):
                    mat = dereferenceMaterial(mat)
    return mat


def dereferenceMaterial(mat):
    """
    Creates a local material with the same name if mat is referenced
    Args:
        mat (str): Material name to check and dereference
    Returns:
        localMaterial (str): Local material name
    """
    logger.debug("Dereferencing {0}".format(mat))
    if cmds.referenceQuery(mat, isNodeReferenced=True):
        newMaterial = mat.split(':')[-1]
        objects = lib.getAssignedMeshes(mat, shapes=True, l=True)
        # Method 1: By duplicating the material and assigning it to objects
        newMaterial = cmds.duplicate(mat, n=newMaterial)[0]
        lib.setMaterial(newMaterial, objects)
        # Method 2:  By saving and writing attributes in new material (slower and relies on MNPRX)
        """
        matAttrs = dict()
        getMaterialAttrs(mat, matAttrs)
        newMaterial = createMaterial(objects, newMaterial, matAttrs["graph"])
        setMaterialAttrs(newMaterial, matAttrs)
        """
        return newMaterial
    else:
        return mat