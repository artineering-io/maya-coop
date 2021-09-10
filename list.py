"""
@summary:       Maya cooperative list library
@run:           import coop.list as clist (suggested)
@license:       MIT
@repository:    https://github.com/artineering-io/maya-coop
"""
from . import logger as clog

LOG = clog.logger("coop.list")

try:
    basestring  # Python 2
except NameError:
    basestring = (str,)  # Python 3


def flatten_list(raw_list):
    """
    Flattens list and removes duplicates
    Args:
        raw_list (list): List to flatten
    Returns:
        list: Flattened list
    """
    flat_list = list()
    raw_list = enlist(raw_list)
    for elem in raw_list:
        if isinstance(elem, list):
            recursion = flatten_list(elem)
            for re in recursion:
                if re not in flat_list:
                    flat_list.append(re)
        else:
            if elem not in flat_list:
                flat_list.append(elem)
    return flat_list


def remove_duplicates(obj_list):
    """
    Remove duplicate entries in list and keep order of entries
    Args:
        obj_list (list): List to remove duplicate entries from

    Returns:
        New List
    """
    if not obj_list:
        obj_list = []
    new_list = []
    new_set = set()  # working with sets speeds up the workflow
    for obj in obj_list:
        if obj not in new_set:
            new_set.add(obj)
            new_list.append(obj)
    return new_list


def add(obj_list, obj):
    """
    Adds object if it didn't exist before
    Args:
        obj_list (list): List to add element onto
        obj (unicode): object to be added
    """
    if obj not in obj_list:
        obj_list.append(obj)


def update(obj_list, update_list):
    """
    Adds each object within a list if it didn't exist before
    Args:
        obj_list (list): List to update with elements of update_list
        update_list (list): List to add to obj_list
    """
    for obj in update_list:
        add(obj_list, obj)


def enlist(arg, silent=True):
    """
    Enlist a given argument
    Args:
        arg: argument to put into a list
        silent (bool): If the function should print warnings if the wrong data was given (default=False)
    Returns:
        List: The argument in a list
    """
    if isinstance(arg, basestring):
        if not silent:
            LOG.info("{0} is a string, enlisting it".format(arg))
        return [arg]
    elif isinstance(arg, int):
        if not silent:
            LOG.info("{0} is an int, enlisting it".format(arg))
        return [arg]
    elif arg is None:
        return []
    return arg


# UNIT TESTS
def _flatten_list_test():
    raw_list = [[3, 5, [7, [5, 5]]], 2, [1, 2], 3]
    expected_list = [3, 5, 7, 2, 1]
    test_list = flatten_list(raw_list)
    if expected_list != test_list:
        return False
    return True
