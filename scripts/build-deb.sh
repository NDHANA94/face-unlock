#!/usr/bin/env bash
# Build the .deb from the source tree. Runs inside the build container
# (see Makefile), or on an Ubuntu 26.04 host with the Build-Depends installed.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

scripts/fetch-vendor.sh
scripts/build-dlib-wheel.sh

echo "==> Building package"
dpkg-buildpackage -b -us -uc

PKG_VERSION="$(dpkg-parsechangelog -S Version)"
ARCH="$(dpkg-architecture -qDEB_HOST_ARCH)"
. /etc/os-release
if [[ "$ID" != "ubuntu" ]]; then
    echo "error: this package build targets Ubuntu" >&2
    exit 1
fi
DISTRO="ubuntu${VERSION_ID}"
SOURCE_DEB="face-unlock_${PKG_VERSION}_${ARCH}.deb"
DEB="face-unlock-${DISTRO}-${ARCH}-${PKG_VERSION}.deb"
mkdir -p dist
mv "../$SOURCE_DEB" "dist/$DEB"
rm -f ../face-unlock_"${PKG_VERSION}"_*.buildinfo ../face-unlock_"${PKG_VERSION}"_*.changes \
      ../face-unlock-dbgsym_*.ddeb

if command -v lintian >/dev/null; then
    echo "==> lintian"
    lintian --no-tag-display-limit "dist/$DEB" || true
fi
echo "==> Built dist/$DEB"
