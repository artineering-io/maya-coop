# -*- coding: utf-8 -*-
"""
@license:       MIT
@repository:    https://github.com/artineering-io/maya-coop
#                          _     _ _
#     ___ ___   ___  _ __ | |   (_) |__
#    / __/ _ \ / _ \| '_ \| |   | | '_ \
#   | (_| (_) | (_) | |_) | |___| | |_) |
#    \___\___/ \___/| .__/|_____|_|_.__/
#                   |_|
@summary:       Maya cooperative python library
@run:           import coop.coopLib as lib (suggested)
"""
from __future__ import print_function
from __future__ import unicode_literals
import os, sys, subprocess, shutil, re, logging, json, math, traceback, platform
from functools import wraps
import maya.mel as mel
import maya.cmds as cmds

# python api 2.0
import maya.api.OpenMaya as om
def maya_useNewAPI():
    pass


try:
    basestring  # Python 2
except NameError:
    basestring = (str,)  # Python 3

try:
    xrange  # Python 2
except NameError:
    xrange = range  # Python 3

# LOGGING
logging.basicConfig()  # errors and everything else (2 separate log groups)
logger = logging.getLogger("coopLib")  # create a logger for this file
logger.setLevel(logging.DEBUG)  # defines the logging level (INFO for releases)

# Please follow google style docstrings!
"""
This is an example of Google style.

Args:
    param1: This is the first param.
    param2: This is a second param.

Returns:
    This is a description of what is returned.

Raises:
    KeyError: Raises an exception.
"""


#        _                          _
#     __| | ___  ___ ___  _ __ __ _| |_ ___  _ __ ___
#    / _` |/ _ \/ __/ _ \| '__/ _` | __/ _ \| '__/ __|
#   | (_| |  __/ (_| (_) | | | (_| | || (_) | |  \__ \
#    \__,_|\___|\___\___/|_|  \__,_|\__\___/|_|  |___/
#
def timer(f):
    """
    Decorator to time functions
    Args:
        f: function to be timed

    Returns:
        wrapped function with a timer
    """

    @wraps(f)  # timer = wraps(timer) | helps wrap the docstring of original function
    def wrapper(*args, **kwargs):
        import time
        time_start = time.time()
        try:
            return f(*args, **kwargs)
        except:
            traceback.print_exc()
        finally:
            time_end = time.time()
            logger.debug("[Time elapsed at {0}:    {1:.4f} sec]".format(f.__name__, time_end - time_start))

    return wrapper


def undo(f):
    """
    Puts the wrapped `func` into a single Maya Undo action
    Args:
        f: function to be undone

    Returns:
        wrapped function within an undo chunk
    """

    @wraps(f)
    def undo_wrapper(*args, **kwargs):
        try:
            # start an undo chunk
            cmds.undoInfo(openChunk=True, cn="{0}".format(f))
            return f(*args, **kwargs)
        except:
            traceback.print_exc()
        finally:
            # after calling the func, end the undo chunk
            cmds.undoInfo(closeChunk=True, cn="{0}".format(f))

    return undo_wrapper


#    _     _     _   _   _ _   _ _
#   | |   (_)___| |_| | | | |_(_) |___
#   | |   | / __| __| | | | __| | / __|
#   | |___| \__ \ |_| |_| | |_| | \__ \
#   |_____|_|___/\__|\___/ \__|_|_|___/
#
# List utilities within a helper class to work with lists.
# It works in a similar way to set(), but it keeps the order of its elements
class ListUtils(object):
    @staticmethod
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

    @staticmethod
    def add(obj_list, obj):
        """
        Adds object if it didn't exist before
        Args:
            obj_list (list): List to add element onto
            obj (unicode): object to be added
        """
        if obj not in obj_list:
            obj_list.append(obj)

    @staticmethod
    def update(obj_list, update_list):
        """
        Adds each object within a list if it didn't exist before
        Args:
            obj_list (list): List to update with elements of update_list
            update_list (list): List to add to obj_list
        """
        for obj in update_list:
            ListUtils.add(obj_list, obj)


######################################################################################
# GENERAL UTILITIES
######################################################################################
def get_host():
    """
    Checks for host application of python environment
    Returns:
        (unicode): Host name (e.g., Maya, Blender)
    """
    host = os.path.basename(sys.executable)
    if "maya" in host:
        return "Maya"
    if "blender" in host:
        return "Blender"


def get_py_version(version=0):
    """
    Checks for the version of python currently running
    Args:
        version (float): desired version to check with
    Returns:
        Python version (unicode): The version currently running if no version is supplied
        Version check (bool): True if current version is higher than the given version. False if not
    """
    v = platform.python_version()
    f_v = float(v[:v.rindex('.')])
    if not version:
        return f_v
    if f_v >= float(version):
        return True
    return False


def get_maya_version():
    """
    Returns the current Maya version (E.g. 2017.0, 2018.0, 2019.0, etc)
    """
    return mel.eval("getApplicationVersionAsFloat")


def get_local_os():
    """
    Returns the operating system (OS) of the local machine
    Returns:
        (unicode): Either "win", "mac" or "linux"
    """
    if cmds.about(mac=True):
        return "mac"
    elif cmds.about(linux=True):
        return "linux"
    return "win"


def plugin_ext():
    """
    Returns the plugin extension depending on the local operating system
    Returns:
        (unicode): Either "mll", "bundle" or "so"
    """
    extensions = {"win": "mll", "mac": "bundle", "linux": "so"}
    return extensions[get_local_os()]


def get_env_dir():
    """
    Gets the environment directory
    Returns:
        directory (unicode): the directory of the Maya.env file
    """
    env_dir = os.path.abspath(cmds.about(env=True, q=True))
    return os.path.dirname(env_dir)


def get_module_path(module):
    """
    Gets the path of a Maya module, if it exists
    Args:
        module (unicode): Name of the module

    Returns:
        (unicode): Path to the module (empty if it doesn't exist)
    """
    try:
        return cmds.moduleInfo(path=True, moduleName=module)
    except RuntimeError:
        return ""


def get_lib_dir():
    """
    Gets the coop library directory
    Returns:
        directory (unicode): the directory where the coopLib is found at
    """
    return Path(__file__).parent().path


