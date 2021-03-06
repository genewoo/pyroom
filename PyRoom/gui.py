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
basic global GUI

Additionally allows user to apply custom settings
"""

import gtk
import gobject
import pango
import gtksourceview
import gtk.glade
import ConfigParser
import os

class FadeLabel(gtk.Label):
    """ GTK Label with timed fade out effect """

    active_duration = 3000  # Fade start after this time
    fade_duration = 1500.0  # Fade duration

    def __init__(self, message='', active_color=None, inactive_color=None):
        gtk.Label.__init__(self, message)
        if not active_color:
            active_color = '#ffffff'
        self.active_color = active_color
        if not inactive_color:
            inactive_color = '#000000'
        self.fade_level = 0
        self.inactive_color = inactive_color
        self.idle = 0

    def set_text(self, message, duration=None):
        """change text that is displayed
        @param message: message to display
        @param duration: duration in miliseconds"""
        if not duration:
            duration = self.active_duration
        self.modify_fg(gtk.STATE_NORMAL,
                       gtk.gdk.color_parse(self.active_color))
        gtk.Label.set_text(self, message)
        if self.idle:
            gobject.source_remove(self.idle)
        self.idle = gobject.timeout_add(duration, self.fade_start)

    def fade_start(self):
        """start fading timer"""
        self.fade_level = 1.0
        if self.idle:
            gobject.source_remove(self.idle)
        self.idle = gobject.timeout_add(25, self.fade_out)

    def fade_out(self):
        """now fade out"""
        color = gtk.gdk.color_parse(self.inactive_color)
        (red1, green1, blue1) = (color.red, color.green, color.blue)
        color = gtk.gdk.color_parse(self.active_color)
        (red2, green2, blue2) = (color.red, color.green, color.blue)
        red = red1 + int(self.fade_level * abs(red1 - red2))
        green = green1 + int(self.fade_level * abs(green1 - green2))
        blue = blue1 + int(self.fade_level * abs(blue1 - blue2))
        self.modify_fg(gtk.STATE_NORMAL, gtk.gdk.Color(red, green, blue))
        self.fade_level -= 1.0 / (self.fade_duration / 25)
        if self.fade_level > 0:
            return True
        self.idle = 0
        return False

class GUI(object):
    """our basic global gui object"""

    def __init__(self, style, pyroom_config, edit_instance):
        self.status = FadeLabel()
        self.style = style
        self.edit_instance = edit_instance

        # Main window

        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_name('PyRoom')
        self.window.set_title("PyRoom")
        self.window.connect('delete_event', self.delete_event)
        self.window.connect('destroy', self.destroy)

        self.textbox = gtksourceview.SourceView()
        self.textbox.connect('scroll-event', self.scroll_event)

        self.textbox.set_wrap_mode(gtk.WRAP_WORD)

        self.fixed = gtk.Fixed()
        self.vbox = gtk.VBox()
        self.window.add(self.fixed)
        self.fixed.put(self.vbox, 0, 0)

        self.boxout = gtk.EventBox()
        self.boxout.set_border_width(1)
        self.boxin = gtk.EventBox()
        self.boxin.set_border_width(1)
        self.vbox.pack_start(self.boxout, True, True, 6)
        self.boxout.add(self.boxin)

        self.scrolled = gtk.ScrolledWindow()
        self.boxin.add(self.scrolled)
        self.scrolled.add(self.textbox)
        self.scrolled.set_policy(gtk.POLICY_NEVER, gtk.POLICY_NEVER)
        self.scrolled.show()
        self.scrolled.set_property('resize-mode', gtk.RESIZE_PARENT)
        self.textbox.set_property('resize-mode', gtk.RESIZE_PARENT)
        self.vbox.set_property('resize-mode', gtk.RESIZE_PARENT)
        self.vbox.show_all()

        # Status
        self.hbox = gtk.HBox()
        self.hbox.set_spacing(12)
        self.hbox.pack_end(self.status, True, True, 0)
        self.vbox.pack_end(self.hbox, False, False, 0)
        self.status.set_alignment(0.0, 0.5)
        self.status.set_justify(gtk.JUSTIFY_LEFT)


        self.config = ConfigParser.ConfigParser()
        if self.style:
            theme = os.path.join(pyroom_config.themes_dir,
                                 style + ".theme")
            if not os.path.isfile(theme) :
            	theme = os.path.join(pyroom_config.global_themes_dir,
            	style + ".theme")
        else:
            theme = os.path.join(pyroom_config.themes_dir,
            pyroom_config.config.get("visual", "theme") + ".theme")
            if not os.path.isfile(theme) :
            	theme = os.path.join(pyroom_config.global_themes_dir,
            	pyroom_config.config.get("visual", "theme") + ".theme")
        self.config.read(theme)

    def quit(self):
        """ quit pyroom """
        gtk.main_quit()

    def delete_event(self, widget, event, data=None):
        """ Quit """
        self.edit_instance.dialog_quit()
        return True

    def destroy(self, widget, data=None):
        """ Quit """
        gtk.main_quit()

    def scroll_event(self, widget, event):
        """ Scroll event dispatcher """

        if event.direction == gtk.gdk.SCROLL_UP:
            self.scroll_up()
        elif event.direction == gtk.gdk.SCROLL_DOWN:
            self.scroll_down()

    def scroll_down(self):
        """ Scroll window down """

        adj = self.scrolled.get_vadjustment()
        if adj.upper > adj.page_size:
            adj.value = min(adj.upper - adj.page_size, adj.value
                             + adj.step_increment)

    def scroll_up(self):
        """ Scroll window up """

        adj = self.scrolled.get_vadjustment()
        if adj.value > adj.step_increment:
            adj.value -= adj.step_increment
        else:
            adj.value = 0

    def apply_style(self, style=None, mode='normal'):
        """
        apply the given style and rerender the textbox
        @param style: style that was selected
        @param mode: normal if style is builtin or at first call on startup,
                     otherwise custom
        """
        if mode == 'normal':
            get_color = lambda color: gtk.gdk.color_parse(
                                        self.config.get('theme', color)
                                        )
        elif mode == 'custom':
            self.style = style
            get_color = lambda color: gtk.gdk.color_parse(self.style[color])

        self.window.modify_bg(gtk.STATE_NORMAL, get_color('background'))
        self.textbox.modify_bg(gtk.STATE_NORMAL, get_color('background'))
        self.textbox.modify_base(gtk.STATE_NORMAL, get_color('background'))
        self.textbox.modify_base(gtk.STATE_SELECTED, get_color('foreground'))
        self.textbox.modify_text(gtk.STATE_NORMAL, get_color('foreground'))
        self.textbox.modify_text(gtk.STATE_SELECTED, get_color('background'))
        self.textbox.modify_fg(gtk.STATE_NORMAL, get_color('foreground'))
        self.status.active_color = self.config.get('theme', 'foreground')
        self.status.inactive_color = self.config.get('theme', 'background')
        self.boxout.modify_bg(gtk.STATE_NORMAL, 
                              get_color('border'),
                             )
        font_and_size = "%s %d" % (self.config.get('theme', 'font'),
                                   float(self.config.get('theme', 'fontsize')))
        self.textbox.modify_font(pango.FontDescription(font_and_size))
        
        gtkrc_string = """\
        style "pyroom-colored-cursor" { 
        GtkTextView::cursor-color = '%s'
        }
        class "GtkWidget" style "pyroom-colored-cursor"
        """ % self.config.get('theme', 'foreground')
        gtk.rc_parse_string(gtkrc_string)

        # for multiple monitors
        screen = gtk.gdk.screen_get_default() 
        root_window = screen.get_root_window() 
        mouse_x, mouse_y, mouse_mods = root_window.get_pointer()
        current_monitor_number = screen.get_monitor_at_point(mouse_x,mouse_y)
        monitor_geometry = screen.get_monitor_geometry(current_monitor_number)
        (screen_width, screen_height) = (monitor_geometry.width,
                                         monitor_geometry.height)

        if mode == "normal":
            width_percentage = float(self.config.get('theme', 'width'))
            height_percentage = float(self.config.get('theme', 'height'))
            padding = int(float(self.config.get('theme', 'padding')))
            font_and_size = "%s %d" % (self.config.get('theme', 'font'),
                           float(self.config.get('theme', 'fontsize')))
        elif mode == "custom":
            width_percentage = self.style['size'][0]
            height_percentage = self.style['size'][1]
            padding = int(float(self.style['padding']))
            font_and_size = "%s %d" % (self.style['font'],
                           float(self.style['fontsize']))

        self.textbox.modify_font(pango.FontDescription(font_and_size))
        self.vbox.set_size_request(int(width_percentage * screen_width),
                                   int(height_percentage * screen_height))
        self.fixed.move(self.vbox, 
            int(((1 - width_percentage) * screen_width) / 2),
            int(((1 - height_percentage) * screen_height) / 2),
        )
        
        self.textbox.set_border_width(padding) 
