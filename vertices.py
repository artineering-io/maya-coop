"""
@summary:       Maya cooperative python library
@run:           import coop.vtx_colors as cvtx
@license:       MIT
@repository:    https://github.com/artineering-io/maya-coop
"""
from __future__ import print_function
from __future__ import unicode_literals
import maya.cmds as cmds
import maya.mel as mel
import lib as clib
import logger as clog


# python api 2.0
import maya.api.OpenMaya as om
def maya_useNewAPI():
    pass


LOG = clog.logger("coop.vertices")


@clib.undo
def create_color_set_api(shapes, color_sets, delete_history=True):
    """
    Create a color set on shapes (with api) with (0, 0, 0, 0) as default color
    Args:
        shapes (unicode, list): shapes to create color set in
        color_sets (unicode, list): color sets to create in shapes
        delete_history (bool): If createColorSet history should be deleted
    """
    shapes = clib.u_enlist(shapes)
    color_sets = clib.u_enlist(color_sets)
    for shape in shapes:
        o_shape = clib.get_m_object(shape)
        fn_mesh = om.MFnMesh(o_shape)
        shape_color_sets = fn_mesh.getColorSetNames()
        for color_set in color_sets:
            if color_set not in shape_color_sets:
                fn_mesh.createColorSet(color_set, False, rep=om.MFnMesh.kRGBA)
                vtx_colors = fn_mesh.getVertexColors(colorSet=color_set, defaultUnsetColor=om.MColor((0, 0, 0, 0)))
                fn_mesh.setCurrentColorSetName(color_set)
                fn_mesh.setVertexColors(vtx_colors, range(len(vtx_colors)))
    if delete_history:
        delete_color_set_history(shapes)


@clib.undo
def create_color_set(shapes, color_sets, delete_history=True):
    """
    Create a color set on shapes (with cmds) with (0, 0, 0, 0) as default color
    Note: SLOW, use create_color_set_api instead
    Args:
        shapes (unicode, list): shapes to create color set in
        color_sets (unicode, list): color sets to create in shapes
        delete_history (bool): If createColorSet history should be deleted
    """
    shapes = clib.u_enlist(shapes)
    color_sets = clib.u_enlist(color_sets)
    selection = cmds.ls(sl=True)
    for shape in shapes:
        cmds.select(shape, r=True)
        shape_color_sets = cmds.polyColorSet(shape, query=True, allColorSets=True) or []
        for color_set in color_sets:
            if color_set not in shape_color_sets:
                cmds.polyColorSet(shape, cs=color_set, representation="RGBA", create=True)
                cmds.polyColorPerVertex(rgb=(0.0, 0.0, 0.0), a=0.0)  # needs the object selected
    cmds.select(selection, r=True)
    if delete_history:
        delete_color_set_history(shapes)


def delete_color_set_history(shapes):
    """
    Deletes unnecessary history nodes created by color sets
    Args:
        shapes (unicode, list): shapes to delete history nodes from
    """
    shapes = clib.u_enlist(shapes)  # unit tests
    nodes2delete = []
    for shape in shapes:
        history = cmds.listHistory(shape)
        create_color_set_nodes = cmds.ls(history, exactType='createColorSet')
        nodes2delete.extend(create_color_set_nodes)
    if nodes2delete:
        cmds.delete(nodes2delete)


@clib.undo
def delete_color_sets(shapes, color_sets):
    """
    Deletes vertex color sets and their history from shapes
    Args:
        shapes (list): Shapes to delete vertex color sets from
        color_sets (list, unicode): Vertex color sets to delete
    """
    shapes = clib.u_enlist(shapes)  # put in list
    color_sets = clib.u_enlist(color_sets)  # put in list
    nodes2delete = []
    for shape in shapes:
        shape_color_sets = cmds.polyColorSet(shape, query=True, allColorSets=True) or []
        for color_set in color_sets:
            if color_set in shape_color_sets:
                cmds.polyColorSet(shape, colorSet=color_set, delete=True)
                history = cmds.listHistory(shape)
                for node in history:
                    # check if attribute exists
                    if not cmds.attributeQuery('colorSetName', n=node, ex=True):
                        continue
                    # attribute exists, check name of color set name
                    color_set_name = cmds.getAttr("{0}.colorSetName".format(node))
                    if color_set_name == color_set:
                        nodes2delete.append(node)
    if nodes2delete:
        cmds.delete(nodes2delete)
    LOG.debug("Vertex color sets {} deleted for: {}".format(color_sets, shapes))