def open_url(url):
    """
    Opens the url in the default browser
    Args:
        url (unicode): The URL to open
    """
    import webbrowser
    webbrowser.open(url, new=2, autoraise=True)


def downloader(url, dest):
    """
    Downloads a file at the specified url to the destination
    Args:
        url: URL of file to download
        dest: destination of downloaded file

    Returns:
        bool: True if succeeded, False if failed
    """
    import urllib
    dwn = urllib.URLopener()
    try:
        dwn.retrieve(url, dest)
    except:
        traceback.print_exc()
        return False
    return True


def restart_maya(brute=True):
    """
    Restarts maya (CAUTION)
    Args:
        brute (bool): True if the Maya process should stop, False if Maya should be exited normally
    """
    if not brute:
        maya_py_dir = Path(sys.executable).parent().child("mayapy.exe")
        script_dir = Path(__file__).parent().child("coopRestart.py")
        subprocess.Popen([maya_py_dir.path, script_dir.path])
        cmds.quit(force=True)
    else:
        os.execl(sys.executable, sys.executable, *sys.argv)


def run_cmd(cmd, cwd):
    """
    Run a command in a separate shell and print its results
    Args:
        cmd (unicode): Command to run in a shell
        cwd (unicode): Current working directory (path where command will be executed from)
    """
    print("> {}".format(cmd))
    process = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    (output, error) = process.communicate()
    if output:
        print("Output: {}".format(output))
    if error:
        print("Error: {}".format(error))


def dialog_restart(brute=True):
    """
    Opens restart dialog to restart maya
    Args:
        brute (bool): True if the Maya process should stop, False if Maya should be exited normally
    """
    restart = cmds.confirmDialog(title='Restart Maya',
                                 message='Maya needs to be restarted in order to show changes\n'
                                         'Would you like to restart maya now?',
                                 button=['Yes', 'No'], defaultButton='Yes', cancelButton='No', dismissString='No',
                                 ma='center')
    if restart == 'Yes':
        restart_maya(brute)


def dialog_save(starting_directory="", title="Save as...", file_filter="All Files (*.*)"):
    """
    Simple save dialog in Maya
    Args:
        starting_directory (unicode): Starting directory. (default: project root directory)
        title (unicode): Dialog title. (default: "Save as...")
        file_filter (unicode): File filter. (default: "All Files (*.*)")

    Returns:
        Path (unicode) to save as
    """
    if not starting_directory:
        starting_directory = cmds.workspace(rd=True, q=True)
    save_path = cmds.fileDialog2(fileFilter=file_filter, fileMode=0,
                                 startingDirectory=starting_directory,
                                 cap=title, dialogStyle=2)
    if not save_path:
        display_error("Filepath not specified", True)
        return ""
    return save_path[0]


def dialog_open(starting_directory="", title="Open file", file_filter="All Files (*.*)"):
    """
    Simple open dialog in Maya
    Args:
        starting_directory (unicode): Starting directory. (default: project root directory)
        title (unicode): Dialog title. (default: "Save as...")
        file_filter (unicode): File filter. (default: "All Files (*.*)")

    Returns:
        Path (unicode) to open
    """
    if not starting_directory:
        starting_directory = cmds.workspace(rd=True, q=True)
    open_path = cmds.fileDialog2(fileFilter=file_filter, fileMode=1,
                                 startingDirectory=starting_directory,
                                 cap=title, dialogStyle=2)
    if not open_path:
        display_error("No path specified", True)
    return open_path[0]


######################################################################################
# MAYA UTILITIES
######################################################################################
def create_empty_node(input_name):
    """
    Creates a completely empty node
    Args:
         input_name (unicode): Name of the new empty node
    """
    cmds.select(cl=True)
    cmds.group(em=True, name=input_name)
    node_name = cmds.ls(sl=True)
    keyable_attributes = cmds.listAttr(node_name, k=True)
    for attribute in keyable_attributes:
        cmds.setAttr('{0}.{1}'.format(node_name[0], attribute), l=True, k=False)


def get_node_data(node_name, settable=True, quiet=False):
    """
    Returns the node data in a dictionary
    Args:
        node_name (unicode): Name of the node to get data from
        settable (bool): Only the data that can be set (default: bool)
        quiet (bool):

    Returns:
        Dictionary containing a dictionary with attribute: value
    """
    data = dict()
    node_attrs = cmds.listAttr(node_name, settable=settable)
    for attr in node_attrs:
        try:
            if cmds.attributeQuery(attr, node=node_name, attributeType=True) != "compound":
                data[attr] = cmds.getAttr("{}.{}".format(node_name, attr))
            else:
                for sub_attr in cmds.attributeQuery(attr, node=node_name, listChildren=True):
                    data[sub_attr] = cmds.getAttr("{}.{}".format(node_name, sub_attr))
        except RuntimeError as err:
            if not quiet:
                print("get_node_data() -> Couldn't get {}.{} because of: {}".format(node_name, attr, err))
    return data


def set_node_data(node_name, node_data):
    """
    Sets the node data contained in a dictionary
    Args:
        node_name (unicode): Name of the node to set data to
        node_data (dict): Dictionary of node data {attribute: value}
    """
    for attr in node_data:
        set_attr(node_name, attr, node_data[attr])


def purge_missing(objects):
    """
    Deletes non-existing objects within a list of objects
    Args:
        objects []: List of objects to check
    Returns:
        List of existing objects
    """
    objs = []
    for obj in objects:
        if isinstance(obj, list) or isinstance(obj, tuple):
            objs.extend(purge_missing(obj))
        else:
            if cmds.objExists(obj):
                objs.append(obj)
    return objs


def get_active_model_panel():
    """
    Get the active model editor panel
    Returns:
        modelPanel name (unicode)
    """
    active_panel = cmds.getPanel(wf=True)
    if cmds.getPanel(typeOf=active_panel) == 'modelPanel':
        return active_panel
    else:
        return cmds.playblast(ae=True)


