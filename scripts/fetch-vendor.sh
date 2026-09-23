#!/usr/bin/env bash
# Download the pinned third-party sources bundled into the package and verify
# them against vendor/SHA256SUMS. Safe to re-run; existing files are reused.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENDOR="$ROOT/vendor"
mkdir -p "$VENDOR"
cd "$VENDOR"

HOWDY_COMMIT="d3ab99382f88f043d15f15c1450ab69433892a1c"
DLIB_VERSION="20.0.1"
MODELS_BASE="https://github.com/davisking/dlib-models/raw/master"

fetch() {  # fetch <url> <output>
    [[ -s "$2" ]] && return 0
    echo "  downloading $2"
    curl -fsSL --retry 3 -o "$2.part" "$1"
    mv "$2.part" "$2"
}

echo "==> Fetching vendor sources"
fetch "https://github.com/boltgolt/howdy/archive/$HOWDY_COMMIT.tar.gz" "howdy-$HOWDY_COMMIT.tar.gz"
fetch "https://files.pythonhosted.org/packages/source/d/dlib/dlib-$DLIB_VERSION.tar.gz" "dlib-$DLIB_VERSION.tar.gz"
for model in dlib_face_recognition_resnet_model_v1 shape_predictor_5_face_landmarks mmod_human_face_detector; do
    fetch "$MODELS_BASE/$model.dat.bz2" "$model.dat.bz2"
done

echo "==> Verifying checksums"
sha256sum --check --strict SHA256SUMS
