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
@run:           import coopLib as lib (suggested)
"""
from __future__ import print_function
import os, sys, subprocess, shutil, re, logging, json, math, traceback
from functools import wraps
import maya.mel as mel
import maya.cmds as cmds
import maya.api.OpenMaya as om  # python api 2.0

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
        timeStart = time.time()
        try:
            return f(*args, **kwargs)
        except:
            traceback.print_exc()
        finally:
            timeEnd = time.time()
            logger.debug("[Time elapsed at {0}:    {1:.4f} sec]".format(f.__name__, timeEnd - timeStart))

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
    def undoWrapper(*args, **kwargs):
        try:
            # start an undo chunk
            cmds.undoInfo(openChunk=True, cn="{0}".format(f))
            return f(*args, **kwargs)
        except:
            traceback.print_exc()
        finally:
            # after calling the func, end the undo chunk
            cmds.undoInfo(closeChunk=True, cn="{0}".format(f))

    return undoWrapper


#    _     _     _   _   _ _   _ _
#   | |   (_)___| |_| | | | |_(_) |___
#   | |   | / __| __| | | | __| | / __|
#   | |___| \__ \ |_| |_| | |_| | \__ \
#   |_____|_|___/\__|\___/ \__|_|_|___/
#
# List utilities within a helper class to work with lists.
class ListUtils(object):
    @staticmethod
    def removeDuplicates(objList):
        """
        Remove duplicate entries in lists
        Args:
            lst (list): List to remove duplicate entries from

        Returns:
            New List
        """
        if not objList:
            objList = []
        newList = []
        newSet = set()  # working with sets speeds up the workflow
        for obj in objList:
            if obj not in newSet:
                newSet.add(obj)
                newList.append(obj)
        return newList

    @staticmethod
    def add(objList, obj):
        """
        Adds object if it didn't exist before
        Args:
            obj (str): object to be added
        """
        if obj not in objList:
            objList.append(obj)

    @staticmethod
    def update(objList, updateList):
        """
        Adds each object within a list if it didn't exist before
        Args:
            objList (list): list of objects to be added
        """
        for obj in updateList:
            ListUtils.add(objList, obj)


######################################################################################
# GENERAL UTILITIES
######################################################################################
def checkAboveVersion(year):
    """
    Checks if Maya is above a certain version
    Args:
        year (float): year to check
    Returns:
        bool: True or False depending on the Maya version
    """
    version = os.path.basename(os.path.dirname(os.path.dirname(cmds.internalVar(usd=True))))
    vYear = version.split('-')[0]
    if float(vYear) > float(year):
        return True
    return False


def mayaVersion():
    """
    Returns the current Maya version (E.g. 2017.0, 2018.0, 2019.0, etc)
    """
    return mel.eval("getApplicationVersionAsFloat")


def localOS():
    """
    Returns the Operating System (OS) of the local machine ( win, mac, linux )
    """
    if cmds.about(mac=True):
        return "mac"
    elif cmds.about(linux=True):
        return "linux"
    return "win"


def getEnvDir():
    """
    Gets the environment directory
    Returns:
        directory (str): the directory of the Maya.env file
    """
    envDir = os.path.abspath(cmds.about(env=True, q=True))
    return os.path.dirname(envDir)


def getLibDir():
    """
    Gets the coop library directory
    Returns:
        directory (str): the directory where the coopLib is found at
    """
    return os.path.dirname(os.path.realpath(__file__))


def createDirectory(directory):
    """
    Creates the given directory if it doesn't exist already
    Args:
        directory (str): The directory to create
    """
    if directory:
        if not os.path.exists(directory):
            os.makedirs(directory)
    else:
        raise ValueError("No directory has been given to create.")


def openUrl(url):
    """
    Opens the url in the default browser
    Args:
        url (str): The URL to open
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


def restartMaya(brute=True):
    """
    Restarts maya (CAUTION)
    Args:
        brute (bool): True if the Maya process should stop, False if Maya should be exited normally
    """
    if not brute:
        mayaPyDir = os.path.join(os.path.dirname(sys.executable), "mayapy")
        if cmds.about(nt=True, q=True):
            mayaPyDir += ".exe"
        scriptDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "coopRestart.py")
        print(scriptDir)
        subprocess.Popen([mayaPyDir, scriptDir])
        cmds.quit(force=True)
    else:
        os.execl(sys.executable, sys.executable, *sys.argv)


def restartDialog(brute=True):
    """
    Opens restart dialog to restart maya
    Args:
        brute (bool): True if the Maya process should stop, False if Maya should be exited normally
    """
    restart = cmds.confirmDialog(title='Restart Maya',
                                 message='Maya needs to be restarted in order to show changes\nWould you like to restart maya now?',
                                 button=['Yes', 'No'], defaultButton='Yes', cancelButton='No', dismissString='No',
                                 ma='center')
    if restart == 'Yes':
        restartMaya(brute)


######################################################################################
# MAYA UTILITIES
######################################################################################
def createEmptyNode(inputName):
    """
    Creates a completely empty node
    Args:
         inputName (str): Name of the new empty node
    """
    cmds.select(cl=True)
    cmds.group(em=True, name=inputName)
    nodeName = cmds.ls(sl=True)
    keyableAttributes = cmds.listAttr(nodeName, k=True)
    for attribute in keyableAttributes:
        cmds.setAttr('{0}.{1}'.format(nodeName[0], attribute), l=True, k=False)