def detach_shelf():
    """
    Detaches the current shelves
    """
    shelf_top_level = mel.eval('$tempMelVar=$gShelfTopLevel')
    shelf_name = cmds.shelfTabLayout(shelf_top_level, st=True, q=True)
    shelf_paths = os.path.abspath(cmds.internalVar(ush=True)).split(';')
    shelf_file = "shelf_{0}.mel".format(shelf_name)

    # find path of shelf
    shelf_file_path = ""
    for shelfPath in shelf_paths:
        files = os.listdir(shelfPath)
        if shelf_file in files:
            shelf_file_path = os.path.join(shelfPath, shelf_file)
    if not shelf_file_path:
        display_error("Can't detach shelf, try closing Maya with the shelf open and try again")
        return

    # read mel shelf file
    with open(shelf_file_path, 'r') as shelf_file:
        text = shelf_file.read()
    # build new mel command
    mel_commands = ""
    buttons = 0
    lines = [line for line in text.splitlines() if line]  # get rid of empty lines
    for line in lines:
        if line.strip() == "shelfButton":
            buttons += 1
        if buttons > 0:
            mel_commands += line
    mel_commands = mel_commands[:-2]

    # check if window doesn't already exist
    window_title = "{} popup shelf".format(shelf_name)
    window_name = "{}_popup_shelf".format(shelf_name)
    if cmds.window(window_name, exists=True):
        cmds.showWindow(window_name)
        return

    # make a window, give it a layout, then make a model editor
    window = cmds.window(window_title, w=800, h=46, rtf=True)
    cmds.shelfLayout(spa=5)
    mel.eval(mel_commands)
    cmds.setParent('..')

    # show window
    cmds.window(window, w=46 * buttons, e=True)
    cmds.showWindow(window)


def delete_shelves(shelves_dict=None, restart=True):
    """
    Delete shelves specified in dictionary
    Args:
        shelves_dict (dict): Dictionary of shelf name and mel file without prefix: e.g. {"Animation" : "Animation.mel"}
        restart (bool): If a restart dialog should appear in the end
    """
    env_dir = get_env_dir()
    if not shelves_dict:
        cmds.error('No shelf array given')
    # Maya creates all default shelves in prefs only after each has been opened (initialized)
    for shelf in shelves_dict:
        try:
            mel.eval('jumpToNamedShelf("{0}");'.format(shelf))
        except:
            continue
    mel.eval('saveAllShelves $gShelfTopLevel;')  # all shelves loaded (save them)
    # time to delete them
    shelf_top_level = mel.eval('$tempMelVar=$gShelfTopLevel') + '|'
    for shelf in shelves_dict:
        shelf_layout = shelves_dict[shelf].split('.mel')[0]
        if cmds.shelfLayout(shelf_top_level + shelf_layout, q=True, ex=True):
            cmds.deleteUI(shelf_top_level + shelf_layout, layout=True)
    # mark them as deleted to avoid startup loading
    shelf_dir = os.path.join(env_dir, 'prefs', 'shelves')
    for shelf in shelves_dict:
        shelf_name = os.path.join(shelf_dir, 'shelf_' + shelves_dict[shelf])
        deleted_shelf_name = shelf_name + '.deleted'
        if os.path.isfile(shelf_name):
            # make sure the deleted file doesn't already exist
            if os.path.isfile(deleted_shelf_name):
                os.remove(shelf_name)
                continue
            os.rename(shelf_name, deleted_shelf_name)
    if restart:
        dialog_restart()


def restore_shelves():
    """ Restores previously deleted shelves """
    shelf_dir = os.path.join(get_env_dir(), 'prefs', 'shelves')
    for shelf in os.listdir(shelf_dir):
        if shelf.endswith('.deleted'):
            restored_shelf = os.path.join(shelf_dir, shelf.split('.deleted')[0])
            deleted_shelf = os.path.join(shelf_dir, shelf)
            # check if it has not been somehow restored
            if os.path.isfile(restored_shelf):
                os.remove(deleted_shelf)
            else:
                os.rename(deleted_shelf, restored_shelf)
    dialog_restart()


def get_shapes(objects, renderable=False, l=False, quiet=False):
    """
    Get shapes of objects/components
    Args:
        objects (list): List of objects or components
        renderable (bool): If shape needs to be renderable
        l (bool): If full path is desired or not
        quiet (bool): If command should print errors or not
    Returns:
        (list): List of shapes
    """
    # transform string input (if any) to a list
    if isinstance(objects, basestring):
        objects = [objects]

    objs = set()
    for comp in objects:
        objs.add(comp.split(".")[0])  # to also work with components of multiple objects
    if not objs:
        if not quiet:
            print_error("Please select a mesh or component to extract the shape from")
            return []

    objs = purge_missing(objs)  # make sure all objects exist

    shapes = []
    for obj in objs:
        potential_shape = []
        # check if its a mesh object
        obj_type = cmds.objectType(obj)
        if obj_type == "mesh" or obj_type == "nurbsSurface":
            potential_shape = cmds.ls(obj, l=l)  # make an array
        else:
            potential_shape = cmds.listRelatives(obj, shapes=True, noIntermediate=True, path=True, fullPath=l) or []
            # shapes.extend(shp)
        # check if renderable
        if renderable and potential_shape:
            if not is_renderable(potential_shape[0]):
                continue
        # add potential shape to list
        shapes.extend(potential_shape)

    if not shapes and not quiet:
        print_warning("No shape nodes found in {0}".format(objects))

    return shapes


def is_renderable(obj, quiet=True):
    """
    Checks if object is renderable
    Args:
        obj (unicode): Name of object to verify
        quiet (bool): If the function should keep quiet (default=True)
    Returns:
        (bool) if its renderable or not
    """
    # unit test
    # make sure we are not working with components/attributes
    obj = cmds.ls(obj, objectsOnly=True, l=True)
    if isinstance(obj, list) or isinstance(obj, tuple):
        if len(obj) == 1:
            obj = obj[0]
        else:
            logger.error("isRenderable - {0} cannot be checked".format(obj))
            return False
    if not cmds.objExists(obj):
        if not quiet:
            logger.error("{0} does not exist, skipping it".format(obj))
        return False
    # doIt
    if cmds.getAttr("{0}.template".format(obj)):
        if not quiet:
            logger.error("{0} is a template object, skipping it".format(obj))
        return False
    if not cmds.getAttr("{0}.visibility".format(obj)):
        # Let's check if it has any in-connection (its animated)
        if not cmds.listConnections("{0}.visibility".format(obj)):
            if not quiet:
                logger.error("{0} is not visible, skipping it".format(obj))
            return False
    if not cmds.getAttr("{0}.lodVisibility".format(obj)):
        # Let's check if it has any in-connection (its animated)
        if not cmds.listConnections("{0}.lodVisibility".format(obj)):
            if not quiet:
                logger.error("{0} has no lodVisibility, skipping it".format(obj))
            return False
    # TODO Display layer override check
    renderable = True
    # check parents
    parent = cmds.listRelatives(obj, parent=True, path=True)
    if parent:
        renderable = renderable and is_renderable(parent[0])
    return renderable


