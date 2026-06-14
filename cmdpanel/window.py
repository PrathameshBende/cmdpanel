"""
window.py — Main application window.

Uses gtk4-layer-shell to sit on the desktop wallpaper layer.
CRITICAL: Gtk4LayerShell.init_for_window() must be called before
the window is realized. We override do_realize() to guarantee this.
"""

import uuid
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gtk, Adw, GLib, GObject, Gtk4LayerShell

from .store import load_commands, save_commands, load_settings, save_settings
from .runner import run_command
from .output_panel import OutputPanel
from .command_row import CommandRow
from .dialog_command import CommandDialog
from .dialog_settings import SettingsDialog


class CmdPanelWindow(Gtk.Window):
    """
    Plain Gtk.Window — NOT Adw.ApplicationWindow.
    Adw.ApplicationWindow sets window properties during __init__ that
    cause early realization, which prevents layer-shell from working.
    We use Gtk.Window and apply Adwaita styling manually.
    """

    def __init__(self, app):
        super().__init__(application=app)
        self.set_title("CmdPanel")
        self.set_decorated(False)
        self.set_resizable(False)

        # ── Layer shell MUST be called before realize ────────────────────────
        Gtk4LayerShell.init_for_window(self)
        Gtk4LayerShell.set_layer(self, Gtk4LayerShell.Layer.BOTTOM)
        Gtk4LayerShell.set_keyboard_mode(self, Gtk4LayerShell.KeyboardMode.NONE)
        Gtk4LayerShell.set_exclusive_zone(self, 0)

        self._settings = load_settings()
        self._apply_anchor()

        self._commands: list[dict] = load_commands()
        self._rows: dict[str, CommandRow] = {}

        self._build_ui()
        self._refresh_list()

        self.connect("close-request", self._on_close)

    def _apply_anchor(self):
        anchor = self._settings.get("anchor", "top-right")
        margin = self._settings.get("margin", 24)

        edge_map = {
            "top-right":    [Gtk4LayerShell.Edge.TOP, Gtk4LayerShell.Edge.RIGHT],
            "top-left":     [Gtk4LayerShell.Edge.TOP, Gtk4LayerShell.Edge.LEFT],
            "bottom-right": [Gtk4LayerShell.Edge.BOTTOM, Gtk4LayerShell.Edge.RIGHT],
            "bottom-left":  [Gtk4LayerShell.Edge.BOTTOM, Gtk4LayerShell.Edge.LEFT],
        }

        # Clear all anchors first
        for edge in [Gtk4LayerShell.Edge.TOP, Gtk4LayerShell.Edge.BOTTOM,
                     Gtk4LayerShell.Edge.LEFT, Gtk4LayerShell.Edge.RIGHT]:
            Gtk4LayerShell.set_anchor(self, edge, False)
            Gtk4LayerShell.set_margin(self, edge, 0)

        for edge in edge_map.get(anchor, edge_map["top-right"]):
            Gtk4LayerShell.set_anchor(self, edge, True)
            Gtk4LayerShell.set_margin(self, edge, margin)

    # ── UI ───────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self._root.add_css_class("widget-root")
        self.set_child(self._root)

        # ── Left: command list ───────────────────────────────────────────────
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        left.set_size_request(280, -1)
        left.add_css_class("left-panel")
        self._root.append(left)

        # Header row
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        header.add_css_class("widget-header")
        left.append(header)

        title = Gtk.Label(label="My Commands", xalign=0)
        title.add_css_class("heading")
        title.set_hexpand(True)
        title.set_margin_start(14)
        title.set_margin_top(10)
        title.set_margin_bottom(10)
        header.append(title)

        search_btn = Gtk.ToggleButton(icon_name="system-search-symbolic")
        search_btn.add_css_class("flat")
        search_btn.set_tooltip_text("Search")
        header.append(search_btn)

        add_btn = Gtk.Button(icon_name="list-add-symbolic")
        add_btn.add_css_class("flat")
        add_btn.set_tooltip_text("New command")
        add_btn.connect("clicked", self._on_add)
        header.append(add_btn)

        settings_btn = Gtk.Button(icon_name="preferences-system-symbolic")
        settings_btn.add_css_class("flat")
        settings_btn.set_tooltip_text("Settings")
        settings_btn.set_margin_end(4)
        settings_btn.connect("clicked", self._on_settings)
        header.append(settings_btn)

        # Search bar
        self._search_bar = Gtk.SearchBar()
        self._search_bar.set_search_mode(False)
        left.append(self._search_bar)

        search_entry = Gtk.SearchEntry()
        search_entry.set_hexpand(True)
        search_entry.connect("search-changed", self._on_search_changed)
        self._search_bar.set_child(search_entry)
        self._search_bar.connect_entry(search_entry)
        self._search_query = ""

        search_btn.bind_property(
            "active", self._search_bar, "search-mode-enabled",
            GObject.BindingFlags.BIDIRECTIONAL,
        )

        # Command list
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_max_content_height(500)
        scroll.set_propagate_natural_height(True)
        left.append(scroll)

        self._list_box = Gtk.ListBox()
        self._list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self._list_box.add_css_class("boxed-list")
        self._list_box.add_css_class("command-list")
        self._list_box.set_margin_start(10)
        self._list_box.set_margin_end(10)
        self._list_box.set_margin_top(8)
        self._list_box.set_margin_bottom(10)
        self._list_box.set_filter_func(self._filter_func)
        scroll.set_child(self._list_box)

        empty = Gtk.Label(label="No commands yet.\nClick + to add one.")
        empty.set_justify(Gtk.Justification.CENTER)
        empty.add_css_class("dim-label")
        empty.set_margin_top(32)
        empty.set_margin_bottom(32)
        self._list_box.set_placeholder(empty)

        # ── Right: output panel (hidden until a command runs) ────────────────
        self._output_revealer = Gtk.Revealer()
        self._output_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_LEFT)
        self._output_revealer.set_transition_duration(200)
        self._output_revealer.set_reveal_child(False)
        self._root.append(self._output_revealer)

        self._output_panel = OutputPanel(on_clear=self._hide_output)
        self._output_panel.set_size_request(340, -1)
        self._output_revealer.set_child(self._output_panel)

    def _show_output(self):
        self._output_revealer.set_reveal_child(True)

    def _hide_output(self):
        self._output_revealer.set_reveal_child(False)

    # ── List management ──────────────────────────────────────────────────────

    def _refresh_list(self):
        while True:
            row = self._list_box.get_row_at_index(0)
            if row is None:
                break
            self._list_box.remove(row)
        self._rows.clear()

        ordered = sorted(self._commands, key=lambda c: (not c.get("favorite", False)))
        for cmd in ordered:
            self._add_row(cmd)

    def _add_row(self, cmd: dict):
        row = CommandRow(
            cmd,
            on_run=self._on_run,
            on_edit=self._on_edit,
            on_delete=self._on_delete,
            on_reorder=self._on_reorder,
        )
        self._rows[cmd.get("id", "")] = row
        self._list_box.append(row)

    def _filter_func(self, row):
        if not self._search_query:
            return True
        for cmd_id, r in self._rows.items():
            if r is row:
                cmd = self._find_command(cmd_id)
                if cmd:
                    q = self._search_query.lower()
                    return (q in cmd.get("name", "").lower()
                            or q in cmd.get("command", "").lower())
        return True

    def _find_command(self, cmd_id):
        for cmd in self._commands:
            if cmd.get("id") == cmd_id:
                return cmd
        return None

    def _save(self):
        save_commands(self._commands)

    # ── Reorder ──────────────────────────────────────────────────────────────

    def _on_reorder(self, src_id, dst_id, above):
        src = self._find_command(src_id)
        dst = self._find_command(dst_id)
        if not src or not dst:
            return
        self._commands.remove(src)
        i = self._commands.index(dst)
        self._commands.insert(i if above else i + 1, src)
        self._save()
        self._refresh_list()

    # ── Handlers ─────────────────────────────────────────────────────────────

    def _on_add(self, _):
        def save(entry):
            entry["id"] = str(uuid.uuid4())
            self._commands.append(entry)
            self._save()
            self._add_row(entry)
        CommandDialog(self, on_save=save).present(self)

    def _on_edit(self, cmd):
        def save(updated):
            for i, c in enumerate(self._commands):
                if c.get("id") == updated.get("id"):
                    self._commands[i] = updated
                    break
            self._save()
            self._refresh_list()
        CommandDialog(self, on_save=save, existing=cmd).present(self)

    def _on_delete(self, cmd):
        dialog = Adw.AlertDialog(
            heading="Delete Command?",
            body=f'"{cmd.get("name", "")}" will be permanently deleted.',
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", lambda d, r: self._do_delete(cmd) if r == "delete" else None)
        dialog.present(self)

    def _do_delete(self, cmd):
        self._commands = [c for c in self._commands if c.get("id") != cmd.get("id")]
        self._save()
        self._refresh_list()

    def _on_run(self, cmd):
        self._show_output()
        self._output_panel.start(cmd.get("name", ""), cmd.get("command", ""))
        run_command(
            cmd.get("command", ""),
            on_line=self._output_panel.append_line,
            on_done=self._output_panel.finish,
        )

    def _on_settings(self, _):
        SettingsDialog(self).present(self)

    def _on_search_changed(self, entry):
        self._search_query = entry.get_text()
        self._list_box.invalidate_filter()

    def _on_close(self, _):
        settings = load_settings()
        save_settings(settings)
        return False
