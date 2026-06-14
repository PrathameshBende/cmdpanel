"""
store.py — Persistent JSON storage for commands and settings.
"""

import json
import os
from pathlib import Path
from typing import Any

DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "cmdpanel"
COMMANDS_FILE = DATA_DIR / "commands.json"
SETTINGS_FILE = DATA_DIR / "settings.json"


def _ensure_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


# ── Commands ────────────────────────────────────────────────────────────────

def load_commands() -> list[dict]:
    _ensure_dir()
    if not COMMANDS_FILE.exists():
        return []
    try:
        with open(COMMANDS_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_commands(commands: list[dict]):
    _ensure_dir()
    with open(COMMANDS_FILE, "w") as f:
        json.dump(commands, f, indent=2)


# ── Settings ────────────────────────────────────────────────────────────────

DEFAULT_SETTINGS: dict[str, Any] = {
    "start_on_login": False,
    "remember_size": True,
    "remember_position": True,
    "window_width": 360,
    "window_height": 640,
    "window_x": -1,
    "window_y": -1,
}


def load_settings() -> dict:
    _ensure_dir()
    if not SETTINGS_FILE.exists():
        return DEFAULT_SETTINGS.copy()
    try:
        with open(SETTINGS_FILE) as f:
            data = json.load(f)
        # Fill missing keys with defaults
        return {**DEFAULT_SETTINGS, **data}
    except (json.JSONDecodeError, OSError):
        return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict):
    _ensure_dir()
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)
