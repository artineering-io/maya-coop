"""
@summary:       Maya cooperative materials library
@run:           import coop.materials as matlib (suggested)
@license:       MIT
@repository:    https://github.com/artineering-io/maya-coop
"""
from __future__ import print_function
from __future__ import unicode_literals
import maya.cmds as cmds
import lib as clib


def get_assigned_meshes(objects=None, shapes=True, l=False):
    """
    Get the assigned meshes (shapes) out of a material
    Args:
        objects (list, unicode): objects to get meshes assigned to material from (default: selected)
        shapes (bool): Return shapes or transform node names (default: shapes)
        l (bool): Long names of meshes (default: False)
    Returns:
        (list): List of meshes
    """
    assigned_meshes = []
    if not objects:
        objects = cmds.ls(sl=True, l=True)
    materials = get_materials(objects)
    shading_engines = cmds.listConnections(materials, type="shadingEngine") or []
    for shading_engine in shading_engines:
        meshes = cmds.sets(shading_engine, q=True) or []  # meshes
        meshes = cmds.ls(meshes, l=l)
        if meshes:
            if not shapes:   # get transforms instead (unless components are assigned)
                for mesh in meshes:
                    if not clib.is_component(mesh):
                        mesh = cmds.listRelatives(mesh, parent=True, fullPath=l)  # transforms
                    assigned_meshes.extend(clib.u_enlist(mesh))
            else:
                assigned_meshes.extend(meshes)
    return assigned_meshes


def get_materials(objects):
    """
    Get materials of objects
    Args:
        objects (list, unicode): List of objects/components to get the materials from
    Returns:
        (list): Materials
    """
    objects = clib.u_enlist(objects)
    materials = cmds.ls(objects, l=True, mat=True)
    transforms = cmds.ls(objects, l=True, et="transform")
    shapes = cmds.ls(objects, l=True, s=True, noIntermediate=True)

    if not materials and not transforms and not shapes:
        return _get_material_of_components(objects)  # could be components

    if transforms:
        clib.ListUtils.update(shapes, cmds.ls(transforms, o=True, dag=True, s=True, noIntermediate=True))

    if shapes:
        # _clean_shading_engines(shapes)
        shading_engines = get_shading_engines(shapes)
        for se in shading_engines:
            mats = cmds.ls(cmds.listConnections(se), mat=True)
            if not mats:
                # connect the default material to the shading engine
                default_material = "lambert1"
                clib.print_warning("No material connected to {}. Connecting default material.".format(se))
                cmds.connectAttr("{}.outColor".format(default_material), "{}.surfaceShader".format(se), f=True)
            clib.ListUtils.update(materials, mats)

    return materials


def get_shading_engines(objects):
    """
    Get shading engines of objects
    Args:
        objects (list, unicode): List of objects/components to get the materials from

    Returns:
        (list): Shading engines of objects
    """
    shapes = clib.get_shapes(objects, l=True)
    shading_engines = clib.ListUtils.remove_duplicates(cmds.listConnections(shapes, type="shadingEngine") or [])
    return shading_engines


def set_material(mat, objects, quiet=True):
    """
    Set material onto objects
    Args:
        mat (unicode): Name of material to set to objects
        objects (list): List of objects that the material is assigned to
        quiet (bool): If the function should print what its doing
    """
    def hypershade_fallback():
        selection = cmds.ls(sl=True, l=True)
        cmds.select(objects, r=True)
        cmds.hyperShade(assign=mat)
        cmds.select(selection, r=True)

    mat = clib.u_stringify(mat)
    if not quiet:
        print("set_material(): setting {} onto {}".format(mat, objects))
    shading_engines = get_shading_engines(objects)
    if shading_engines:
        for shading_engine in shading_engines:
            if not cmds.isConnected("{0}.outColor".format(mat), "{0}.surfaceShader".format(shading_engine)):
                if objects == cmds.sets(shading_engine, q=True):  # replace material
                    cmds.connectAttr("{0}.outColor".format(mat), "{0}.surfaceShader".format(shading_engine), f=True)
                else:
                    hypershade_fallback()  # assign
    else:
        hypershade_fallback()


