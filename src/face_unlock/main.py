# Author: WM Nipun Dhananjaya
# Date:   24/09/2026
#
# Licensed under the MIT License. See the project LICENSE file for details.
"""Application entry point."""

import gi
import json
from pathlib import Path

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

from . import APP_ID, VERSION  # noqa: E402
from .i18n import _  # noqa: E402
from .system import Helper, NO_PKEXEC  # noqa: E402

CSS = """
@define-color accent_bg_color #3269dc;
@define-color accent_fg_color #ffffff;
@define-color accent_color #2559c2;
window.face-window { color: #24334d;
    background: linear-gradient(135deg, #e4eefb, #f5edf7 48%, #e1f4f2); }
.face-window headerbar { background: transparent; box-shadow: none; }
.face-window .background { background-color: transparent; }
.face-window .boxed-list { border: 1px solid alpha(white, 0.95); border-radius: 22px;
    background: alpha(white, 0.62); box-shadow: 0 6px 20px alpha(#657899, 0.08); }
.face-window .boxed-list > row { border-bottom-color: alpha(#7389ac, 0.12); }
.face-window row:hover { background-color: alpha(white, 0.45); }
.face-window .subtitle, .muted { color: #596a84; opacity: 1; }
.face-window button { border-radius: 14px; transition: 180ms ease-in-out; }
.face-window button.suggested-action { background: linear-gradient(135deg, #467ce8, #4665d6);
    color: white; font-weight: 700; padding: 12px 24px;
    box-shadow: 0 5px 16px alpha(#4269ca, 0.22); }
.face-window button.suggested-action:hover { background: #527fea; }
.face-window button:focus-visible { outline: 2px solid #3269dc; outline-offset: 3px; }
.face-window switch:checked { background: #4079df; color: white; }
.hero { border-radius: 28px; border: 1px solid white; padding: 24px;
    background: linear-gradient(125deg, alpha(white, 0.85), alpha(white, 0.4));
    box-shadow: 0 8px 24px alpha(#657899, 0.08); }
.hero-title { font-size: 27px; font-weight: 800; letter-spacing: -0.6px; }
.welcome-title { font-size: 38px; font-weight: 800; letter-spacing: -1px; }
.eyebrow { color: #536fa1; font-size: 10px; font-weight: 800; letter-spacing: 2px; }
.status-chip { color: #315f82; background: alpha(white, 0.65);
    border: 1px solid white; border-radius: 20px;
    padding: 7px 14px; font-size: 11px; font-weight: 600; }
.scan-grid { border-radius: 34px;
    background: radial-gradient(ellipse at center, alpha(#8aadef, 0.32), alpha(white, 0.1) 72%); }
.scan-ring { border: 1px solid alpha(white, 0.98); border-radius: 999px;
    background: alpha(white, 0.25); box-shadow: 0 6px 24px alpha(#657899, 0.12); }
.scan-inner { border: 1px dashed alpha(#6484c4, 0.45); border-radius: 999px;
    background: alpha(white, 0.25); }
.scan-face { color: #5e81c8; }
.scan-line { background: linear-gradient(to right, transparent, #719cef, transparent);
    box-shadow: 0 0 12px alpha(#719cef, 0.4); }
.preview { border-radius: 26px; border: 1px solid white;
    background: linear-gradient(135deg, #dfebf6, #eeedf8);
    min-width: 280px; min-height: 260px; }
.preview-hint { color: #526d8a; font-size: 11px; }
.glass-dialog { background: #edf3fc; color: #24334d; border-radius: 24px;
    border: 1px solid alpha(#7389ac, 0.18); }
dialog { background: alpha(black, 0.55); }
dialog > .glass-dialog { background: #edf3fc; }
.alert-dialog, .alert-dialog .dialog-content-area, .alert-dialog .response-area {
    background: #edf3fc; color: #24334d; }
.alert-dialog .title { color: #1c2a44; }
.alert-dialog .body { color: #3c4d6a; }
"""

