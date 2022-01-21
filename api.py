"""
@summary:       Maya cooperative python api 2.0 library
@run:           import coop.api as capi (suggested)
@license:       MIT
@repository:    https://github.com/artineering-io/maya-coop
"""
from __future__ import print_function
from __future__ import unicode_literals
import maya.api.OpenMaya as om

def maya_useNewAPI():
    pass


def get_node_mobject(node, get_type=False):
    """
    Gets MObject of a node
    Args:
        node (unicode): Name of node
        get_type (bool): If the api type should be returned
    Returns:
        (MObject, unicode): The MObject of the node or its API type
    """
    selection_list = om.MSelectionList()
    selection_list.add(node)
    o_node = selection_list.getDependNode(0)
    if not get_type:
        return o_node
    else:
        return o_node.apiTypeStr


def get_attr_mobject(node_attr, get_type=False):
    """
    Gets MObject of a node
    Args:
        node_attr (unicode): Attribute of the node in the format node.attr
        get_type (bool): If the api type should be returned
    Returns:
        (MObject, unicode): The MObject of the node or its API type
    """
    plug = get_mplug(node_attr)
    o_attr = plug.attribute()
    if not get_type:
        return o_attr
    else:
        return o_attr.apiTypeStr


def get_mplug(node_attr):
    """
    Gets the MPlug of a node.attr
    Args:
        node_attr (unicode): Node attribute formatted as node.attr
    Returns
        (MPlug): MPlug of the node.attr
    """
    selection_list = om.MSelectionList()
    selection_list.add(node_attr)
    return selection_list.getPlug(0)
