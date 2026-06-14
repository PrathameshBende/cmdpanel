"""
style.py — Custom CSS for CmdPanel.
"""

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk

CSS = """
/* -- Widget root ---------------------------------------------------- */

.widget-root {
    background-color: alpha(@window_bg_color, 0.92);
    border-radius: 14px;
    border: 1px solid alpha(@borders, 0.35);
}

/* -- Left panel ----------------------------------------------------- */

.left-panel {
    border-radius: 14px 0 0 14px;
}

/* -- Header --------------------------------------------------------- */

.widget-header {
    border-bottom: 1px solid alpha(@borders, 0.3);
    border-radius: 14px 0 0 0;
}

/* -- Command list --------------------------------------------------- */

.command-list {
    background: transparent;
}

.command-run-btn {
    border-radius: 0;
    border: none;
}

.command-row {
    border-radius: 10px;
}

/* -- Drag handle ---------------------------------------------------- */

.drag-handle {
    color: alpha(@foreground_color, 0.3);
    font-size: 1.1em;
}

.drag-handle:hover {
    color: alpha(@foreground_color, 0.7);
}

/* -- Drag feedback -------------------------------------------------- */

.dragging {
    opacity: 0.4;
}

.drop-target-above {
    border-top: 2px solid @accent_color;
}

.drop-target-below {
    border-bottom: 2px solid @accent_color;
}

.drag-icon-label {
    background-color: @card_bg_color;
    border: 1px solid alpha(@borders, 0.8);
    border-radius: 8px;
    padding: 6px 12px;
}

/* -- Output panel --------------------------------------------------- */

.output-panel {
    border-left: 1px solid alpha(@borders, 0.3);
    border-radius: 0 14px 14px 0;
    background-color: alpha(@card_bg_color, 0.6);
}

.output-header {
    border-bottom: 1px solid alpha(@borders, 0.25);
    border-radius: 0 14px 0 0;
}

.output-view {
    background-color: transparent;
    font-family: monospace;
    font-size: 0.875em;
}

/* -- Status colours ------------------------------------------------- */

label.success { color: #42be65; }
label.error   { color: #fa4d56; }
"""


def load_css():
    provider = Gtk.CssProvider()
    provider.load_from_data(CSS.encode())
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(),
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )
