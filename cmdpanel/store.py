"""
store.py — Persistent JSON storage for commands.
"""

import json
import os
from pathlib import Path
from typing import Any

DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "cmdpanel"
COMMANDS_FILE = DATA_DIR / "commands.json"


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