def purgeMissing(objects):
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
            objs.extend(purgeMissing(obj))
        else:
            if cmds.objExists(obj):
                objs.append(obj)
    return objs


def getActiveModelPanel():
    """
    Get the active model editor panel
    Returns:
        modelPanel name (str)
    """
    activePanel = cmds.getPanel(wf=True)
    if cmds.getPanel(typeOf=activePanel) == 'modelPanel':
        return activePanel
    else:
        return cmds.playblast(ae=True)


def detachShelf():
    """
    Detaches the current shelves
    IN PROGRESS
    """
    shelfTopLevel = mel.eval('$tempMelVar=$gShelfTopLevel')
    shelfName = cmds.shelfTabLayout(shelfTopLevel, st=True, q=True)
    shelfPaths = os.path.abspath(cmds.internalVar(ush=True)).split(';')
    shelfFile = "shelf_{0}.mel".format(shelfName)

    shelfFilePath = ""
    for shelfPath in shelfPaths:
        files = os.listdir(shelfPath)
        if shelfFile in files:
            shelfFilePath = os.path.join(shelfPath, shelfFile)
    print(shelfFilePath)


def deleteShelves(shelvesDict=None, restart=True):
    """
    Delete shelves specified in dictionary
    Args:
        shelvesDict (dict): Dictionary of shelf name and mel file without prefix: e.g. {"Animation" : "Animation.mel"}
    Raises:
        restartDialog()
    """
    envDir = getEnvDir()
    if not shelvesDict:
        cmds.error('No shelf array given')
    # Maya creates all default shelves in prefs only after each has been opened (initialized)
    for shelf in shelvesDict:
        try:
            mel.eval('jumpToNamedShelf("{0}");'.format(shelf))
        except:
            continue
    mel.eval('saveAllShelves $gShelfTopLevel;')  # all shelves loaded (save them)
    # time to delete them
    shelfTopLevel = mel.eval('$tempMelVar=$gShelfTopLevel') + '|'
    for shelf in shelvesDict:
        shelfLayout = shelvesDict[shelf].split('.mel')[0]
        if cmds.shelfLayout(shelfTopLevel + shelfLayout, q=True, ex=True):
            cmds.deleteUI(shelfTopLevel + shelfLayout, layout=True)
    # mark them as deleted to avoid startup loading
    shelfDir = os.path.join(envDir, 'prefs', 'shelves')
    for shelf in shelvesDict:
        shelfName = os.path.join(shelfDir, 'shelf_' + shelvesDict[shelf])
        deletedShelfName = shelfName + '.deleted'
        if os.path.isfile(shelfName):
            # make sure the deleted file doesn't already exist
            if os.path.isfile(deletedShelfName):
                os.remove(shelfName)
                continue
            os.rename(shelfName, deletedShelfName)
    if restart:
        restartDialog()


def restoreShelves():
    """
    Restores previously deleted shelves
    Raises:
        restartDialog()
    """
    scriptsDir = os.path.abspath(cmds.internalVar(usd=True))
    envDir = os.path.dirname(scriptsDir)
    shelfDir = os.path.join(envDir, 'prefs', 'shelves')
    for shelf in os.listdir(shelfDir):
        if shelf.endswith('.deleted'):
            restoredShelf = os.path.join(shelfDir, shelf.split('.deleted')[0])
            deletedShelf = os.path.join(shelfDir, shelf)
            # check if it has not been somehow restored
            if os.path.isfile(restoredShelf):
                os.remove(deletedShelf)
            else:
                os.rename(deletedShelf, restoredShelf)
    restartDialog()


def getShapes(objects, renderable=False, l=False, quiet=False):
    """
    Get shapes of objects/components
    Args:
        objects (list): List of objects or components
        fp (bool): If full path is desired or not
    """
    # transform string input (if any) to a list
    if isinstance(objects, basestring):
        objects = [objects]

    objs = set()
    for comp in objects:
        objs.add(comp.split(".")[0])  # to also work with components of multiple objects
    if not objs:
        if not quiet:
            printError("Please select a mesh or component to extract the shape from")
            return []

    objs = purgeMissing(objs)  # make sure all objects exist

    shapes = []
    for obj in objs:
        potentialShape = []
        # check if its a mesh object
        objType = cmds.objectType(obj)
        if objType == "mesh" or objType == "nurbsSurface":
            potentialShape = cmds.ls(obj, l=l)  # make an array
            # shapes.extend(cmds.ls(obj, l=l))  # there might be more objects with the same name
        else:
            potentialShape = cmds.listRelatives(obj, shapes=True, noIntermediate=True, path=True, fullPath=l) or []
            # shapes.extend(shp)
        # check if renderable
        if renderable and potentialShape:
            if not isRenderable(potentialShape[0]):
                continue
        # add potential shape to list
        shapes.extend(potentialShape)

    if not shapes and not quiet:
        printWarning("No shape nodes found in {0}".format(objects))

    return shapes