def get_transforms(objects, full_path=False):
    """
    Get transform nodes of objects
    Args:
        objects (list): List of objects
        full_path (bool): If full path or not
    Returns:
        List of transform nodes
    """
    transforms = []
    for node in objects:
        transforms.append(get_transform(node, full_path))
    return transforms


def get_transform(node, full_path=False):
    """
    Get transform node of object
    Args:
        node (unicode): Name of node
        full_path (bool): If full path or not
    Returns:
        Name of transform node
    """
    if 'transform' != cmds.nodeType(node):
        return cmds.listRelatives(node, fullPath=full_path, parent=True)[0]
    else:
        return node


def copy_attributes(attributes):
    """
    Batch copy attributes of first selected object to the rest of selected objects:
    e.g. lib.copyAttributes(['jointOrientX', 'jointOrientY', 'jointOrientZ'])
    Args:
        attributes (list): List of attributes (unicode)
    """
    selected = cmds.ls(sl=True)
    if selected:
        source = selected.pop(0)
        for attribute in attributes:
            source_value = cmds.getAttr("{0}.{1}".format(source, attribute))
            for target in selected:
                set_attr(target, attribute, source_value)


def set_attr(obj, attr, value, silent=False):
    """
    Generic setAttr convenience function which changes the Maya command depending on the data type
    Args:
        obj (unicode): node
        attr (unicode): attribute
        value (any): the value to set
        silent (bool): if the function is silent when errors occur
    """
    try:
        if isinstance(value, basestring):
            cmds.setAttr("{0}.{1}".format(obj, attr), value, type="string")
        elif isinstance(value, list) or isinstance(value, tuple):
            if len(value) == 3:
                cmds.setAttr("{0}.{1}".format(obj, attr), value[0], value[1], value[2], type="double3")
            elif len(value) == 2:
                cmds.setAttr("{0}.{1}".format(obj, attr), value[0], value[1], type="double2")
            elif len(value) == 1:
                # check for list within a list generated by getAttr command
                if isinstance(value[0], list) or isinstance(value[0], tuple):
                    set_attr(obj, attr, value[0])
                    return
                cmds.setAttr("{0}.{1}".format(obj, attr), value[0])
            elif cmds.attributeQuery(attr, node=obj, attributeType=True) == "compound":
                idx = 0
                for sub_attr in cmds.attributeQuery(attr, node=obj, listChildren=True):
                    set_attr(obj, sub_attr, value[idx])
                    idx += 1
            else:
                cmds.setAttr("{0}.{1}".format(obj, attr), tuple(value), type="doubleArray")
        else:
            cmds.setAttr("{0}.{1}".format(obj, attr), value)
        return True
    except RuntimeError:
        if not silent:
            cmds.warning("{0}.{1} could not be set to {2}.".format(obj, attr, value))
            logger.debug("Attribute of type: {0}.".format(type(value)))
        return False


def get_next_free_multi_index(node, attr, idx=0):
    """
    Find the next unconnected multi index starting at the passed index
    Args:
        node (unicode): node to search in
        attr (unicode): attribute to search in
        idx (int): starting index to search from
    Returns:
        The next free index
    """
    while idx < 10000000:  # assume a max of 10 million connections
        if len(cmds.listConnections('{0}.{1}[{2}]'.format(node, attr, idx)) or []) == 0:
            return idx
        idx += 1
    # No connections means the first index is available
    return 0


def get_next_free_multi_index_considering_children(node, attr, idx=0):
    """
    Find the next unconnected multi index, considering children attributes, starting at the passed index
    Args:
        node (unicode): node to search in
        attr (unicode): attribute to search in
        idx (int): starting index to search from
    Returns:
        The next free index
    """
    while idx < 10000000:  # assume a max of 10 million connections
        if len(cmds.listConnections('{0}.{1}[{2}]'.format(node, attr, idx)) or []) == 0:
            free = True
            child_attrs = cmds.attributeQuery(attr, n=node, listChildren=True) or []
            for childAttr in child_attrs:
                if cmds.attributeQuery(childAttr, n="{0}.{1}".format(node, attr), multi=True):
                    if get_next_free_multi_index_considering_children("{0}.{1}[{2}]".format(node, attr, idx),
                                                                      childAttr) > 0:
                        free = False
                        break
            if free:
                return idx
        idx += 1
    # No connections means the first index is available
    return 0


def distance_between(obj1, obj2):
    """
    Distance between objects
    Args:
        obj1 (unicode): object 1
        obj2 (unicode): object 2

    Returns:
        Distance between the objects (in world space)
    """
    v1_world = cmds.xform('{0}'.format(obj1), q=True, worldSpace=True, piv=True)  # list with 6 elements
    v2_world = cmds.xform('{0}'.format(obj2), q=True, worldSpace=True, piv=True)  # list with 6 elements
    return distance(v1_world, v2_world)