def separate_materials(objects=None, new_name=""):
    """
    Duplicates the material and assigns it to objects i.e., separating it
    Args:
        objects (list): Either a list or selected objects
        new_name (unicode): New name to name separate material into

    Returns:
        (list): List of new materials created by this function
    """
    if objects is None:
        objects = cmds.ls(sl=True, l=True)  # get selected
    else:
        objects = cmds.ls(objects, l=True)
    materials = get_materials(objects)
    new_materials = []
    for mat in materials:
        new_material = new_name
        if not new_name:
            new_material = mat
        new_material = cmds.duplicate(mat, name=new_material, inputConnections=True)[0]
        new_materials.append(new_material)
        replace_material(mat, new_material, objects)
    return new_materials


def replace_material(old_material, new_material, objects=None):
    """
    Replaces the old material with the new_materials in objects or in selected objects
    Args:
        old_material (unicode): Name of the old mapterial
        new_material (unicode): Name of the new material
        objects (list): List of objects to replace materials (default: selected)
    """
    if not objects:
        objects = cmds.ls(sl=True, l=True)
    else:
        objects = cmds.ls(objects, l=True)
    assigned_objects = get_assigned_meshes(old_material, shapes=False, l=True)
    for obj in assigned_objects:
        if obj in objects:
            set_material(new_material, obj)


def _get_material_of_components(components):
    """
    Get materials of components
    Args:
        components (list): List of components to get materials from
    Returns:
        (list): Materials
    """
    materials = []
    for c in components:
        if clib.is_component(c):
            obj = cmds.ls(c, objectsOnly=True)
            shading_engines = clib.ListUtils.remove_duplicates(cmds.listConnections(obj, type="shadingEngine"))
            # Note: we could have used set() above, but the order of elements can be important for certain tools
            for se in shading_engines:
                s = cmds.sets(se, q=True)
                if len(cmds.ls(c, flatten=True)) == 1:
                    s = cmds.ls(s, flatten=True)
                if c in s:
                    materials.extend(cmds.ls(cmds.listConnections(se), mat=True))
    # components might not have a material
    if not materials:
        for c in components:
            if clib.is_component(c):
                materials = get_materials(cmds.ls(components, objectsOnly=True))
                if not materials:
                    clib.display_warning("No materials on {}, assigning default Lambert material".format(components))
                    default_material = "lambert1"
                    set_material(default_material, c)
                    if default_material not in materials:
                        materials.append(default_material)
    return materials


def _clean_shading_engines(objects):
    """
    Makes sure the shading engines are clean
    Args:
        objects (list): Objects to clean shading engines from

    Returns:
        (list): shading engines connected to objects
    """
    shading_engines = []
    shapes = []
    for obj in objects:
        if cmds.objectType(obj) != "mesh":
            shapes.append(clib.get_shapes(obj, l=True))
        else:
            shapes.append(obj)
    for shape in shapes:
        shading_engines = clib.ListUtils.remove_duplicates(cmds.listConnections(shape, type="shadingEngine"))
        if "MNPRX_SE" in shading_engines:
            shading_engines.remove("MNPRX_SE")  # MNPRX instance shading engine
        if len(shading_engines) > 1:
            # remove initialShadingGroup if still available
            if "initialShadingGroup" in shading_engines:
                shading_engines.remove("initialShadingGroup")
                destinations = cmds.listConnections(shape, t='shadingEngine', plugs=True)
                for dest in destinations:
                    if "initialShadingGroup" in dest:
                        try:
                            source = cmds.listConnections(dest, s=True, plugs=True)[0]
                            cmds.disconnectAttr(source, dest)
                            clib.print_warning("initialShadingGroup has been removed from {0}".format(shape))
                            break
                        except RuntimeError:
                            clib.print_warning("Couldn't disconnect {0} from {1}".format(shape, dest))
    return shading_engines


def delete_unused_materials():
    """ Deletes unused materials from the scene """
    materials = cmds.ls(mat=True)
    schedule = []
    for mat in materials:
        if not get_assigned_meshes(mat):
            schedule.append(mat)
    cmds.delete(schedule)