def isRenderable(obj, quiet=True):
    """
    Checks if object is renderable
    Args:
        obj (str): Name of object to verify
        quiet (bool): If the function should keep quiet (default=True)
    Returns:
        (bool) if its renderable or not
    """
    # unit test
    if isinstance(obj, list) or isinstance(obj, tuple):
        if len(obj) == 1:
            obj = obj[0]
        else:
            logger.error("isRenderable - {0} cannot be checked".format(obj))
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
        renderable = renderable and isRenderable(parent[0])
    return renderable


def getTransforms(objects, fullPath=False):
    """
    Get transform nodes of objects
    Args:
        objects (list): List of objects
        fullPath (bool): If full path or not
    Returns:
        List of transform nodes
    """
    transforms = []
    for node in objects:
        transforms.append(getTransform(node, fullPath))
    return transforms


def getTransform(node, fullPath=False):
    """
    Get transform node of object
    Args:
        node (str): Name of node
        fullPath (bool): If full path or not
    Returns:
        Name of transform node
    """
    if 'transform' != cmds.nodeType(node):
        return cmds.listRelatives(node, fullPath=fullPath, parent=True)[0]
    else:
        return node


def changeAttributes(attributes, value):
    """
    Batch change attributes of selected objects:
    e.g. lib.changeAttributes(['jointOrientX', 'jointOrientY', 'jointOrientZ'], 0)
    Args:
        attributes (list): List of attributes (str)
        value: Value to set into attributes
    """
    selected = cmds.ls(sl=True)
    for sel in selected:
        for attribute in attributes:
            try:
                cmds.setAttr("{0}.{1}".format(sel, attribute), value)
            except:
                cmds.warning(
                    "There is an issue with {0}.{1}. The value {2} could not be set".format(sel, attribute, value))


def copyAttributes(attributes):
    """
    Batch copy attributes of first selected object to the rest of selected objects:
    e.g. lib.copyAttributes(['jointOrientX', 'jointOrientY', 'jointOrientZ'])
    Args:
        attributes (list): List of attributes (str)
    """
    selected = cmds.ls(sl=True)
    if selected:
        source = selected.pop(0)
        for attribute in attributes:
            sourceValue = cmds.getAttr("{0}.{1}".format(source, attribute))
            for target in selected:
                try:
                    cmds.setAttr("{0}.{1}".format(target, attribute), sourceValue)
                except:
                    cmds.warning(
                        "There is an issue with {0}.{1}. The value {2} could not be set".format(target, attribute,
                                                                                                sourceValue))


def setAttr(obj, attr, value, silent=False):
    """
    Generic setAttr convenience function which changes the Maya command depending on the data type
    Args:
        obj (str): node
        attr (str): attribute
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
                    setAttr(obj, attr, value[0])
                    return
                cmds.setAttr("{0}.{1}".format(obj, attr), value[0])
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


def getNextFreeMultiIndex(node, attr, idx=0):
    """
    Find the next unconnected multi index starting at the passed index
    Args:
        node (str): node to search in
        attr (str): attribute to search in
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


def getNextFreeMultiIndexConsideringChildren(node, attr, idx=0):
    """
    Find the next unconnected multi index, considering children attributes, starting at the passed index
    Args:
        node (str): node to search in
        attr (str): attribute to search in
        idx (int): starting index to search from
    Returns:
        The next free index
    """
    while idx < 10000000:  # assume a max of 10 million connections
        if len(cmds.listConnections('{0}.{1}[{2}]'.format(node, attr, idx)) or []) == 0:
            free = True
            childAttrs = cmds.attributeQuery(attr, n=node, listChildren=True) or []
            for childAttr in childAttrs:
                if cmds.attributeQuery(childAttr, n="{0}.{1}".format(node, attr), multi=True):
                    if getNextFreeMultiIndexConsideringChildren("{0}.{1}[{2}]".format(node, attr, idx), childAttr) > 0:
                        free = False
                        break
            if free:
                return idx
        idx += 1
    # No connections means the first index is available
    return 0


def distanceBetween(obj1, obj2):
    """
    Distance between objects
    Args:
        obj1 (str): object 1
        obj2 (str): object 2

    Returns:
        Distance between the objects (in world space)
    """
    v1World = cmds.xform('{0}'.format(obj1), q=True, worldSpace=True, piv=True)  # list with 6 elements
    v2World = cmds.xform('{0}'.format(obj2), q=True, worldSpace=True, piv=True)  # list with 6 elements
    return distance(v1World, v2World)


