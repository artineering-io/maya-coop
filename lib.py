# -*- coding: utf-8 -*-
"""
@summary:       Maya cooperative python library
@run:           import coop.coopLib as clib (suggested)
@license:       MIT
@repository:    https://github.com/artineering-io/maya-coop
"""
from __future__ import print_function
from __future__ import unicode_literals
import os, sys, subprocess, shutil, re, math, traceback, platform
from functools import wraps
import maya.mel as mel
import maya.cmds as cmds
import maya.utils

from . import logger as clog
from . import list as clist

# python api 2.0
import maya.api.OpenMaya as om


maya_useNewAPI = True 


try:
    basestring  # Python 2
except NameError:
    basestring = (str,)  # Python 3

try:
    xrange  # Python 2
except NameError:
    xrange = range  # Python 3

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

LOG = clog.logger("coop.lib")


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
            LOG.debug("[Time elapsed at {0}:    {1:.4f} sec]".format(f.__name__, time_end - time_start))

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


def keep_selection(f):
    """
    Saves and restores the selection after running a function
    Args:
        f: function to be addressed

    Returns:
        wrapped function where the change of selection doesn't matter
    """

    @wraps(f)
    def selection_wrapper(*args, **kwargs):
        try:
            selection = cmds.ls(sl=True, l=True)
            return f(*args, **kwargs)
        except:
            traceback.print_exc()
        finally:
            # after calling the func, restore the previous selection
            cmds.select(selection, r=True)

    return selection_wrapper


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


def get_os_separator():
    """
    Returns the path separator for the operating system (OS) on the local machine
    Returns:
        (unicode): Either ':' or ';'
    """
    sep = ':'  # separator
    if get_local_os() == "win":
        sep = ';'
    return sep


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


def get_scene_name():
    """
    Gets the name of the currently opened scene
    Returns:
        scene_name (unicode): The name of the current scene or "unnamed_scene"
    """
    scene_name = cmds.file(q=True, sn=True, shn=True)
    if scene_name:
        end_idx = scene_name.rfind('.')
        scene_name = scene_name[:end_idx]
    else:
        scene_name = "unnamed_scene"
    return scene_name


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


def run_python_as_admin(py_cmd, close=True):
    """
    Runs a python command in a separate interactive python shell with admin rights prompt
    Args:
        py_cmd (unicode): One liner python command
        close (bool): Close python shell if no errors occurred
    """
    import ctypes
    py_cmd = py_cmd.rstrip()
    if close:
        if py_cmd[-1] != ';':
            py_cmd += ';'
        py_cmd += " import os; os.kill(os.getpid(), 9);"
    mayapy = Path(sys.executable).parent().child("mayapy.exe").path
    ctypes.windll.shell32.ShellExecuteW(None, "runas", mayapy,
                                        subprocess.list2cmdline([str("-i"), str("-c"), py_cmd]), None, 1)


