"""
@summary:       Maya cooperative shelf library
@run:           import coop.shelves as cshelf (suggested)
@license:       MIT
@repository:    https://github.com/artineering-io/maya-coop
"""
from __future__ import print_function
from __future__ import unicode_literals
import os
import maya.cmds as cmds
import maya.mel as mel
from . import logger as clog
from . import list as clist
from . import lib as clib

LOG = clog.logger("coop.shelf")


def delete_shelves(shelves=None, restart=True):
    """
    Delete shelves specified in dictionary
    Args:
        shelves (unicode, list): Shelves to delete e.g. "Animation", "Animation.mel"
        restart (bool): If a restart dialog should appear in the end
    """
    if not shelves:
        LOG.warning('No shelves specified to delete')
        return
    # standardize shelve names
    shelves_filenames, shelves_names = format_shelves(shelves)
    # Maya creates all default shelves in prefs only after each has been opened (initialized)
    for shelf in shelves_names:
        try:
            mel.eval('jumpToNamedShelf("{0}");'.format(shelf))
        except RuntimeError:
            continue
    mel.eval('saveAllShelves $gShelfTopLevel;')  # all shelves loaded (save them)
    # time to delete them
    shelf_top_level = mel.eval('$tempMelStringVar=$gShelfTopLevel') + '|'
    for shelf in shelves_names:
        if cmds.shelfLayout(shelf_top_level + shelf, q=True, ex=True):
            cmds.deleteUI(shelf_top_level + shelf, layout=True)
    # mark them as deleted to avoid startup loading
    env_dir = clib.get_env_dir()
    shelf_dir = os.path.join(env_dir, 'prefs', 'shelves')
    for shelf in shelves_filenames:
        shelf_path = os.path.join(shelf_dir, shelf)
        deleted_shelf_path = shelf_path + '.deleted'
        if os.path.isfile(shelf_path):
            # make sure the deleted file doesn't already exist
            if os.path.isfile(deleted_shelf_path):
                os.remove(shelf_path)
            os.rename(shelf_path, deleted_shelf_path)
    if restart:
        clib.dialog_restart()


def restore_shelves():
    """ Restores previously deleted shelves """
    shelf_dir = os.path.join(clib.get_env_dir(), 'prefs', 'shelves')
    for shelf in os.listdir(shelf_dir):
        if shelf.endswith('.deleted'):
            restored_shelf = os.path.join(shelf_dir, shelf.split('.deleted')[0])
            deleted_shelf = os.path.join(shelf_dir, shelf)
            # check if it has not been somehow restored
            if os.path.isfile(restored_shelf):
                os.remove(deleted_shelf)
            else:
                os.rename(deleted_shelf, restored_shelf)
    clib.dialog_restart()


def format_shelves(shelves):
    """
    Format shelves into their filename and names i.e., ['shelf_Animation.mel'], ['Animation']
    Args:
        shelves (unicode, list): Shelves to format into filename, name
    Returns:
        (list, list): Shelf filenames and names
    """
    shelves_filenames = []
    shelves_names = []
    shelves = clist.enlist(shelves)
    for shelf in shelves:
        if shelf.startswith('shelf_'):
            if shelf.endswith('.mel'):
                shelves_filenames.append(shelf)
                shelves_names.append(shelf[6:shelf.index('.mel')])
            else:
                shelves_filenames.append("{}.mel".format(shelf))
                shelves_names.append(shelf[6:])
        else:
            if shelf.endswith('.mel'):
                shelves_filenames.append("shelf_{}".format(shelf))
                shelves_names.append(shelf[:shelf.index('.mel')])
            else:
                shelves_filenames.append("shelf_{}.mel".format(shelf))
                shelves_names.append(shelf)
    return shelves_filenames, shelves_names
