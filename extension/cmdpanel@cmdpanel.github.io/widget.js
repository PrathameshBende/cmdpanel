/**
 * widget.js — CmdPanel desktop widget
 *
 * Renders entirely with Shell Toolkit (St) inside the GNOME Shell process.
 * Lives on Main.layoutManager._backgroundGroup at a z-order below all windows,
 * so it is truly "on the wallpaper" with zero compositor tricks needed.
 *
 * Layout (horizontal, output panel opens on right when a command runs):
 *
 *   ┌──────────────────────────────┬──────────────────────────────┐
 *   │  My Commands          🔍 ＋  │  OUTPUT          Done   ✕   │
 *   │  ──────────────────────────  │  ──────────────────────────  │
 *   │  ⠿  🔧 Command name  ⋮       │  ▶ name                      │
 *   │  ⠿  📦 Other cmd     ⋮       │  $ shell command             │
 *   │  …                           │  stdout lines…               │
 *   └──────────────────────────────┴──────────────────────────────┘
 *
 * DBus: all persistence and subprocess execution is delegated to cmdpaneld.
 * The daemon is auto-started by the session bus on first method call.
 */

import St      from 'gi://St';
import Clutter from 'gi://Clutter';
import GLib    from 'gi://GLib';
import Gio     from 'gi://Gio';
import GObject from 'gi://GObject';
import Pango   from 'gi://Pango';

import * as Main      from 'resource:///org/gnome/shell/ui/main.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

import { createProxy, callMethod, DBUS_NAME } from './dbus.js';

// ── Geometry constants ────────────────────────────────────────────────────────
const PANEL_W  = 280;   // command list width  (px)
const OUTPUT_W = 340;   // output panel width  (px)
const MAX_H    = 560;   // max height of scroll area
const MARGIN   = 24;    // distance from screen edge
const RADIUS   = 14;    // corner radius

// ── Colour tokens (Carbon palette, dark-mode friendly) ────────────────────────
const C = {
    bg:       'rgba(28,28,28,0.92)',
    border:   'rgba(255,255,255,0.12)',
    rowHover: 'rgba(255,255,255,0.06)',
    accent:   '#78a9ff',
    green:    '#42be65',
    red:      '#fa4d56',
    yellow:   '#f1c21b',
    dim:      '#6f6f6f',
    text:     '#f4f4f4',
    subtext:  '#c6c6c6',
    outputBg: 'rgba(20,20,20,0.6)',
};

// ── Inline CSS ────────────────────────────────────────────────────────────────
const CSS = `
.cmdpanel-root {
    background-color: ${C.bg};
    border: 1px solid ${C.border};
    border-radius: ${RADIUS}px;
}
.cmdpanel-header {
    border-bottom: 1px solid ${C.border};
    padding: 0 4px 0 14px;
    min-height: 40px;
}
.cmdpanel-title {
    color: ${C.text};
    font-weight: bold;
    font-size: 0.95em;
}
.cmdpanel-icon-btn {
    color: ${C.subtext};
    border-radius: 6px;
    padding: 4px 6px;
}
.cmdpanel-icon-btn:hover { background-color: ${C.rowHover}; color: ${C.text}; }

.cmdpanel-search-box {
    background-color: rgba(255,255,255,0.07);
    border: 1px solid ${C.border};
    border-radius: 8px;
    color: ${C.text};
    margin: 6px 10px;
    padding: 4px 8px;
}
.cmdpanel-row {
    border-radius: 10px;
    padding: 0;
    min-height: 36px;
}
.cmdpanel-row:hover { background-color: ${C.rowHover}; }

.cmdpanel-drag-handle {
    color: rgba(255,255,255,0.25);
    font-size: 1.1em;
    padding: 0 4px 0 8px;
}
.cmdpanel-row-label {
    color: ${C.text};
    font-size: 0.9em;
}
.cmdpanel-row-icon {
    font-size: 1em;
    width: 22px;
    padding: 0 2px;
}
.cmdpanel-row-fav {
    color: ${C.yellow};
    font-size: 0.85em;
    padding: 0 2px;
}
.cmdpanel-menu-btn {
    color: ${C.dim};
    border-radius: 50%;
    padding: 2px 6px;
    margin-right: 4px;
}
.cmdpanel-menu-btn:hover { color: ${C.text}; background-color: ${C.rowHover}; }

.cmdpanel-empty {
    color: ${C.dim};
    text-align: center;
    padding: 32px 16px;
    font-size: 0.9em;
}

/* output panel */
.cmdpanel-output-panel {
    background-color: ${C.outputBg};
    border-left: 1px solid ${C.border};
    border-radius: 0 ${RADIUS}px ${RADIUS}px 0;
}
.cmdpanel-output-header {
    border-bottom: 1px solid ${C.border};
    padding: 6px 4px 6px 12px;
    min-height: 40px;
}
.cmdpanel-output-title {
    color: ${C.subtext};
    font-size: 0.8em;
    font-weight: bold;
    letter-spacing: 0.05em;
}
.cmdpanel-output-status-ok  { color: ${C.green}; font-size: 0.75em; }
.cmdpanel-output-status-err { color: ${C.red};   font-size: 0.75em; }
.cmdpanel-output-status     { color: ${C.dim};   font-size: 0.75em; }
.cmdpanel-output-text {
    font-family: monospace;
    font-size: 0.8em;
    color: ${C.subtext};
}
.cmdpanel-output-cmd-line  { color: ${C.accent}; font-weight: bold; font-family: monospace; font-size: 0.8em; }
.cmdpanel-output-ok-line   { color: ${C.green};  font-weight: bold; font-family: monospace; font-size: 0.8em; }
.cmdpanel-output-err-line  { color: ${C.red};    font-weight: bold; font-family: monospace; font-size: 0.8em; }
.cmdpanel-output-dim-line  { color: ${C.dim};    font-family: monospace; font-size: 0.8em; }
`;