DARK_CSS = """
@define-color accent_bg_color #98b7ff;
@define-color accent_fg_color #152342;
@define-color accent_color #a6c1ff;
window.face-window { color: #e5eaf5;
    background: linear-gradient(135deg, #18243a, #282239 48%, #152f34); }
.face-window .boxed-list { border-color: alpha(#c4d6ff, 0.15);
    background: alpha(#243248, 0.75); box-shadow: 0 6px 20px alpha(black, 0.12); }
.face-window .boxed-list > row { border-bottom-color: alpha(#a4bbdf, 0.12); }
.face-window row:hover { background-color: alpha(white, 0.05); }
.face-window .subtitle, .face-window .muted { color: #b0bed5; }
.face-window button.suggested-action { background: linear-gradient(135deg, #a7c5ff, #b6b7fa);
    color: #172641; box-shadow: 0 5px 16px alpha(black, 0.16); }
.face-window button.suggested-action:hover { background: #c0d5ff; }
.face-window button:focus-visible { outline-color: #b1caff; }
.face-window switch:checked { background: #a6c1ff; color: #172641; }
.face-window .hero { border-color: alpha(#c4d6ff, 0.18);
    background: linear-gradient(125deg, alpha(#a5c2ee, 0.12), alpha(#a6a4e2, 0.06));
    box-shadow: 0 8px 24px alpha(black, 0.12); }
.face-window .eyebrow { color: #a5bce7; }
.face-window .status-chip { color: #bad4f6; background: alpha(#9fbeee, 0.10);
    border-color: alpha(#c4d6ff, 0.18); }
.face-window .scan-grid { background: radial-gradient(ellipse at center,
    alpha(#8aadef, 0.15), transparent 72%); }
.face-window .scan-ring { border-color: alpha(#c4d6ff, 0.35);
    background: alpha(#b1c4fa, 0.06); box-shadow: 0 6px 24px alpha(black, 0.16); }
.face-window .scan-inner { border-color: alpha(#bdc8f5, 0.4); background: alpha(white, 0.03); }
.face-window .scan-face { color: #b6cfff; }
.face-window .scan-line { background: linear-gradient(to right, transparent, #b6cfff, transparent); }
.face-window .preview { border-color: alpha(#c4d6ff, 0.25);
    background: linear-gradient(135deg, #23384b, #302f4b); }
.face-window .preview-hint { color: #adbed8; }
.face-window .glass-dialog { background: #202d43; color: #e5eaf5;
    border: 1px solid alpha(#a4bbdf, 0.22); }
dialog { background: alpha(black, 0.65); }
dialog > .glass-dialog { background: #202d43; }
.alert-dialog, .alert-dialog .dialog-content-area, .alert-dialog .response-area {
    background: #202d43; color: #e5eaf5; }
.alert-dialog .title { color: #f1f5ff; }
.alert-dialog .body { color: #c0cee5; }
"""

APPEARANCES = {
    "light": Adw.ColorScheme.FORCE_LIGHT,
    "dark": Adw.ColorScheme.FORCE_DARK,
    "system": Adw.ColorScheme.DEFAULT,
}