def snap(source='', targets=None, snap_type="translation"):
    """
    Snap targets objects to source object
    If not specified, the first selected object is considered as source, the rest as targets
    Args:
        source (unicode): Source transform name
        targets (list): List of target transform names (unicode)
        snap_type: Either "translation" (default), "rotation" or "position" (translation + rotation)
    Note:
        Targets should not have their transformations frozen
    """
    # check if there are source and targets defined/selected
    if not source:
        selected = cmds.ls(sl=True)
        if selected:
            source = selected.pop(0)
            if not targets:
                targets = selected
        else:
            cmds.error("No source specified or selected.")
    if not targets:
        targets = cmds.ls(sl=True)
    else:
        if isinstance(targets, basestring):
            targets = [targets]
    if not targets:
        cmds.error("No targets to snap defined or selected")

    # using xform brings pr
    # proceed to snap
    if snap_type == "translation":
        world_translate_xform = cmds.xform('{0}'.format(source), q=True, worldSpace=True,
                                           piv=True)  # list with 6 elements
        for target in targets:
            cmds.xform('{0}'.format(target), worldSpace=True,
                       t=(world_translate_xform[0], world_translate_xform[1], world_translate_xform[2]))
        print_info("Translation snapped")

    if snap_type == "rotation":
        source_xform = cmds.xform('{0}'.format(source), q=True, worldSpace=True, ro=True)
        for target in targets:
            cmds.xform('{0}'.format(target), worldSpace=True, ro=(source_xform[0], source_xform[1], source_xform[2]))
        print_info("Rotation snapped")

    if snap_type == "position":
        source_pos = cmds.xform('{0}'.format(source), q=True, worldSpace=True, piv=True)  # list with 6 elements
        source_rot = cmds.xform('{0}'.format(source), q=True, worldSpace=True, ro=True)
        for target in targets:
            cmds.xform('{0}'.format(target), worldSpace=True, t=(source_pos[0], source_pos[1], source_pos[2]))
            cmds.xform('{0}'.format(target), worldSpace=True, ro=(source_rot[0], source_rot[1], source_rot[2]))
        print_info("Position snapped")


######################################################################################
# RENDERING UTILITIES
######################################################################################
IMGFORMATS = {'.jpg': 8, '.png': 32, '.tif': 3, '.exr': 40, '.iff': 7}
IMGFORMATS_ORDER = ['.png', '.jpg', '.exr', '.tif', '.iff']
QUALITIES_ORDER = {'Standard', 'FXAA', '4x SSAA', 'TAA'}


def is_component(obj):
    """
    Check if an object is a component or not
    Args:
        obj (unicode): Object name to check if its a component

    Returns:
        (bool): True if it is a component
    """
    if "." in obj:
        return True
    return False


def set_vertex_color_sets(shapes, color_sets, value=None):
    """
    Set and create vertex color sets on shapes
    Args:
        shapes (list): Shapes to delete vertex color sets from
        color_sets (list): Vertex color sets to delete
        value (list): List of values to set (default [0.0, 0.0, 0.0, 0.0])
    Warning: Saving vertex colors using the Maya API doesn't save on references
    """
    # unit tests
    if isinstance(shapes, basestring):
        shapes = [shapes]
    if isinstance(color_sets, basestring):
        color_sets = [color_sets]
    if value is None:
        value = [0.0, 0.0, 0.0, 0.0]
    # doIt
    for shape in shapes:
        if cmds.objectType(shape) != "mesh":
            print_info("{0} is not a mesh, skipping it".format(shape))
            continue
        shape_color_sets = cmds.polyColorSet(shape, query=True, allColorSets=True) or []
        for colorSet in color_sets:
            if colorSet not in shape_color_sets:
                logger.debug("Creating {0} vertex color set for {1}".format(colorSet, shape))
                cmds.polyColorSet(shape, cs=colorSet, representation="RGBA", create=True)
            o_shape = get_m_object(shape)
            fn_mesh = om.MFnMesh(o_shape)  # access mesh data (oShape can also be replaced by MDagPath of shape)
            o_vertex_color_array = fn_mesh.getVertexColors(colorSet)  # MColorArray
            vertex_list_length = len(o_vertex_color_array)
            vertex_index_array = list(xrange(vertex_list_length))
            for vertex in vertex_index_array:
                o_vertex_color_array[vertex].r = value[0]
                o_vertex_color_array[vertex].g = value[1]
                o_vertex_color_array[vertex].b = value[2]
                o_vertex_color_array[vertex].a = value[3]
            fn_mesh.setCurrentColorSetName(colorSet)
            fn_mesh.setVertexColors(o_vertex_color_array, vertex_index_array)
            # with face vertex color
            """
            # get mesh data
            faceIndexArray = list()
            localVertexIndexArray = list()
            vertexColorArray = list()
            emptyColor = om.MColor([0.0, 0.0, 0.0, 0.0])
            itComponent = om.MItMeshFaceVertex(oShape)
            while not itComponent.isDone():
                #localVertexIndexArray.append(itComponent.faceVertexId())
                localVertexIndexArray.append(itComponent.vertexId())
                faceIndexArray.append(itComponent.faceId())
                vertexColorArray.append(emptyColor)
                itComponent.next()
            # set color data=
            fnMesh.setCurrentColorSetName(colorSet)
            fnMesh.setFaceVertexColors(vertexColorArray, faceIndexArray, localVertexIndexArray)
            """
            logger.info("Vertex color set {0} set for: {1}".format(colorSet, shape))
        delete_color_set_history(shape)


@undo
def delete_vertex_color_sets(shapes, color_sets, quiet=True):
    """
    Delete the vertex color set and its history
    Args:
        shapes (list): Shapes to delete vertex color sets from
        color_sets (list): Vertex color sets to delete
        quiet (bool): If the function should prompt debug messages
    """
    if quiet:
        logger.setLevel(logging.INFO)
    shapes = u_enlist(shapes)  # put in list
    color_sets = u_enlist(color_sets)  # put in list
    for shape in shapes:
        shape_color_sets = cmds.polyColorSet(shape, query=True, allColorSets=True) or []
        for colorSet in color_sets:
            if colorSet in shape_color_sets:
                cmds.polyColorSet(shape, colorSet=colorSet, delete=True)
                history = cmds.listHistory(shape)
                nodes2delete = []
                for node in history:
                    # check if attribute exists
                    if not cmds.attributeQuery('colorSetName', n=node, ex=True):
                        continue
                    # attribute exists, check name of color set name
                    color_set_name = cmds.getAttr("{0}.colorSetName".format(node))
                    if color_set_name == colorSet:
                        nodes2delete.append(node)
                        logger.debug("{0} node scheduled for deletion".format(node))
                if nodes2delete:
                    cmds.delete(nodes2delete)
                logger.debug("Vertex color set {0} deleted for: {1}".format(colorSet, shape))
    logger.setLevel(logging.DEBUG)