// ── Load CSS into the Shell theme ─────────────────────────────────────────────
// St.CssProvider does not exist in GNOME Shell's JS bindings (that's a GTK4
// class).  The correct approach is to write CSS to a temp file and call
// St.Theme.load_stylesheet() with the file path.
let _cssFile = null;

function _loadCSS() {
    const path = `${GLib.get_tmp_dir()}/cmdpanel-${GLib.get_monotonic_time()}.css`;
    GLib.file_set_contents(path, CSS);
    _cssFile = path;
    St.ThemeContext
        .get_for_stage(global.stage)
        .get_theme()
        .load_stylesheet(Gio.File.new_for_path(path));
    return path;
}

function _unloadCSS() {
    if (_cssFile) {
        try {
            St.ThemeContext
                .get_for_stage(global.stage)
                .get_theme()
                .unload_stylesheet(Gio.File.new_for_path(_cssFile));
        } catch (_) {}
        try { GLib.unlink(_cssFile); } catch (_) {}
        _cssFile = null;
    }
}

// ── Helper: make a flat icon/text button ─────────────────────────────────────
function _iconBtn(label, tooltip, callback) {
    const btn = new St.Button({
        style_class: 'cmdpanel-icon-btn',
        label,
        reactive: true,
        track_hover: true,
        can_focus: true,
    });
    if (tooltip)
        btn.accessible_name = tooltip;
    btn.connect('clicked', callback);
    return btn;
}

// ─────────────────────────────────────────────────────────────────────────────
// OutputPanel
// ─────────────────────────────────────────────────────────────────────────────
class OutputPanel {
    constructor(onClear) {
        this._onClear = onClear;

        this.actor = new St.BoxLayout({
            style_class: 'cmdpanel-output-panel',
            vertical: true,
            width: OUTPUT_W,
        });

        // header
        const header = new St.BoxLayout({
            style_class: 'cmdpanel-output-header',
            vertical: false,
        });
        this.actor.add_child(header);

        this._titleLabel = new St.Label({
            style_class: 'cmdpanel-output-title',
            text: 'OUTPUT',
            y_align: Clutter.ActorAlign.CENTER,
            x_expand: true,
        });
        header.add_child(this._titleLabel);

        this._statusLabel = new St.Label({
            style_class: 'cmdpanel-output-status',
            text: '',
            y_align: Clutter.ActorAlign.CENTER,
        });
        header.add_child(this._statusLabel);

        const clearBtn = _iconBtn('✕', 'Clear output', () => this._clear());
        clearBtn.set_style('margin: 2px 4px;');
        header.add_child(clearBtn);

        // scrollable text area
        this._scroll = new St.ScrollView({
            style: `max-height: ${MAX_H - 40}px;`,
            x_expand: true,
            y_expand: true,
            overlay_scrollbars: true,
        });
        this.actor.add_child(this._scroll);

        this._textBox = new St.BoxLayout({
            vertical: true,
            x_expand: true,
            style: 'padding: 6px 8px;',
        });
        this._scroll.set_child(this._textBox);
    }

    start(commandName, commandStr) {
        this._clearText();
        this._statusLabel.set_style_class_name('cmdpanel-output-status');
        this._statusLabel.set_text('Running…');
        this._appendLine(`▶ ${commandName}`, 'cmdpanel-output-cmd-line');
        this._appendLine(`$ ${commandStr}`,  'cmdpanel-output-dim-line');
        this._appendLine('', null);
    }

