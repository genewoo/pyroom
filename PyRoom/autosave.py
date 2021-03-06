# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# PyRoom - A clone of WriteRoom
# Copyright (c) 2007 Nicolas P. Rougier & NoWhereMan
# Copyright (c) 2008 The Pyroom Team - See AUTHORS file for more information
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------


"""
provide autosave functions

allows a user to automatically save their files to /var/tmp/pyroom at a time
period that is defined in the settings dialog (default is every 3 minutes)
"""

import gobject
import os
import tempfile

from pyroom_error import PyroomError

#Elapsed time in seconds, autosave in minutes.
ELAPSED_TIME = 0 
AUTOSAVE_TIME = 3

TEMP_FOLDER = tempfile.gettempdir()
TIMEOUT_ID = 0

FILE_UNNAMED = _('* Unnamed *')  


def autosave_init(edit_instance, mill=1000):
    """Init the internal autosave timer"""
    global ELAPSED_TIME
    global TIMEOUT_ID
    TIMEOUT_ID = gobject.timeout_add(mill, timeout, edit_instance)
    ELAPSED_TIME = 0


def save_file(filename, text):
    """save text fo filename"""
    try:
        out_file = open(filename, "w")
        out_file.write(text)
        out_file.close()
    except IOError:
        raise PyroomError(_("Could not autosave file %s") % filename)

def autosave_quit():
    """dispose the internal timer"""
    gobject.source_remove(TIMEOUT_ID)


def autosave_file(edit_instance, buf_id):
    """AutoSave the Buffer to temp folder"""
    buf = edit_instance.buffers[buf_id]
    if not os.path.isdir(TEMP_FOLDER):
        os.mkdir(TEMP_FOLDER)

    if not hasattr(buf, 'tmp_filename'):
        if buf.filename == FILE_UNNAMED:
            buf.tmp_filename = tempfile.mkstemp(suffix="",
                prefix="noname_tmp_", dir=TEMP_FOLDER, text=True)[1]
        else:
            buf_name = os.path.split(buf.filename)[1]
            buf.tmp_filename = tempfile.mkstemp(suffix="",
                prefix = buf_name + "_tmp_", dir=TEMP_FOLDER, text=True)[1]
    save_file(buf.tmp_filename, buf.get_text(buf.get_start_iter(),
        buf.get_end_iter()))
    edit_instance.status.set_text(_('AutoSaving Buffer %(buf_id)d, to temp\
     file %(buf_tmp_filename)s') % {'buf_id': buf_id, 
                   'buf_tmp_filename': buf.tmp_filename})

def timeout(edit_instance):
    "the Timer Function"
    global ELAPSED_TIME

    if int(AUTOSAVE_TIME) != 0:
        ELAPSED_TIME += 1
        if ELAPSED_TIME >= int(AUTOSAVE_TIME) * 60:
            for buf in edit_instance.buffers:
                autosave_file(edit_instance, 
                    edit_instance.buffers.index(buf))
            ELAPSED_TIME = 0
        return True # continue repeat timeout event
    else:
        return False #stop timeout event
