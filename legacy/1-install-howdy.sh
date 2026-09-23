#!/usr/bin/env bash
# Step 1: build and install Howdy 3 (beta) from source, point it at the IR
# camera, and enable face authentication in PAM (login screen, lock screen,
# sudo). Password login keeps working as a fallback.
# Run as your normal user (NOT with sudo); it asks for sudo only when needed.
set -euo pipefail

[[ $EUID -eq 0 ]] && { echo "Run this as your normal user, not root."; exit 1; }

IR_DEV="/dev/v4l/by-id/usb-BISON_ELECTRONICS_INC._FHD_Webcam_0001-video-index0"
SRC="$HOME/.local/src/howdy"
PAMDIR="/usr/lib/x86_64-linux-gnu/security"
PREFIX="/usr/local"

echo "==> Installing build dependencies"
sudo apt-get update
sudo apt-get install -y \
    python3 python3-pip python3-setuptools python3-wheel python3-dev python3-numpy \
    cmake make build-essential meson ninja-build git wget bzip2 \
    libpam0g-dev libinih-dev libevdev-dev python3-opencv libopencv-dev

echo "==> Installing dlib for the system Python (compiles from source, can take ~10 min)"
python3 -c "import dlib" 2>/dev/null \
    || sudo pip3 install --break-system-packages dlib

echo "==> Fetching Howdy source"
if [[ -d "$SRC/.git" ]]; then
    git -C "$SRC" pull --ff-only
else
    git clone --depth 1 https://github.com/boltgolt/howdy.git "$SRC"
fi

echo "==> Building Howdy"
cd "$SRC"
rm -rf build
meson setup build \
    --prefix="$PREFIX" \
    -Dconfig_dir=/etc/howdy \
    -Dpam_dir="$PAMDIR" \
    -Dpython_path=/usr/bin/python3 \
    -Dinstall_pam_config=true
meson compile -C build

echo "==> Installing Howdy"
sudo meson install -C build

echo "==> Downloading dlib face models"
(cd "$PREFIX/share/dlib-data" && sudo ./install.sh)

echo "==> Pointing Howdy at the IR camera"
sudo sed -i \
    -e "s|^device_path = .*|device_path = $IR_DEV|" \
    -e "s|^detection_notice = .*|detection_notice = true|" \
    /etc/howdy/config.ini

echo "==> Enabling Howdy in PAM (common-auth)"
sudo install -m 644 "$PREFIX/share/pam-configs/howdy" /usr/share/pam-configs/howdy
sudo pam-auth-update --enable howdy

echo
echo "Done. Next: run ./2-enroll-face.sh to register your face."
