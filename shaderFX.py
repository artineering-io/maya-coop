"""
@summary:       ShaderFX library
@run:           import coop.shaderFX as csfx (suggested)
@license:       MIT
@repository:    https://github.com/artineering-io/maya-coop
"""
import maya.cmds as cmds
from . import lib as clib
from . import materials as cmat


def get_id(material, unique_node_name, quiet=False):
    """
    Utility function to get the id of uniqueNodeName within a shaderFX material
    Args:
        material (unicode): Material to get node id from
        unique_node_name (unicode): Unique node name in ShaderFX
        quiet (bool): If warnings should print or not

    Returns:
        (int): Node id in ShaderFX graph
    """
    node_id = 0
    if cmds.objectType(material) == 'ShaderfxShader':
        try:
            node_id = cmds.shaderfx(sfxnode=material, getNodeIDByName=unique_node_name)
        except RuntimeError:
            if not quiet:
                clib.print_warning("Node {0} was not found in the material {1}".format(unique_node_name, material))
    return node_id


def set_node_value(material, unique_node_name, value, quiet=False):
    """
    Utility function to set the node value within a shaderFX material
    Args:
        material (unicode): Material to get node id from
        unique_node_name (unicode): Unique node name in ShaderFX
        value (any): Value to set into node
        quiet (bool): If warnings should print or not
    """
    node_id = get_id(material, unique_node_name, quiet)
    if node_id:
        selection = cmds.ls(sl=True, l=True)
        cmds.select(material, r=True)  # triggers and scripts are only made if material is selected
        if "value" in cmds.shaderfx(sfxnode=material, listProperties=node_id):
            v = cmds.shaderfx(sfxnode=material, getPropertyValue=(node_id, "value"))
            if v is not value:
                if isinstance(value, bool):
                    cmds.shaderfx(sfxnode=material, edit_bool=(node_id, "value", value))
                elif isinstance(value, float):
                    cmds.shaderfx(sfxnode=material, edit_float=(node_id, "value", value))
                elif isinstance(value, int):
                    cmds.shaderfx(sfxnode=material, edit_int=(node_id, "value", value))
        else:
            v = cmds.shaderfx(sfxnode=material, getPropertyValue=(node_id, "options"))[-1]
            if v is not value:
                cmds.shaderfx(sfxnode=material, edit_stringlist=(node_id, "options", int(value)))
        cmds.select(selection, r=True)
    else:
        if not quiet:
            clib.print_warning("Setting of {0} node to {1} has failed".format(unique_node_name, value))
    return node_id


def get_node_value(material, unique_node_name, quiet=False):
    """
    Utility function to get the node value within a shaderFX material
    Args:
        material (unicode): Material to get node id from
        unique_node_name (unicode): Unique node name in ShaderFX
        quiet (bool): If warnings should print or not
    """
    value = None
    node_id = get_id(material, unique_node_name, quiet)
    if node_id:
        if "value" in cmds.shaderfx(sfxnode=material, listProperties=node_id):
            value = cmds.shaderfx(sfxnode=material, getPropertyValue=(node_id, "value"))
        else:
            value = int(cmds.shaderfx(sfxnode=material, getPropertyValue=(node_id, "options"))[-1])
    return value


def get_node_name(material, node_id):
    """
    Get the name of a node based on its id
    Args:
        material (unicode): Material to get node name from
        node_id (int): Node id to get name of
    """
    return cmds.shaderfx(sfxnode=material, getPropertyValue=(node_id, "name"))


def list_node_ids(material, node_type=None):
    """
    List nodes of a certain type
    Args:
        material (unicode): Name of the shaderFX material
        node_type (unicode): Type to list (Type names correspond to names in ShaderFX node panel)
    """
    node_count = cmds.shaderfx(sfxnode=material, getNodeCount=True)
    ids = []
    for node_id in range(node_count):
        if node_type is None:
            ids.append(node_id)
        else:
            class_name = cmds.shaderfx(sfxnode=material, getNodeClassName=node_id)
            if node_type == class_name:
                ids.append(node_id)
    return ids