    appendLine(line) {
        this._appendLine(line, null);
        this._scrollToEnd();
    }

    finish(ok) {
        if (ok) {
            this._appendLine('', null);
            this._appendLine('✓ Done.', 'cmdpanel-output-ok-line');
            this._statusLabel.set_style_class_name('cmdpanel-output-status-ok');
            this._statusLabel.set_text('Done');
        } else {
            this._appendLine('', null);
            this._appendLine('✗ Failed.', 'cmdpanel-output-err-line');
            this._statusLabel.set_style_class_name('cmdpanel-output-status-err');
            this._statusLabel.set_text('Failed');
        }
        this._scrollToEnd();
    }

    _appendLine(text, styleClass) {
        const lbl = new St.Label({
            style_class: styleClass ?? 'cmdpanel-output-text',
            text,
            x_expand: true,
        });
        lbl.clutter_text.set_line_wrap(true);
        lbl.clutter_text.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR);
        lbl.clutter_text.set_ellipsize(Pango.EllipsizeMode.NONE);
        this._textBox.add_child(lbl);
    }

    _clearText() {
        this._textBox.destroy_all_children();
    }

    _clear() {
        this._clearText();
        this._statusLabel.set_text('');
        this._onClear?.();
    }

    _scrollToEnd() {
        GLib.idle_add(GLib.PRIORITY_DEFAULT_IDLE, () => {
            const bar = this._scroll.get_vscroll_bar();
            if (bar) {
                const adj = bar.get_adjustment();
                adj.set_value(adj.get_upper() - adj.get_page_size());
            }
            return GLib.SOURCE_REMOVE;
        });
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// CommandRow
// ─────────────────────────────────────────────────────────────────────────────
class CommandRow {
    /**
     * @param {object} cmd
     * @param {{onRun, onEdit, onDelete, onCopy, onFavorite, onDragStart}} cbs
     */
    constructor(cmd, cbs) {
        this.cmd = cmd;
        this._cbs = cbs;

        this.actor = new St.BoxLayout({
            style_class: 'cmdpanel-row',
            vertical: false,
            reactive: true,
            track_hover: true,
            x_expand: true,
        });

        // drag handle
        const handle = new St.Label({
            style_class: 'cmdpanel-drag-handle',
            text: '⠿',
            y_align: Clutter.ActorAlign.CENTER,
            reactive: true,
        });
        this.actor.add_child(handle);

        // Drag-and-drop reorder: drag starts on handle press
        handle.connect('button-press-event', (_a, _ev) => {
            cbs.onDragStart?.(cmd);
            return Clutter.EVENT_STOP;
        });

        // icon / emoji — only show if one is set
        if (cmd.icon) {
            const iconLbl = new St.Label({
                style_class: 'cmdpanel-row-icon',
                text: cmd.icon,
                y_align: Clutter.ActorAlign.CENTER,
            });
            this.actor.add_child(iconLbl);
        }

        // name (expands)
        const nameLbl = new St.Label({
            style_class: 'cmdpanel-row-label',
            text: cmd.name || '',
            y_align: Clutter.ActorAlign.CENTER,
            x_expand: true,
        });
        nameLbl.clutter_text.set_ellipsize(Pango.EllipsizeMode.END);
        this.actor.add_child(nameLbl);

        // favorite star
        if (cmd.favorite) {
            const star = new St.Label({
                style_class: 'cmdpanel-row-fav',
                text: '★',
                y_align: Clutter.ActorAlign.CENTER,
            });
            this.actor.add_child(star);
        }

        // ▶ run button
        const runBtn = new St.Button({
            style_class: 'cmdpanel-icon-btn',
            label: '▶',
            reactive: true,
            track_hover: true,
            y_align: Clutter.ActorAlign.CENTER,
        });
        runBtn.connect('clicked', () => cbs.onRun(cmd));
        this.actor.add_child(runBtn);

        // ⋮ context menu
        const menuBtn = new St.Button({
            style_class: 'cmdpanel-menu-btn',
            label: '⋮',
            reactive: true,
            track_hover: true,
            y_align: Clutter.ActorAlign.CENTER,
        });
        this.actor.add_child(menuBtn);

        this._menu = new PopupMenu.PopupMenu(menuBtn, 0.5, St.Side.RIGHT);
        Main.uiGroup.add_child(this._menu.actor);
        this._menu.actor.hide();

        this._menu.addAction('▶  Run',                () => cbs.onRun(cmd));
        this._menu.addAction('✎  Edit',               () => cbs.onEdit(cmd));
        this._menu.addAction('⧉  Copy command',       () => cbs.onCopy(cmd));
        this._menu.addAction(
            cmd.favorite ? '★  Remove favourite' : '☆  Mark favourite',
            () => cbs.onFavorite(cmd)
        );
        this._menu.addAction('🗑  Delete',             () => cbs.onDelete(cmd));

        menuBtn.connect('clicked', () => this._menu.toggle());
    }

    destroy() {
        this._menu.destroy();
        this.actor.destroy();
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// CommandDialog  (modal prompt using a floating St panel)
// ─────────────────────────────────────────────────────────────────────────────
class CommandDialog {
    /**
     * @param {object|null} existing  — pass null for "New", object for "Edit"
     * @param {function(object)} onSave
     */
    constructor(existing, onSave) {
        this._onSave   = onSave;
        this._existing = existing ?? {};

        // Dark overlay — covers the entire stage
        this._overlay = new St.Widget({
            reactive: true,
            style: 'background-color: rgba(0,0,0,0.55);',
        });
        this._overlay.add_constraint(
            new Clutter.BindConstraint({
                source: global.stage,
                coordinate: Clutter.BindCoordinate.ALL,
            })
        );
        Main.uiGroup.add_child(this._overlay);

        // Dialog box
        this._box = new St.BoxLayout({
            vertical: true,
            reactive: true,
            style: `
                background-color: #1c1c1c;
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 12px;
                padding: 20px;
                width: 400px;
            `,
        });

        const monitor = Main.layoutManager.primaryMonitor;
        this._box.set_position(
            monitor.x + Math.round((monitor.width  - 400) / 2),
            monitor.y + Math.round((monitor.height - 280) / 2),
        );
        Main.uiGroup.add_child(this._box);

        // Title
        this._box.add_child(new St.Label({
            text: existing ? 'Edit Command' : 'New Command',
            x_expand: true,
            style: 'color: #f4f4f4; font-weight: bold; font-size: 1em; margin-bottom: 16px;',
        }));

        // Name entry
        this._nameEntry = new St.Entry({
            hint_text: 'Command name',
            style: 'background-color: #2a2a2a; color: #f4f4f4; border: 1px solid rgba(255,255,255,0.15); border-radius: 8px; padding: 6px 8px; margin-bottom: 10px;',
            x_expand: true,
            text: existing?.name ?? '',
            reactive: true,
            can_focus: true,
        });
        this._box.add_child(this._nameEntry);

        // Command label
        this._box.add_child(new St.Label({
            text: 'Command',
            style: 'color: #6f6f6f; font-size: 0.8em; margin-bottom: 4px;',
        }));

        // Command entry — single line (multi-line is unreliable in St)
        this._cmdEntry = new St.Entry({
            hint_text: 'bash command…',
            style: `
                background-color: #2a2a2a;
                color: #f4f4f4;
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 8px;
                padding: 8px;
                font-family: monospace;
                font-size: 0.9em;
                margin-bottom: 16px;
            `,
            x_expand: true,
            text: existing?.command ?? '',
            reactive: true,
            can_focus: true,
        });
        this._box.add_child(this._cmdEntry);

        // Buttons row
        const btnRow = new St.BoxLayout({
            vertical: false,
            x_expand: true,
            style: 'spacing: 8px;',
        });
        this._box.add_child(btnRow);
        btnRow.add_child(new St.Widget({ x_expand: true }));

        const cancelBtn = new St.Button({
            label: 'Cancel',
            style: 'background-color: #3a3a3a; color: #f4f4f4; border-radius: 8px; padding: 8px 18px;',
            reactive: true,
            can_focus: true,
        });
        cancelBtn.connect('clicked', () => this.close());
        btnRow.add_child(cancelBtn);

        const saveBtn = new St.Button({
            label: 'Save',
            style: 'background-color: #0f62fe; color: #fff; border-radius: 8px; padding: 8px 18px;',
            reactive: true,
            can_focus: true,
        });
        saveBtn.connect('clicked', () => this._save());
        btnRow.add_child(saveBtn);

        this._nameEntry.grab_key_focus();
    }

    _save() {
        const name    = this._nameEntry.get_text().trim();
        const command = this._cmdEntry.get_text().trim();
        if (!name || !command) return;

        const entry = {
            name,
            command,
            icon:     '',
            favorite: this._existing.favorite ?? false,
        };
        if (this._existing.id)
            entry.id = this._existing.id;

        this._onSave(entry);
        this.close();
    }

    close() {
        this._overlay.destroy();
        this._box.destroy();
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// ConfirmDialog
// ─────────────────────────────────────────────────────────────────────────────
class ConfirmDialog {
    constructor(heading, body, destructiveLabel, onConfirm) {
        this._overlay = new St.Widget({
            reactive: true,
            style: 'background-color: rgba(0,0,0,0.55);',
        });
        this._overlay.add_constraint(
            new Clutter.BindConstraint({
                source: global.stage,
                coordinate: Clutter.BindCoordinate.ALL,
            })
        );
        Main.uiGroup.add_child(this._overlay);

        this._box = new St.BoxLayout({
            vertical: true,
            style: `
                background-color: #1c1c1c;
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 12px;
                padding: 24px;
                width: 320px;
            `,
        });
        const monitor = Main.layoutManager.primaryMonitor;
        this._box.set_position(
            monitor.x + Math.round((monitor.width  - 320) / 2),
            monitor.y + Math.round((monitor.height - 160) / 2),
        );
        Main.uiGroup.add_child(this._box);

        this._box.add_child(new St.Label({
            text: heading,
            style: 'color: #f4f4f4; font-weight: bold; font-size: 1em; margin-bottom: 8px;',
        }));
        this._box.add_child(new St.Label({
            text: body,
            style: 'color: #c6c6c6; font-size: 0.9em; margin-bottom: 20px;',
        }));

        const btnRow = new St.BoxLayout({
            vertical: false,
            x_expand: true,
            style: 'spacing: 8px;',
        });
        this._box.add_child(btnRow);
        btnRow.add_child(new St.Widget({ x_expand: true }));

        const cancelBtn = new St.Button({
            label: 'Cancel',
            style: 'background-color: #3a3a3a; color: #f4f4f4; border-radius: 8px; padding: 8px 18px;',
            reactive: true,
        });
        cancelBtn.connect('clicked', () => this.close());
        btnRow.add_child(cancelBtn);

        const confirmBtn = new St.Button({
            label: destructiveLabel,
            style: 'background-color: #da1e28; color: #fff; border-radius: 8px; padding: 8px 18px;',
            reactive: true,
        });
        confirmBtn.connect('clicked', () => { onConfirm(); this.close(); });
        btnRow.add_child(confirmBtn);

        this._overlay.connect('button-press-event', () => {
            this.close();
            return Clutter.EVENT_STOP;
        });
        this._box.connect('button-press-event', () => Clutter.EVENT_STOP);

    }

    close() {
        this._overlay.destroy();
        this._box.destroy();
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// DragDropManager — lightweight drag-and-drop reorder within the list
// ─────────────────────────────────────────────────────────────────────────────
class DragDropManager {
    /**
     * @param {function(string, number)} onReorder - (draggedId, newIndex)
     */
    constructor(onReorder) {
        this._onReorder  = onReorder;
        this._draggedCmd = null;
        this._rows       = [];         // [{cmd, actor}]

        // Ghost label that follows the pointer
        this._ghost = new St.Label({
            style: `
                background-color: rgba(120,169,255,0.18);
                border: 1px solid #78a9ff;
                border-radius: 8px;
                color: #f4f4f4;
                font-size: 0.9em;
                padding: 4px 12px;
            `,
            text: '',
        });
        this._ghost.hide();
        Main.uiGroup.add_child(this._ghost);

        this._motionId = global.stage.connect('motion-event', (_s, ev) => {
            if (!this._draggedCmd) return Clutter.EVENT_PROPAGATE;
            const [x, y] = ev.get_coords();
            this._ghost.set_position(x + 12, y + 4);
            return Clutter.EVENT_PROPAGATE;
        });

        this._releaseId = global.stage.connect('button-release-event', (_s, ev) => {
            if (!this._draggedCmd) return Clutter.EVENT_PROPAGATE;
            const [x, y] = ev.get_coords();
            this._finishDrop(x, y);
            return Clutter.EVENT_PROPAGATE;
        });
    }

    setRows(rows) {
        this._rows = rows;  // array of {cmd, actor}
    }

    startDrag(cmd) {
        this._draggedCmd = cmd;
        this._ghost.set_text(cmd.icon ? `${cmd.icon} ${cmd.name}` : cmd.name);
        this._ghost.show();
    }

    _finishDrop(x, y) {
        this._ghost.hide();
        const dragged = this._draggedCmd;
        this._draggedCmd = null;
        if (!dragged) return;

        // Find the row actor under the drop point
        let targetIdx = -1;
        for (let i = 0; i < this._rows.length; i++) {
            const { actor } = this._rows[i];
            const [ax, ay] = actor.get_transformed_position();
            const [aw, ah] = [actor.width, actor.height];
            if (x >= ax && x <= ax + aw && y >= ay && y <= ay + ah) {
                targetIdx = i;
                break;
            }
        }
        if (targetIdx === -1) return;

        // Find current index of dragged item in _rows
        const fromIdx = this._rows.findIndex(r => r.cmd.id === dragged.id);
        if (fromIdx === -1 || fromIdx === targetIdx) return;

        this._onReorder(dragged.id, targetIdx);
    }

    destroy() {
        if (this._motionId) {
            global.stage.disconnect(this._motionId);
            this._motionId = null;
        }
        if (this._releaseId) {
            global.stage.disconnect(this._releaseId);
            this._releaseId = null;
        }
        this._ghost.destroy();
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// CmdPanelWidget  — the main exported class
// ─────────────────────────────────────────────────────────────────────────────
export class CmdPanelWidget {
    constructor(extension) {
        this._ext           = extension;
        this._proxy         = null;
        this._commands      = [];
        this._rows          = [];      // CommandRow instances in display order
        this._sigIds        = [];      // DBus signal subscription ids
        this._currentJobId  = null;
        this._outputVisible = false;
    }

    // ── Lifecycle ─────────────────────────────────────────────────────────────

    open() {
        this._cssProvider = _loadCSS();
        this._buildUI();
        this._dragMgr = new DragDropManager((id, toIdx) => this._onReorder(id, toIdx));
        this._connectDbus();
    }

    close() {
        // Disconnect DBus signals
        if (this._proxy) {
            for (const id of this._sigIds)
                this._proxy.disconnectSignal(id);
        }
        this._sigIds = [];
        this._proxy  = null;

        this._dragMgr?.destroy();
        this._dragMgr = null;

        this._root?.destroy();
        this._root = null;

        _unloadCSS();
        this._cssProvider = null;
    }

    // ── UI construction ───────────────────────────────────────────────────────

    _buildUI() {
        // Root container — horizontal, holds left panel + output panel
        this._root = new St.BoxLayout({
            style_class: 'cmdpanel-root',
            vertical: false,
            reactive: true,
        });

        // Place it on the background layer (behind all windows).
        // _backgroundGroup is the correct layer for "always behind windows" in
        // GNOME Shell 45+.  It is the same layer used by the desktop icons extension.
        Main.layoutManager._backgroundGroup.add_child(this._root);

        this._positionRoot();

        // ── Left panel ────────────────────────────────────────────────────────
        this._leftPanel = new St.BoxLayout({
            vertical: true,
            width: PANEL_W,
        });
        this._root.add_child(this._leftPanel);

        this._buildHeader();
        this._buildSearchBar();
        this._buildCommandList();

        // ── Resize handle (bottom-right corner) ──────────────────────────────
        const resizeRow = new St.BoxLayout({
            vertical: false,
            x_expand: true,
        });
        this._leftPanel.add_child(resizeRow);
        resizeRow.add_child(new St.Widget({ x_expand: true })); // spacer pushes handle right

        const resizeHandle = new St.Label({
            text: '◢',
            reactive: true,
            track_hover: true,
            style: 'color: rgba(255,255,255,0.25); padding: 2px 4px; font-size: 0.9em;',
        });
        resizeRow.add_child(resizeHandle);

        let resizeStartX, resizeStartY, resizeStartW, resizeStartH;
        resizeHandle.connect('button-press-event', (_a, event) => {
            const [ex, ey] = event.get_coords();
            resizeStartX = ex;
            resizeStartY = ey;
            resizeStartW = this._leftPanel.width;
            resizeStartH = this._scroll.get_height();
            this._resizingWidget = true;
            return Clutter.EVENT_STOP;
        });
        resizeHandle.connect('motion-event', (_a, event) => {
            if (!this._resizingWidget) return Clutter.EVENT_PROPAGATE;
            const [ex, ey] = event.get_coords();
            const newW = Math.max(180, Math.min(700, resizeStartW + (ex - resizeStartX)));
            const newH = Math.max(80,  Math.min(900, resizeStartH + (ey - resizeStartY)));
            this._leftPanel.set_width(newW);
            this._scroll.set_height(newH);
            return Clutter.EVENT_STOP;
        });
        resizeHandle.connect('button-release-event', () => {
            this._resizingWidget = false;
            return Clutter.EVENT_PROPAGATE;
        });

        // ── Output panel (hidden until a command runs) ────────────────────────
        this._outputPanel = new OutputPanel(() => this._hideOutput());
        this._outputPanel.actor.hide();
        this._root.add_child(this._outputPanel.actor);
    }

    _positionRoot() {
        const monitor = Main.layoutManager.primaryMonitor;
        const x = monitor.x + monitor.width - PANEL_W - MARGIN;
        const y = monitor.y + MARGIN;
        this._root.set_position(x, y);
    }

    _buildHeader() {
        const header = new St.BoxLayout({
            style_class: 'cmdpanel-header',
            vertical: false,
            x_expand: true,
        });
        this._leftPanel.add_child(header);

        // Title doubles as drag handle for moving the widget
        const title = new St.Label({
            style_class: 'cmdpanel-title',
            text: 'My Commands',
            y_align: Clutter.ActorAlign.CENTER,
            x_expand: true,
            reactive: true,
            track_hover: true,
            style: 'cursor: move;',
        });
        header.add_child(title);

        // Drag-to-move
        let dragStartX, dragStartY, rootStartX, rootStartY;
        title.connect('button-press-event', (_a, event) => {
            const [ex, ey] = event.get_coords();
            dragStartX = ex;
            dragStartY = ey;
            [rootStartX, rootStartY] = this._root.get_position();
            this._draggingWidget = true;
            return Clutter.EVENT_STOP;
        });
        title.connect('motion-event', (_a, event) => {
            if (!this._draggingWidget) return Clutter.EVENT_PROPAGATE;
            const [ex, ey] = event.get_coords();
            const monitor = Main.layoutManager.primaryMonitor;
            const nx = Math.max(monitor.x, Math.min(monitor.x + monitor.width  - PANEL_W, rootStartX + (ex - dragStartX)));
            const ny = Math.max(monitor.y, Math.min(monitor.y + monitor.height - 60,       rootStartY + (ey - dragStartY)));
            this._root.set_position(nx, ny);
            return Clutter.EVENT_STOP;
        });
        title.connect('button-release-event', () => {
            this._draggingWidget = false;
            return Clutter.EVENT_PROPAGATE;
        });

        this._searchVisible = false;
        header.add_child(_iconBtn('🔍', 'Search', () => this._toggleSearch()));
        header.add_child(_iconBtn('＋', 'New command', () => this._onAdd()));
    }

    _buildSearchBar() {
        this._searchBar = new St.BoxLayout({ vertical: false });
        this._searchBar.hide();
        this._leftPanel.add_child(this._searchBar);

        this._searchEntry = new St.Entry({
            style_class: 'cmdpanel-search-box',
            hint_text: 'Search commands…',
            x_expand: true,
        });
        this._searchEntry.clutter_text.connect('text-changed', () => this._refreshList());
        this._searchBar.add_child(this._searchEntry);
    }

    _buildCommandList() {
        this._scroll = new St.ScrollView({
            style: `max-height: ${MAX_H}px;`,
            x_expand: true,
            overlay_scrollbars: true,
        });
        this._leftPanel.add_child(this._scroll);

        this._listBox = new St.BoxLayout({
            vertical: true,
            x_expand: true,
            style: 'padding: 8px 10px;',
        });
        this._scroll.set_child(this._listBox);

        this._emptyLabel = new St.Label({
            style_class: 'cmdpanel-empty',
            text: 'No commands yet.\nClick ＋ to add one.',
            x_expand: true,
        });
        this._emptyLabel.clutter_text.set_line_wrap(true);
        this._emptyLabel.clutter_text.set_justify(true);
        this._listBox.add_child(this._emptyLabel);
    }

    // ── DBus connection ───────────────────────────────────────────────────────

    _connectDbus() {
        // Ask the session bus to auto-start the daemon via its .service file
        Gio.DBus.session.call(
            'org.freedesktop.DBus', '/org/freedesktop/DBus',
            'org.freedesktop.DBus', 'StartServiceByName',
            new GLib.Variant('(su)', [DBUS_NAME, 0]),
            null, Gio.DBusCallFlags.NONE, -1, null,
            (_conn, res) => {
                try { Gio.DBus.session.call_finish(res); } catch (_) { /* already running */ }
                this._createProxy();
            }
        );
    }

    _createProxy() {
        createProxy((proxy, error) => {
            if (error) {
                console.warn('CmdPanel: DBus proxy failed:', error.message);
                // Retry after 3 s
                GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 3, () => {
                    this._createProxy();
                    return GLib.SOURCE_REMOVE;
                });
                return;
            }
            this._proxy = proxy;

            // Subscribe to streaming job signals
            this._sigIds.push(
                proxy.connectSignal('JobLine', (_p, _s, [jobId, line]) => {
                    if (jobId === this._currentJobId)
                        this._outputPanel.appendLine(line);
                }),
                proxy.connectSignal('JobDone', (_p, _s, [jobId, ok]) => {
                    if (jobId === this._currentJobId)
                        this._outputPanel.finish(ok);
                }),
            );

            this._loadCommands();
        });
    }

    // ── Data ──────────────────────────────────────────────────────────────────

    _loadCommands() {
        if (!this._proxy) return;
        callMethod(this._proxy, 'GetCommands', null).then(result => {
            try {
                // result is a GLib.Variant "(s)", unpack the tuple then the string
                this._commands = JSON.parse(result.get_child_value(0).get_string()[0]);
            } catch (_) {
                this._commands = [];
            }
            this._refreshList();
        }).catch(e => console.warn('CmdPanel GetCommands error:', e.message));
    }

    _saveCommands() {
        if (!this._proxy) return;
        callMethod(
            this._proxy,
            'SaveCommands',
            new GLib.Variant('(s)', [JSON.stringify(this._commands)])
        ).catch(e => console.warn('CmdPanel SaveCommands error:', e.message));
    }

    // ── List rendering ────────────────────────────────────────────────────────

    _refreshList() {
        // Destroy old rows
        for (const row of this._rows) row.destroy();
        this._rows = [];

        // Favourites first, then stable insertion order
        const ordered = [...this._commands].sort(
            (a, b) => (b.favorite ? 1 : 0) - (a.favorite ? 1 : 0)
        );

        const query = this._searchEntry?.get_text().toLowerCase() ?? '';

        for (const cmd of ordered) {
            if (query &&
                !cmd.name.toLowerCase().includes(query) &&
                !cmd.command.toLowerCase().includes(query))
                continue;

            const row = new CommandRow(cmd, {
                onRun:       (c) => this._onRun(c),
                onEdit:      (c) => this._onEdit(c),
                onDelete:    (c) => this._onDelete(c),
                onCopy:      (c) => this._onCopy(c),
                onFavorite:  (c) => this._onFavorite(c),
                onDragStart: (c) => this._dragMgr?.startDrag(c),
            });
            this._listBox.add_child(row.actor);
            this._rows.push(row);
        }

        // Update drag manager with current rows
        this._dragMgr?.setRows(this._rows.map(r => ({ cmd: r.cmd, actor: r.actor })));

        this._emptyLabel.visible = this._rows.length === 0;
    }

    // ── Event handlers ────────────────────────────────────────────────────────

    _toggleSearch() {
        this._searchVisible = !this._searchVisible;
        if (this._searchVisible) {
            this._searchBar.show();
            this._searchEntry.grab_key_focus();
        } else {
            this._searchBar.hide();
            this._searchEntry.set_text('');
            this._refreshList();
        }
    }

    _onAdd() {
        new CommandDialog(null, (entry) => {
            entry.id = GLib.uuid_string_random();
            this._commands.push(entry);
            this._saveCommands();
            this._refreshList();
        });
    }

    _onEdit(cmd) {
        new CommandDialog(cmd, (updated) => {
            const i = this._commands.findIndex(c => c.id === updated.id);
            if (i >= 0) this._commands[i] = updated;
            this._saveCommands();
            this._refreshList();
        });
    }

    _onDelete(cmd) {
        new ConfirmDialog(
            'Delete Command?',
            `"${cmd.name}" will be permanently deleted.`,
            'Delete',
            () => {
                this._commands = this._commands.filter(c => c.id !== cmd.id);
                this._saveCommands();
                this._refreshList();
            }
        );
    }

    _onCopy(cmd) {
        St.Clipboard.get_default().set_text(St.ClipboardType.CLIPBOARD, cmd.command);
    }

    _onFavorite(cmd) {
        const c = this._commands.find(x => x.id === cmd.id);
        if (!c) return;
        c.favorite = !c.favorite;
        this._saveCommands();
        this._refreshList();
    }

    _onReorder(draggedId, toIdx) {
        // Reorder in this._commands (which may include items filtered out of view)
        const fromIdx = this._commands.findIndex(c => c.id === draggedId);
        if (fromIdx === -1) return;
        const [item] = this._commands.splice(fromIdx, 1);
        // toIdx is index in the rendered (possibly filtered) list; insert at same position
        this._commands.splice(toIdx, 0, item);
        this._saveCommands();
        this._refreshList();
    }

    _onRun(cmd) {
        if (!this._proxy) return;
        this._showOutput();
        this._outputPanel.start(cmd.name, cmd.command);
        callMethod(
            this._proxy,
            'RunCommand',
            new GLib.Variant('(s)', [cmd.id])
        ).then(result => {
            this._currentJobId = result.get_child_value(0).get_string()[0];
        }).catch(e => {
            this._outputPanel.appendLine(`[DBus error] ${e.message}`);
            this._outputPanel.finish(false);
        });
    }

    _showOutput() {
        if (!this._outputVisible) {
            this._outputPanel.actor.show();
            this._outputVisible = true;
            const monitor = Main.layoutManager.primaryMonitor;
            const totalW  = PANEL_W + OUTPUT_W;
            this._root.set_position(
                monitor.x + monitor.width - totalW - MARGIN,
                monitor.y + MARGIN,
            );
        }
    }

    _hideOutput() {
        if (this._outputVisible) {
            this._outputPanel.actor.hide();
            this._outputVisible = false;
            this._positionRoot();
        }
    }
}
