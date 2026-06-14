#!/usr/bin/env bash
set -euo pipefail

APP_ID="io.github.cmdpanel"
GRN='\033[0;32m'
NC='\033[0m'

echo "Uninstalling CmdPanel..."

pip uninstall -y cmdpanel 2>/dev/null || true
rm -f "$HOME/.local/share/applications/${APP_ID}.desktop"
rm -f "$HOME/.config/autostart/cmdpanel.desktop"
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

echo -e "${GRN}✓ CmdPanel removed.${NC}"
echo "  Your saved commands are kept at: ~/.local/share/cmdpanel/"
echo "  Remove them manually if desired."
