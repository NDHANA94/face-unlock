#!/usr/bin/env bash
# Compile the pinned dlib source into a wheel under vendor/wheels/.
# Runs inside the build container (or on a host with the build deps).
# Compiling dlib takes several minutes, so the wheel is cached between builds.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DLIB_VERSION="20.0.1"
PYTAG="cp$(python3 -c 'import sys; print(f"{sys.version_info[0]}{sys.version_info[1]}")')"
OUT="$ROOT/vendor/wheels"

if ls "$OUT"/dlib-"$DLIB_VERSION"-"$PYTAG"-*.whl >/dev/null 2>&1; then
    echo "==> dlib $DLIB_VERSION wheel for $PYTAG already built"
    exit 0
fi

mkdir -p "$OUT"
echo "==> Building dlib $DLIB_VERSION wheel for $PYTAG (this takes a while)"
CMAKE_BUILD_PARALLEL_LEVEL="$(nproc)" \
    python3 -m pip wheel --no-deps --no-build-isolation --no-cache-dir \
    --wheel-dir "$OUT" "$ROOT/vendor/dlib-$DLIB_VERSION.tar.gz"
ls -la "$OUT"
