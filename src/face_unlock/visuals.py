# Author: WM Nipun Dhananjaya
# Date:   24/09/2026
#
# Licensed under the MIT License. See the project LICENSE file for details.
"""Decorative scan graphics, with GTK's reduced-motion preference respected."""

import math
from gi.repository import Gtk


class ScanVisual(Gtk.Overlay):
    """A decorative face guide, not a representation of recognition progress."""

    def __init__(self, size=200):
        super().__init__(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER,
                         width_request=size, height_request=size,
                         can_target=False)
        self._size = size
        self._tick_id = 0
        self._start_time = None
        self.add_css_class('scan-visual')
        self.set_child(Gtk.Box(css_classes=['scan-grid']))
        ring = Gtk.Box(css_classes=['scan-ring'], margin_top=12, margin_bottom=12,
                       margin_start=12, margin_end=12)
        self.add_overlay(ring)
        self._halo = Gtk.Box(css_classes=['scan-inner'], margin_top=30, margin_bottom=30,
                             margin_start=30, margin_end=30)
        self.add_overlay(self._halo)
        self.add_overlay(Gtk.Image(icon_name='avatar-default-symbolic',
                                   pixel_size=int(size * .36), css_classes=['scan-face']))
        self._line = Gtk.Box(css_classes=['scan-line'], height_request=2,
                             margin_start=18, margin_end=18, margin_top=size // 2,
                             valign=Gtk.Align.START)
        self.add_overlay(self._line)
        self.connect('map', self._mapped)
        self.connect('unmap', self._unmapped)

    def _mapped(self, *_):
        if not self._tick_id and self.get_settings().get_property('gtk-enable-animations'):
            self._start_time = None
            self._tick_id = self.add_tick_callback(self._animate)

    def _unmapped(self, *_):
        if self._tick_id:
            self.remove_tick_callback(self._tick_id)
            self._tick_id = 0
        self._line.set_margin_top(self._size // 2)
        self._halo.set_opacity(1)

    def _animate(self, _widget, clock):
        if not self.get_settings().get_property('gtk-enable-animations'):
            self._tick_id = 0
            self._line.set_margin_top(self._size // 2)
            self._halo.set_opacity(1)
            return False
        now = clock.get_frame_time()
        if self._start_time is None:
            self._start_time = now
        phase = (now - self._start_time) / 1_000_000
        wave = (math.sin(phase * 1.7) + 1) / 2
        self._line.set_margin_top(round(24 + wave * (self._size - 48)))
        self._halo.set_opacity(.4 + wave * .6)
        return True