def bake_vertex_colors(shapes):
    """
    Bake vertex colors into shape nodes (not working, set issue in AREA Forum)
    https://forums.autodesk.com/t5/maya-programming/baking-vertex-colors-onto-shape-node/td-p/9119416
    Args:
        shapes (list): Shapes to bake vertex colors
    """
    # unit tests
    if isinstance(shapes, basestring):
        shapes = [shapes]
    # doIt
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
                set_attr(shape, "colorSet[{0}].colorName".format(color_set_index), color_set_name)
                set_attr(shape, "colorSet[{0}].representation".format(color_set_index), representation)
                set_attr(shape, "colorSet[{0}].clamped".format(color_set_index), clamped)
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
                    for v in vertices:
                        mel_cmd += " {0}".format(fv)
                        fv += 1
                mel_cmd += ';'
                print(mel_cmd)
                mel.eval(mel_cmd)  # we run the mel command here
                # delete polyColorPerVertex nodes that pertain this colorSet
                cmds.delete(node)
                logger.debug("Vertex color set {0} baked on {1}".format(color_set_name, shape))
            if cmds.objectType(node) == "createColorSet":
                cmds.delete(node)  # no need for them in history


def delete_color_set_history(shapes=None):
    """
    Deletes unnecessary history nodes created by color sets
    Args:
        shapes (unicode, list): shapes to delete history nodes from
    """
    if shapes is None:
        return
    shapes = u_enlist(shapes)  # unit tests
    nodes2delete = []
    for shape in shapes:
        # go through history
        history = cmds.listHistory(shape)
        for node in history:
            if cmds.objectType(node) == "createColorSet":
                nodes2delete.append(node)
    if nodes2delete:
        cmds.delete(nodes2delete)
        # logger.debug("Deleted the following nodes {0}".format(nodes2Delete))


def change_texture_path(path):
    """
    Change all texture paths
    Useful when moving around the textures of the scene
    Args:
        path (string): Relative path from project (e.g. "sourceimages/house")
    """
    all_file_nodes = cmds.ls(et='file')
    for node in all_file_nodes:
        file_path = cmds.getAttr("{0}.fileTextureName".format(node))
        file_name = os.path.basename(file_path)
        cmds.setAttr("{0}.fileTextureName".format(node), "{0}/{1}".format(path, file_name), type='string')


def screenshot(file_dir, width, height, img_format=".jpg", override="", ogs=True):
    # check if fileDir has image format
    if img_format not in file_dir:
        file_dir += img_format

    # get existing values
    prev_format = cmds.getAttr("defaultRenderGlobals.imageFormat")
    prev_override = cmds.getAttr("hardwareRenderingGlobals.renderOverrideName")

    # set render settings
    cmds.setAttr("defaultRenderGlobals.imageFormat", IMGFORMATS[img_format])
    if override:
        cmds.setAttr("hardwareRenderingGlobals.renderOverrideName", override, type="string")

    if ogs:
        # render viewport
        rendered_dir = cmds.ogsRender(cv=True, w=width, h=height)  # render the frame
        shutil.move(os.path.abspath(rendered_dir), os.path.abspath(file_dir))  # move to specified dir
    else:
        frame = cmds.currentTime(q=True)
        cmds.playblast(cf=file_dir, fo=True, fmt='image', w=width, h=height,
                       st=frame, et=frame, v=False, os=True)

    # bring everything back to normal
    cmds.setAttr("defaultRenderGlobals.imageFormat", prev_format)
    cmds.setAttr("hardwareRenderingGlobals.renderOverrideName", prev_override, type="string")

    print_info("Image saved successfully in {0}".format(file_dir))
    return file_dir


#    __  __                           _    ____ ___     ____    ___
#   |  \/  | __ _ _   _  __ _        / \  |  _ \_ _|   |___ \  / _ \
#   | |\/| |/ _` | | | |/ _` |      / _ \ | |_) | |      __) || | | |
#   | |  | | (_| | |_| | (_| |     / ___ \|  __/| |     / __/ | |_| |
#   |_|  |_|\__,_|\__, |\__,_|    /_/   \_\_|  |___|   |_____(_)___/
#                 |___/
def get_m_object(node, getType=False):
    """
    Gets mObject of a node (Python API 2.0)
    Args:
        node (unicode): name of node
    Returns:
        Node of the object
    """
    selection_list = om.MSelectionList()
    selection_list.add(node)
    o_node = selection_list.getDependNode(0)
    if not getType:
        return o_node
    else:
        return o_node.apiTypeStr


def schedule_refresh_all_views():
    """ Schedules a refresh of all views """
    import maya.OpenMayaUI as omUI
    omUI.M3dView.scheduleRefreshAllViews()


def print_info(info):
    """
    Prints the information statement in the command response (to the right of the command line)
    Args:
        info (unicode): Information to be displayed
    """
    om.MGlobal.displayInfo(info)


def display_info(info):
    """
    Displays the information on the viewport
    Prints the information statement in the command response (to the right of the command line)
    Args:
        info (unicode): Information to be displayed
    """
    if get_maya_version() > 2018:
        m = '<span style="color:#82C99A;">{}</span>'.format(info)
        cmds.inViewMessage(msg=m, pos="midCenter", fade=True)
    print_info(info)


def print_warning(warning):
    """
    Prints the warning statement in the command response (to the right of the command line)
    Args:
        warning (unicode): Warning to be displayed
    """
    om.MGlobal.displayWarning(warning)


def display_warning(warning):
    """
    Displays a warning on the viewport
    Prints the warning statement in the command response (to the right of the command line)
    Args:
        warning (unicode): Warning to be displayed
    """
    if get_maya_version() > 2018:
        m = '<span style="color:#F4FA58;">Warning: </span><span style="color:#DDD">{}</span>'.format(warning)
        cmds.inViewMessage(msg=m, pos="midCenter", fade=True)
    print_warning(warning)


