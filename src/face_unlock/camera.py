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
import time
from collections import deque

from gi.repository import Gdk, GLib

# Frames darker than this (mean, 0-255) count as unlit.
DARK_LEVEL = 8
PREVIEW_INTERVAL = 0.1  # At most ten displayed frames per second.


class CameraPreview:
    def __init__(self, on_frame, on_error=None):
        """on_frame(texture, lit_ratio) and on_error(device) run on the UI thread."""
        self._on_frame = on_frame
        self._on_error = on_error
        self._stop = threading.Event()
        self._thread = None
        self._pending_lock = threading.Lock()
        self._pending_frame = None
        self._delivery_scheduled = False

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self, device_path):
        if not self.stop():
            return False
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, args=(device_path, self._stop), daemon=True)
        self._thread.start()
        return True

    def stop(self):
        """Stop capturing; report whether the device has been released."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=3)
            if self._thread.is_alive():
                return False
            self._thread = None
        with self._pending_lock:
            self._pending_frame = None
            self._delivery_scheduled = False
        return True

    def _run(self, device_path, stop):
        import cv2  # slow import; keep it off the UI thread

        capture = cv2.VideoCapture(device_path, cv2.CAP_V4L2)
        if not capture.isOpened():
            capture.release()
            self._report_error(device_path, stop)
            return
        # Drivers may reject these hints; the timed loop below still bounds
        # decoding and UI work when they do.
        capture.set(cv2.CAP_PROP_FPS, 10)
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        recent = deque(maxlen=30)
        next_frame = 0.0
        try:
            while not stop.is_set():
                delay = next_frame - time.monotonic()
                if delay > 0 and stop.wait(delay):
                    break
                ok, frame = capture.read()
                if stop.is_set():
                    break
                if not ok:
                    self._report_error(device_path, stop)
                    return
                next_frame = time.monotonic() + PREVIEW_INTERVAL
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
                lit = float(gray.mean()) > DARK_LEVEL
                recent.append(lit)
                if not lit:
                    continue
                gray = cv2.flip(gray, 1)  # mirror, like looking in a mirror
                height, width = gray.shape
                texture = Gdk.MemoryTexture.new(
                    width, height, Gdk.MemoryFormat.G8, GLib.Bytes.new(gray.tobytes()), width)
                with self._pending_lock:
                    self._pending_frame = (texture, sum(recent) / len(recent))
                    if not self._delivery_scheduled:
                        self._delivery_scheduled = True
                        GLib.idle_add(self._deliver, stop)
        finally:
            capture.release()

    def _deliver(self, stop):
        with self._pending_lock:
            if stop is not self._stop:
                return GLib.SOURCE_REMOVE
            frame = self._pending_frame
            self._pending_frame = None
            self._delivery_scheduled = False
        if frame is not None and not stop.is_set():
            texture, lit_ratio = frame
            self._on_frame(texture, lit_ratio)
        return GLib.SOURCE_REMOVE

    def _report_error(self, device_path, stop):
        if self._on_error and not stop.is_set():
            GLib.idle_add(self._deliver_error, device_path, stop)

    def _deliver_error(self, device_path, stop):
        if stop is self._stop and not stop.is_set():
            self._on_error(device_path)
        return GLib.SOURCE_REMOVE