def snap(source='', targets=[], type="translation"):
    """
    Snap targets objects to source object
    If not specified, the first selected object is considered as source, the rest as targets
    Args:
        source (str): Source transform name
        targets (list): List of target transform names (str)
        type: Either "translation" (default), "rotation" or "position" (translation + rotation)
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
    if type == "translation":
        worldTranslateXform = cmds.xform('{0}'.format(source), q=True, worldSpace=True,
                                         piv=True)  # list with 6 elements
        for target in targets:
            cmds.xform('{0}'.format(target), worldSpace=True,
                       t=(worldTranslateXform[0], worldTranslateXform[1], worldTranslateXform[2]))
        printInfo("Translation snapped")

    if type == "rotation":
        sourceXform = cmds.xform('{0}'.format(source), q=True, worldSpace=True, ro=True)
        for target in targets:
            cmds.xform('{0}'.format(target), worldSpace=True, ro=(sourceXform[0], sourceXform[1], sourceXform[2]))
        printInfo("Rotation snapped")

    if type == "position":
        sourcePos = cmds.xform('{0}'.format(source), q=True, worldSpace=True, piv=True)  # list with 6 elements
        sourceRot = cmds.xform('{0}'.format(source), q=True, worldSpace=True, ro=True)
        for target in targets:
            cmds.xform('{0}'.format(target), worldSpace=True, t=(sourcePos[0], sourcePos[1], sourcePos[2]))
            cmds.xform('{0}'.format(target), worldSpace=True, ro=(sourceRot[0], sourceRot[1], sourceRot[2]))
        printInfo("Position snapped")


######################################################################################
# RENDERING UTILITIES
######################################################################################
IMGFORMATS = {'.jpg': 8, '.png': 32, '.tif': 3, '.exr': 40, '.iff': 7}
IMGFORMATS_ORDER = ['.png', '.jpg', '.exr', '.tif', '.iff']
QUALITIES_ORDER = {'Standard', 'FXAA', '4x SSAA', 'TAA'}


def getMaterials(objects):
    """
    Get materials of objects
    Args:
        objects (list): List of objects to get the materials from
    Returns:
        List of materials
    """
    materials = cmds.ls(objects, l=True, mat=True)
    transforms = cmds.ls(objects, l=True, et="transform")
    shapes = cmds.ls(objects, l=True, s=True, noIntermediate=True)

    # get shapes from transforms
    if transforms:
        ListUtils.update(shapes, cmds.ls(transforms, o=True, dag=True, s=True, noIntermediate=True))

    if shapes:
        # get materials from shading engines
        cleanShadingEngines(shapes)
        shadingEngines = ListUtils.removeDuplicates(cmds.listConnections(shapes, type="shadingEngine"))
        for se in shadingEngines:
            mats = cmds.ls(cmds.listConnections(se), mat=True)
            if not mats:
                # connect the default material to the shading engine
                defaultMat = "lambert1"
                logger.info("No material connected to {0}. Connecting default material".format(se))
                cmds.connectAttr("{0}.outColor".format(defaultMat), "{0}.surfaceShader".format(se), f=True)
            ListUtils.update(materials, mats)

    return materials


def setMaterial(mat, objects):
    """
    Set material onto objects
    Args:
        mat (str): Name of material to set to objects
        objects (list): List of objects that the material is assigned to
    """
    mat = u_stringify(mat)
    shadingEngines = cleanShadingEngines(objects)
    if shadingEngines:
        for shadingEngine in shadingEngines:
            cmds.connectAttr("{0}.outColor".format(mat), "{0}.surfaceShader".format(shadingEngine), f=True)
    else:
        # fallback to hypershade cmd
        selection = cmds.ls(sl=True, l=True)
        cmds.select(objects, r=True)
        cmds.hyperShade(assign=mat)
        cmds.select(selection, r=True)


def cleanShadingEngines(objs, quiet=True):
    """
    Makes sure the shading engines are clean
    Args:
        objs (list): Objects to clean shading engines from
    """
    shadingEngines = []
    shapes = getShapes(objs, l=True)
    for shape in shapes:
        shadingEngines = ListUtils.removeDuplicates(cmds.listConnections(shape, type="shadingEngine"))
        if "MNPRX_SE" in shadingEngines:
            shadingEngines.remove("MNPRX_SE")  # MNPRX instance shading engine
        if len(shadingEngines) > 1:
            if not quiet:
                logger.warning("Two shading engines in {0}".format(shape))
            # remove initialShadingGroup if still available
            if "initialShadingGroup" in shadingEngines:
                shadingEngines.remove("initialShadingGroup")
                destinations = cmds.listConnections(shape, t='shadingEngine', plugs=True)
                for dest in destinations:
                    if "initialShadingGroup" in dest:
                        try:
                            source = cmds.listConnections(dest, s=True, plugs=True)[0]
                            cmds.disconnectAttr(source, dest)
                            logger.debug("initialShadingGroup has been removed from {0}".format(shape))
                            break
                        except RuntimeError:
                            logger.warning("Couldn't disconnect {0} from {1}".format(shape, dest))
    return shadingEngines

def getAssignedMeshes(materials, shapes=True, l=False):
    """
    Get the assigned meshes (shapes) out of a material
    Args:
        material (str): Material name to get meshes from
        shapes (bool): Return shapes or transform node names [Defailt=True]
    Returns:
        List of meshes
    """
    meshes = []
    # get shading engines
    if isinstance(materials, basestring):
        materials = [materials]
    shadingEngines = cmds.listConnections(materials, type="shadingEngine")
    if shadingEngines:
        for shadingEngine in shadingEngines:
            m = cmds.sets(shadingEngine, q=True) or []  # shapes
            m = cmds.ls(m, l=l)
            if m:
                if not shapes:
                    m = cmds.listRelatives(m, parent=True, fullPath=l)  # transforms
                meshes.extend(m)
    return meshes


def setVertexColorSets(shapes, colorSets, value=[0.0, 0.0, 0.0, 0.0]):
    """
    Set and create vertex color sets on shapes
    Args:
        shapes (lst): Shapes to delete vertex color sets from
        colorSets (lst): Vertex color sets to delete
        value (list): List of values to set (default [0.0, 0.0, 0.0, 0.0])
    Warning: Saving vertex colors using the Maya API doesn't save on references
    """
    # unit tests
    if isinstance(shapes, basestring):
        shapes = [shapes]
    if isinstance(colorSets, basestring):
        colorSets = [colorSets]
    # doIt
    for shape in shapes:
        if cmds.objectType(shape) != "mesh":
            printInfo("{0} is not a mesh, skipping it".format(shape))
            continue
        shapeColorSets = cmds.polyColorSet(shape, query=True, allColorSets=True) or []
        for colorSet in colorSets:
            if colorSet not in shapeColorSets:
                logger.debug("Creating {0} vertex color set for {1}".format(colorSet, shape))
                cmds.polyColorSet(shape, cs=colorSet, representation="RGBA", create=True)
            oShape = getMObject(shape)
            fnMesh = om.MFnMesh(oShape)  # access mesh data (oShape can also be replaced by MDagPath of shape)
            oVertexColorArray = fnMesh.getVertexColors(colorSet)  # MColorArray
            vertexListLength = len(oVertexColorArray)
            vertexIndexArray = list(xrange(vertexListLength))
            for vertex in vertexIndexArray:
                oVertexColorArray[vertex].r = value[0]
                oVertexColorArray[vertex].g = value[1]
                oVertexColorArray[vertex].b = value[2]
                oVertexColorArray[vertex].a = value[3]
            fnMesh.setCurrentColorSetName(colorSet)
            fnMesh.setVertexColors(oVertexColorArray, vertexIndexArray)
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
        deleteColorSetHistory(shape)


def deleteVertexColorSets(shapes, colorSets):
    """
    Delete the vertex color set and its history
    Args:
        shapes (lst): Shapes to delete vertex color sets from
        colorSets (lst): Vertex color sets to delete
    """
    shapes = u_enlist(shapes)  # put in list
    colorSets = u_enlist(colorSets)  # put in list
    for shape in shapes:
        shapeColorSets = cmds.polyColorSet(shape, query=True, allColorSets=True) or []
        for colorSet in colorSets:
            if colorSet in shapeColorSets:
                cmds.polyColorSet(shape, colorSet=colorSet, delete=True)
                history = cmds.listHistory(shape)
                nodes2Delete = []
                for node in history:
                    # check if attribute exists
                    if not cmds.attributeQuery('colorSetName', n=node, ex=True):
                        continue
                    # attribute exists, check name of color set name
                    colorSetName = cmds.getAttr("{0}.colorSetName".format(node))
                    if colorSetName == colorSet:
                        nodes2Delete.append(node)
                        logger.debug("{0} node scheduled for deletion".format(node))
                if nodes2Delete:
                    cmds.delete(nodes2Delete)
                logger.info("Vertex color set {0} deleted for: {1}".format(colorSet, shape))


def bakeVertexColors(shapes):
    """
    Bake vertex colors into shape nodes (not working, set issue in AREA Forum)
    https://forums.autodesk.com/t5/maya-programming/baking-vertex-colors-onto-shape-node/td-p/9119416
    Args:
        shapes (lst): Shapes to bake vertex colors
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
                colorSetName = cmds.getAttr("{0}.colorSetName".format(node))
                print("Color set name: {0}".format(colorSetName))
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
                colorSets = cmds.getAttr("{0}.colorSet[*].colorName".format(shape))
                # make sure its in an array
                if isinstance(colorSets, basestring):
                    colorSets = [colorSets]
                colorSetIndex = colorSets.index(colorSetName)
                print("Color set index is {0}".format(colorSetIndex))
                setAttr(shape, "colorSet[{0}].colorName".format(colorSetIndex), colorSetName)
                setAttr(shape, "colorSet[{0}].representation".format(colorSetIndex), representation)
                setAttr(shape, "colorSet[{0}].clamped".format(colorSetIndex), clamped)
                for i in range(len(alphas)):
                    """
                    attr = "colorSet[{0}].colorSetPoints[{1}]".format(colorSetIndex, i)
                    setAttr(shape, attr, [reds[i], greens[i], blues[i], alphas[i]])
                    """
                    attr = "colorSet[{0}].colorSetPoints[{1}].colorSetPointsR".format(colorSetIndex, i)
                    #setAttr(shape, attr, reds[i])
                    cmds.setAttr("{0}.{1}".format(shape, attr), reds[i])
                    attr = "colorSet[{0}].colorSetPoints[{1}].colorSetPointsG".format(colorSetIndex, i)
                    #setAttr(shape, attr, greens[i])
                    cmds.setAttr("{0}.{1}".format(shape, attr), greens[i])
                    attr = "colorSet[{0}].colorSetPoints[{1}].colorSetPointsB".format(colorSetIndex, i)
                    # setAttr(shape, attr, blues[i])
                    cmds.setAttr("{0}.{1}".format(shape, attr), blues[i])
                    attr = "colorSet[{0}].colorSetPoints[{1}].colorSetPointsA".format(colorSetIndex, i)
                    #setAttr(shape, attr, alphas[i])
                    cmds.setAttr("{0}.{1}".format(shape, attr), alphas[i])
                # add to shape
                faceN = cmds.polyEvaluate(shape, face=True)  # query amount of faces
                melCmd = 'setAttr -s {0} "{1}.fc[0:{2}]" -type "polyFaces"'.format(faceN, shape, faceN-1)
                # melCmd = 'setAttr -s {0} -ch {1} "{2}.fc[0:{3}]" -type "polyFaces" '.format(faceN, faceN*4, shape, faceN-1)
                # melCmd = 'setAttr {0}.polyFaceAttr -type polyFaces '.format(shape, colorSetIndex)
                fv = 0
                for f in range(faceN):
                    # find adjacent vertices
                    vString = cmds.polyInfo("{0}.f[{1}]".format(shape, f), fv=True)[0]
                    vertices = vString.split(':')[1].split()
                    melCmd += ' mc {0} {1}'.format(colorSetIndex, len(vertices))
                    for v in vertices:
                        melCmd += " {0}".format(fv)
                        fv += 1
                melCmd += ';'
                print(melCmd)
                mel.eval(melCmd)  # we run the mel command here
                # delete polyColorPerVertex nodes that pertain this colorSet
                cmds.delete(node)
                logger.debug("Vertex color set {0} baked on {1}".format(colorSetName, shape))
            if cmds.objectType(node) == "createColorSet":
                cmds.delete(node)  # no need for them in history


