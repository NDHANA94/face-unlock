# Author: WM Nipun Dhananjaya
# Date:   24/09/2026
#
# Licensed under the MIT License. See the project LICENSE file for details.
"""Main window."""

import time

from gi.repository import Adw, GLib, Gtk

from . import system
from .enroll import EnrollDialog
from .i18n import _
from .preview import PreviewFrame
from .visuals import ScanVisual

# (label, certainty) — lower certainty values are stricter
STRICTNESS = [
    (_("Relaxed"), 4.5),
    (_("Balanced"), 3.5),
    (_("Strict"), 2.8),
    (_("Very Strict"), 2.2),
]


class Window(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title=_("Face Unlock"),
                         default_width=740, default_height=860)
        self.add_css_class("face-window")
        self.set_size_request(360, 480)
        self._helper = system.Helper()
        self._models = []
        self._cameras = []
        self._loading = False       # true while widgets are set from system state
        self._timeout_source = 0

        self._toasts = Adw.ToastOverlay()
        self._stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE, transition_duration=250)
        self._toasts.set_child(self._stack)
        self._stack.add_named(Adw.Spinner(), "loading")
        self._stack.add_named(self._build_welcome(), "welcome")
        self._stack.add_named(self._build_settings(), "settings")
        self._problem = Adw.StatusPage()
        self._stack.add_named(self._problem, "problem")

        header = Adw.HeaderBar()
        header.set_title_widget(Gtk.Label(label="FACE / UNLOCK", css_classes=["eyebrow"]))
        menu = Gtk.MenuButton(icon_name="open-menu-symbolic", tooltip_text=_("Main Menu"),
                              primary=True)
        menu.set_menu_model(app.build_menu())
        header.pack_end(menu)
        view = Adw.ToolbarView(content=self._toasts)
        view.add_top_bar(header)
        self.set_content(view)
        self.refresh()

    # --- pages -------------------------------------------------------------

    def _build_welcome(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20,
                      margin_top=24, margin_bottom=32, margin_start=24, margin_end=24)
        box.append(Gtk.Label(label=_("YOUR FACE. YOUR ACCESS."), css_classes=["eyebrow"]))
        box.append(ScanVisual(220))
        box.append(Gtk.Label(label=_("A glance. You're in."), css_classes=["welcome-title"],
                             wrap=True, justify=Gtk.Justification.CENTER))
        box.append(Gtk.Label(label=_("Unlock your device and approve requests with your face."),
                             wrap=True, justify=Gtk.Justification.CENTER, css_classes=["muted"]))
        box.append(Gtk.Label(label=_("ON-DEVICE RECOGNITION"), halign=Gtk.Align.CENTER,
                             css_classes=["status-chip"]))
        button = Gtk.Button(label=_("Get started"), halign=Gtk.Align.CENTER,
                            css_classes=["pill", "suggested-action"])
        button.connect("clicked", self._on_setup)
        self._setup_camera_row = Adw.ComboRow(title=_("Camera"))
        cameras = Gtk.ListBox(css_classes=["boxed-list"], selection_mode=Gtk.SelectionMode.NONE)
        cameras.append(self._setup_camera_row)
        box.append(cameras)
        box.append(button)
        box.append(Gtk.Label(label=_("RGB + IR cameras  ·  Password fallback  ·  No cloud"),
                             wrap=True, justify=Gtk.Justification.CENTER,
                             css_classes=["caption", "muted"]))
        clamp = Adw.Clamp(child=box, maximum_size=560)
        return Gtk.ScrolledWindow(child=clamp, hscrollbar_policy=Gtk.PolicyType.NEVER)

    def _build_settings(self):
        page = Adw.PreferencesPage()
        hero_group = Adw.PreferencesGroup()
        hero = Gtk.Box(spacing=20, css_classes=["hero"])
        hero.append(ScanVisual(112))
        copy = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8,
                       valign=Gtk.Align.CENTER, hexpand=True)
        copy.append(Gtk.Label(label=_("FACE RECOGNITION"), xalign=0, css_classes=["eyebrow"]))
        self._hero_title = Gtk.Label(label=_("Ready when you are"), xalign=0,
                                     wrap=True, css_classes=["hero-title"])
        copy.append(self._hero_title)
        self._hero_status = Gtk.Label(xalign=0, wrap=True, css_classes=["muted"])
        copy.append(self._hero_status)
        hero.append(copy)
        hero_group.add(hero)
        page.add(hero_group)

        self._banner = Adw.Banner(title=_("Add a face to start using Face Unlock"),
                                  button_label=_("Add Face"))
        self._banner.connect("button-clicked", self._on_add_face)

        main = Adw.PreferencesGroup()
        self._enabled_row = Adw.SwitchRow(
            title=_("Face Unlock"),
            subtitle=_("Use your face for the login screen, lock screen and administrator prompts"))
        self._enabled_row.connect("notify::active", self._on_enabled_changed)
        main.add(self._enabled_row)
        page.add(main)

        # Faces
        self._faces = Adw.PreferencesGroup(
            title=_("Your face profiles"),
            description=_("Each face is a scan of you. Add one with glasses or in different "
                          "light if recognition is unreliable."))
        add = Gtk.Button(icon_name="list-add-symbolic", tooltip_text=_("Add Face"),
                         css_classes=["flat"], valign=Gtk.Align.CENTER)
        add.connect("clicked", self._on_add_face)
        self._faces.set_header_suffix(add)
        self._face_rows = []
        page.add(self._faces)

        test_group = Adw.PreferencesGroup()
        self._test_row = Adw.ActionRow(title=_("Test Recognition"),
                                       subtitle=_("Check that Face Unlock recognizes you"))
        self._test_spinner = Adw.Spinner(visible=False)
        self._test_button = Gtk.Button(label=_("Try a scan"), valign=Gtk.Align.CENTER,
                                       css_classes=["suggested-action"])
        self._test_button.connect("clicked", self._on_test)
        self._test_row.add_suffix(self._test_spinner)
        self._test_row.add_suffix(self._test_button)
        test_group.add(self._test_row)
        page.add(test_group)

        # Camera
        camera_group = Adw.PreferencesGroup(title=_("Camera"))
        self._camera_row = Adw.ComboRow(title=_("Camera"))
        self._camera_row.connect("notify::selected", self._on_camera_changed)
        camera_group.add(self._camera_row)
        preview_row = Adw.ActionRow(title=_("Camera Preview"),
                                    subtitle=_("See what the camera sees"),
                                    activatable=True)
        preview_row.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
        preview_row.connect("activated", self._on_preview)
        camera_group.add(preview_row)
        page.add(camera_group)

        # Behavior
        behavior = Adw.PreferencesGroup(title=_("Fine-tune recognition"))
        self._strictness_row = Adw.ComboRow(
            title=_("Strictness"),
            subtitle=_("Stricter settings reject look-alikes but may need more tries"),
            model=Gtk.StringList.new([label for label, _v in STRICTNESS]))
        self._strictness_row.connect("notify::selected", self._on_strictness_changed)
        behavior.add(self._strictness_row)
        self._timeout_row = Adw.SpinRow.new_with_range(1, 15, 1)
        self._timeout_row.set_title(_("Scan Time Limit"))
        self._timeout_row.set_subtitle(_("Seconds to look for your face before asking for the password"))
        self._timeout_row.connect("notify::value", self._on_timeout_changed)
        behavior.add(self._timeout_row)
        self._switches = {}
        for key, title, subtitle in (
            ("core.detection_notice", _("Show Scanning Message"),
             _("Display “Attempting facial authentication” while scanning")),
            ("core.abort_if_lid_closed", _("Skip When Lid Is Closed"),
             _("Go straight to the password when the laptop is docked with the lid shut")),
            ("core.abort_if_ssh", _("Skip in Remote Sessions"),
             _("Never use the camera for SSH logins")),
        ):
            row = Adw.SwitchRow(title=title, subtitle=subtitle)
            row.connect("notify::active", self._on_switch_changed, key)
            behavior.add(row)
            self._switches[key] = row
        page.add(behavior)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(self._banner)
        box.append(page)
        page.set_vexpand(True)
        return box

    # --- state -------------------------------------------------------------

    def refresh(self):
        if not system.engine_installed():
            self._show_problem("dialog-error-symbolic", _("Face Unlock Is Not Installed Correctly"),
                               _("Reinstall the face-unlock package and try again."))
            return
        self._cameras = system.list_cameras()
        if not self._cameras:
            self._show_problem("camera-disabled-symbolic", _("No Camera Found"),
                               _("Face Unlock needs an RGB or infrared camera. "
                                 "Make sure it is not disabled in the firmware settings."))
            return
        names = [self._camera_label(c) for c in self._cameras]
        self._setup_camera_row.set_model(Gtk.StringList.new(names))
        configured = system.read_config().get("video", "device_path", fallback="none")
        index = next((i for i, c in enumerate(self._cameras)
                      if configured in (c.path, c.node)), 0)
        self._setup_camera_row.set_selected(index)
        self._stack.set_visible_child_name("loading")
        self._helper.run(["list"], self._on_models_loaded)

    def _show_problem(self, icon, title, description):
        self._problem.set_icon_name(icon)
        self._problem.set_title(title)
        self._problem.set_description(description)
        self._stack.set_visible_child_name("problem")

    def _on_models_loaded(self, result):
        if not result.get("ok"):
            self._show_problem("dialog-error-symbolic", _("Could Not Read Face Data"),
                               result.get("error", ""))
            return
        self._set_models(result["models"])
        enabled = system.face_unlock_enabled()
        if not self._models and not enabled:
            self._stack.set_visible_child_name("welcome")
        else:
            self._load_settings()
            self._stack.set_visible_child_name("settings")

    def _load_settings(self):
        config = system.read_config()
        self._loading = True
        try:
            self._enabled_row.set_active(system.face_unlock_enabled())
            self._update_hero()

            names = [self._camera_label(c) for c in self._cameras]
            self._camera_row.set_model(Gtk.StringList.new(names))
            configured = config.get("video", "device_path", fallback="none")
            index = next((i for i, c in enumerate(self._cameras)
                          if configured in (c.path, c.node)), 0)
            self._camera_row.set_selected(index)

            certainty = config.getfloat("video", "certainty", fallback=3.5)
            nearest = min(range(len(STRICTNESS)), key=lambda i: abs(STRICTNESS[i][1] - certainty))
            self._strictness_row.set_selected(nearest)
            self._timeout_row.set_value(config.getint("video", "timeout", fallback=4))
            for key, row in self._switches.items():
                section, name = key.split(".")
                row.set_active(config.getboolean(section, name, fallback=False))
        finally:
            self._loading = False

    def _set_models(self, models):
        self._models = models
        for row in self._face_rows:
            self._faces.remove(row)
        self._face_rows = []
        for model in models:
            added = time.strftime("%x", time.localtime(model["time"]))
            row = Adw.ActionRow(title=GLib.markup_escape_text(model["label"]),
                                subtitle=_("Added {date}").format(date=added))
            row.add_prefix(Gtk.Image(icon_name="avatar-default-symbolic"))
            remove = Gtk.Button(icon_name="user-trash-symbolic", tooltip_text=_("Remove"),
                                valign=Gtk.Align.CENTER, css_classes=["flat"])
            remove.connect("clicked", self._on_remove_face, model)
            row.add_suffix(remove)
            self._faces.add(row)
            self._face_rows.append(row)
        if not models:
            empty = Adw.ActionRow(title=_("No faces added"), css_classes=["dim-label"])
            self._faces.add(empty)
            self._face_rows.append(empty)
        self._banner.set_revealed(not models)
        self._test_row.set_sensitive(bool(models))
        self._update_hero()

    def _update_hero(self):
        enabled = system.face_unlock_enabled()
        ready = enabled and bool(self._models)
        self._hero_title.set_label(_("Ready when you are") if ready else _("Make it yours"))
        if ready:
            text = _("Face Unlock is on · {n} saved profiles").format(n=len(self._models))
        elif self._models:
            text = _("Face Unlock is off · Your profiles are saved")
        else:
            text = _("Add your first face profile to get started")
        self._hero_status.set_label(text)

    @staticmethod
    def _camera_label(camera):
        return f"{camera.name} ({'IR' if camera.is_ir else 'RGB'})"

    def _selected_camera(self):
        index = self._camera_row.get_selected()
        if 0 <= index < len(self._cameras):
            return self._cameras[index]
        return self._cameras[0]

    def toast(self, message):
        self._toasts.add_toast(Adw.Toast(title=message, timeout=4))

    def _report(self, result, success_message=None):
        """Show the outcome of a helper call. Returns True on success."""
        if result.get("ok"):
            if success_message:
                self.toast(success_message)
            return True
        if not result.get("cancelled"):
            self.toast(result.get("error") or result.get("message") or _("Something went wrong"))
        return False

    # --- setup flow --------------------------------------------------------

    def _on_setup(self, *args):
        camera = self._cameras[self._setup_camera_row.get_selected()]
        self._load_settings()
        self._loading = True
        self._camera_row.set_selected(self._cameras.index(camera))
        self._loading = False
        self._open_enroll(first_time=True)

    def _open_enroll(self, first_time=False):
        camera = self._selected_camera()

        def present():
            default = _("My Face") if not self._models else _("Face {n}").format(n=len(self._models) + 1)
            dialog = EnrollDialog(self._helper, camera.path, default,
                                  lambda models: self._on_enrolled(models, first_time), is_ir=camera.is_ir)
            dialog.present(self)

        # The displayed selection can be a fallback for an unset or unplugged
        # device. Persist it for the engine before opening any enrollment flow.
        configured = system.read_config().get("video", "device_path", fallback="none")
        if configured in (camera.path, camera.node):
            present()
        else:
            self._helper.run(["configure", f"video.device_path={camera.path}"],
                             lambda result: self._report(result) and present())

    def _on_enrolled(self, models, first_time):
        self._set_models(models)
        if first_time or not system.face_unlock_enabled():
            self._helper.run(["enable"], self._on_setup_enabled)
        else:
            self.toast(_("Face added"))

    def _on_setup_enabled(self, result):
        self._report(result, _("Face Unlock is on. Lock your screen to try it."))
        self._load_settings()
        self._stack.set_visible_child_name("settings")

    # --- handlers ----------------------------------------------------------

    def _on_add_face(self, *args):
        self._open_enroll(first_time=False)

    def _on_remove_face(self, button, model):
        dialog = Adw.AlertDialog(
            heading=_("Remove “{label}”?").format(label=model["label"]),
            body=_("Face Unlock will no longer use this scan.") if len(self._models) > 1 else
                 _("This is your only face. Face Unlock will stop working for you until you add one."))
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("remove", _("Remove"))
        dialog.set_response_appearance("remove", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", self._on_remove_response, model)
        dialog.present(self)

    def _on_remove_response(self, dialog, response, model):
        if response != "remove":
            return

        def done(result):
            if self._report(result, _("Face removed")):
                self._set_models(result["models"])
        self._helper.run(["remove", str(model["id"])], done)

    def _on_enabled_changed(self, row, _pspec):
        if self._loading:
            return
        want = row.get_active()
        if want and not self._models:
            self._set_active_quietly(row, False)
            self._open_enroll(first_time=True)
            return

        def done(result):
            if self._report(result, _("Face Unlock is on") if want else _("Face Unlock is off")):
                self._update_hero()
                return
            self._set_active_quietly(row, system.face_unlock_enabled())
        self._helper.run(["enable" if want else "disable"], done)

    def _set_active_quietly(self, row, active):
        self._loading = True
        row.set_active(active)
        self._loading = False

    def _on_test(self, *args):
        self._test_button.set_sensitive(False)
        self._test_spinner.set_visible(True)
        self._test_row.set_subtitle(_("Look at the camera…"))

        def done(result):
            self._test_button.set_sensitive(True)
            self._test_spinner.set_visible(False)
            if result.get("cancelled"):
                self._test_row.set_subtitle(_("Check that Face Unlock recognizes you"))
                return
            message = result.get("message") or result.get("error") or _("Something went wrong")
            self._test_row.set_subtitle(("✓ " if result.get("ok") else "✗ ") + message)
        self._helper.run(["verify"], done)

    def _on_preview(self, *args):
        frame = PreviewFrame()
        frame.set_margin_top(12)
        frame.set_margin_bottom(24)
        frame.set_margin_start(24)
        frame.set_margin_end(24)
        view = Adw.ToolbarView(content=frame, css_classes=["glass-dialog"])
        view.add_top_bar(Adw.HeaderBar())
        dialog = Adw.Dialog(title=_("Camera Preview"), child=view, content_width=400)
        dialog.connect("closed", lambda *_: frame.stop())
        dialog.present(self)
        camera = self._selected_camera()
        frame.start(camera.path, is_ir=camera.is_ir)

    def _configure(self, *settings):
        def done(result):
            if not self._report(result):
                self._load_settings()  # put the widgets back
        self._helper.run(["configure", *settings], done)

    def _on_camera_changed(self, row, _pspec):
        if not self._loading:
            self._configure(f"video.device_path={self._selected_camera().path}")

    def _on_strictness_changed(self, row, _pspec):
        if not self._loading:
            self._configure(f"video.certainty={STRICTNESS[row.get_selected()][1]}")

    def _on_timeout_changed(self, row, _pspec):
        if self._loading:
            return
        # Wait until the user stops clicking before asking for a password
        if self._timeout_source:
            GLib.source_remove(self._timeout_source)

        def apply():
            self._timeout_source = 0
            self._configure(f"video.timeout={int(row.get_value())}")
            return GLib.SOURCE_REMOVE
        self._timeout_source = GLib.timeout_add(800, apply)

    def _on_switch_changed(self, row, _pspec, key):
        if not self._loading:
            self._configure(f"{key}={'true' if row.get_active() else 'false'}")
