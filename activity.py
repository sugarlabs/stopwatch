# Copyright 2007 Collabora Ltd.
# Copyright 2011-2012 rafael ortiz rafael@activitycentral.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""Stopwatch Activity"""
"""Actividad Cronometro"""
import logging

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('TelepathyGLib', '0.12')

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import TelepathyGLib

from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.activity.activity import Activity
from sugar3.activity.widgets import StopButton, ShareButton, TitleEntry, \
     ActivityButton
from sugar3.presence import presenceservice
from sugar3.presence.tubeconn import TubeConnection

import stopwatch
import dobject

import cPickle
try:
    import json
except ImportError:
    import simplejson as json

SERVICE = "org.laptop.StopWatch"


class StopWatchActivity(Activity):
    """StopWatch Activity as specified in activity.info"""
    def __init__(self, handle):
        """Set up the StopWatch activity."""
        Activity.__init__(self, handle)
        self._logger = logging.getLogger('stopwatch-activity')

        GObject.threads_init()

        toolbar_box = ToolbarBox()
        self.activity_button = ActivityButton(self)
        toolbar_box.toolbar.insert(self.activity_button, 0)
        self.activity_button.show()

        title_entry = TitleEntry(self)
        toolbar_box.toolbar.insert(title_entry, -1)
        title_entry.show()

        try:
                from sugar3.activity.widgets import DescriptionItem
                description_item = DescriptionItem(self)
                toolbar_box.toolbar.insert(description_item, -1)
                description_item.show()
        except:
                pass

        share_button = ShareButton(self)
        toolbar_box.toolbar.insert(share_button, -1)
        share_button.show()

        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_expand(True)
        toolbar_box.toolbar.insert(separator, -1)
        separator.show()

        stop_button = StopButton(self)
        toolbar_box.toolbar.insert(stop_button, -1)
        stop_button.show()

        self.set_toolbar_box(toolbar_box)

        self.tubebox = dobject.TubeBox()
        self.timer = dobject.TimeHandler("main", self.tubebox)
        self.gui = stopwatch.GUIView(self.tubebox, self.timer, self)

        self.set_canvas(self.gui.display)
        self.show_all()

        self.initiating = False

        # get the Presence Service
        self.pservice = presenceservice.get_instance()
        # Buddy object for you
        owner = self.pservice.get_owner()
        self.owner = owner

        self.connect('shared', self._shared_cb)
        self.connect('joined', self._joined_cb)

        self.add_events(Gdk.EventMask.VISIBILITY_NOTIFY_MASK)
        self.connect("visibility-notify-event", self._visible_cb)
        self.connect("notify::active", self._active_cb)

        self.connect('key-press-event', self._keypress_cb)

    def _shared_cb(self, activity):
        self._logger.debug('My activity was shared')
        self.initiating = True
        self._sharing_setup()

        self._logger.debug('This is my activity: making a tube...')
        self._tubes_channel.OfferDBusTube(
            SERVICE, {})

    def _sharing_setup(self):
        if self.shared_activity is None:
            self._logger.error('Failed to share or join activity')
            return

        self.conn = self.shared_activity.telepathy_conn
        tubes_chan = self.shared_activity.telepathy_tubes_chan
        text_chan = self.shared_activity.telepathy_text_chan

        self._tubes_channel = tubes_chan[TelepathyGLib.IFACE_CHANNEL_TYPE_TUBES]
        self._text_channel = text_chan[TelepathyGLib.IFACE_CHANNEL_INTERFACE_GROUP]

        self._tubes_channel.connect_to_signal('NewTube', self._new_tube_cb)

    def _list_tubes_reply_cb(self, tubes):
        for tube_info in tubes:
            self._new_tube_cb(*tube_info)

    def _list_tubes_error_cb(self, e):
        self._logger.error('ListTubes() failed: %s', e)

    def _joined_cb(self, activity):
        if not self.shared_activity:
            return

        self._logger.debug('Joined an existing shared activity')
        self.initiating = False
        self._sharing_setup()

        self._logger.debug('This is not my activity: waiting for a tube...')
        self._tubes_channel.ListTubes(
            reply_handler=self._list_tubes_reply_cb,
            error_handler=self._list_tubes_error_cb)

    def _new_tube_cb(self, id, initiator, type, service, params, state):
        self._logger.debug('New tube: ID=%d initator=%d type=%d service=%s '
                           'params=%r state=%d',
                           id, initiator, type, service, params, state)
        if type == TelepathyGLib.TubeType.DBUS and \
           service == SERVICE:
            if state == TelepathyGLib.TubeState.LOCAL_PENDING:
                self._tubes_channel.AcceptDBusTube(
                    id)
            tube_conn = TubeConnection(self.conn, self._tubes_channel, id,
                                       group_iface=self._text_channel)
            self.tubebox.insert_tube(tube_conn, self.initiating)

    def read_file(self, file_path):
        f = open(file_path, 'r')
        s = f.read()
        try:
            q = json.loads(s)
        except ValueError:
            q = cPickle.loads(s)
        f.close()
        self.gui.set_all(q)

    def write_file(self, file_path):
        self.metadata['mime_type'] = 'application/x-stopwatch-activity'
        q = self.gui.get_all()
        f = open(file_path, 'w')
        s = json.dumps(q)
        f.write(s)
        f.close()

    def _active_cb(self, widget, event):
        self._logger.debug("_active_cb")
        if self.props.active:
            self.gui.resume()
        else:
            self.gui.pause()

    def _visible_cb(self, widget, event):
        self._logger.debug("_visible_cb")
        if event.get_state() == Gdk.VisibilityState.FULLY_OBSCURED:
            self.gui.pause()
        else:
            self.gui.resume()

    def _keypress_cb(self, widget, event):
        if event.keyval in (Gdk.KEY_Up, Gdk.KEY_ISO_Left_Tab):
            self.gui.select_up()
            return True
        elif event.keyval in (Gdk.KEY_Down, Gdk.KEY_Tab):
            self.gui.select_down()
            return True