def deleteColorSetHistory(shapes=[]):
    """
    Deletes unnecessary history nodes created by color sets
    Args:
        shapes (list): shapes to delete history nodes from
    """
    shapes = u_enlist(shapes)  # unit tests
    nodes2Delete = []
    for shape in shapes:
        # go through history
        history = cmds.listHistory(shape)
        for node in history:
            if cmds.objectType(node) == "createColorSet":
                nodes2Delete.append(node)
    if nodes2Delete:
        cmds.delete(nodes2Delete)
        # logger.debug("Deleted the following nodes {0}".format(nodes2Delete))


def changeTexturePath(path):
    """
    Change all texture paths
    Useful when moving around the textures of the scene
    Args:
        path (string): Relative path from project (e.g. "sourceimages\house)
    """
    allFileNodes = cmds.ls(et='file')
    for node in allFileNodes:
        filePath = cmds.getAttr("{0}.fileTextureName".format(node))
        fileName = os.path.basename(filePath)
        cmds.setAttr("{0}.fileTextureName".format(node), "{0}/{1}".format(path, fileName), type='string')


def screenshot(fileDir, width, height, format=".jpg", override="", ogs=True):
    # check if fileDir has image format
    if format not in fileDir:
        fileDir += format

    # get existing values
    prevFormat = cmds.getAttr("defaultRenderGlobals.imageFormat")
    prevOverride = cmds.getAttr("hardwareRenderingGlobals.renderOverrideName")

    # set render settings
    cmds.setAttr("defaultRenderGlobals.imageFormat", IMGFORMATS[format])
    if override:
        cmds.setAttr("hardwareRenderingGlobals.renderOverrideName", override, type="string")

    if ogs:
        # render viewport
        renderedDir = cmds.ogsRender(cv=True, w=width, h=height)  # render the frame
        shutil.move(os.path.abspath(renderedDir), os.path.abspath(fileDir))  # move to specified dir
    else:
        frame = cmds.currentTime(q=True)
        cmds.playblast(cf=fileDir, fo=True, fmt='image', w=width, h=height,
                       st=frame, et=frame, v=False, os=True)

    # bring everything back to normal
    cmds.setAttr("defaultRenderGlobals.imageFormat", prevFormat)
    cmds.setAttr("hardwareRenderingGlobals.renderOverrideName", prevOverride, type="string")

    printInfo("Image saved successfully in {0}".format(fileDir))
    return fileDir


