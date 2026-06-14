"""
command_row.py — A single command row in the list.
Shows icon + name, and a popover menu for edit/delete/copy.
Supports drag-to-reorder via GTK4 DragSource / DropTarget.
"""

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk, GLib


# Shared drag state — which row is currently being dragged
_dragging_row = None


class CommandRow(Gtk.ListBoxRow):
    """
    A clickable row representing one command.

    Callbacks:
        on_run(command_dict)
        on_edit(command_dict)
        on_delete(command_dict)
        on_reorder(src_id, dst_id)  — called when a drag-drop reorder completes
    """

    def __init__(self, command: dict, on_run, on_edit, on_delete, on_reorder=None):
        super().__init__()
        self._command = command
        self._on_run = on_run
        self._on_edit = on_edit
        self._on_delete = on_delete
        self._on_reorder = on_reorder

        self.add_css_class("command-row")
        self.set_activatable(True)

        # ── Main content ────────────────────────────────────────────────────
        outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        outer.set_margin_top(2)
        outer.set_margin_bottom(2)
        self.set_child(outer)

        # Drag handle (⠿)
        self._drag_handle = Gtk.Label(label="⠿")
        self._drag_handle.add_css_class("drag-handle")
        self._drag_handle.set_valign(Gtk.Align.CENTER)
        self._drag_handle.set_margin_start(8)
        self._drag_handle.set_margin_end(2)
        self._drag_handle.set_tooltip_text("Drag to reorder")
        outer.append(self._drag_handle)

        # Run button (the whole left part)
        self._run_btn = Gtk.Button()
        self._run_btn.add_css_class("flat")
        self._run_btn.add_css_class("command-run-btn")
        self._run_btn.set_hexpand(True)
        self._run_btn.connect("clicked", lambda _: on_run(command))
        outer.append(self._run_btn)

        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        content.set_margin_start(4)
        content.set_margin_end(4)
        content.set_margin_top(8)
        content.set_margin_bottom(8)
        self._run_btn.set_child(content)

        icon = command.get("icon", "")
        if icon:
            icon_label = Gtk.Label(label=icon)
            icon_label.add_css_class("command-icon")
            content.append(icon_label)
        else:
            placeholder = Gtk.Image.new_from_icon_name("utilities-terminal-symbolic")
            placeholder.add_css_class("dim-label")
            content.append(placeholder)

        self._name_label = Gtk.Label(label=command.get("name", ""), xalign=0)
        self._name_label.set_hexpand(True)
        self._name_label.set_ellipsize(3)  # Pango.EllipsizeMode.END
        content.append(self._name_label)

        # ── Menu button ─────────────────────────────────────────────────────
        menu_btn = Gtk.MenuButton()
        menu_btn.add_css_class("flat")
        menu_btn.add_css_class("circular")
        menu_btn.set_icon_name("view-more-symbolic")
        menu_btn.set_valign(Gtk.Align.CENTER)
        menu_btn.set_margin_end(4)
        menu_btn.set_tooltip_text("More options")
        outer.append(menu_btn)

        popover = Gtk.Popover()
        menu_btn.set_popover(popover)

        menu_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        menu_box.set_margin_top(4)
        menu_box.set_margin_bottom(4)
        menu_box.set_margin_start(4)
        menu_box.set_margin_end(4)
        popover.set_child(menu_box)

        for label, icon_name, callback in [
            ("Run", "media-playback-start-symbolic", lambda: on_run(command)),
            ("Edit", "document-edit-symbolic", lambda: on_edit(command)),
            ("Copy command", "edit-copy-symbolic", self._copy_command),
            ("Delete", "user-trash-symbolic", lambda: on_delete(command)),
        ]:
            btn = Gtk.Button()
            btn.add_css_class("flat")
            btn.set_hexpand(True)
            btn_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            btn_content.set_margin_start(8)
            btn_content.set_margin_end(16)
            btn_content.set_margin_top(4)
            btn_content.set_margin_bottom(4)
            btn_content.append(Gtk.Image.new_from_icon_name(icon_name))
            btn_content.append(Gtk.Label(label=label, xalign=0))
            btn.set_child(btn_content)
            if label == "Delete":
                btn.add_css_class("destructive-action")
            _cb = callback  # capture
            btn.connect("clicked", lambda _, cb=_cb: (cb(), popover.popdown()))
            menu_box.append(btn)

        # ── Drag-to-reorder ─────────────────────────────────────────────────
        self._setup_drag()

    # ── Drag source (on the handle) ─────────────────────────────────────────

    def _setup_drag(self):
        # DragSource attached to the handle label
        drag_src = Gtk.DragSource()
        drag_src.set_actions(Gdk.DragAction.MOVE)
        drag_src.connect("prepare", self._on_drag_prepare)
        drag_src.connect("drag-begin", self._on_drag_begin)
        drag_src.connect("drag-end", self._on_drag_end)
        self._drag_handle.add_controller(drag_src)

        # DropTarget on the whole row
        drop_tgt = Gtk.DropTarget.new(type=GLib.TYPE_STRING, actions=Gdk.DragAction.MOVE)
        drop_tgt.connect("drop", self._on_drop)
        drop_tgt.connect("motion", self._on_drop_motion)
        drop_tgt.connect("leave", self._on_drop_leave)
        self.add_controller(drop_tgt)

    def _on_drag_prepare(self, src, x, y):
        global _dragging_row
        _dragging_row = self
        cmd_id = self._command.get("id", "")
        return Gdk.ContentProvider.new_for_value(cmd_id)

    def _on_drag_begin(self, src, drag):
        self.add_css_class("dragging")
        # Build a simple drag icon from the row's name
        icon = Gtk.DragIcon.get_for_drag(drag)
        label = Gtk.Label(label=f"  {self._command.get('icon', '📌')}  {self._command.get('name', '')}  ")
        label.add_css_class("drag-icon-label")
        icon.set_child(label)

    def _on_drag_end(self, src, drag, delete_data):
        global _dragging_row
        self.remove_css_class("dragging")
        self.remove_css_class("drop-target-above")
        self.remove_css_class("drop-target-below")
        _dragging_row = None

    # ── Drop target ─────────────────────────────────────────────────────────

    def _on_drop_motion(self, tgt, x, y):
        global _dragging_row
        if _dragging_row is None or _dragging_row is self:
            return Gdk.DragAction(0)
        # Highlight above or below based on cursor position
        height = self.get_height()
        if y < height / 2:
            self.add_css_class("drop-target-above")
            self.remove_css_class("drop-target-below")
        else:
            self.add_css_class("drop-target-below")
            self.remove_css_class("drop-target-above")
        return Gdk.DragAction.MOVE

    def _on_drop_leave(self, tgt):
        self.remove_css_class("drop-target-above")
        self.remove_css_class("drop-target-below")

    def _on_drop(self, tgt, value, x, y):
        self.remove_css_class("drop-target-above")
        self.remove_css_class("drop-target-below")
        src_id = value  # the dragged command's id
        dst_id = self._command.get("id", "")
        if src_id == dst_id:
            return False
        height = self.get_height()
        above = y < height / 2
        if self._on_reorder:
            self._on_reorder(src_id, dst_id, above)
        return True

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _copy_command(self):
        cmd = self._command.get("command", "")
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(cmd)

    def update(self, command: dict):
        self._command = command
        self._name_label.set_text(command.get("name", ""))

    @property
    def command(self):
        return self._command
