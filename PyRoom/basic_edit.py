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
provide basic editor functionality

contains basic functions needed for pyroom - any core functionality is included
within this file
"""

import gtk
import gtk.glade
import gtksourceview
import os

from pyroom_error import PyroomError
from gui import GUI
from preferences import Preferences
import autosave

FILE_UNNAMED = _('* Unnamed *')

KEY_BINDINGS = '\n'.join([
_('Control-H: Show help in a new buffer'),
_('Control-I: Show buffer information'),
_('Control-P: Shows Preferences dialog'),
_('Control-N: Create a new buffer'),
_('Control-O: Open a file in a new buffer'),
_('Control-Q: Quit'),
_('Control-S: Save current buffer'),
_('Control-Shift-S: Save current buffer as'),
_('Control-W: Close buffer and exit if it was the last buffer'),
_('Control-Y: Redo last typing'),
_('Control-Z: Undo last typing'),
_('Control-Page Up: Switch to previous buffer'),
_('Control-Page Down: Switch to next buffer'), ])

HELP = \
    _("""PyRoom - distraction free writing
Copyright (c) 2007 Nicolas Rougier, NoWhereMan
Copyright (c) 2008 Bruno Bord and the PyRoom team

Welcome to PyRoom and distraction-free writing.

To hide this help window, press Control-W.

PyRoom stays out of your way with formatting options and buttons, 
it is largely keyboard controlled, via shortcuts. You can find a list
of available keyboard shortcuts later.

If enabled in preferences, pyroom will save your files automatically every
few minutes or when you press the keyboard shortcut.

Commands:
---------
%s

