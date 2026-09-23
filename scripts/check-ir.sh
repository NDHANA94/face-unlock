#!/usr/bin/env bash
# Capture frames from the IR camera and report brightness per frame.
# This camera strobes its IR emitter: lit frames alternate with black ones,
# which is normal. The emitter is working if the lit frames are bright.
set -euo pipefail

DEV="${IR_DEVICE:-/dev/v4l/by-id/usb-BISON_ELECTRONICS_INC._FHD_Webcam_0001-video-index0}"
OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT

timeout 15 gst-launch-1.0 -q v4l2src device="$DEV" num-buffers=30 \
    ! videoconvert ! video/x-raw,format=GRAY8 ! filesink location="$OUT/ir.raw"

python3 - "$OUT/ir.raw" <<'EOF'
import sys
d = open(sys.argv[1], 'rb').read()
n = len(d) // 30
means = [round(sum(d[i*n:(i+1)*n]) / n, 1) for i in range(30)]
print("Per-frame mean brightness (0-255):", means)
lit = sum(m > 15 for m in means)
print(f"{lit}/30 frames lit ->", "IR emitter is working" if lit >= 5 else "IR emitter looks OFF")
EOF