def eval_deferred(function, lowestPriority=False):
    """
    Runs a function in a deferred manner (once Maya becomes idle)
    Args:
        function (unicode, func): Function to evaluate
        lowestPriority (bool): True will make this priority lowest (normal is low)
    """
    if lowestPriority is None:
        cmds.evalDeferred(function)
    else:
        try:
            cmds.evalDeferred(function, lowestPriority=True)
        except TypeError:
            maya.utils.executeDeferred(function, lowestPriority=True)


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
        (unicode): Path to save as
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
        title (unicode): Dialog title. (default: "Open file")
        file_filter (unicode): File filter. (default: "All Files (*.*)")

    Returns:
        (unicode): Path to open
    """
    if not starting_directory:
        starting_directory = cmds.workspace(rd=True, q=True)
    open_path = cmds.fileDialog2(fileFilter=file_filter, fileMode=1,
                                 startingDirectory=starting_directory,
                                 cap=title, dialogStyle=2)
    if not open_path:
        display_error("No path specified", True)
    return open_path[0]


def dialog_select_dir(starting_directory="", title="Open file"):
    """
    Simple browse and select dir dialog
    Args:
        starting_directory (unicode): Starting directory. (default: project root directory)
        title (unicode): Dialog title. (default: "Select folder")

    Returns:
        (unicode): Path to selected directory
    """
    if not starting_directory:
        starting_directory = cmds.workspace(rd=True, q=True)
    selected_dir = cmds.fileDialog2(dir=starting_directory,
                                    fileMode=3, cap=title,
                                    dialogStyle=2)
    if not selected_dir:
        display_error("No directory specified", True)
    return selected_dir[0]


def dialog_yes_no(title="Confirmation", message="Are you sure?", icon=""):
    """
    Simple Yes/No confirmation dialog
    Args:
        title (unicode): Title of the dialog (default: Confirmation)
        message (unicode): Dialog message (default: "Are you sure?")
        icon (unicode): "question", "information", "warning" or "critical" (default: "")

    Returns:
        (unicode): "Yes" or "No"
    """
    confirm = cmds.confirmDialog(title=title, message=message,
                                 button=['Yes', 'No'], defaultButton='Yes', cancelButton='No', dismissString='No',
                                 ma='center', icon=icon)
    if confirm == "Yes":
        return True
    return False


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


def get_node_data(node_name, settable=True, visible=False, quiet=False):
    """
    Returns the node data in a dictionary
    Args:
        node_name (unicode): Name of the node to get data from
        settable (bool): Only the data that can be set (default: True)
        visible (bool): Only the data that can be seen (default: False)
        quiet (bool):

    Returns:
        Dictionary containing a dictionary with attribute: value
    """
    data = dict()
    data["name"] = node_name
    data["type"] = cmds.objectType(node_name)
    attr_data = dict()
    node_attrs = cmds.listAttr(node_name, settable=settable, visible=visible)
    for attr in node_attrs:
        try:
            if cmds.attributeQuery(attr, node=node_name, attributeType=True) != "compound":
                attr_data[attr] = cmds.getAttr("{}.{}".format(node_name, attr))
            else:
                for sub_attr in cmds.attributeQuery(attr, node=node_name, listChildren=True):
                    attr_data[sub_attr] = cmds.getAttr("{}.{}.{}".format(node_name, attr, sub_attr))
        except (RuntimeError, ValueError) as err:
            if not quiet:
                print("get_node_data() -> Couldn't get {}.{} because of: {}".format(node_name, attr, err))
    data["attrs"] = attr_data
    return data


def set_node_data(node_data, custom_name=""):
    """
    Sets the node data contained in a dictionary
    Args:
        node_data (dict): Dictionary of node data {attribute: value}
        custom_name (unicode): Custom name of the node to set data to
    """
    if not custom_name:
        custom_name = node_data["name"]
    if not cmds.objExists(custom_name):
        cmds.createNode(node_data["type"], name=custom_name)
    for attr in node_data["attrs"]:
        check_set_attr(custom_name, attr, node_data["attrs"][attr])


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


def get_viewport_render_api():
    """
    Returns:
        (unicode): Either DirectX11, OpenGL or Legacy depending on the active API
    """
    engine = mel.eval("getPreferredRenderingEngine")
    if engine.startswith("DirectX11"):
        return "DirectX11"
    elif engine == "OpenGL":
        return "Legacy"
    return "OpenGL"


def detach_shelf():
    """
    Detaches the current shelves
    """
    shelf_top_level = mel.eval('global string $gShelfTopLevel;\r$tempMelStringVar=$gShelfTopLevel')
    shelf_name = cmds.shelfTabLayout(shelf_top_level, st=True, q=True)
    shelf_paths = os.path.abspath(cmds.internalVar(ush=True)).split(get_os_separator())
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


def get_shapes(objects, renderable=False, l=False, quiet=False):
    """
    Get shapes of objects/components
    Args:
        objects (list, unicode): List of objects or components
        renderable (bool): If shape needs to be renderable
        l (bool): If full path is desired or not
        quiet (bool): If command should print errors or not
    Returns:
        (list): List of shapes
    """
    passed_objs = clist.flatten_list(objects)

    # convert any passed components and avoid duplicates (keeping the order)
    objs = list()
    for obj in passed_objs:
        if is_string(obj):
            obj = obj.split(".")[0]
            if obj not in objs:
                objs.append(obj)
        else:
            print_error("Passing non-string values to get_shapes(): {}".format(objects))

    if not objs and not quiet:
        print_error("No mesh or component to extract the shape from: {}".format(objects))
        return []

    objs = purge_missing(objs)  # make sure all objects exist

    shapes = []
    for obj in objs:
        potential_shape = cmds.ls(obj, shapes=True, l=l)
        if not potential_shape:
            potential_shape = cmds.listRelatives(obj, shapes=True, noIntermediate=True, path=True, fullPath=l) or []
        # check if renderable
        if renderable and potential_shape:
            if not is_renderable(potential_shape[0]):
                continue
        # add potential shape to list
        shapes.extend(potential_shape)

    if not shapes and not quiet:
        print_warning("No shape nodes found in {0}".format(objects))

    return shapes


def get_view_camera(shape=False):
    """
    Get the view camera transform or shape.
    Maya is quite inconsistent on what cmds.lookThru() returns, ergo this function
    Args:
        shape (bool): If the shape should be returned instead of the transform

    Returns:
        (unicode): Transform or shape of the current view camera
    """
    camera = cmds.lookThru(q=True)
    if shape:
        if not cmds.ls(camera, shapes=True):
            camera = get_shapes(camera)
    elif cmds.ls(camera, shapes=True):
        camera = get_transform(camera)
    return u_stringify(camera)


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
            LOG.error("isRenderable - {0} cannot be checked".format(obj))
            return False
    if not cmds.objExists(obj):
        if not quiet:
            LOG.error("{0} does not exist, skipping it".format(obj))
        return False
    # doIt
    if cmds.getAttr("{0}.template".format(obj)):
        if not quiet:
            LOG.error("{0} is a template object, skipping it".format(obj))
        return False
    if not cmds.getAttr("{0}.visibility".format(obj)):
        # Let's check if it has any in-connection (its animated)
        if not cmds.listConnections("{0}.visibility".format(obj)):
            if not quiet:
                LOG.error("{0} is not visible, skipping it".format(obj))
            return False
    if not cmds.getAttr("{0}.lodVisibility".format(obj)):
        # Let's check if it has any in-connection (its animated)
        if not cmds.listConnections("{0}.lodVisibility".format(obj)):
            if not quiet:
                LOG.error("{0} has no lodVisibility, skipping it".format(obj))
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
        if is_component(node):
            return get_transform(get_shapes(node, l=True)[0], full_path)
        try:
            return cmds.listRelatives(node, type='transform', fullPath=full_path, parent=True)[0]
        except TypeError:
            cmds.warning("{} doesn't have a transform".format(node))
            return ""
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


def split_node_attr(node_attr):
    """
    Split a node.attr in their individual elements
    Args:
        node_attr (unicode): A node with its attributes

    Returns:
        (unicode, unicode): The node and the attribute separated
    """
    u_stringify(node_attr)
    if node_attr:
        split_idx = node_attr.find('.')
        node = node_attr[:split_idx]
        attr = node_attr[split_idx + 1:]
        return node, attr
    else:
        print_error("'{}' could not be split into node and attribute".format(node_attr), True)


def set_attr(obj, attr, value, silent=False):
    """
    Generic setAttr convenience function which changes the Maya command depending on the data type
    Args:
        obj (unicode): node
        attr (unicode): attribute
        value (any): the value to set
        silent (bool): if the function is silent when errors occur
    """
    node_attr = "{}.{}".format(obj, attr)
    # check for existence
    if not cmds.attributeQuery(attr, n=obj, ex=True):
        if not silent:
            cmds.warning("{} can't be set as it doesn't exist".format(node_attr))
        return False
    # try setting it
    try:
        if isinstance(value, basestring):
            cmds.setAttr(node_attr, value, type="string")
        elif isinstance(value, list) or isinstance(value, tuple):
            if len(value) == 3:
                cmds.setAttr(node_attr, value[0], value[1], value[2], type="double3")
            elif len(value) == 2:
                cmds.setAttr(node_attr, value[0], value[1], type="double2")
            elif len(value) == 1:
                # check for list within a list generated by getAttr command
                if isinstance(value[0], list) or isinstance(value[0], tuple):
                    set_attr(obj, attr, value[0])
                    return
                cmds.setAttr(node_attr, value[0])
            elif cmds.attributeQuery(attr, node=obj, attributeType=True) == "compound":
                idx = 0
                for sub_attr in cmds.attributeQuery(attr, node=obj, listChildren=True):
                    set_attr(obj, sub_attr, value[idx])
                    idx += 1
            else:
                cmds.setAttr(node_attr, tuple(value), type="doubleArray")
        else:
            cmds.setAttr(node_attr, value)
        return True
    except RuntimeError:
        # Could fail because of attribute connection
        if cmds.listConnections(node_attr):
            return False
        # Could fail because of parent
        parent_attr = cmds.attributeQuery(attr, node=obj, listParent=True) or []
        if parent_attr:
            return False
        # No excuse, fail gracefully
        if not silent:
            cmds.warning("{} could not be set to {}.".format(node_attr, value))
            LOG.debug("Attribute of type: {}.".format(type(value)))
        return False


def check_set_attr(obj, attr, value, silent=True):
    """
    Generic setAttr convenience function that checks the attribute and changes it only if necessary
    Args:
        obj (unicode): node
        attr (unicode): attribute
        value (any): the value to set
        silent (bool): if the function is silent when errors occur
    """
    if cmds.attributeQuery(attr, node=obj, exists=True):
        prev_value = cmds.getAttr("{}.{}".format(obj, attr))
        if isinstance(prev_value, list):
            if len(prev_value) == 1:
                prev_values = list(prev_value[0])
                if value != prev_values:
                    set_attr(obj, attr, value, silent)
        elif value != prev_value:
            set_attr(obj, attr, value, silent)


def set_attrs(objs, attr_data, specific_attrs=None, silent=False):
    """
    Sets attributes of attr_data to obj
    Args:
        objs (unicode, list): Objects to set attributes onto
        attr_data (dict): Dictionary of attribute data { "attribute_name": value }
        specific_attrs (list): Specific attributes to set attr_data onto (if None, all attr_data)
        silent (bool): If warnings should be shown when attribute data could not be assigned
    """
    objs = u_enlist(objs)
    for obj in objs:
        if specific_attrs:
            for attr in specific_attrs:
                set_attr(obj, attr, attr_data[attr], silent)
        else:
            for attr in attr_data:
                set_attr(obj, attr, attr_data[attr], silent)


def break_connections(objs, attrs, delete_inputs=False):
    """
    Breaks all connections to specific attributes within objs
    Args:
        objs (unicode, list): Object which has connections
        attrs (unicode, list): Attribute to disconnect
        delete_inputs (bool): If the any remaining input nodes should be deleted
    """
    objs = u_enlist(objs)
    attrs = u_enlist(attrs)
    for obj in objs:
        if not cmds.objExists(obj):
            LOG.warning("Could not break connections of {} as it doesn't exist".format(obj))
            continue
        for attr in attrs:
            source = "{}.{}".format(obj, attr)
            if not cmds.attributeQuery(attr, n=obj, ex=True):
                LOG.warning("Could not break connections of {} as the attribute doesn't exist".format(source))
                continue
            plugs = cmds.listConnections(source, p=True) or []
            for plug in plugs:
                if cmds.listConnections(source, s=True, d=False) is None:
                    cmds.disconnectAttr(source, plug)
                else:
                    # source is a 'destination' (right side of connection)
                    if delete_inputs:
                        cmds.delete(source, inputConnectionsAndNodes=True)
                    else:
                        cmds.disconnectAttr(plug, source)


def disconnect_attrs(source, source_attr, dest, dest_attr):
    """
    Checks and disconnects source attribute from destination attribute, if possible
    Args:
        source (unicode): Source object
        source_attr (unicode): Source attribute
        dest (unicode): Destination object
        dest_attr (unicode): Destination attribute
    """
    if cmds.isConnected("{}.{}".format(source, source_attr), "{}.{}".format(dest, dest_attr)):
        cmds.disconnectAttr("{}.{}".format(source, source_attr), "{}.{}".format(dest, dest_attr))


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


def get_common_objs(objs1, objs2):
    """
    Get common objects (intersection) between obj lists
    Note: This does NOT keep the order of the elements in the lists
    Args:
        objs1 (list): List of objects (short or long names)
        objs2 (list): List of objects (short or long names)

    Returns:
        (list): list of common objects (long names) between both lists
    """
    objs1 = set(cmds.ls(objs1, l=True))
    objs2 = cmds.ls(objs2, l=True)
    return list(objs1.intersection(objs2))


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


#               _       _        __      _ _           _
#    _ __  _ __(_)_ __ | |_     / /   __| (_)___ _ __ | | __ _ _   _
#   | '_ \| '__| | '_ \| __|   / /   / _` | / __| '_ \| |/ _` | | | |
#   | |_) | |  | | | | | |_   / /   | (_| | \__ \ |_) | | (_| | |_| |
#   | .__/|_|  |_|_| |_|\__| /_/     \__,_|_|___/ .__/|_|\__,_|\__, |
#   |_|                                         |_|            |___/
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
    if get_maya_version() > 2018 and not cmds.about(batch=True):
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
    if get_maya_version() > 2018 and not cmds.about(batch=True):
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
    if get_maya_version() > 2018 and not cmds.about(batch=True):
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
            self.path = u_decode(path)
        elif get_py_version() < 3:
            if isinstance(path, unicode):
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
        children = os.path.normpath(u_stringify(child)).split(os.sep)
        self.path = os.path.abspath(os.path.join(self.path, *children))
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
        contents = []
        try:
            contents = os.listdir(self.path)
        except WindowsError:
            traceback.print_exc()
        return contents

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

    def find_parent(self, parent_basename, search_path=""):
        """
        Finds the parent folder that has the parent_basename
        Args:
            parent_basename (unicode): Basename of parent folder
            search_path (unicode): Custom search path to find parent folder in

        Returns:
            (unicode): Parent folder path or ""
        """
        cur_path = self.path
        if search_path:  # custom search path (not self.path)
            cur_path = search_path
        parent_path = os.path.abspath(os.path.join(cur_path, os.pardir))
        if parent_path == search_path:
            print_warning("Can't find parent folder: {}".format(parent_basename))
            return ""  # no parent available anymore
        p_basename = os.path.basename(parent_path)
        if p_basename == parent_basename:
            return parent_path
        else:
            return self.find_parent(parent_basename, parent_path)

    def file_size(self):
        """
        Returns the file size of the path in MB
        Returns:
            (float): Size of the file in MB
        """
        if self.exists():
            return os.path.getsize(self.path) / 1024.0 / 1024.0
        return 0


def make_path_relative(path, root_path=None):
    """
    Returns the relative path, if any, compared to the project path or root path
    Args:
        path (unicode): path of current file or directory
        root_path (unicode): Optional path to also make path relative to
    Returns:
        rel_path (unicode): relative path to project, if available (with forward slashes)
    """
    path = Path(path).slash_path()
    new_path = path
    if root_path:
        root_path = Path(root_path).slash_path()
        if new_path.startswith(root_path):
            new_path = new_path[len(root_path):]
    else:
        project_path = Path(cmds.workspace(q=True, rootDirectory=True)).slash_path()
        if new_path.startswith(project_path):
            new_path = new_path[len(project_path):]
    if new_path != path:
        # We have a relative path, make sure we don't return slash as the first character
        if new_path[0] == '/':
            return new_path[1:]
    return new_path


#        _        _
#    ___| |_ _ __(_)_ __   __ _
#   / __| __| '__| | '_ \ / _` |
#   \__ \ |_| |  | | | | | (_| |
#   |___/\__|_|  |_|_| |_|\__, |
#                         |___/
def is_string(v):
    """
    Returns if a variable is a string
    Args:
        v (unicode): variable to check if it's a string
    Returns:
        (bool): If variable is a string
    """
    return isinstance(v, basestring)  # basestring is 'str' in Python 3


def to_camel_case(text, split=" "):
    """
    Converts text to camel case, e.g. ("the camel is huge" => "theCamelIsHuge")
    Args:
        text (string): Text to be camel-cased
        split (char): Char to split text into
    """
    if len(text) < 2:
        return text.lower()

    camel_case_text = text
    splitter = text.split(split)
    if splitter:
        camel_case_text = splitter[0][0].lower()
        if len(splitter[0]) > 1:
            camel_case_text += splitter[0][1:]
        for index in range(1, len(splitter)):
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


def to_pascal_case(text, split=" "):
    """
    Converts text to pascal case, e.g. ("the camel is huge" => "TheCamelIsHuge")
    Args:
        text (unicode): Text to be pascal-cased
        split (char): Char to split text into

    Returns:
        (unicode) string as PascalCase
    """
    pascal_case_text = ""
    text = to_camel_case(text, split)
    if text:
        pascal_case_text = text[0].upper()
        if len(text) > 1:
            pascal_case_text += text[1:]
    return pascal_case_text


def to_underscore_case(text, title=False):
    """
        Converts text to underscore case, e.g. ("the camel is huge" => "the_camel_is_huge")
    Args:
        text (unicode): Text to be underscore-cased
        title (bool): If each word should be titlelized

    Returns:
        (unicode) string as underscore_case
    """
    if title:
        text = text.title()
    return text.replace(' ', "_")


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
            LOG.info("{0} is a string, enlisting it".format(arg))
        return [arg]
    elif isinstance(arg, int):
        if not silent:
            LOG.info("{0} is an int, enlisting it".format(arg))
        return [arg]
    elif arg is None:
        return []
    return arg


def u_stringify(arg, silent=True):
    """
    Unit test to check if given argument is not a string
    Args:
        arg: argument to put into a string
        silent (bool): If the function should print warnings if the wrong data was given (default=False)
    Returns:
        (unicode): The argument in a string
    """
    str_arg = ""
    if arg:
        str_arg = arg
        if isinstance(arg, list) or isinstance(arg, tuple):
            if not silent:
                LOG.info("{0} is a list/tuple, taking first element".format(arg))
            str_arg = arg[0]
        elif isinstance(arg, int):
            str_arg = str(arg)
    return str_arg


def u_decode(text):
    """
    Unit test to make sure text is decoded
    Args:
        text (unicode, str)
    """
    if sys.getfilesystemencoding() != "utf-8":
        text = text.decode()
    return text


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
        return True
    except:
        return False
    finally:
        conn.close()


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
        LOG.info("Saved scene compressed as: {0}".format(zip_path.path))
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
