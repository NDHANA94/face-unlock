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

VERSION="$(dpkg-parsechangelog -S Version)"
ARCH="$(dpkg-architecture -qDEB_HOST_ARCH)"
DEB="face-unlock_${VERSION}_${ARCH}.deb"
mkdir -p dist
mv "../$DEB" dist/
rm -f ../face-unlock_"${VERSION}"_*.buildinfo ../face-unlock_"${VERSION}"_*.changes \
      ../face-unlock-dbgsym_*.ddeb

if command -v lintian >/dev/null; then
    echo "==> lintian"
    lintian --no-tag-display-limit "dist/$DEB" || true
fi
echo "==> Built dist/$DEB"