def _bake_vertex_colors(shapes):
    """
    Bake vertex colors into shape nodes (not working, set issue in AREA Forum)
    https://forums.autodesk.com/t5/maya-programming/baking-vertex-colors-onto-shape-node/td-p/9119416
    Args:
        shapes (unicode, list): Shapes to bake vertex colors
    """
    shapes = clib.u_enlist(shapes)
    for shape in shapes:
        history = cmds.listHistory(shape)
        for node in history:
            if cmds.objectType(node) == "polyColorPerVertex":
                print("Baking {0}".format(node))
                # GET
                # get color set name
                color_set_name = cmds.getAttr("{0}.colorSetName".format(node))
                print("Color set name: {0}".format(color_set_name))
                # get representation
                representation = cmds.getAttr("{0}.representation".format(node))
                print("Representation: {0}".format(representation))
                # get clamped
                clamped = cmds.getAttr("{0}.clamped".format(node))
                print("Clamped: {0}".format(clamped))
                # get vertex colors
                alphas = cmds.getAttr("{0}.vertexColor[*].vertexFaceColor[*].vertexFaceAlpha".format(node))
                reds = cmds.getAttr("{0}.vertexColor[*].vertexFaceColor[*].vertexFaceColorR".format(node))
                greens = cmds.getAttr("{0}.vertexColor[*].vertexFaceColor[*].vertexFaceColorG".format(node))
                blues = cmds.getAttr("{0}.vertexColor[*].vertexFaceColor[*].vertexFaceColorB".format(node))
                print(alphas)
                print(reds)
                print(greens)
                print(blues)
                # SET
                # get which color set in shape
                color_sets = cmds.getAttr("{0}.colorSet[*].colorName".format(shape))
                # make sure its in an array
                if isinstance(color_sets, basestring):
                    color_sets = [color_sets]
                color_set_index = color_sets.index(color_set_name)
                print("Color set index is {0}".format(color_set_index))
                clib.set_attr(shape, "colorSet[{0}].colorName".format(color_set_index), color_set_name)
                clib.set_attr(shape, "colorSet[{0}].representation".format(color_set_index), representation)
                clib.set_attr(shape, "colorSet[{0}].clamped".format(color_set_index), clamped)
                for i in range(len(alphas)):
                    """
                    attr = "colorSet[{0}].colorSetPoints[{1}]".format(colorSetIndex, i)
                    setAttr(shape, attr, [reds[i], greens[i], blues[i], alphas[i]])
                    """
                    attr = "colorSet[{0}].colorSetPoints[{1}].colorSetPointsR".format(color_set_index, i)
                    # setAttr(shape, attr, reds[i])
                    cmds.setAttr("{0}.{1}".format(shape, attr), reds[i])
                    attr = "colorSet[{0}].colorSetPoints[{1}].colorSetPointsG".format(color_set_index, i)
                    # setAttr(shape, attr, greens[i])
                    cmds.setAttr("{0}.{1}".format(shape, attr), greens[i])
                    attr = "colorSet[{0}].colorSetPoints[{1}].colorSetPointsB".format(color_set_index, i)
                    # setAttr(shape, attr, blues[i])
                    cmds.setAttr("{0}.{1}".format(shape, attr), blues[i])
                    attr = "colorSet[{0}].colorSetPoints[{1}].colorSetPointsA".format(color_set_index, i)
                    # setAttr(shape, attr, alphas[i])
                    cmds.setAttr("{0}.{1}".format(shape, attr), alphas[i])
                # add to shape
                face_no = cmds.polyEvaluate(shape, face=True)  # query amount of faces
                mel_cmd = 'setAttr -s {0} "{1}.fc[0:{2}]" -type "polyFaces"'.format(face_no, shape, face_no - 1)
                # mel_cmd = 'setAttr -s {0} -ch {1} "{2}.fc[0:{3}]" -type "polyFaces" '\
                #     .format(face_no, face_no*4, shape, face_no-1)
                # melCmd = 'setAttr {0}.polyFaceAttr -type polyFaces '.format(shape, colorSetIndex)
                fv = 0
                for f in range(face_no):
                    # find adjacent vertices
                    v_string = cmds.polyInfo("{0}.f[{1}]".format(shape, f), fv=True)[0]
                    vertices = v_string.split(':')[1].split()
                    mel_cmd += ' mc {0} {1}'.format(color_set_index, len(vertices))
                    for _ in vertices:
                        mel_cmd += " {0}".format(fv)
                        fv += 1
                mel_cmd += ';'
                print(mel_cmd)
                mel.eval(mel_cmd)  # we run the mel command here
                # delete polyColorPerVertex nodes that pertain this colorSet
                cmds.delete(node)
                LOG.debug("Vertex color set {0} baked on {1}".format(color_set_name, shape))
            if cmds.objectType(node) == "createColorSet":
                cmds.delete(node)  # no need for them in history