def print_error(error, show_traceback=False):
    """
    Prints the error statement in the command response (to the right of the command line)
    Args:
        error (unicode): Error to be displayed
        show_traceback (bool): If the error should stop the execution and show a traceback
    """
    if not show_traceback:
        om.MGlobal.displayError(error)
    else:
        cmds.evalDeferred(lambda: print_error(error))
        raise RuntimeError(error)


def display_error(error, show_traceback=False):
    """
    Displays an error on the viewport
    Prints the error statement in the command response (to the right of the command line)
    Args:
        error (unicode): Error to be displayed
        show_traceback (bool): If python should error our and show a traceback
    """
    if get_maya_version() > 2018:
        m = '<span style="color:#F05A5A;">Error: </span><span style="color:#DDD">{}</span>'.format(error)
        cmds.inViewMessage(msg=m, pos="midCenterBot", fade=True)
    print_error(error, show_traceback)


#                _   _
#    _ __   __ _| |_| |__
#   | '_ \ / _` | __| '_ \
#   | |_) | (_| | |_| | | |
#   | .__/ \__,_|\__|_| |_|
#   |_|
class Path(object):
    def __init__(self, path):
        if isinstance(path, str):
            self.path = path.decode(sys.getfilesystemencoding())
        elif isinstance(path, unicode):
            self.path = path
        else:
            print_error("{} is not a string".format(path), True)

    def parent(self):
        """
        Navigates to the parent of the path
        """
        self.path = os.path.abspath(os.path.join(self.path, os.pardir))
        return self

    def child(self, child):
        """
        Joins the child to the path
        Args:
            child: folder to join to the path
        """
        self.path = os.path.abspath(os.path.join(self.path, child))
        return self

    def create_dir(self):
        """
        Creates the directory of the path, if it doesn't exist already
        """
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        return self

    def delete(self):
        """
        Deletes all contents of current Path
        Returns:
            Path (obj): parent of current path
        """
        if self.exists():
            import shutil
            try:
                shutil.rmtree(self.path)
            except:
                # it is most likely a file
                os.remove(self.path)
        return self

    def basename(self):
        """
        Returns the basename of the path
        """
        return os.path.basename(self.path)

    def exists(self):
        """
        Returns if current path exists or not
        Returns:
            bool
        """
        return os.path.exists(self.path)

    def swap_extension(self, new_extension):
        """
        Swaps the current file extension, if available
        Returns:
            Path (obj): modified path obj
        """
        self.path, ext = os.path.splitext(self.path)
        self.path += new_extension
        return self

    def slash_path(self):
        """
        Returns the path with forward slashes
        Returns:
            path (unicode): path with forward slashes
        """
        return self.path.replace(os.sep, '/')

    def list_dir(self):
        """
        List everything in a directory - files and directories.
        Returns:
            (list): list with everything in the directory
        """
        return os.listdir(self.path)

    def find_all(self, filename, relative=True):
        """
        Finds the filename and lists its locations in the Path.
        Returns:
            (list): list with everything in the directory
        """
        found = []
        for root, dirs, files in os.walk(self.path):
            if filename in files:
                found.append(os.path.join(root, filename))
        if relative:
            return [os.path.relpath(f, self.path) for f in found]
        else:
            return found

    def file_size(self):
        """
        Returns the file size of the path in MB
        Returns:
            (float): Size of the file in MB
        """
        if self.exists():
            return os.path.getsize(self.path) / 1024.0 / 1024.0
        return 0


#        _        _
#    ___| |_ _ __(_)_ __   __ _
#   / __| __| '__| | '_ \ / _` |
#   \__ \ |_| |  | | | | | (_| |
#   |___/\__|_|  |_|_| |_|\__, |
#                         |___/
def to_camel_case(text):
    """
    Converts text to camel case, e.g. ("the camel is huge" => "theCamelIsHuge")
    Args:
        text (string): Text to be camel-cased
    """
    camel_case_text = text
    splitter = text.split()
    if splitter:
        camel_case_text = splitter[0]
        for index in xrange(1, len(splitter)):
            camel_case_text += splitter[index].capitalize()
    return camel_case_text


def de_camelize(text):
    """
    Converts camel case to normal case, e.g. ("theCamelIsHuge" => "the camel is huge")
    Args:
        text (string): Text to be decamelized
    """
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1 \2', text)
    return re.sub('([a-z0-9])([A-Z])', r'\1 \2', s1).title()


#                    _   _
#    _ __ ___   __ _| |_| |__
#   | '_ ` _ \ / _` | __| '_ \
#   | | | | | | (_| | |_| | | |
#   |_| |_| |_|\__,_|\__|_| |_|
#
def clamp(min_v, max_v, value):
    """
    Clamps a value between a min and max value
    Args:
        min_v: Minimum value
        max_v: Maximum value
        value: Value to be clamped

    Returns:
        Returns the clamped value
    """
    return min_v if value < min_v else max_v if value > max_v else value


def lerp(value1=0.0, value2=1.0, parameter=0.5):
    """
    Linearly interpolates between value1 and value2 according to a parameter.
    Args:
        value1: First interpolation value
        value2: Second interpolation value
        parameter: Parameter of interpolation

    Returns:
        The linear intepolation between value 1 and value 2
    """
    return value1 + parameter * (value2 - value1)


def saturate(value):
    """
    Saturates the value between 0 and 1
    Args:
        value: Value to be saturated

    Returns:
    The saturated value between 0 and 1
    """
    return clamp(0.0, 1.0, value)


def linstep(min_v=0.0, max_v=1.0, value=0.5):
    """
    Linear step function
    Args:
        min_v: minimum value
        max_v: maximum value
        value: value to calculate the step in

    Returns:
        The percentage [between 0 and 1] of the distance between min and max (e.g. linstep(1, 3, 2.5) -> 0.75).
    """
    return saturate((value - min_v) / (max_v - min_v))


def distance(v1, v2):
    """
    Distance between vectors v1 and v2
    Args:
        v1 (list): vector 1
        v2 (list): vector 2

    Returns:
        Distance between the vectors
    """
    v1_v2 = [v2[0] - v1[0], v2[1] - v1[1], v2[2] - v1[2]]
    return math.sqrt(v1_v2[0] * v1_v2[0] + v1_v2[1] * v1_v2[1] + v1_v2[2] * v1_v2[2])


