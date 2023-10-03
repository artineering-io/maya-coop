"""
@summary:       Maya cooperative materials library
@run:           import coop.materials as matlib (suggested)
@license:       MIT
@repository:    https://github.com/artineering-io/maya-coop
"""
from __future__ import print_function
from __future__ import unicode_literals
import maya.cmds as cmds
from . import lib as clib
from . import logger as clog
from . import list as clist


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
    if not objects:
        return []
    materials = cmds.ls(objects, l=True, mat=True)
    transforms = cmds.ls(objects, l=True, et="transform")
    shapes = cmds.ls(objects, l=True, s=True, noIntermediate=True)

    if not materials and not transforms and not shapes:
        return _get_material_of_components(objects)  # could be components

    if transforms:
        clist.update(shapes, cmds.ls(transforms, o=True, dag=True, s=True, noIntermediate=True))

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
            clist.update(materials, mats)

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
    shading_engines = clist.remove_duplicates(cmds.listConnections(shapes, type="shadingEngine") or [])
    return shading_engines


def create_material(mat_type, name="", select_it=False):
    """
    Create a material of a specific type
    Args:
        mat_type (unicode): Material type i.e., 'anisotropic', 'blinn'
        name (unicode): Name of the material
        select_it (bool): If the material should be selected after creation

    Returns:
        (unicode): Name of the material
    """
    if name:
        return cmds.shadingNode(mat_type, asShader=True, n=name, skipSelect=not select_it)
    else:
        return cmds.shadingNode(mat_type, asShader=True, skipSelect=not select_it)


def set_material(mat, objects, quiet=True):
    """
    Set material onto objects
    Args:
        mat (unicode): Name of material to set to objects
        objects (unicode, list): List of objects that the material is assigned to
        quiet (bool): If the function should print what its doing
    """
    log = clog.logger("set_material()")
    mat = clib.u_stringify(mat)
    objects = clib.u_enlist(objects)
    if not quiet:
        log.debug("set_material(): setting {} onto :\n{}".format(mat, objects))
    # get shapes, components
    shapes = []
    for obj in objects:
        if cmds.objectType(obj) not in ["mesh", "nurbsSurface"]:
            shapes.extend(clib.get_shapes(obj))
        else:
            shapes.append(obj)
    shapes = cmds.ls(shapes, l=True)  # long names
    # check if material is not already assigned
    materials = get_materials(shapes)
    assigned_shapes = get_assigned_meshes(materials, l=True)
    if set(shapes) == set(assigned_shapes) and set(clib.u_enlist(mat)) == set(materials):
        return  # material is already assigned to the objects
    # assign new material
    try:
        # sets assign
        shading_engine = cmds.sets(empty=True, renderable=True, noSurfaceShader=True, name="{}SG".format(mat))
        cmds.defaultNavigation(connectToExisting=True, source=mat, destination=shading_engine, f=True)
        for shape in shapes:
            cmds.sets(shape, e=True, forceElement=shading_engine)
    except RuntimeError:
        log.warning("Failed to assign material using sets. Falling back to Hypershade assign")
        # hypershade assign
        selection = cmds.ls(sl=True)
        cmds.select(objects, r=True)
        cmds.hyperShade(assign=mat)
        cmds.select(selection, r=True)


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
        old_material (unicode): Name of the old material
        new_material (unicode): Name of the new material
        objects (list): List of objects to replace materials (default: selected)
    """
    if not objects:
        objects = cmds.ls(sl=True, l=True)
    else:
        objects = cmds.ls(objects, l=True)
    assigned_objects = get_assigned_meshes(old_material, shapes=False, l=True)
    for obj in objects:
        if clib.get_transform(obj, full_path=True) in clib.get_transforms(assigned_objects, full_path=True):
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
            shading_engines = clist.remove_duplicates(cmds.listConnections(obj, type="shadingEngine"))
            # Note: we could have used set() above, but the order of elements can be important for certain tools
            for se in shading_engines:
                s = cmds.sets(se, q=True)
                intersection = set(cmds.ls(s, flatten=True)).intersection(set(cmds.ls(c, flatten=True)))
                if intersection:
                    mats = cmds.ls(cmds.listConnections(se), mat=True) or []
                    for m in mats:
                        if m not in materials:
                            materials.append(m)
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
        shading_engines = clist.remove_duplicates(cmds.listConnections(shape, type="shadingEngine"))
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


def get_texture(material, tex_attr, rel=False):
    """
    Gets the texture from the connected file node of a texture attribute
    Args:
        material (unicode): name of the material
        tex_attr (unicode): name of the texture attribute
        rel (bool): Make file paths relative to Maya project
    Returns:
        (unicode): texture path of the material
    """
    tex_path = ""
    node_attr = "{}.{}".format(material, tex_attr)
    sources = cmds.listConnections(node_attr, type='file')
    if sources:
        file_attr = "{}.computedFileTextureNamePattern".format(sources[0])
        tex_path = cmds.getAttr(file_attr)
        if rel:
            tex_path = clib.make_path_relative(tex_path)
    return tex_path


def set_texture(material, tex_attr, file_path):
    """
    Connects a file node with all its additional nodes
    Args:
        material (unicode): name of the material
        tex_attr (unicode): name of the texture attribute
        file_path (unicode): filepath of texture
    Returns:
        (unicode): Name of connected file node
    """
    file_node = ""
    if file_path:
        if file_path.startswith("/"):
            file_path = file_path[1:]  # making sure we remove the "/" at the beginning
        full_attr = "{}.{}".format(material, tex_attr)
        sources = cmds.listConnections(full_attr, type='file')
        if sources:
            file_node = sources[0]
            # There can be only one source connected to a texture input attribute
            cmds.setAttr(file_node + '.fileTextureName', file_path, type='string')
        else:
            place2d_node = cmds.shadingNode('place2dTexture', asUtility=True, ss=True)
            file_node = cmds.shadingNode('file', asTexture=True, ss=True)
            clib.set_attr(file_node, "fileTextureName", file_path)
            # Make the default connections
            cmds.defaultNavigation(connectToExisting=True, source=place2d_node, destination=file_node)
            cmds.defaultNavigation(connectToExisting=True, source=file_node, destination=full_attr, force=True)
    else:
        clib.break_connections(material, tex_attr, delete_inputs=True)
    return file_node


def reload_textures(materials, tex_attr, rel=True):
    """
    Reload the assigned textures on the file nodes of materials
    Args:
        materials (unicode, list): Materials to reload textures on
        tex_attr (unicode): Attribute to reload textures in
        rel (bool): Make file paths relative to Maya project
    """
    materials = clib.u_enlist(materials)
    for mat in materials:
        node_attr = "{}.{}".format(mat, tex_attr)
        sources = cmds.listConnections(node_attr, type='file')
        if sources:
            file_attr = "{}.fileTextureName".format(sources[0])
            file_path = cmds.getAttr(file_attr)
            if rel:
                file_path = clib.make_path_relative(file_path)
            cmds.setAttr(file_attr, file_path, type='string')


def get_connected_node(material, attr, prefix=""):
    """
    Gets the texture from the connected file node of a texture attribute
    Args:
        material (unicode): name of the material
        attr (unicode): name of the attribute to get connected node from
        prefix (unicode): prefix to add to node
    Returns:
        (unicode): texture path of the material
    """
    node = ""
    node_attr = "{}.{}".format(material, attr)
    sources = cmds.listConnections(node_attr)
    if sources:
        node = "{}{}".format(prefix, sources[0])
    return node


def refresh_materials(materials=None):
    """
    Refreshes the shading engines of materials to fetch changes that might
    not have been propagated
    Args:
        materials (list, unicode): Materials to refresh
    """
    if materials is None:
        materials = cmds.ls(mat=True)
    shading_engines = cmds.listConnections(materials, type="shadingEngine")
    cmds.dgdirty(shading_engines)





