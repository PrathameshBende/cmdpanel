"""
app.py — Application entry point.
"""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio

from .window import CmdPanelWindow
from .style import load_css


class CmdPanelApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="io.github.cmdpanel",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.connect("activate", self._on_activate)

    def _on_activate(self, app):
        load_css()
        win = CmdPanelWindow(app)
        # Hold the app so it doesn't exit when GTK thinks no managed
        # windows are open (Gtk.Window instead of Adw.ApplicationWindow)
        self.hold()
        win.connect("close-request", lambda _: self.release())
        win.present()
