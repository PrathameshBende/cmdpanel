#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# CmdPanel — uninstall.sh
# Removes the daemon, extension, DBus service, and desktop entry.
# Your saved commands are NOT deleted unless you pass --purge.
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

EXT_UUID="cmdpanel@cmdpanel.github.io"
APP_ID="io.github.cmdpanel"
PURGE=false

GRN='\033[0;32m'; YEL='\033[1;33m'; BLU='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${BLU}[•]${NC} $*"; }
success() { echo -e "${GRN}[✓]${NC} $*"; }
warn()    { echo -e "${YEL}[!]${NC} $*"; }

for arg in "$@"; do
    [[ "$arg" == "--purge" ]] && PURGE=true
done

echo ""
echo -e "${BLU}▸ CmdPanel uninstaller${NC}"
echo "──────────────────────────────────────────────────────────"

# ── 1. Disable and remove the GNOME Shell extension ──────────────────────────
info "Removing GNOME Shell extension..."
if command -v gnome-extensions &>/dev/null; then
    gnome-extensions disable "$EXT_UUID" 2>/dev/null && \
        info "Extension disabled." || true
fi
EXT_DIR="$HOME/.local/share/gnome-shell/extensions/$EXT_UUID"
if [[ -d "$EXT_DIR" ]]; then
    rm -rf "$EXT_DIR"
    success "Extension files removed."
else
    warn "Extension directory not found — skipping."
fi

# ── 2. Uninstall Python package (daemon) ─────────────────────────────────────
info "Removing Python package..."
if pip show cmdpanel &>/dev/null 2>&1; then
    pip uninstall -y cmdpanel 2>/dev/null && success "Python package removed." || \
        warn "pip uninstall failed — try: pip uninstall cmdpanel"
else
    warn "Python package not found — skipping."
fi

# ── 3. DBus service file ──────────────────────────────────────────────────────
SERVICE="$HOME/.local/share/dbus-1/services/io.github.cmdpanel.Daemon.service"
if [[ -f "$SERVICE" ]]; then
    rm -f "$SERVICE"
    success "DBus service file removed."
fi

# ── 4. Desktop entry ──────────────────────────────────────────────────────────
DESKTOP="$HOME/.local/share/applications/${APP_ID}.desktop"
if [[ -f "$DESKTOP" ]]; then
    rm -f "$DESKTOP"
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
    success "Desktop entry removed."
fi

# ── 5. Autostart entry (if it exists) ────────────────────────────────────────
AUTOSTART="$HOME/.config/autostart/cmdpanel.desktop"
if [[ -f "$AUTOSTART" ]]; then
    rm -f "$AUTOSTART"
    success "Autostart entry removed."
fi

# ── 6. User data ──────────────────────────────────────────────────────────────
DATA_DIR="$HOME/.local/share/cmdpanel"
if [[ "$PURGE" == true ]]; then
    if [[ -d "$DATA_DIR" ]]; then
        rm -rf "$DATA_DIR"
        success "User data purged ($DATA_DIR)."
    fi
else
    if [[ -d "$DATA_DIR" ]]; then
        warn "Your saved commands are kept at: $DATA_DIR"
        warn "To delete them too, run:  ./uninstall.sh --purge"
    fi
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GRN}✓ CmdPanel removed.${NC}"
echo ""
warn "Log out and back in (or restart GNOME Shell on X11) to fully unload the extension."
echo ""