def create_material(name, graph_dir="", custom_graph=""):
    """
    Create a shaderFX material
    Args:
        name (unicode): Name of the new material
        graph_dir (unicode): Directory of where custom graphs are located
        custom_graph (unicode): Name of custom_graph

    Returns:
        (unicode): Name of new material
    """
    graph = ""
    if graph_dir and custom_graph:
        graph_path = clib.Path(graph_dir).child(custom_graph)
        if graph_path.exists():
            graph = graph_path.path
        else:
            clib.print_error("No custom graph was found in {}".format(graph_path.path))
    # resolve name clashes with SFX
    if cmds.objExists(name):
        if "_SFX" not in name:
            name += "_SFX"
    # create node and load custom_graph if available
    shader = cmds.shadingNode('ShaderfxShader', asShader=True, name=name)
    if graph:
        cmds.shaderfx(sfxnode=shader, loadGraph=graph)
    return shader


def refresh_materials(objects=None):
    """ Forces an update of assigned shaderFX materials """
    if objects:
        materials = cmat.get_materials(objects)
    else:
        materials = cmds.ls(type="ShaderfxShader")
    selection = cmds.ls(sl=True, l=True)
    restore_selection = False
    for mat in materials:
        if cmds.objectType(mat) == 'ShaderfxShader':
            cmds.select(mat, r=True)  # needs to be selected
            restore_selection = True
            cmds.shaderfx(sfxnode=mat, update=True)
    if restore_selection:
        cmds.select(selection, r=True)


def filepath_check(text=None, fix=False):
    """
    Checks all existing ShaderFX materials for non-ascii paths

    Returns:
        Prints warnings in the script editor for all non-ascii paths and sets these paths to ""
    """
    sfx_materials = clib.u_enlist(text)
    if not sfx_materials:
        sfx_materials = cmds.ls(exactType='ShaderfxShader')
    for sfx in sfx_materials:
        attrs = cmds.listAttr(sfx, usedAsFilename=True)
        for attr in attrs:
            path = cmds.getAttr("{}.{}".format(sfx, attr))
            try:
                "{}.{} is {}".format(sfx, attr, path)
            except UnicodeEncodeError:
                # there are characters that Maya doesn't support
                clib.print_warning("{}.{} has an unsupported file path".format(sfx, attr))
                if fix:
                    cmds.setAttr("{}.{}".format(sfx, attr), "", type="string")


def check_corrupted(attr_name="cangiante", delete=False):
    """
    Checks all ShaderFX materials for corruption
    Args:
        attr_name (unicode): Attribute name that should exist
        delete (bool): If the corrupted ShaderFX materials should also be deleted
    """
    sfx_materials = cmds.ls(exactType='ShaderfxShader')
    scheduled = []
    for mat in sfx_materials:
        if is_corrupted(mat, attr_name):
            print("{} is corrupted, scheduling deletion".format(mat))
            scheduled.append(mat)
    if scheduled and delete:
        cmds.delete(scheduled)


def is_corrupted(material, attr_name="cangiante"):
    """
    Checks if the ShaderFX material is corrupted
    Args:
        material (unicode): Name of material to check
        attr_name (unicode): Attribute name that should exist

    Returns:
        (bool): True if it is corrupted
    """
    corrupted = False
    if not cmds.attributeQuery(attr_name, node=material, exists=True):
        # doesn't exist, try with the first character capitalized (just in case)
        _attr_name = attr_name[0].upper()
        if len(attr_name) > 1:
            _attr_name += attr_name[1:]
        if not cmds.attributeQuery(_attr_name, node=material, exists=True):
            corrupted = True
    if corrupted:  # MNPRX last check
        if get_id(material, "graphName"):
            if get_node_value(material, "graphName") != "mnpr_uber":
                corrupted = False
    return corrupted
