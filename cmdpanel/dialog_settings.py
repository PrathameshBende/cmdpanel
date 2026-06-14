"""
dialog_settings.py — App settings dialog.
"""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from .store import load_settings, save_settings
from .autostart import set_autostart, is_autostart_enabled


class SettingsDialog(Adw.PreferencesDialog):
    def __init__(self, parent):
        super().__init__()
        self.set_title("Settings")
        self._settings = load_settings()

        page = Adw.PreferencesPage()
        self.add(page)

        # ── Startup ─────────────────────────────────────────────────────────
        startup_group = Adw.PreferencesGroup(title="Startup")
        page.add(startup_group)

        login_row = Adw.SwitchRow(
            title="Start on Login",
            subtitle="Launch automatically when you log in",
        )
        login_row.set_active(is_autostart_enabled())
        login_row.connect("notify::active", self._on_login_toggled)
        startup_group.add(login_row)

        # ── Window ──────────────────────────────────────────────────────────
        window_group = Adw.PreferencesGroup(title="Window")
        page.add(window_group)

        size_row = Adw.SwitchRow(title="Remember Size")
        size_row.set_active(self._settings.get("remember_size", True))
        size_row.connect("notify::active", lambda r, _: self._save("remember_size", r.get_active()))
        window_group.add(size_row)

        pos_row = Adw.SwitchRow(title="Remember Position")
        pos_row.set_active(self._settings.get("remember_position", True))
        pos_row.connect("notify::active", lambda r, _: self._save("remember_position", r.get_active()))
        window_group.add(pos_row)

    def _on_login_toggled(self, row, _):
        set_autostart(row.get_active())

    def _save(self, key, value):
        self._settings[key] = value
        save_settings(self._settings)
