#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# CmdPanel — setup.sh
# Installs the Python daemon and the GNOME Shell extension.
#
# Architecture:
#   - cmdpaneld       Python DBus daemon (pip install --user)
#   - widget.js       GNOME Shell extension (St widgets, runs inside Shell)
#   - dbus.js         DBus proxy used by the extension
#   - extension.js    Extension entry point
#
# The daemon handles all persistence and subprocess execution.
# The extension renders the UI inside the GNOME Shell process.
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXT_UUID="cmdpanel@cmdpanel.github.io"
APP_ID="io.github.cmdpanel"

RED='\033[0;31m'; GRN='\033[0;32m'; YEL='\033[1;33m'; BLU='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${BLU}[•]${NC} $*"; }
success() { echo -e "${GRN}[✓]${NC} $*"; }
warn()    { echo -e "${YEL}[!]${NC} $*"; }
die()     { echo -e "${RED}[✗]${NC} $*" >&2; exit 1; }

echo ""
echo -e "${BLU}▸ CmdPanel installer${NC}"
echo "──────────────────────────────────────────────────────────"

# ── 1. Verify OS and GNOME Shell ─────────────────────────────────────────────
if ! command -v gnome-shell &>/dev/null; then
    die "gnome-shell not found. CmdPanel requires GNOME Shell."
fi

SHELL_VER=$(gnome-shell --version | grep -oP '\d+' | head -1)
info "GNOME Shell version: $SHELL_VER"
if [[ "$SHELL_VER" -lt 45 ]]; then
    die "GNOME Shell 45+ required (found $SHELL_VER). The extension uses ES module syntax."
fi

if ! command -v python3 &>/dev/null; then
    die "python3 not found."
fi

PY_VER=$(python3 -c 'import sys; print(sys.version_info.minor)')
if [[ "$PY_VER" -lt 11 ]]; then
    die "Python 3.11+ required."
fi

# ── 2. Install system dependencies ───────────────────────────────────────────
info "Installing system dependencies..."

if command -v dnf &>/dev/null; then
    # Fedora / RHEL
    sudo dnf install -y \
        python3-gobject \
        python3-dbus \
        dbus-python \
        python3-pip \
        2>/dev/null && success "System deps installed (dnf)." || \
        warn "Some dnf packages may have failed — continuing."

elif command -v apt-get &>/dev/null; then
    # Debian / Ubuntu
    sudo apt-get install -y \
        python3-gi \
        python3-dbus \
        python3-pip \
        2>/dev/null && success "System deps installed (apt)." || \
        warn "Some apt packages may have failed — continuing."

elif command -v pacman &>/dev/null; then
    # Arch
    sudo pacman -S --needed --noconfirm \
        python-gobject \
        python-dbus \
        python-pip \
        2>/dev/null && success "System deps installed (pacman)." || \
        warn "Some pacman packages may have failed — continuing."
else
    warn "Unknown package manager. Make sure python3-gobject and dbus-python are installed."
fi

# ── 3. Install the Python daemon via pip ─────────────────────────────────────
info "Installing Python package (cmdpaneld daemon)..."
pip install --user "$SCRIPT_DIR" && success "Python package installed." || \
    die "pip install failed. Check errors above."

USER_BIN="$(python3 -m site --user-base)/bin"

# Verify the entry point was created
if [[ ! -f "$USER_BIN/cmdpaneld" ]]; then
    die "cmdpaneld not found at $USER_BIN — pip install may have failed."
fi
success "Daemon installed at $USER_BIN/cmdpaneld"

# ── 4. Install the GNOME Shell extension ─────────────────────────────────────
EXT_DIR="$HOME/.local/share/gnome-shell/extensions/$EXT_UUID"
info "Installing extension to $EXT_DIR ..."
mkdir -p "$EXT_DIR"
cp -r "$SCRIPT_DIR/extension/$EXT_UUID/." "$EXT_DIR/"
success "Extension files installed."

# ── 5. DBus service file (auto-starts daemon on first use) ───────────────────
DBUS_SERVICES_DIR="$HOME/.local/share/dbus-1/services"
mkdir -p "$DBUS_SERVICES_DIR"
cp "$SCRIPT_DIR/data/io.github.cmdpanel.Daemon.service" \
   "$DBUS_SERVICES_DIR/io.github.cmdpanel.Daemon.service"
success "DBus service file installed (daemon auto-starts on demand)."

# ── 6. Desktop entry ─────────────────────────────────────────────────────────
APPS_DIR="$HOME/.local/share/applications"
mkdir -p "$APPS_DIR"
cat > "$APPS_DIR/${APP_ID}.desktop" << EOF
[Desktop Entry]
Type=Application
Name=CmdPanel
Comment=GNOME Shell desktop command widget
Exec=cmdpaneld
Icon=utilities-terminal
Categories=Utility;
Terminal=false
NoDisplay=true
EOF
update-desktop-database "$APPS_DIR" 2>/dev/null || true
success "Desktop entry installed."

# ── 7. PATH check ─────────────────────────────────────────────────────────────
if ! echo "$PATH" | grep -q "$USER_BIN"; then
    warn "$USER_BIN is not in your PATH."
    warn "Add this to your ~/.bashrc or ~/.zshrc:"
    echo ""
    echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
    warn "Then run: source ~/.bashrc"
fi

# ── 8. Existing data check ────────────────────────────────────────────────────
DATA_FILE="$HOME/.local/share/cmdpanel/commands.json"
if [[ -f "$DATA_FILE" ]]; then
    success "Found existing commands at $DATA_FILE — they will be loaded automatically."
else
    info "No existing commands found. You'll start fresh."
fi

# ── 9. Enable the extension ───────────────────────────────────────────────────
echo ""
info "Enabling extension..."
if command -v gnome-extensions &>/dev/null; then
    gnome-extensions enable "$EXT_UUID" 2>/dev/null && \
        success "Extension enabled." || \
        warn "Could not auto-enable — see step 2 below."
else
    warn "gnome-extensions CLI not found — enable manually (see below)."
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GRN}✓ Installation complete!${NC}"
echo ""
echo "  Next steps:"
echo ""
echo "  1. Log out and back in to load the extension (required on Wayland):"
echo "       — or on X11: Alt+F2 → type 'r' → Enter"
echo ""
echo "  2. If the extension isn't enabled automatically:"
echo "       gnome-extensions enable $EXT_UUID"
echo "       — or via the GNOME Extensions app"
echo ""
echo "  The widget appears in the top-right corner of your desktop,"
echo "  behind all windows. Drag the title bar to move it."
echo ""
echo "  Daemon logs:  journalctl --user -t cmdpaneld -f"
echo ""