#    _                            _        __                             _
#   (_)_ __ ___  _ __   ___  _ __| |_     / /   _____  ___ __   ___  _ __| |_
#   | | '_ ` _ \| '_ \ / _ \| '__| __|   / /   / _ \ \/ / '_ \ / _ \| '__| __|
#   | | | | | | | |_) | (_) | |  | |_   / /   |  __/>  <| |_) | (_) | |  | |_
#   |_|_| |_| |_| .__/ \___/|_|   \__| /_/     \___/_/\_\ .__/ \___/|_|   \__|
#               |_|                                     |_|
def exportVertexColors(objs, path):
    """
    Exports vertex colors of objs to a json file at path
    Args:
        objs: objects to export from
        path: path to save json file to
    """
    # initialize variables
    namespace = False
    namespacePrompt = False

    # get shapes, its control sets and colors
    shapeDict = {}
    shapes = getShapes(objs)
    for shape in shapes:
        print("Extracting vertex colors from {0}".format(shape))
        shapeName = "{0}".format(shape)

        # check for namespaces
        namespacePos = shape.rfind(":")
        namespaceQuery = namespacePos > 0
        if not namespacePrompt and namespaceQuery:
            # ask if shapes should be exported with namespaces
            result = cmds.confirmDialog(title="Wait a second...",
                                        icon="question",
                                        message="Would you like to export vertex colors with namespace?",
                                        button=['Yes', 'No'], defaultButton='No', cancelButton='No', dismissString='No',
                                        ma='center')
            if result == "Yes":
                namespace = True
            namespacePrompt = True
        # change shape name accordingly
        if not namespace:
            if namespaceQuery:
                shapeName = shape[namespacePos + 1:]

        # get data
        colorSetDict = {}
        oShape = getMObject(shape)  # grabs the MObject of the shape
        fnMesh = om.MFnMesh(oShape)  # access mesh data (oShape can also be replaced by MDagPath)
        colorSets = cmds.polyColorSet(shape, query=True, allColorSets=True)
        if colorSets:
            for colorSet in colorSets:
                oVertexColorArray = fnMesh.getVertexColors(colorSet)  # MColorArray
                colorSetDict[colorSet] = [vtxColor.getColor() for vtxColor in oVertexColorArray]
            shapeDict[shapeName] = colorSetDict

    # write and save json info
    with open(path, 'w') as f:
        json.dump(shapeDict, f, separators=(',', ':'), indent=2)

    printInfo("Vertex colors successfully exported")


