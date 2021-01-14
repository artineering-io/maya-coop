"""
@summary:       Schedule library  to run commands only ONCE
@run:           import coop.scheduler as schedule
@license:       MIT
@repository:    https://github.com/artineering-io/maya-coop
"""
from __future__ import print_function
from __future__ import unicode_literals
import maya.mel as mel
import maya.cmds as cmds
import maya.OpenMayaUI as omUI

AE_UPDATE_SCHEDULED = False


def ae_update_schedule():
    """ Schedule an update of the Attribute Editor """

    def update_ae():
        global AE_UPDATE_SCHEDULED
        mel.eval("refreshEditorTemplates;")
        AE_UPDATE_SCHEDULED = False

    global AE_UPDATE_SCHEDULED
    if not AE_UPDATE_SCHEDULED:
        cmds.evalDeferred(lambda: update_ae())
        AE_UPDATE_SCHEDULED = True


def refresh_all_views():
    """ Schedules a refresh of all views """
    omUI.M3dView.scheduleRefreshAllViews()
