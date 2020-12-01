"""
@summary:       Maya cooperative ShaderFX library
@run:           import coop.shaderFX as csfx (suggested)
@license:       MIT
@repository:    https://github.com/artineering-io/maya-coop
"""
import maya.cmds as cmds
import coopLib as clib


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
                clib.printWarning("Node {0} was not found in the material {1}".format(unique_node_name, material))
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
            if isinstance(value, bool):
                cmds.shaderfx(sfxnode=material, edit_bool=(node_id, "value", value))
            elif isinstance(value, float):
                cmds.shaderfx(sfxnode=material, edit_float=(node_id, "value", value))
            elif isinstance(value, int):
                cmds.shaderfx(sfxnode=material, edit_int=(node_id, "value", value))
        else:
            cmds.shaderfx(sfxnode=material, edit_stringlist=(node_id, "options", value))
        cmds.select(selection, r=True)
    else:
        if not quiet:
            clib.printWarning("Setting of {0} node to {1} has failed".format(unique_node_name, value))
    return node_id


def get_node_value(material, unique_node_name, quiet=False):
    """
    Utility function to get the node value within a shaderFX material
    Args:
        material (unicode): Material to get node id from
        unique_node_name (unicode): Unique node name in ShaderFX
        quiet (bool): If warnings should print or not
    """
    value = -1
    node_id = get_id(material, unique_node_name, quiet)
    if node_id:
        if "value" in cmds.shaderfx(sfxnode=material, listProperties=node_id):
            value = cmds.shaderfx(sfxnode=material, getPropertyValue=(node_id, "value"))
        else:
            value = cmds.shaderfx(sfxnode=material, getPropertyValue=(node_id, "options"))[-1]
    return value


def reference_check(mat, prompt_viewed=False):
    """
    Checks if the material is referenced and processes it accordingly
    Args:
        mat (unicode): material to check
        prompt_viewed (bool): if the reference prompt has been viewed
    """
    # check if material is referenced
    if cmds.referenceQuery(mat, isNodeReferenced=True) and not prompt_viewed:
        message = "Referenced ShaderFX materials may not save correctly\n" \
                  "Do you wish to convert them to local materials instead?"
        button = ['Yes', 'Yes, convert ALL', 'No']
        reply = cmds.confirmDialog(t="Referenced materials", m=message, b=button, icn="warning", ma="center")
        prompt_viewed = True
        if "Yes" in reply:
            if "Yes" == reply:
                if clib.getAssignedMeshes(mat):
                    mat = dereference_material(mat)
            else:
                materials = cmds.ls(type="ShaderfxShader")
                for m in materials:
                    if m != mat:
                        if clib.getAssignedMeshes(m):
                            dereference_material(m)
                if clib.getAssignedMeshes(mat):
                    mat = dereference_material(mat)
    return mat


def dereference_material(mat):
    """
    Creates a local material with the same name if mat is referenced
    Args:
        mat (unicode): Material name to check and dereference

    Returns:
        (unicode): Local material name
    """
    if cmds.referenceQuery(mat, isNodeReferenced=True):
        new_material = mat.split(':')[-1]
        objects = clib.getAssignedMeshes(mat, shapes=True, l=True)
        # duplicate the material and assign it to objects
        new_material = cmds.duplicate(mat, n=new_material)[0]
        clib.setMaterial(new_material, objects)
        return new_material
    else:
        return mat


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
                clib.printWarning("{}.{} has an unsupported file path".format(sfx, attr))
                if fix:
                    cmds.setAttr("{}.{}".format(sfx, attr), "", type="string")


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
            clib.printError("No custom graph was found in {}".format(graph_path.path))
    # resolve name clashes with SFX
    if cmds.objExists(name):
        name += "_SFX"
    # create node and load custom_graph if available
    shader = cmds.shadingNode('ShaderfxShader', asShader=True, name=name)
    if graph:
        cmds.shaderfx(sfxnode=shader, loadGraph=graph)
    return shader
