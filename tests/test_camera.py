"""Capture lifecycle checks without opening a physical camera."""
import sys
import types
import unittest
from unittest import mock

import numpy as np
import gi
gi.require_version('Gdk', '4.0')

from face_unlock import camera


class CameraPreviewTests(unittest.TestCase):
    def test_restart_waits_for_previous_capture_to_release(self):
        preview = camera.CameraPreview(lambda *_: None)
        thread = mock.Mock()
        thread.is_alive.return_value = True
        preview._thread = thread
        with mock.patch.object(preview, "_run") as run:
            self.assertFalse(preview.start("/dev/video1"))
        thread.join.assert_called_once_with(timeout=3)
        run.assert_not_called()
        self.assertIs(preview._thread, thread)
        self.assertTrue(preview._stop.is_set())

    def test_fast_camera_keeps_only_latest_preview_frame(self):
        frames = []
        queued = []
        class Capture:
            def __init__(self, *_):
                self.reads = 0
            def isOpened(self):
                return True
            def read(self):
                self.reads += 1
                if self.reads > 50:
                    return False, None
                return True, np.full((2, 2), self.reads, dtype=np.uint8)
            def release(self):
                pass
            def set(self, _property, _value):
                return True
        fake_cv2 = types.SimpleNamespace(CAP_V4L2=1, CAP_PROP_FPS=5,
                                         CAP_PROP_BUFFERSIZE=38, VideoCapture=Capture,
                                         flip=lambda frame, _axis: frame)
        fake_gdk = types.SimpleNamespace(MemoryTexture=types.SimpleNamespace(
            new=lambda _w, _h, _format, data, _stride: data),
            MemoryFormat=types.SimpleNamespace(G8=1))
        fake_glib = types.SimpleNamespace(Bytes=types.SimpleNamespace(new=lambda data: data),
                                          idle_add=lambda fn, *args: queued.append((fn, args)),
                                          SOURCE_REMOVE=False)
        preview = camera.CameraPreview(lambda texture, ratio: frames.append((texture, ratio)))
        delays = []
        class Stop:
            def is_set(self):
                return False
            def wait(self, delay):
                delays.append(delay)
                return False
        preview._stop = Stop()
        ticks = iter(i * 0.01 for i in range(120))
        with mock.patch.dict(sys.modules, {"cv2": fake_cv2}), \
                mock.patch.object(camera, "Gdk", fake_gdk), \
                mock.patch.object(camera, "GLib", fake_glib), \
                mock.patch.object(camera.time, "monotonic", side_effect=lambda: next(ticks)):
            preview._run("/dev/video0", preview._stop)
            deliveries = [(fn, args) for fn, args in queued if fn == preview._deliver]
            self.assertEqual(len(deliveries), 1)
            fn, args = deliveries[0]
            fn(*args)
        self.assertEqual(len(frames), 1)
        self.assertGreater(frames[0][1], 0)
        self.assertTrue(delays)
        self.assertGreater(min(delays), 0)
