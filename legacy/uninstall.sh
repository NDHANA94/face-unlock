#!/usr/bin/env bash
# Disable face login and remove Howdy.
set -euo pipefail

sudo pam-auth-update --disable howdy || true
sudo rm -f /usr/share/pam-configs/howdy

SRC="$HOME/.local/src/howdy"
[[ -d "$SRC/build" ]] && sudo ninja -C "$SRC/build" uninstall || true
echo "Face login removed. Password login is unchanged. (/etc/howdy kept; delete it manually if wanted.)"
