#!/usr/bin/env bash
# Step 2: register your face with Howdy and test recognition.
set -euo pipefail

USER_NAME="${SUDO_USER:-$USER}"

echo "==> Adding a face model for $USER_NAME. Look straight at the camera."
sudo howdy -U "$USER_NAME" add

cat <<EOF

Tip: add 1-2 more models (with and without glasses, different lighting) for
better reliability:   sudo howdy -U $USER_NAME add

==> Opening a test window (press Ctrl+C to close it)
EOF
sudo howdy test || true

echo
echo "Try it: open a NEW terminal and run 'sudo -k; sudo true'. Your face should"
echo "authenticate you. Then lock the screen (Super+L) and look at the camera."