class Application(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.window = None
        self._authenticated = False
        self._auth_error = None
        self._hold_count = 0
        self._appearance_path = Path(GLib.get_user_config_dir()) / "face-unlock" / "appearance.json"
        try:
            appearance = json.loads(self._appearance_path.read_text()).get("appearance", "light")
        except (OSError, ValueError, AttributeError):
            appearance = "light"
        if not isinstance(appearance, str) or appearance not in APPEARANCES:
            appearance = "light"
        self._appearance = appearance
        action = Gio.SimpleAction.new_stateful("appearance", GLib.VariantType.new("s"),
                                              GLib.Variant("s", appearance))
        action.connect("activate", self._on_appearance)
        self.add_action(action)
        for name, callback, accels in (
            ("refresh", lambda *_: self.window and self.window.refresh(), ["<Control>r"]),
            ("about", self._on_about, []),
            ("quit", lambda *_: self.quit(), ["<Control>q"]),
        ):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.add_action(action)
            self.set_accels_for_action(f"app.{name}", accels)

    def do_startup(self):
        Adw.Application.do_startup(self)
        manager = self.get_style_manager()
        manager.set_color_scheme(APPEARANCES[self._appearance])
        provider = Gtk.CssProvider()
        self._css_provider = provider
        self._update_theme()
        manager.connect("notify::dark", lambda *_: self._update_theme())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def _update_theme(self):
        self._css_provider.load_from_string(
            CSS + (DARK_CSS if self.get_style_manager().get_dark() else ""))

    def _on_appearance(self, action, value):
        choice = value.get_string()
        if choice not in APPEARANCES:
            return
        try:
            self._appearance_path.parent.mkdir(parents=True, exist_ok=True)
            # GLib replaces the preference file atomically.
            GLib.file_set_contents(str(self._appearance_path),
                                   json.dumps({"appearance": choice}).encode())
        except (OSError, GLib.Error):
            if self.window:
                self.window.toast(_("Could not save your appearance preference"))
            return
        action.set_state(value)
        self._appearance = choice
        self.get_style_manager().set_color_scheme(APPEARANCES[choice])

    def do_activate(self):
        from .window import Window
        # The user must authenticate before the app reveals any state, so
        # enrollments, model lists, and camera previews are not exposed to a
        # passer-by who happens to launch the app.
        if not self._authenticated:
            self._authenticate()
            # Keep the main loop alive while pkexec runs. Without an active
            # window the loop would otherwise exit before the callback fires.
            self.hold()
            self._hold_count = 1
            return
        if self.window is None:
            self.window = Window(self)
            # Quit cleanly when the user closes the only window.
            self.window.connect("destroy", lambda *_: self._on_window_destroyed())
        self.window.present()

    def _authenticate(self):
        """Ask polkit for the user's password before opening the main window."""
        # Development mode: allow running the GUI without a password prompt.
        if NO_PKEXEC:
            self._authenticated = True
            self.do_activate()
            return
        helper = Helper()
        helper.run(["authenticate"], self._on_authenticated)

    def _release_hold(self):
        """Drop the main-loop hold acquired in do_activate."""
        if self._hold_count:
            self.release()
            self._hold_count = 0

    def _on_window_destroyed(self):
        # Closing the main window ends the session.
        self.window = None
        self.quit()

    def do_window_removed(self, window):
        # Fallback: even if our explicit "destroy" handler misses (for example
        # because the window is replaced), quit when no windows remain.
        Adw.Application.do_window_removed(self, window)
        if not self.get_windows():
            self.quit()

    def _on_authenticated(self, result):
        self._release_hold()
        if result.get("ok"):
            self._authenticated = True
            self.do_activate()
            return
        if result.get("cancelled"):
            self.quit()
            return
        self._auth_error = result.get("error") or result.get("message")
        self._show_auth_error()

    def _show_auth_error(self):
        body = _("Your password is required to open Face Unlock.")
        if self._auth_error:
            body += "\n\n" + self._auth_error
        dialog = Adw.AlertDialog(heading=_("Authentication Required"), body=body)
        dialog.add_response("close", _("Close"))
        dialog.set_default_response("close")
        dialog.set_close_response("close")
        # Keep the loop alive while the error dialog is up.
        self.hold()
        dialog.connect("response", lambda *_: (self.release(), self.quit()))
        dialog.present(None)

    def build_menu(self):
        menu = Gio.Menu()
        appearance = Gio.Menu()
        for label, value in ((_("Light"), "light"), (_("Dark"), "dark"), (_("Follow system"), "system")):
            item = Gio.MenuItem.new(label, None)
            item.set_action_and_target_value("app.appearance", GLib.Variant("s", value))
            appearance.append_item(item)
        menu.append_submenu(_("Appearance"), appearance)
        menu.append(_("Refresh"), "app.refresh")
        menu.append(_("About Face Unlock"), "app.about")
        return menu

    def _on_about(self, *args):
        about = Adw.AboutDialog(
            application_name=_("Face Unlock"),
            application_icon=APP_ID,
            developer_name="Nipun Dhananjaya",
            version=VERSION,
            comments=_("Windows Hello–style face authentication for Ubuntu, "
                       "using an RGB or infrared camera."),
            license_type=Gtk.License.MIT_X11,
            copyright="© 2026 Nipun Dhananjaya",
        )
        about.add_credit_section(_("Built on"), [
            "Howdy https://github.com/boltgolt/howdy",
            "dlib http://dlib.net",
        ])
        about.add_legal_section("Howdy", "© 2018 boltgolt", Gtk.License.MIT_X11, None)
        about.add_legal_section("dlib", "© Davis E. King", Gtk.License.CUSTOM,
                                "Boost Software License 1.0")
        about.present(self.window)


def main(argv):
    # Print-and-exit for queries that don't need a display or the GUI loop.
    for arg in argv[1:]:
        if arg in ("-h", "--help"):
            print(_("Usage: face-unlock [OPTION…]"))
            print()
            print(_("  --version           print the application version and exit"))
            print(_("  --help              print this help and exit"))
            print()
            print(_("Run without arguments to open the Face Unlock settings app."))
            return 0
        if arg in ("-V", "--version"):
            print(f"face-unlock {VERSION}")
            return 0
    return Application().run(argv)
