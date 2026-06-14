"""
autostart.py — Manage the XDG autostart .desktop entry.
"""

import os
from pathlib import Path

AUTOSTART_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "autostart"
DESKTOP_FILE = AUTOSTART_DIR / "cmdpanel.desktop"

DESKTOP_CONTENT = """\
[Desktop Entry]
Type=Application
Name=CmdPanel
Comment=Minimal desktop command widget
Exec=cmdpanel
Icon=utilities-terminal
Categories=Utility;
X-GNOME-Autostart-enabled=true
"""


def set_autostart(enabled: bool):
    if enabled:
        AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
        DESKTOP_FILE.write_text(DESKTOP_CONTENT)
    else:
        if DESKTOP_FILE.exists():
            DESKTOP_FILE.unlink()


def is_autostart_enabled() -> bool:
    return DESKTOP_FILE.exists()
