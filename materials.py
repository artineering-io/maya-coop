"""
@summary:       Maya cooperative materials library
@run:           import coop.materials as matlib (suggested)
@license:       MIT
@repository:    https://github.com/artineering-io/maya-coop
"""
from __future__ import print_function
from __future__ import unicode_literals
import maya.cmds as cmds
import coopLib as clib


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
    materials = clib.getMaterials(objects)
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