def importVertexColors(path):
    """
    Import vertex colors from a json file at path
    Args:
        path: path of json file with vertex color information
    """
    # initialize variables
    namespace = ""
    namespacePrompt = False

    # load json file
    with open(path, 'r') as f:
        shapeDict = json.load(f)

    # assign vertex color parameters on each shape
    for shape in shapeDict:
        print("Importing parameters to {0}".format(shape))
        shapeName = "{0}".format(shape)
        if namespace:
            shapeName = "{0}:{1}".format(namespace, shapeName)

        # check for namespaces
        if not cmds.objExists(shape) and not namespacePrompt:
            result = cmds.promptDialog(title='Possible namespace issues',
                                       message='Some shapes where not found in the scene. Could they be under a different namespace?',
                                       button=['Change namespace', 'No'], defaultButton='Change namespace',
                                       cancelButton='No', dismissString='No')
            if result == 'Change namespace':
                namespace = cmds.promptDialog(query=True, text=True)
                shapeName = "{0}:{1}".format(namespace, shapeName)
            namespacePrompt = True

        if cmds.objExists(shapeName):
            oShape = getMObject(shapeName)  # grabs the MObject of the shape
            fnMesh = om.MFnMesh(oShape)  # access mesh data (oShape can also be replaced by MDagPath)
            colorSets = cmds.polyColorSet(shapeName, query=True, allColorSets=True)
            if colorSets == None:
                colorSets = []
            for colorSet in shapeDict[shape]:
                if colorSet not in colorSets:
                    cmds.polyColorSet(shapeName, newColorSet=colorSet)
                oVertexColorArray = fnMesh.getVertexColors(colorSet)  # MColorArray
                vertexListLength = len(oVertexColorArray)
                vertexIndexArray = list(xrange(vertexListLength))
                vertexIndex = 0
                for vertexColor in shapeDict[shape][colorSet]:
                    oVertexColorArray[vertexIndex] = vertexColor
                    vertexIndex += 1
                fnMesh.setCurrentColorSetName(colorSet)
                fnMesh.setVertexColors(oVertexColorArray, vertexIndexArray)
        else:
            logger.debug("No {0} shape exists in the scene".format(shapeName))
    printInfo("Vertex colors successfully exported from {0}".format(os.path.basename(path)))


#    __  __                           _    ____ ___     ____    ___
#   |  \/  | __ _ _   _  __ _        / \  |  _ \_ _|   |___ \  / _ \
#   | |\/| |/ _` | | | |/ _` |      / _ \ | |_) | |      __) || | | |
#   | |  | | (_| | |_| | (_| |     / ___ \|  __/| |     / __/ | |_| |
#   |_|  |_|\__,_|\__, |\__,_|    /_/   \_\_|  |___|   |_____(_)___/
#                 |___/
def getMObject(node, getType=False):
    """
    Gets mObject of a node (Python API 2.0)
    Args:
        node (str): name of node
    Returns:
        Node of the object
    """
    selectionList = om.MSelectionList()
    selectionList.add(node)
    oNode = selectionList.getDependNode(0)
    if not getType:
        return oNode
    else:
        return oNode.apiTypeStr


def printInfo(info):
    """
    Prints the information statement in the command response (to the right of the command line)
    Args:
        info (str): Information to be displayed
    """
    om.MGlobal.displayInfo(info)


def printWarning(warning):
    """
    Prints the warning statement in the command response (to the right of the command line)
    Args:
        warning (str): Warning to be displayed
    """
    om.MGlobal.displayWarning(warning)


def printError(error):
    """
    Prints the error statement in the command response (to the right of the command line)
    Args:
        error (str): Error to be displayed
    """
    om.MGlobal.displayError(error)


#                _   _
#    _ __   __ _| |_| |__
#   | '_ \ / _` | __| '_ \
#   | |_) | (_| | |_| | | |
#   | .__/ \__,_|\__|_| |_|
#   |_|
class Path(object):
    def __init__(self, path):
        self.path = path

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

    def createDir(self):
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
        return self.parent()

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

    def swapExtension(self, newExtension):
        """
        Swaps the current file extension, if available
        Returns:
            Path (obj): modified path obj
        """
        self.path, ext = os.path.splitext(self.path)
        self.path += newExtension
        return self

    def slashPath(self):
        """
        Returns the path with forward slashes
        Returns:
            path (str): path with forward slashes
        """
        return self.path.replace(os.sep, '/')

