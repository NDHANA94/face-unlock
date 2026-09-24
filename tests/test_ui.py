# Author: WM Nipun Dhananjaya
# Date:   24/09/2026
#
# Licensed under the MIT License. See the project LICENSE file for details.
"""GTK workflow checks; run with FACE_UNLOCK_UI_TESTS=1 and a display."""
import os
import unittest
from unittest import mock
import configparser


@unittest.skipUnless(os.environ.get('FACE_UNLOCK_UI_TESTS') == '1', 'requires GTK display')
class CameraSetupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from face_unlock.main import Application
        cls.app = Application()
        cls.app.register(None)

    def setUp(self):
        from face_unlock import system
        from face_unlock.window import Window
        self.rgb = system.Camera('/dev/video0', '/dev/video0', 'Webcam', False)
        self.ir = system.Camera('/dev/video2', '/dev/video2', 'Infrared', True)
        self.config = configparser.ConfigParser()
        self.config.read_dict({'video': {'device_path': 'none'}})
        self.calls = []
        def run(_helper, args, callback):
            self.calls.append(args)
            callback({'ok': True, 'models': []})
        for patch in (
            mock.patch.object(system, 'engine_installed', return_value=True),
            mock.patch.object(system, 'list_cameras', return_value=[self.ir, self.rgb]),
            mock.patch.object(system, 'read_config', return_value=self.config),
            mock.patch.object(system, 'face_unlock_enabled', return_value=False),
            mock.patch.object(system.Helper, 'run', run),
        ):
            patch.start()
            self.addCleanup(patch.stop)
        self.window = Window(self.app)
        self.addCleanup(self.window.destroy)

    def test_setup_lists_both_camera_types(self):
        self.assertEqual(self.window._stack.get_visible_child_name(), 'welcome')
        self.assertEqual(self.window._cameras, [self.ir, self.rgb])
        self.assertEqual(self.window._setup_camera_row.get_model().get_n_items(), 2)

    def test_rgb_only_machine_can_reach_setup(self):
        from face_unlock import system
        with mock.patch.object(system, 'list_cameras', return_value=[self.rgb]):
            self.window.refresh()
        self.assertEqual(self.window._stack.get_visible_child_name(), 'welcome')
        self.assertEqual(self.window._cameras, [self.rgb])

    def test_setup_configures_and_enrolls_selected_rgb_camera(self):
        self.window._setup_camera_row.set_selected(1)
        with mock.patch('face_unlock.window.EnrollDialog') as dialog:
            self.window._on_setup()
        self.assertIn(['configure', 'video.device_path=/dev/video0'], self.calls)
        self.assertEqual(dialog.call_args.args[1], '/dev/video0')
        self.assertFalse(dialog.call_args.kwargs['is_ir'])

    def test_cancelled_configuration_does_not_enroll(self):
        from face_unlock import system
        with mock.patch.object(system.Helper, 'run', side_effect=lambda args, cb: cb({'cancelled': True})), \
                mock.patch('face_unlock.window.EnrollDialog') as dialog:
            self.window._on_setup()
        dialog.assert_not_called()

    def test_add_face_from_settings_configures_camera_before_dialog(self):
        self.window._load_settings()
        self.window._camera_row.set_selected(1)
        self.calls.clear()
        with mock.patch('face_unlock.window.EnrollDialog') as dialog:
            self.window._on_add_face()
        self.assertEqual(self.calls, [['configure', 'video.device_path=/dev/video0']])
        self.assertEqual(dialog.call_args.args[1], '/dev/video0')

    def test_add_face_cancelled_configuration_does_not_open_dialog(self):
        from face_unlock import system
        self.window._load_settings()
        with mock.patch.object(system.Helper, 'run', side_effect=lambda args, cb: cb({'cancelled': True})), \
                mock.patch('face_unlock.window.EnrollDialog') as dialog:
            self.window._on_add_face()
        dialog.assert_not_called()

    def test_appearance_selection_is_saved_and_applied(self):
        import json
        import tempfile
        from pathlib import Path
        from gi.repository import GLib
        with tempfile.TemporaryDirectory() as folder, \
                mock.patch.object(self.app, '_appearance_path', Path(folder) / 'appearance.json'):
            action = self.app.lookup_action('appearance')
            previous = action.get_state()
            try:
                for choice in ('dark', 'light'):
                    action.activate(GLib.Variant('s', choice))
                    self.assertEqual(self.app.get_style_manager().get_dark(), choice == 'dark')
                    self.assertEqual(json.loads(self.app._appearance_path.read_text())['appearance'], choice)
            finally:
                action.activate(previous)

    def test_unauthenticated_activate_holds_main_loop(self):
        # Without a hold, the GTK main loop exits as soon as do_activate
        # returns because no window has been presented yet.
        self.assertEqual(self.app._hold_count, 0)
        self.app.do_activate()
        self.assertGreater(self.app._hold_count, 0)
        # Releasing the hold must bring the count back to zero.
        self.app._on_authenticated({'cancelled': True})
        self.assertEqual(self.app._hold_count, 0)

    def test_password_is_sent_over_stdin(self):
        from gi.repository import Gtk
        from face_unlock import main
        entry = Gtk.PasswordEntry()
        entry.set_text('example-password')
        with mock.patch.object(main, 'Helper') as helper:
            self.app._on_password_response(None, 'open', entry)
        helper.return_value.run.assert_called_once_with(
            ['authenticate'], self.app._on_authenticated,
            input_text='example-password\n')
        self.assertEqual(entry.get_text(), '')

    def test_window_removed_quits_application(self):
        # Exercise GTK's real window removal rather than passing a fake widget.
        with mock.patch.object(self.app, 'quit') as quit:
            self.window.destroy()
            quit.assert_called_once()
