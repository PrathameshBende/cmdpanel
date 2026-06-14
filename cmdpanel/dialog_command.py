"""
dialog_command.py — Add / Edit command dialog.
"""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw


class CommandDialog(Adw.Dialog):
    """
    Modal dialog for creating or editing a command entry.
    On confirm, calls `on_save(command_dict)`.
    """

    def __init__(self, parent, on_save, existing: dict | None = None):
        super().__init__()
        self._on_save = on_save
        self._existing = existing or {}

        self.set_title("Edit Command" if existing else "New Command")
        self.set_content_width(400)

        # ── Layout ──────────────────────────────────────────────────────────
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)

        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        toolbar_view.add_top_bar(header)

        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda _: self.close())
        header.pack_start(cancel_btn)

        self._save_btn = Gtk.Button(label="Save")
        self._save_btn.add_css_class("suggested-action")
        self._save_btn.connect("clicked", self._on_save_clicked)
        header.pack_end(self._save_btn)

        # ── Form ────────────────────────────────────────────────────────────
        clamp = Adw.Clamp(maximum_size=380)
        toolbar_view.set_content(clamp)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        box.set_margin_start(16)
        box.set_margin_end(16)
        clamp.set_child(box)

        # Icon + Name row
        icon_name_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.append(icon_name_box)

        self._icon_entry = Gtk.Entry()
        self._icon_entry.set_placeholder_text("🔧")
        self._icon_entry.set_max_width_chars(3)
        self._icon_entry.set_width_chars(3)
        self._icon_entry.set_tooltip_text("Emoji icon (optional)")
        icon_name_box.append(self._icon_entry)

        self._name_entry = Gtk.Entry()
        self._name_entry.set_placeholder_text("Command name")
        self._name_entry.set_hexpand(True)
        self._name_entry.connect("changed", self._validate)
        icon_name_box.append(self._name_entry)

        # Command text view
        cmd_frame = Gtk.Frame()
        cmd_frame.add_css_class("card")
        box.append(cmd_frame)

        cmd_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        cmd_frame.set_child(cmd_box)

        cmd_label = Gtk.Label(label="Command", xalign=0)
        cmd_label.add_css_class("caption")
        cmd_label.set_margin_top(8)
        cmd_label.set_margin_start(12)
        cmd_label.set_margin_bottom(4)
        cmd_box.append(cmd_label)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(80)
        scrolled.set_max_content_height(160)
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        cmd_box.append(scrolled)

        self._cmd_buffer = Gtk.TextBuffer()
        self._cmd_view = Gtk.TextView(buffer=self._cmd_buffer)
        self._cmd_view.set_monospace(True)
        self._cmd_view.set_top_margin(4)
        self._cmd_view.set_bottom_margin(8)
        self._cmd_view.set_left_margin(12)
        self._cmd_view.set_right_margin(12)
        self._cmd_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._cmd_buffer.connect("changed", self._validate)
        scrolled.set_child(self._cmd_view)

        # Favorite row
        fav_row = Adw.ActionRow(title="Mark as Favorite")
        fav_row.add_css_class("card")
        self._fav_switch = Gtk.Switch()
        self._fav_switch.set_valign(Gtk.Align.CENTER)
        fav_row.add_suffix(self._fav_switch)
        fav_row.set_activatable_widget(self._fav_switch)
        box.append(fav_row)

        # ── Pre-fill if editing ──────────────────────────────────────────────
        if existing:
            self._icon_entry.set_text(existing.get("icon", ""))
            self._name_entry.set_text(existing.get("name", ""))
            self._cmd_buffer.set_text(existing.get("command", ""))
            self._fav_switch.set_active(existing.get("favorite", False))

        self._validate()

    def _validate(self, *_):
        name_ok = bool(self._name_entry.get_text().strip())
        cmd_ok = bool(self._cmd_buffer.get_text(
            self._cmd_buffer.get_start_iter(),
            self._cmd_buffer.get_end_iter(),
            False,
        ).strip())
        self._save_btn.set_sensitive(name_ok and cmd_ok)

    def _on_save_clicked(self, _):
        entry = {
            "name": self._name_entry.get_text().strip(),
            "command": self._cmd_buffer.get_text(
                self._cmd_buffer.get_start_iter(),
                self._cmd_buffer.get_end_iter(),
                False,
            ).strip(),
            "favorite": self._fav_switch.get_active(),
            "icon": self._icon_entry.get_text().strip(),
        }
        # Preserve original id if editing
        if "id" in self._existing:
            entry["id"] = self._existing["id"]
        self._on_save(entry)
        self.close()