""" % KEY_BINDINGS)

def define_keybindings(edit_instance):
    """define keybindings, respectively to keyboard layout"""
    keymap = gtk.gdk.keymap_get_default()
    basic_bindings = {
        gtk.keysyms.Page_Up: edit_instance.prev_buffer,
        gtk.keysyms.Page_Down: edit_instance.next_buffer,
        gtk.keysyms.H: edit_instance.show_help,
        gtk.keysyms.I: edit_instance.show_info,
        gtk.keysyms.N: edit_instance.new_buffer,
        gtk.keysyms.O: edit_instance.open_file,
        gtk.keysyms.P: edit_instance.preferences.show,
        gtk.keysyms.Q: edit_instance.dialog_quit,
        gtk.keysyms.S: edit_instance.save_file,
        gtk.keysyms.W: edit_instance.close_dialog,
        gtk.keysyms.Y: edit_instance.redo,
        gtk.keysyms.Z: edit_instance.undo,
    }
    translated_bindings = {}
    for key, value in basic_bindings.items():
        hardware_keycode = keymap.get_entries_for_keyval(key)[0][0]
        translated_bindings[hardware_keycode] = value
    return translated_bindings

class BasicEdit(object):
    """editing logic that gets passed around"""

    def __init__(self, style, pyroom_config):
        self.current = 0
        self.buffers = []
        self.style = style
        self.config = pyroom_config.config
        self.gui = GUI(style, pyroom_config, self)
        self.preferences = Preferences(gui=self.gui, style=style,
            pyroom_config=pyroom_config)
        self.status = self.gui.status
        self.window = self.gui.window
        self.textbox = self.gui.textbox

        self.new_buffer()

        self.textbox.connect('key-press-event', self.key_press_event)

        # Set line numbers visible, set linespacing
        self.textbox.set_show_line_numbers(int(self.config.get("visual",
                                               "linenumber")))
        self.textbox.set_pixels_below_lines(int(self.config.get("visual", "linespacing")))
        self.textbox.set_pixels_above_lines(int(self.config.get("visual", "linespacing")))
        self.textbox.set_pixels_inside_wrap(int(self.config.get("visual", "linespacing")))
                
        # Autosave timer object
        autosave.autosave_init(self)

        self.window.show_all()
        self.window.fullscreen()

        # Handle multiple monitors
        screen = gtk.gdk.screen_get_default()
        root_window = screen.get_root_window()
        mouse_x, mouse_y, mouse_mods = root_window.get_pointer()
        current_monitor_number = screen.get_monitor_at_point(mouse_x, mouse_y)
        monitor_geometry = screen.get_monitor_geometry(current_monitor_number)
        self.window.move(monitor_geometry.x, monitor_geometry.y)
        self.window.set_geometry_hints(None, min_width=monitor_geometry.width,
          min_height=monitor_geometry.height, max_width=monitor_geometry.width,
          max_height=monitor_geometry.height
        )

        # Defines the glade file functions for use on closing a buffer
        self.wTree = gtk.glade.XML(os.path.join(
            pyroom_config.pyroom_absolute_path, "interface.glade"),
            "SaveBuffer")
        self.dialog = self.wTree.get_widget("SaveBuffer")
        self.dialog.set_transient_for(self.window)
        dic = {
                "on_button-close_clicked": self.unsave_dialog,
                "on_button-cancel_clicked": self.cancel_dialog,
                "on_button-save_clicked": self.save_dialog,
                }
        self.wTree.signal_autoconnect(dic)

        #Defines the glade file functions for use on exit
        self.aTree = gtk.glade.XML(os.path.join(
            pyroom_config.pyroom_absolute_path, "interface.glade"),
            "QuitSave")
        self.quitdialog = self.aTree.get_widget("QuitSave")
        self.quitdialog.set_transient_for(self.window)
        dic = {
                "on_button-close2_clicked": self.quit_quit,
                "on_button-cancel2_clicked": self.cancel_quit,
                "on_button-save2_clicked": self.save_quit,
                }
        self.aTree.signal_autoconnect(dic)
        self.keybindings = define_keybindings(self)

    def key_press_event(self, widget, event):
        """ key press event dispatcher """
        if event.state & gtk.gdk.CONTROL_MASK:
            if event.hardware_keycode in self.keybindings:
                if self.keybindings[event.hardware_keycode] == self.save_file\
                    and event.state & gtk.gdk.SHIFT_MASK:
                    self.save_file_as()
                else:
                    self.keybindings[event.hardware_keycode]()
                return True
        return False

    def show_info(self):
        """ Display buffer information on status label for 5 seconds """

        buf = self.buffers[self.current]
        if buf.can_undo() or buf.can_redo():
            status = _(' (modified)')
        else:
            status = ''
        self.status.set_text(_('Buffer %(buffer_id)d: %(buffer_name)s\
%(status)s, %(char_count)d byte(s), %(word_count)d word(s)\
, %(lines)d line(s)') % {
            'buffer_id': self.current + 1,
            'buffer_name': buf.filename,
            'status': status,
            'char_count': buf.get_char_count(),
            'word_count': self.word_count(buf),
            'lines': buf.get_line_count(),
            }, 5000)

    def undo(self):
        """ Undo last typing """

        buf = self.textbox.get_buffer()
        if buf.can_undo():
            buf.undo()
        else:
            self.status.set_text(_('Nothing more to undo!'))

    def redo(self):
        """ Redo last typing """

        buf = self.textbox.get_buffer()
        if buf.can_redo():
            buf.redo()
        else:
            self.status.set_text(_('Nothing more to redo!'))

    def toggle_lines(self):
        """ Toggle lines number """
        opposite_state = not self.textbox.get_show_line_numbers()
        self.textbox.set_show_line_numbers(opposite_state)

    def open_file(self):
        """ Open file """

        chooser = gtk.FileChooserDialog('PyRoom', self.window,
                gtk.FILE_CHOOSER_ACTION_OPEN,
                buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        chooser.set_default_response(gtk.RESPONSE_OK)

        res = chooser.run()
        if res == gtk.RESPONSE_OK:
            buf = self.new_buffer()
            buf.filename = chooser.get_filename()
            try:
                buffer_file = open(buf.filename, 'r')
                buf = self.buffers[self.current]
                buf.begin_not_undoable_action()
                utf8 = unicode(buffer_file.read(), 'utf-8')
                buf.set_text(utf8)
                buf.end_not_undoable_action()
                buffer_file.close()
                self.status.set_text(_('File %s open')
                         % buf.filename)
            except IOError, (errno, strerror):
                errortext = _('Unable to open %(filename)s.' % {
                                'filename': buf.filename})
                if errno == 2:
                    errortext += _(' The file does not exist.')
                elif errno == 13:
                    errortext += _(' You do not have permission to \
open the file.')
                raise PyroomError(errortext)
            except:
                raise PyroomError(_('Unable to open %s\n'
                                 % buf.filename))
        else:
            self.status.set_text(_('Closed, no files selected'))
        chooser.destroy()

    def open_file_no_chooser(self, filename):
        """ Open specified file """
        buf = self.new_buffer()
        buf.filename = filename
        try:
            buffer_file = open(buf.filename, 'r')
            buf = self.buffers[self.current]
            buf.begin_not_undoable_action()
            utf8 = unicode(buffer_file.read(), 'utf-8')
            buf.set_text(utf8)
            buf.end_not_undoable_action()
            buffer_file.close()
            self.status.set_text(_('File %s open')
                     % buf.filename)
        except IOError, (errno, strerror):
            errortext = _('Unable to open %(filename)s.' % {
                'filename': buf.filename})
            if errno == 2:
                errortext += _(' The file does not exist.')
            elif errno == 13:
                errortext += _(' You do not have permission to open \
the file.')
            raise PyroomError(errortext)
        except:
            raise PyroomError(_('Unable to open %s\n'
                             % buf.filename))
    def save_file(self):
        """ Save file """
        try:
            buf = self.buffers[self.current]
            if buf.filename != FILE_UNNAMED:
                buffer_file = open(buf.filename, 'w')
                txt = buf.get_text(buf.get_start_iter(),
                                     buf.get_end_iter())
                buffer_file.write(txt)
                buffer_file.close()
                buf.begin_not_undoable_action()
                buf.end_not_undoable_action()
                self.status.set_text(_('File %s saved') % buf.filename)
            else:
                self.save_file_as()
        except IOError, (errno, strerror):
            errortext = _('Unable to save %(filename)s.' % {
                'filename': buf.filename})
            if errno == 13:
                errortext += _(' You do not have permission to write to \
the file.')
            raise PyroomError(errortext)
        except:
            raise PyroomError(_('Unable to save %s\n'
                            % buf.filename))

    def save_file_as(self):
        """ Save file as """

        buf = self.buffers[self.current]
        chooser = gtk.FileChooserDialog('PyRoom', self.window,
                gtk.FILE_CHOOSER_ACTION_SAVE,
                buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                gtk.STOCK_SAVE, gtk.RESPONSE_OK))
        chooser.set_default_response(gtk.RESPONSE_OK)
        if buf.filename != FILE_UNNAMED:
            chooser.set_filename(buf.filename)
        res = chooser.run()
        if res == gtk.RESPONSE_OK:
            buf.filename = chooser.get_filename()
            self.save_file()
        else:
            self.status.set_text(_('Closed, no files selected'))
        chooser.destroy()

    def word_count(self, buf):
        """ Word count in a text buffer """

        iter1 = buf.get_start_iter()
        iter2 = iter1.copy()
        iter2.forward_word_end()
        count = 0
        while iter2.get_offset() != iter1.get_offset():
            count += 1
            iter1 = iter2.copy()
            iter2.forward_word_end()
        return count

    def show_help(self):
        """ Create a new buffer and inserts help """
        buf = self.new_buffer()
        buf.begin_not_undoable_action()
        buf.set_text(HELP)
        buf.end_not_undoable_action()
        self.status.set_text("Displaying help. Press control W to exit and \
continue editing your document.")

    def new_buffer(self):
        """ Create a new buffer """

        buf = gtksourceview.SourceBuffer()
        buf.set_check_brackets(False)
        buf.set_highlight(False)
        buf.filename = FILE_UNNAMED
        self.buffers.insert(self.current + 1, buf)
        buf.place_cursor(buf.get_end_iter())
        self.next_buffer()
        return buf

    def close_dialog(self):
        """ask for confirmation if there are unsaved contents"""
        buf = self.buffers[self.current]
        if buf.can_undo() or buf.can_redo():
            self.dialog.show()
        else:
            self.close_buffer()

    def cancel_dialog(self, widget, data=None):
        """dialog has been canceled"""
        self.dialog.hide()

    def unsave_dialog(self, widget, data =None):
        """don't save before closing"""
        self.dialog.hide()
        self.close_buffer()

    def save_dialog(self, widget, data=None):
        """save when closing"""
        self.dialog.hide()
        self.save_file()
        self.close_buffer()

    def close_buffer(self):
        """ Close current buffer """


        if len(self.buffers) > 1:

            self.buffers.pop(self.current)
            self.current = min(len(self.buffers) - 1, self.current)
            self.set_buffer(self.current)
        else:
            quit()

    def set_buffer(self, index):
        """ Set current buffer """

        if index >= 0 and index < len(self.buffers):
            self.current = index
            buf = self.buffers[index]
            self.textbox.set_buffer(buf)
            if hasattr(self, 'status'):
                self.status.set_text(
                    _('Switching to buffer %(buffer_id)d (%(buffer_name)s)'
                    % {'buffer_id': self.current + 1,
                       'buffer_name': buf.filename}))

    def next_buffer(self):
        """ Switch to next buffer """

        if self.current < len(self.buffers) - 1:
            self.current += 1
        else:
            self.current = 0
        self.set_buffer(self.current)
        self.gui.textbox.scroll_to_mark(
            self.buffers[self.current].get_insert(),
            0.0,
        )

    def prev_buffer(self):
        """ Switch to prev buffer """

        if self.current > 0:
            self.current -= 1
        else:
            self.current = len(self.buffers) - 1
        self.set_buffer(self.current)
        self.gui.textbox.scroll_to_mark(
            self.buffers[self.current].get_insert(),
            0.0,
        )
    def dialog_quit(self):
        """the quit dialog"""
        count = 0
        ret = False
        for buf in self.buffers:
            if (buf.can_undo() or buf.can_redo()) and \
            not buf.get_text(buf.get_start_iter(),
                                 buf.get_end_iter()) == '':
                count = count + 1
        if count > 0:
            self.quitdialog.show()
        else:
            self.quit()

    def cancel_quit(self, widget, data=None):
        """don't quit"""
        self.quitdialog.hide()

    def save_quit(self, widget, data=None):
        """save before quitting"""
        self.quitdialog.hide()
        for buf in self.buffers:
            if buf.can_undo() or buf.can_redo():
                if buf.filename == FILE_UNNAMED:
                    self.save_file_as()
                else:
                    self.save_file()
        self.quit()

    def quit_quit(self, widget, data=None):
        """really quit"""
        self.quitdialog.hide()
        self.quit()

    def quit(self):
        """cleanup before quitting"""
        autosave.autosave_quit()
        self.gui.quit()
# EOF