def remap(value, old_min, old_max, new_min, new_max):
    """
    Remaps the value to a new min and max value
    Args:
        value: value to remap
        old_min: old min of range
        old_max: old max of range
        new_min: new min of range
        new_max: new max of range

    Returns:
        The remapped value in the new range
    """
    return new_min + (((value - old_min) / (old_max - old_min)) * (new_max - new_min))


#
#    _ __   __ _ _ __ ___   ___  ___ _ __   __ _  ___ ___  ___
#   | '_ \ / _` | '_ ` _ \ / _ \/ __| '_ \ / _` |/ __/ _ \/ __|
#   | | | | (_| | | | | | |  __/\__ \ |_) | (_| | (_|  __/\__ \
#   |_| |_|\__,_|_| |_| |_|\___||___/ .__/ \__,_|\___\___||___/
#                                   |_|
def get_namespaces(objects=None):
    """
    Get a list of all namespaces within objects or of the entire scene
    Args:
        objects (unicode, list): List of objects to get namespaces from

    Returns:
        List of namespaces
    """
    # if no objects were specified
    if not objects:
        # get all namespaces in the scene
        namespaces = cmds.namespaceInfo(listOnlyNamespaces=True, recurse=True)
        try:
            namespaces.remove('UI')
        except ValueError:
            pass
        try:
            namespaces.remove('shared')
        except ValueError:
            pass
    else:
        # in case a string is passed as argument, enlist it
        if isinstance(objects, basestring):
            objects = [objects]

        # get namespaces of objects
        namespaces = []
        for obj in objects:
            namespace = obj.rpartition(':')[0]
            if namespace:
                namespaces.append(namespace)

    namespaces = set(namespaces)  # make sure only one entry in list

    return list(namespaces)


def change_namespace(object_name, change_dict):
    """
    Changes the namespaces of the object
    Args:
        object_name (unicode): Name to change namespace
        change_dict (dict): Dictionary of keys {str), values (unicode) to change namespaces to (key->value)

    Returns:
        String with the namespaces changed
    """
    namespace = get_namespaces(object_name)
    if namespace:
        namespace = namespace[0] + ":"
        if namespace in change_dict:
            object_name = object_name.replace(namespace, change_dict[namespace])
    return object_name


def remove_namespace_from_string(object_name):
    """
    Removes the namespace from string
    Args:
        object_name (unicode): Object name to remove namespace from

    Returns:
        String: New name without namespaces
    """
    if len(object_name) == 1:
        object_name = object_name[0]

    if isinstance(object_name, basestring):
        parts = object_name.split(':')
        if len(parts) > 1:
            return parts[-1]
        return parts[-1]
    else:
        print_warning("No string found in {0}".format(object_name))
        return ""


#                _ _       _            _
#    _   _ _ __ (_) |_    | |_ ___  ___| |_ ___
#   | | | | '_ \| | __|   | __/ _ \/ __| __/ __|
#   | |_| | | | | | |_    | ||  __/\__ \ |_\__ \
#    \__,_|_| |_|_|\__|    \__\___||___/\__|___/
#
def u_enlist(arg, silent=True):
    """
    Unit test to check if given argument is not a list
    Args:
        arg: argument to put into a list
        silent (bool): If the function should print warnings if the wrong data was given (default=False)
    Returns:
        List: The argument in a list
    """
    if isinstance(arg, basestring):
        if not silent:
            logger.info("{0} is a string, enlisting it".format(arg))
        return [arg]
    elif isinstance(arg, int):
        if not silent:
            logger.info("{0} is an int, enlisting it".format(arg))
        return [arg]
    return arg


def u_stringify(arg, silent=False):
    """
    Unit test to check if given argument is not a string
    Args:
        arg: argument to put into a string
        silent (bool): If the function should print warnings if the wrong data was given (default=False)
    Returns:
        String: The argument in a string
    """
    if isinstance(arg, list) or isinstance(arg, tuple):
        if not silent:
            logger.info("{0} is a list/tuple, taking first element".format(arg))
        arg = arg[0]
    return arg


def u_internet():
    """
    Unit test to check if computer has internet connection
    Returns:
        Bool: True if computer has internet
    """
    try:
        import httplib
    except ImportError:
        import http.client as httplib
    conn = httplib.HTTPConnection("microsoft.com", timeout=5)
    try:
        conn.request("HEAD", "/")
        conn.close()
        return True
    except:
        conn.close()
        return False


#        _
#    ___(_)_ __
#   |_  / | '_ \
#    / /| | |_) |
#   /___|_| .__/
#         |_|
def save_zip():
    """
    Compress the saved opened scene file within the same directory
    Returns:
        Path (unicode): Path to saved zip file
    """
    import zipfile
    file_name = cmds.file(q=True, sn=True, shn=True)
    if not file_name:
        print_error("Current scene has not been saved before")
        return
    file_path = Path(cmds.file(q=True, sn=True))
    zip_path = Path(file_path.path).swap_extension(".zip")
    zip_out = zipfile.ZipFile(zip_path.path, 'w', zipfile.ZIP_DEFLATED)
    try:
        zip_out.write(file_path.path, file_name)
    finally:
        zip_out.close()
        logger.info("Saved scene compressed as: {0}".format(zip_path.path))
    return zip_path.path


#     __ _
#    / _(_)_  _____  ___
#   | |_| \ \/ / _ \/ __|
#   |  _| |>  <  __/\__ \
#   |_| |_/_/\_\___||___/
#
def remove_callback(procedure):
    """
    Remove callbacks that do not exist anymore (created for example from a plugin which you don't have)
    E.g., remove_callback("CgAbBlastPanelOptChangeCallback")
    Args:
        procedure (unicode): Name of callback procedure

    Returns:
    """
    for mp in cmds.getPanel(typ="modelPanel"):
        # Get callback of the model editor
        callback = cmds.modelEditor(mp, query=True, editorChanged=True)
        # If the callback is the erroneous
        if callback == procedure:
            # Remove the callbacks from the editor
            cmds.modelEditor(mp, edit=True, editorChanged="")
            print_info("{0} successfully removed".format(procedure))