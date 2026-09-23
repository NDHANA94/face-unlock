# Author: WM Nipun Dhananjaya
# Date:   24/09/2026
#
# Licensed under the MIT License. See the project LICENSE file for details.
"""A framed camera preview with camera-specific status."""

from gi.repository import Gtk

from .camera import CameraPreview
from .i18n import _

# Share of frames that must be lit for the illuminator to count as working
LIT_RATIO_OK = 0.2


class PreviewFrame(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.picture = Gtk.Picture(content_fit=Gtk.ContentFit.COVER,
                                   width_request=280, height_request=260)
        self.placeholder = Gtk.Image(icon_name="camera-web-symbolic", pixel_size=48,
                                     css_classes=["dim-label"])
        stack = Gtk.Stack(css_classes=["preview"], overflow=Gtk.Overflow.HIDDEN,
                          halign=Gtk.Align.CENTER)
        stack.add_named(self.placeholder, "placeholder")
        stack.add_named(self.picture, "picture")
        self._stack = stack
        self.status = Gtk.Label(css_classes=["preview-hint"], wrap=True,
                                justify=Gtk.Justification.CENTER)
        self.append(stack)
        self.append(self.status)
        self._camera = CameraPreview(self._on_frame, self._on_error)
        self.connect("unrealize", lambda *_: self.stop())

    def start(self, device_path, is_ir=False):
        self._is_ir = is_ir
        self._stack.set_visible_child_name("placeholder")
        self.status.set_label(_("Starting camera…"))
        self._camera.start(device_path)

    def stop(self):
        self._camera.stop()

    def _on_frame(self, texture, lit_ratio):
        self.picture.set_paintable(texture)
        self._stack.set_visible_child_name("picture")
        if not self._is_ir:
            self.status.set_label(_("Camera is working"))
        elif lit_ratio >= LIT_RATIO_OK:
            self.status.set_label(_("IR illuminator is working"))
        else:
            self.status.set_label(_("The picture is mostly dark — the IR illuminator may be off"))

    def _on_error(self, device_path):
        self._stack.set_visible_child_name("placeholder")
        self.status.set_label(_("Could not open the camera. It may be in use by another app."))
