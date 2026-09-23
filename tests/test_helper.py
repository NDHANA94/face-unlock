# Author: WM Nipun Dhananjaya
# Date:   24/09/2026
#
# Licensed under the MIT License. See the project LICENSE file for details.
"""Tests for the privileged helper's validation and config editing."""

import importlib.machinery
import importlib.util
import json
import os
import pwd
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HELPER_PATH = Path(__file__).resolve().parent.parent / "src" / "helper" / "face-unlock-helper"


def load_helper():
    loader = importlib.machinery.SourceFileLoader("face_unlock_helper", str(HELPER_PATH))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


helper = load_helper()

SAMPLE_INI = """# Howdy config file

[core]
# Print that face detection is being attempted
detection_notice = false
abort_if_ssh = true

[video]
# The certainty
certainty = 3.5
timeout = 4
device_path = none
"""


class IniSetTests(unittest.TestCase):
    def test_replaces_value_and_keeps_comments(self):
        out = helper.ini_set(SAMPLE_INI, "video", "certainty", "2.8")
        self.assertIn("certainty = 2.8\n", out)
        self.assertIn("# The certainty\n", out)
        self.assertEqual(out.count("certainty ="), 1)

    def test_only_touches_the_named_section(self):
        text = "[a]\nkey = 1\n[b]\nkey = 2\n"
        self.assertEqual(helper.ini_set(text, "b", "key", "9"), "[a]\nkey = 1\n[b]\nkey = 9\n")

    def test_adds_missing_key_to_existing_section(self):
        out = helper.ini_set(SAMPLE_INI, "core", "no_confirmation", "true")
        self.assertIn("[core]\nno_confirmation = true\n", out)

    def test_adds_missing_section(self):
        out = helper.ini_set("[core]\nx = 1", "video", "timeout", "5")
        self.assertTrue(out.endswith("[video]\ntimeout = 5\n"))

    def test_key_prefix_is_not_matched(self):
        text = "[video]\ntimeout_notice = true\ntimeout = 4\n"
        out = helper.ini_set(text, "video", "timeout", "7")
        self.assertIn("timeout_notice = true", out)
        self.assertIn("timeout = 7", out)


class ValidationTests(unittest.TestCase):
    def test_numbers_are_range_checked(self):
        check = helper.SETTINGS["video.certainty"]
        self.assertEqual(check("3.5"), "3.5")
        for bad in ("0.5", "7", "nan", "abc", "3.5\nx = y"):
            with self.subTest(bad=bad), self.assertRaises(helper.HelperError):
                check(bad)

    def test_timeout_is_integer(self):
        check = helper.SETTINGS["video.timeout"]
        self.assertEqual(check("5"), "5")
        with self.assertRaises(helper.HelperError):
            check("5.5")

    def test_booleans(self):
        check = helper.SETTINGS["core.abort_if_ssh"]
        self.assertEqual(check("false"), "false")
        with self.assertRaises(helper.HelperError):
            check("yes")

    def test_device_path_rejects_non_video_paths(self):
        check = helper.SETTINGS["video.device_path"]
        for bad in ("/etc/shadow", "/dev/video0/../../etc/passwd", "/dev/v4l/by-id/../x",
                    "/dev/video0\n[core]", "none", "/dev/sda"):
            with self.subTest(bad=bad), self.assertRaises((helper.HelperError, OSError)):
                check(bad)


class CallingUserTests(unittest.TestCase):
    def test_uses_pkexec_uid(self):
        me = pwd.getpwuid(os.getuid())
        if me.pw_uid == 0:
            self.skipTest("needs a non-root account")
        with mock.patch.dict(os.environ, {"PKEXEC_UID": str(me.pw_uid)}):
            argv = ["--user", "someone-else", "list"]
            self.assertEqual(helper.calling_user(argv), me.pw_name)

    def test_refuses_root(self):
        with mock.patch.dict(os.environ, {"PKEXEC_UID": "0"}):
            with self.assertRaises(helper.HelperError):
                helper.calling_user(["list"])

    def test_user_flag_needs_root(self):
        env = {k: v for k, v in os.environ.items() if k != "PKEXEC_UID"}
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(helper.os, "getuid", return_value=1000):
            with self.assertRaises(helper.HelperError):
                helper.calling_user(["--user", "someone", "list"])


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config = os.path.join(self.tmp.name, "config.ini")
        Path(self.config).write_text(SAMPLE_INI)
        patches = [
            mock.patch.object(helper, "CONFIG_FILE", self.config),
            mock.patch.object(helper, "MODELS_DIR", self.tmp.name),
            mock.patch.object(helper.syslog, "syslog"),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def test_configure_writes_whitelisted_settings(self):
        result = helper.cmd_configure("alice", ["video.certainty=2.8", "core.abort_if_ssh=false"])
        self.assertTrue(result["ok"])
        text = Path(self.config).read_text()
        self.assertIn("certainty = 2.8", text)
        self.assertIn("abort_if_ssh = false", text)
        self.assertEqual(os.stat(self.config).st_mode & 0o777, 0o644)

    def test_configure_rejects_unknown_keys(self):
        for arg in ("core.disabled=true", "video.recording_plugin=ffmpeg", "certainty"):
            with self.subTest(arg=arg), self.assertRaises(helper.HelperError):
                helper.cmd_configure("alice", [arg])
        self.assertEqual(Path(self.config).read_text(), SAMPLE_INI)

    def test_configure_is_all_or_nothing(self):
        with self.assertRaises(helper.HelperError):
            helper.cmd_configure("alice", ["video.timeout=5", "video.certainty=99"])
        self.assertEqual(Path(self.config).read_text(), SAMPLE_INI)

    def test_list_hides_encodings(self):
        models = [{"id": 0, "label": "Me", "time": 1, "data": [[0.1] * 128]}]
        Path(self.tmp.name, "alice.dat").write_text(json.dumps(models))
        self.assertEqual(helper.cmd_list("alice", [])["models"],
                         [{"id": 0, "label": "Me", "time": 1}])

    def test_list_without_models(self):
        self.assertEqual(helper.cmd_list("bob", []), {"ok": True, "models": []})

    def test_enroll_validates_label(self):
        for label in ("", "a" * 25, "bad,label", "line\nbreak"):
            with self.subTest(label=label), self.assertRaises(helper.HelperError):
                helper.cmd_enroll("alice", [label])

    def test_enroll_reports_missing_camera(self):
        result = mock.Mock(returncode=14, stdout='Howdy could not find a camera device', stderr='')
        with mock.patch.object(helper, 'howdy_cli', return_value=result):
            response = helper.cmd_enroll('alice', ['My Face'])
        self.assertFalse(response['ok'])
        self.assertIn('camera', response['message'])
        self.assertNotEqual(response['message'], 'The face scan failed.')

    def test_remove_needs_existing_numeric_id(self):
        for arg in ("x", "-1", "5"):
            with self.subTest(arg=arg), self.assertRaises(helper.HelperError):
                helper.cmd_remove("alice", [arg])

    def test_verify_without_models_skips_engine(self):
        with mock.patch.object(helper, "run_engine") as engine:
            result = helper.cmd_verify("alice", [])
        engine.assert_not_called()
        self.assertEqual(result["code"], 10)


if __name__ == "__main__":
    unittest.main()
