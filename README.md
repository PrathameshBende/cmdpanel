# CmdPanel

> Every repetitive terminal command should become a clickable button.

A minimal floating panel for GNOME/Wayland that lets you run shell commands with a single click — no terminal window, no popups, output shown inline.

---

## Features

- **Click to run** — executes in a shell, never opens an external terminal
- **Inline output** — stdout/stderr shown live, auto-scrolling
- **Favorites** — pin important commands to the top
- **Drag to reorder** — grab the ⠿ handle on any row and drag it
- **Search** — filter by name or command text
- **Full CRUD** — add, edit, delete, copy any command
- **Emoji icons** — give commands a visual identity
- **Persistence** — everything stored in `~/.local/share/cmdpanel/commands.json`
- **Autostart** — optional start on login via XDG autostart
- **Pure GTK4 + libadwaita** — feels native on GNOME 46+, Wayland-first

---

## Requirements

- Fedora 40+ (or any distro with GNOME 46+ / libadwaita 1.5+)
- Python 3.11+
- `python3-gobject`, `gtk4`, `libadwaita` (installed automatically by `setup.sh`)

---

## Install

```bash
git clone https://github.com/PrathameshBende/cmdpanel.git
cd cmdpanel
chmod +x setup.sh
./setup.sh
```

Then launch from the terminal or search **CmdPanel** in the GNOME app grid.

---

## Uninstall

```bash
./uninstall.sh
```

Your saved commands in `~/.local/share/cmdpanel/` are kept — delete them manually if you want a clean slate.

---

## Data format

Commands are stored in `~/.local/share/cmdpanel/commands.json`:

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Remount SSD",
    "command": "sudo mount -o remount,rw /dev/sda1 /mnt/data",
    "favorite": true,
    "icon": "💾"
  }
]
```

You can edit this file directly — CmdPanel reads it fresh on each launch.

---

## Project structure

```
cmdpanel/
├── cmdpanel/
│   ├── __init__.py        # Package marker
│   ├── __main__.py        # Entry point (python -m cmdpanel)
│   ├── app.py             # Adw.Application subclass
│   ├── window.py          # Main floating panel window
│   ├── command_row.py     # Single command row widget + drag-to-reorder
│   ├── output_panel.py    # Inline output area
│   ├── dialog_command.py  # Add/Edit command dialog
│   ├── dialog_settings.py # Settings dialog
│   ├── runner.py          # Async subprocess execution
│   ├── store.py           # JSON persistence
│   ├── autostart.py       # XDG autostart management
│   └── style.py           # Custom CSS
├── data/
│   └── io.github.cmdpanel.desktop
├── pyproject.toml
├── setup.sh
├── uninstall.sh
└── README.md
```

---

## License

MIT