#        _        _
#    ___| |_ _ __(_)_ __   __ _
#   / __| __| '__| | '_ \ / _` |
#   \__ \ |_| |  | | | | | (_| |
#   |___/\__|_|  |_|_| |_|\__, |
#                         |___/
def toCamelCase(text):
    """
    Converts text to camel case, e.g. ("the camel is huge" => "theCamelIsHuge")
    Args:
        text (string): Text to be camel-cased
    """
    camelCaseText = text
    splitter = text.split()
    if splitter:
        camelCaseText = splitter[0]
        for index in xrange(1, len(splitter)):
            camelCaseText += splitter[index].capitalize()
    return camelCaseText


def deCamelize(text):
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
def clamp(minV, maxV, value):
    """
    Clamps a value between a min and max value
    Args:
        minV: Minimum value
        maxV: Maximum value
        value: Value to be clamped

    Returns:
        Returns the clamped value
    """
    return minV if value < minV else maxV if value > maxV else value


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


def linstep(minV=0.0, maxV=1.0, value=0.5):
    """
    Linear step function
    Args:
        minV: minimum value
        maxV: maximum value
        value: value to calculate the step in

    Returns:
        The percentage [between 0 and 1] of the distance between min and max (e.g. linstep(1, 3, 2.5) -> 0.75).
    """
    return saturate((value - min) / (max - min))


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


def remap(value, oldMin, oldMax, newMin, newMax):
    """
    Remaps the value to a new min and max value
    Args:
        value: value to remap
        oldMin: old min of range
        oldMax: old max of range
        newMin: new min of range
        newMax: new max of range

    Returns:
        The remapped value in the new range
    """
    return newMin + (((value - oldMin) / (oldMax - oldMin)) * (newMax - newMin))


#
#    _ __   __ _ _ __ ___   ___  ___ _ __   __ _  ___ ___  ___
#   | '_ \ / _` | '_ ` _ \ / _ \/ __| '_ \ / _` |/ __/ _ \/ __|
#   | | | | (_| | | | | | |  __/\__ \ |_) | (_| | (_|  __/\__ \
#   |_| |_|\__,_|_| |_| |_|\___||___/ .__/ \__,_|\___\___||___/
#                                   |_|
def getNamespaces(objects=[]):
    """
    Get a list of all namespaces within objects or of the entire scene
    Args:
        objects (list): List of objects to get namespaces from

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


def changeNamespace(objectName, changeDict):
    """
    Changes the namespaces of the object
    Args:
        objectName (str): Name to change namespace
        changeDict (dict): Dictionary of keys {str), values (str) to change namespaces to (key->value)

    Returns:
        String with the namespaces changed
    """
    namespace = getNamespaces(objectName)
    if namespace:
        namespace = namespace[0] + ":"
        if namespace in changeDict:
            objectName = objectName.replace(namespace, changeDict[namespace])
    return objectName


def removeNamespaceFromString(objectName):
    """
    Removes the namespace from string
    Args:
        objectName (str): Object name to remove namespace from

    Returns:
        String: New name without namespaces
    """
    if len(objectName) == 1:
        objectName = objectName[0]

    if isinstance(objectName, basestring):
        parts = objectName.split(':')
        if len(parts) > 1:
            return parts[-1]
        return parts[-1]
    else:
        printWarning("No string found in {0}".format(objectName))
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
    except:
        import http.client as httplib
    conn = httplib.HTTPConnection("www.microsoft.com", timeout=5)
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
        Path (str): Path to saved zip file
    """
    import zipfile
    fileName = cmds.file(q=True, sn=True, shn=True)
    if not fileName:
        printError("Current scene has not been saved before")
        return
    filePath = Path(cmds.file(q=True, sn=True))
    zipPath = Path(filePath.path).swapExtension(".zip")
    zip = zipfile.ZipFile(zipPath.path, 'w', zipfile.ZIP_DEFLATED)
    try:
        zip.write(filePath.path, fileName)
    finally:
        zip.close()
        logger.info("Saved scene compressed as: {0}".format(zipPath.path))
    return zipPath.path


#     __ _
#    / _(_)_  _____  ___
#   | |_| \ \/ / _ \/ __|
#   |  _| |>  <  __/\__ \
#   |_| |_/_/\_\___||___/
#
def removeCallback(procedure):
    """
    Remove callbacks that do not exist anymore (created for example from a plugin which you don't have)
    E.g., removeProcedure("CgAbBlastPanelOptChangeCallback")
    Args:
        procedure (str): Name of callback procedure

    Returns:
    """
    for mp in cmds.getPanel(typ="modelPanel"):
        # Get callback of the model editor
        callback = cmds.modelEditor(mp, query=True, editorChanged=True)
        # If the callback is the erroneous
        if callback == procedure:
            # Remove the callbacks from the editor
            cmds.modelEditor(mp, edit=True, editorChanged="")
            printInfo("{0} successfully removed".format(procedure))