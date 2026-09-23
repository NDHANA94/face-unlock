# Author: WM Nipun Dhananjaya
# Date:   24/09/2026
#
# Licensed under the MIT License. See the project LICENSE file for details.
"""Live camera preview.

IR cameras strobe their illuminator, so lit frames alternate with black ones.
Black frames are dropped from the preview and counted to tell whether the
illuminator works.
"""
import threading
from collections import deque

from gi.repository import Gdk, GLib

# Frames darker than this (mean, 0-255) count as unlit
DARK_LEVEL = 8


class CameraPreview:
    def __init__(self, on_frame, on_error=None):
        """on_frame(texture, lit_ratio) and on_error(message) run on the UI thread."""
        self._on_frame = on_frame
        self._on_error = on_error
        self._stop = threading.Event()
        self._thread = None

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self, device_path):
        self.stop()
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, args=(device_path,), daemon=True)
        self._thread.start()

    def stop(self):
        """Stop capturing and release the camera (blocks until released)."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=3)
            self._thread = None

    def _run(self, device_path):
        import cv2  # slow import; keep it off the UI thread

        capture = cv2.VideoCapture(device_path, cv2.CAP_V4L2)
        if not capture.isOpened():
            self._report_error(device_path)
            return
        recent = deque(maxlen=30)
        try:
            while not self._stop.is_set():
                ok, frame = capture.read()
                if not ok:
                    self._report_error(device_path)
                    return
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
                lit = float(gray.mean()) > DARK_LEVEL
                recent.append(lit)
                if not lit:
                    continue
                gray = cv2.flip(gray, 1)  # mirror, like looking in a mirror
                height, width = gray.shape
                texture = Gdk.MemoryTexture.new(
                    width, height, Gdk.MemoryFormat.G8, GLib.Bytes.new(gray.tobytes()), width)
                GLib.idle_add(self._deliver, texture, sum(recent) / len(recent))
        finally:
            capture.release()

    def _deliver(self, texture, lit_ratio):
        if not self._stop.is_set():
            self._on_frame(texture, lit_ratio)
        return GLib.SOURCE_REMOVE

    def _report_error(self, device_path):
        if self._on_error and not self._stop.is_set():
            GLib.idle_add(self._on_error, device_path)
