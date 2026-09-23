#!/usr/bin/env python3
"""Render the app's main states to PNG files using the mock helper.

Development tool. Run on a headless display, for example:
    gtk4-broadwayd :5 & GDK_BACKEND=broadway BROADWAY_DISPLAY=:5 scripts/ui-snapshot.py OUTDIR
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "snapshots")
TMP = tempfile.mkdtemp(prefix="face-unlock-ui-")
os.makedirs(OUT, exist_ok=True)

config = os.path.join(TMP, "config.ini")
with open(config, "w") as f:
    f.write("[core]\ndetection_notice = true\nabort_if_ssh = true\nabort_if_lid_closed = true\n"
            "[video]\ncertainty = 3.5\ntimeout = 4\ndevice_path = none\n")
os.environ.update({
    "FACE_UNLOCK_HELPER": os.path.join(ROOT, "tests", "mock-helper"),
    "FACE_UNLOCK_DEV_NO_PKEXEC": "1",
    "FACE_UNLOCK_CONFIG": config,
    "FACE_UNLOCK_COMMON_AUTH": os.path.join(TMP, "common-auth"),
    "MOCK_STATE": os.path.join(TMP, "state.json"),
})
sys.path.insert(0, os.path.join(ROOT, "src"))

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from face_unlock.main import Application  # noqa: E402
from face_unlock import system
from face_unlock.preview import PreviewFrame

# Screenshots must be reproducible and must not open the user's camera.
system.list_cameras = lambda: [system.Camera("/dev/video0", "/dev/video0", "Demo Camera", False)]
PreviewFrame.start = lambda self, *args, **kwargs: self.status.set_label("Camera preview")

app = Application()
app._appearance_path = Path(TMP) / "appearance.json"
app._appearance = os.environ.get("FACE_UNLOCK_SNAPSHOT_THEME", "light")
app.connect("startup", lambda *_: Gtk.IconTheme.get_for_display(
    Gdk.Display.get_default()).add_search_path(os.path.join(ROOT, "data", "icons")))


def shoot(name):
    win = app.window
    width, height = win.get_width(), win.get_height()
    paintable = Gtk.WidgetPaintable.new(win)
    snapshot = Gtk.Snapshot()
    paintable.snapshot(snapshot, width, height)
    node = snapshot.to_node()
    if node is None:
        raise RuntimeError("No rendered frame; use an X11 display or connect a browser to Broadway first")
    texture = win.get_renderer().render_texture(node, None)
    path = os.path.join(OUT, f"{name}.png")
    texture.save_to_png(path)
    print("saved", path)


def set_models(models, enabled):
    with open(os.environ["MOCK_STATE"], "w") as f:
        json.dump({"models": models, "enabled": enabled}, f)
    with open(os.environ["FACE_UNLOCK_COMMON_AUTH"], "w") as f:
        f.write("auth [success=end default=ignore] pam_howdy.so\n" if enabled else "")


steps = [
    (1500, lambda: shoot("1-welcome")),
    (100, lambda: (set_models([{"id": 0, "label": "My Face", "time": 1790000000},
                               {"id": 1, "label": "With Glasses", "time": 1790100000}], True),
                   app.window.refresh())),
    (1500, lambda: shoot("2-settings")),
    (100, lambda: app.window._open_enroll()),
    (3000, lambda: shoot("3-add-face")),
    (100, lambda: app.window.get_visible_dialog()._stack.set_visible_child_name("scanning")),
    (1000, lambda: shoot("4-scanning")),
    (100, lambda: app.window.get_visible_dialog().close()),
    (300, lambda: app.window.set_default_size(390, 700)),
    (700, lambda: shoot("5-compact")),
    (100, lambda: app.quit()),
]


def run_steps(index=0):
    if index >= len(steps):
        return
    delay, action = steps[index]

    def fire():
        try:
            action()
        except Exception:
            import traceback
            traceback.print_exc()
            app.snapshot_failed = True
            app.quit()
            return GLib.SOURCE_REMOVE
        run_steps(index + 1)
        return GLib.SOURCE_REMOVE
    GLib.timeout_add(delay, fire)


set_models([], False)
app.connect("activate", lambda *_: run_steps())
try:
    app.run([])
    if getattr(app, "snapshot_failed", False):
        sys.exit(1)
finally:
    shutil.rmtree(TMP, ignore_errors=True)
