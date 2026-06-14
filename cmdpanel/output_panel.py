"""
output_panel.py — Inline output panel (right side of the widget).
Accepts an on_clear callback so the parent can hide the panel when cleared.
"""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Pango


class OutputPanel(Gtk.Box):
    def __init__(self, on_clear=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._on_clear_cb = on_clear
        self.add_css_class("output-panel")

        # ── Separator on the left edge ───────────────────────────────────────
        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        # The separator is between panels; handled by CSS border instead.

        # ── Header ───────────────────────────────────────────────────────────
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        header.add_css_class("output-header")
        self.append(header)

        self._title_label = Gtk.Label(label="Output", xalign=0)
        self._title_label.add_css_class("caption-heading")
        self._title_label.set_hexpand(True)
        self._title_label.set_margin_start(12)
        self._title_label.set_margin_top(10)
        self._title_label.set_margin_bottom(10)
        header.append(self._title_label)

        self._status_label = Gtk.Label(label="", xalign=1)
        self._status_label.add_css_class("caption")
        self._status_label.set_margin_end(8)
        header.append(self._status_label)

        clear_btn = Gtk.Button(icon_name="edit-clear-symbolic")
        clear_btn.add_css_class("flat")
        clear_btn.set_tooltip_text("Clear and hide output")
        clear_btn.set_margin_end(4)
        clear_btn.set_margin_top(2)
        clear_btn.set_margin_bottom(2)
        clear_btn.connect("clicked", self._on_clear)
        header.append(clear_btn)

        # ── Text view ────────────────────────────────────────────────────────
        self._scroll = Gtk.ScrolledWindow()
        self._scroll.set_vexpand(True)
        self._scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.append(self._scroll)

        self._buffer = Gtk.TextBuffer()
        self._view = Gtk.TextView(buffer=self._buffer)
        self._view.set_editable(False)
        self._view.set_cursor_visible(False)
        self._view.set_monospace(True)
        self._view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._view.set_top_margin(8)
        self._view.set_bottom_margin(8)
        self._view.set_left_margin(12)
        self._view.set_right_margin(12)
        self._view.add_css_class("output-view")
        self._scroll.set_child(self._view)

        # Text tags
        tag_table = self._buffer.get_tag_table()

        self._cmd_tag = Gtk.TextTag(name="cmd")
        self._cmd_tag.set_property("foreground", "#78a9ff")
        self._cmd_tag.set_property("weight", Pango.Weight.BOLD)
        tag_table.add(self._cmd_tag)

        self._ok_tag = Gtk.TextTag(name="ok")
        self._ok_tag.set_property("foreground", "#42be65")
        self._ok_tag.set_property("weight", Pango.Weight.BOLD)
        tag_table.add(self._ok_tag)

        self._err_tag = Gtk.TextTag(name="err")
        self._err_tag.set_property("foreground", "#fa4d56")
        self._err_tag.set_property("weight", Pango.Weight.BOLD)
        tag_table.add(self._err_tag)

        self._dim_tag = Gtk.TextTag(name="dim")
        self._dim_tag.set_property("foreground", "#6f6f6f")
        tag_table.add(self._dim_tag)

    # ── Public API ───────────────────────────────────────────────────────────

    def start(self, command_name: str, command: str):
        self._buffer.set_text("")
        self._append(f"▶ {command_name}\n", "cmd")
        self._append(f"$ {command}\n\n", "dim")
        self._set_status("Running…", None)

    def append_line(self, line: str):
        self._append(line + "\n")
        self._scroll_to_end()

    def finish(self, ok: bool):
        if ok:
            self._append("\n✓ Done.\n", "ok")
            self._set_status("Done", "ok")
        else:
            self._append("\n✗ Failed.\n", "err")
            self._set_status("Failed", "err")
        self._scroll_to_end()

    # ── Private ──────────────────────────────────────────────────────────────

    def _append(self, text: str, tag_name: str | None = None):
        end = self._buffer.get_end_iter()
        if tag_name:
            self._buffer.insert_with_tags_by_name(end, text, tag_name)
        else:
            self._buffer.insert(end, text)

    def _scroll_to_end(self):
        GLib.idle_add(self.__do_scroll)

    def __do_scroll(self):
        end = self._buffer.get_end_iter()
        self._buffer.place_cursor(end)
        self._view.scroll_mark_onscreen(self._buffer.get_insert())
        return False

    def _set_status(self, text: str, tag_name: str | None):
        self._status_label.set_text(text)
        if tag_name == "ok":
            self._status_label.set_css_classes(["caption", "success"])
        elif tag_name == "err":
            self._status_label.set_css_classes(["caption", "error"])
        else:
            self._status_label.set_css_classes(["caption"])

    def _on_clear(self, _):
        self._buffer.set_text("")
        self._status_label.set_text("")
        if self._on_clear_cb:
            self._on_clear_cb()
