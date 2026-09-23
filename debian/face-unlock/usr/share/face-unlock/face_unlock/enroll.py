# Author: WM Nipun Dhananjaya
# Date:   24/09/2026
#
# Licensed under the MIT License. See the project LICENSE file for details.
"""The "Add Face" dialog."""

from gi.repository import Adw, GLib, Gtk

from .i18n import _
from .preview import PreviewFrame
from .visuals import ScanVisual


class EnrollDialog(Adw.Dialog):
    def __init__(self, helper, device_path, default_label, on_enrolled, is_ir=False):
        super().__init__(title=_("Add Face"), content_width=460, content_height=680)
        self._helper = helper
        self._device_path = device_path
        self._is_ir = is_ir
        self._on_enrolled = on_enrolled

        self._stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self._stack.add_named(self._build_ready_page(default_label), "ready")
        self._stack.add_named(self._build_scanning_page(), "scanning")
        self._error_page = Adw.StatusPage(icon_name="dialog-warning-symbolic",
                                          title=_("Face Not Added"))
        retry = Gtk.Button(label=_("Try Again"), halign=Gtk.Align.CENTER,
                           css_classes=["pill", "suggested-action"])
        retry.connect("clicked", lambda *_: self._show_ready())
        self._error_page.set_child(retry)
        self._stack.add_named(self._error_page, "error")

        view = Adw.ToolbarView(content=self._stack, css_classes=["glass-dialog"])
        view.add_top_bar(Adw.HeaderBar())
        self.set_child(view)
        self.connect("closed", lambda *_: self._preview.stop())
        GLib.idle_add(self._show_ready)

    def _build_ready_page(self, default_label):
        self._preview = PreviewFrame()
        self._label = Adw.EntryRow(title=_("Name"), text=default_label)
        self._label.set_max_length(24)
        names = Gtk.ListBox(css_classes=["boxed-list"], selection_mode=Gtk.SelectionMode.NONE)
        names.append(self._label)
        tips = Gtk.Label(
            label=_("Center your face in the picture and look straight at the camera. "
                    "Adding a second face with glasses or in different light makes "
                    "recognition more reliable."),
            wrap=True, justify=Gtk.Justification.CENTER, css_classes=["dim-label"])
        self._scan_button = Gtk.Button(label=_("Scan Face"), halign=Gtk.Align.CENTER,
                                       css_classes=["pill", "suggested-action"])
        self._scan_button.connect("clicked", self._on_scan)
        self._label.connect("entry-activated", self._on_scan)
        self._label.connect("changed", self._validate)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18,
                      margin_top=12, margin_bottom=24, margin_start=24, margin_end=24)
        for child in (self._preview, names, tips, self._scan_button):
            box.append(child)
        return Gtk.ScrolledWindow(child=box, hscrollbar_policy=Gtk.PolicyType.NEVER,
                                  propagate_natural_height=True)

    def _build_scanning_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24,
                      valign=Gtk.Align.CENTER, margin_start=24, margin_end=24)
        box.append(Gtk.Label(label=_("ENROLLING YOUR FACE"), css_classes=["eyebrow"]))
        box.append(ScanVisual(220))
        box.append(Gtk.Label(label=_("Look this way"), css_classes=["hero-title"]))
        box.append(Gtk.Label(label=_("Keep looking at the camera while your face is scanned."),
                             wrap=True, justify=Gtk.Justification.CENTER, css_classes=["muted"]))
        box.append(Gtk.Label(label=_("Your face profile stays on this device"),
                             css_classes=["caption", "muted"]))
        return box

    def _show_ready(self):
        self._stack.set_visible_child_name("ready")
        self._preview.start(self._device_path, is_ir=self._is_ir)
        self._label.grab_focus()
        return GLib.SOURCE_REMOVE

    def _validate(self, *args):
        text = self._label.get_text().strip()
        valid = 0 < len(text) <= 24 and "," not in text
        self._scan_button.set_sensitive(valid)
        if valid:
            self._label.remove_css_class("error")
        else:
            self._label.add_css_class("error")
        return valid

    def _on_scan(self, *args):
        if not self._validate():
            return
        # The engine needs the camera to itself
        self._preview.stop()
        self._stack.set_visible_child_name("scanning")
        self.set_can_close(False)
        self._helper.run(["enroll", self._label.get_text().strip()], self._on_result)

    def _on_result(self, result):
        self.set_can_close(True)
        if result.get("ok"):
            self._on_enrolled(result.get("models", []))
            self.close()
        elif result.get("cancelled"):
            self._show_ready()
        else:
            message = result.get("message") or result.get("error") or _("The face scan failed.")
            if result.get("detail"):
                message += "\n\n" + result["detail"]
            self._error_page.set_description(message)
            self._stack.set_visible_child_name("error")
