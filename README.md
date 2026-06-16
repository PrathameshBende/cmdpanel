# CmdPanel

A floating desktop widget for GNOME Shell that lets you run shell commands with a single click — no terminal, no popups, output shown inline right on your desktop.

---

## What it looks like

The widget sits on the wallpaper layer (behind all windows, never in Alt+Tab). It shows your saved commands in a scrollable list. Click ▶ on any row to run it and see live output in a panel that opens to the right.

---

## Features

- **▶ Run button per command** — explicit button to run, so you never fire a command by accident
- **Live output** — stdout and stderr stream in line by line, auto-scrolling
- **Drag to move** — grab the "My Commands" title bar and drag the widget anywhere on screen
- **Resize** — drag the ◢ handle at the bottom-right to resize width and height
- **Drag to reorder** — grab the ⠿ handle on any row and drag it up or down
- **Search** — click 🔍 to filter commands by name
- **Add / Edit / Delete** — full command management via the ＋ button and ⋮ row menu
- **Favorites** — mark commands as favourite to pin them at the top
- **Copy command** — copy the shell command to clipboard from the ⋮ menu
- **Persistence** — commands stored in `~/.local/share/cmdpanel/commands.json`; survives reboots and extension reloads
- **DBus daemon** — runs as a lightweight background service, auto-started on demand; handles all subprocess execution and persistence so the extension stays fast
- **No sudo password prompts** — commands that need elevated privileges require passwordless sudo configured in `/etc/sudoers` (see below)

---

## Requirements

- GNOME Shell 45 or newer
- Python 3.11 or newer
- `python3-gobject` and `dbus-python` (installed automatically by `setup.sh` on Fedora/Debian/Arch)
- `pip` (Python package installer)

Tested on Fedora 44 with GNOME Shell 50 and Wayland.

---

## Install

```bash
git clone https://github.com/your-username/cmdpanel.git
cd cmdpanel
chmod +x setup.sh
./setup.sh
```

Then **log out and back in** (required on Wayland to load the extension).

The widget appears in the top-right corner of your desktop.

### What setup.sh does

1. Checks GNOME Shell version (45+ required) and Python version (3.11+ required)
2. Installs `python3-gobject` and `dbus-python` via your distro's package manager (dnf / apt / pacman)
3. Installs the Python daemon via `pip install --user`
4. Copies extension files to `~/.local/share/gnome-shell/extensions/`
5. Installs the DBus service file so the daemon auto-starts on demand
6. Installs a `.desktop` entry
7. Enables the extension via `gnome-extensions enable`

---

## Uninstall

```bash
./uninstall.sh
```

Your saved commands in `~/.local/share/cmdpanel/` are kept. To delete everything including your commands:

```bash
./uninstall.sh --purge
```

---

## Using sudo commands

Commands that need `sudo` will hang or fail because there is no terminal to type a password into. To use `sudo` commands in CmdPanel, grant passwordless sudo for the specific binaries you need:

```bash
sudo visudo -f /etc/sudoers.d/cmdpanel
```

Add a line like:

```
your-username ALL=(ALL) NOPASSWD: /usr/sbin/ntfsfix, /usr/bin/mount, /usr/bin/umount
```

Replace `your-username` with your actual username and list only the commands you need.

---

## Data format

Commands are stored in `~/.local/share/cmdpanel/commands.json`:

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Fix D drive",
    "command": "sudo umount /media/user/D && sudo ntfsfix /dev/nvme0n1p4 && sudo mount -t ntfs-3g -o rw /dev/nvme0n1p4 /media/user/D",
    "favorite": true,
    "icon": ""
  }
]
```

You can edit this file directly while the daemon is not running.

---

## Project structure

```
cmdpanel/
├── cmdpanel/               Python daemon package
│   ├── __init__.py
│   ├── daemon.py           DBus daemon — runs commands, manages persistence
│   ├── runner.py           Async subprocess execution
│   ├── store.py            JSON read/write for commands.json
│   └── autostart.py       XDG autostart helper
├── extension/
│   └── cmdpanel@cmdpanel.github.io/
│       ├── extension.js    GNOME Shell extension entry point
│       ├── widget.js       Main UI — St widgets, drag/resize/run
│       ├── dbus.js         DBus proxy to talk to the daemon
│       └── metadata.json   Extension metadata
├── data/
│   └── io.github.cmdpanel.Daemon.service   DBus service file
├── pyproject.toml
├── setup.sh
├── uninstall.sh
└── README.md
```

---

## Troubleshooting

**Widget doesn't appear after install**
Log out and back in. On Wayland you cannot reload GNOME Shell without logging out.

**Extension shows an error in the Extensions app**
Check the logs:
```bash
journalctl /usr/bin/gnome-shell -b --no-pager | grep -i cmdpanel
```

**Daemon not responding / commands don't run**
Check daemon logs:
```bash
journalctl --user -t cmdpaneld -f
```
Restart it manually:
```bash
cmdpaneld
```

**`cmdpaneld` command not found after install**
Your pip user bin directory is not in PATH. Add this to `~/.bashrc`:
```bash
export PATH="$HOME/.local/bin:$PATH"
```
Then `source ~/.bashrc`.

**Extension not enabled after install**
Enable it manually:
```bash
gnome-extensions enable cmdpanel@cmdpanel.github.io
```

---

## License

MIT
