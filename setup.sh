#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# CmdPanel — setup.sh
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

APP_ID="io.github.cmdpanel"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED='\033[0;31m'
GRN='\033[0;32m'
YEL='\033[1;33m'
BLU='\033[0;34m'
NC='\033[0m'

info()    { echo -e "${BLU}[•]${NC} $*"; }
success() { echo -e "${GRN}[✓]${NC} $*"; }
warn()    { echo -e "${YEL}[!]${NC} $*"; }
die()     { echo -e "${RED}[✗]${NC} $*" >&2; exit 1; }

echo ""
echo -e "${BLU}▸ CmdPanel installer${NC}"
echo "──────────────────────────────────────────────────────────"

# ── 1. Wayland check ─────────────────────────────────────────────────────────
if [[ "${XDG_SESSION_TYPE:-}" != "wayland" ]]; then
    warn "XDG_SESSION_TYPE='${XDG_SESSION_TYPE:-unset}'. CmdPanel requires Wayland."
fi

# ── 2. System dependencies ────────────────────────────────────────────────────
info "Checking system dependencies..."

if ! command -v rpm &>/dev/null; then
    warn "Not an RPM-based system. Install manually: python3-gobject gtk4 libadwaita gtk4-layer-shell"
else
    MISSING=()
    for pkg in python3-gobject gtk4 libadwaita gtk4-layer-shell; do
        rpm -q "$pkg" &>/dev/null || MISSING+=("$pkg")
    done
    if [[ ${#MISSING[@]} -gt 0 ]]; then
        info "Installing: ${MISSING[*]}"
        sudo dnf install -y "${MISSING[@]}" || die "dnf install failed."
    fi
    success "System packages present."
fi

# ── 3. Verify GI typelib is discoverable ─────────────────────────────────────
info "Checking GObject introspection typelib path..."

TYPELIB_FOUND=""
for dir in /usr/lib64/girepository-1.0 /usr/lib/girepository-1.0 \
           /usr/local/lib64/girepository-1.0 /usr/local/lib/girepository-1.0; do
    if [[ -f "$dir/Gtk4LayerShell-1.0.typelib" ]]; then
        TYPELIB_FOUND="$dir"
        break
    fi
done

if [[ -z "$TYPELIB_FOUND" ]]; then
    die "Gtk4LayerShell-1.0.typelib not found. Is gtk4-layer-shell installed?"
fi

# Check if it's already in GI_TYPELIB_PATH in the shell rc files
SHELL_RC="$HOME/.bashrc"
[[ -f "$HOME/.zshrc" ]] && SHELL_RC="$HOME/.zshrc"

if ! echo "${GI_TYPELIB_PATH:-}" | grep -q "$TYPELIB_FOUND"; then
    warn "GI_TYPELIB_PATH does not include $TYPELIB_FOUND"
    info "Adding to $SHELL_RC ..."
    # Only add if not already present in the file
    if ! grep -q "GI_TYPELIB_PATH" "$SHELL_RC" 2>/dev/null; then
        echo "" >> "$SHELL_RC"
        echo "# Added by CmdPanel setup" >> "$SHELL_RC"
        echo "export GI_TYPELIB_PATH=\"${TYPELIB_FOUND}\${GI_TYPELIB_PATH:+:\$GI_TYPELIB_PATH}\"" >> "$SHELL_RC"
    fi
    success "Added GI_TYPELIB_PATH to $SHELL_RC"
    # Also export for the current session so the rest of this script works
    export GI_TYPELIB_PATH="${TYPELIB_FOUND}${GI_TYPELIB_PATH:+:$GI_TYPELIB_PATH}"
else
    success "GI_TYPELIB_PATH already includes typelib directory."
fi

# ── 4. Verify layer shell is importable ──────────────────────────────────────
info "Verifying gtk4-layer-shell Python binding..."
python3 -c "
import gi, os
gi.require_version('Gtk4LayerShell', '1.0')
from gi.repository import Gtk4LayerShell
print('  gtk4-layer-shell version:', Gtk4LayerShell.get_major_version())
" || die "gtk4-layer-shell not importable even after path fix. Check your installation."
success "gtk4-layer-shell binding works."

# ── 5. Python package — editable install ─────────────────────────────────────
info "Installing CmdPanel (editable)..."
pip install --user -e "$SCRIPT_DIR" --quiet || die "pip install failed."
success "Python package installed (editable from $SCRIPT_DIR)."

# ── 6. Desktop entry ─────────────────────────────────────────────────────────
APPS_DIR="$HOME/.local/share/applications"
mkdir -p "$APPS_DIR"
cp "$SCRIPT_DIR/data/${APP_ID}.desktop" "$APPS_DIR/"
USER_BIN="$HOME/.local/bin/cmdpanel"
if [[ -f "$USER_BIN" ]]; then
    sed -i "s|Exec=cmdpanel|Exec=${USER_BIN}|" "$APPS_DIR/${APP_ID}.desktop"
fi
update-desktop-database "$APPS_DIR" 2>/dev/null || true
success "Desktop entry installed."

# ── 7. PATH reminder ─────────────────────────────────────────────────────────
if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
    warn "~/.local/bin is not in your PATH. Add to $SHELL_RC:"
    echo ""
    echo '    export PATH="$HOME/.local/bin:$PATH"'
    echo ""
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GRN}✓ CmdPanel installed!${NC}"
echo ""
echo "  Run:  cmdpanel"
echo "  The widget sits on your desktop behind all windows."
echo ""
