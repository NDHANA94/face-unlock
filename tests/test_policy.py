# Author: WM Nipun Dhananjaya
# Date:   24/09/2026
#
# Licensed under the MIT License. See the project LICENSE file for details.
"""Ensure read-only startup never overlaps a management authorization rule."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / 'data/io.github.faceunlock.policy'
HELPER = '/usr/libexec/face-unlock/face-unlock-helper'
PREFIX = 'org.freedesktop.policykit.exec.'


class PolicyTests(unittest.TestCase):
    def matches(self, command):
        matches = []
        for action in ET.parse(POLICY).getroot().findall('action'):
            annotations = {item.get('key'): item.text for item in action.findall('annotate')}
            if annotations.get(PREFIX + 'path') == HELPER and annotations.get(PREFIX + 'argv1', command) == command:
                matches.append(action)
        return matches

    def test_readonly_commands_have_exactly_one_password_free_rule(self):
        for command in ('list', 'verify'):
            with self.subTest(command=command):
                matches = self.matches(command)
                self.assertEqual(len(matches), 1)
                self.assertEqual(matches[0].findtext('defaults/allow_active'), 'yes')
                self.assertEqual(matches[0].findtext('defaults/allow_inactive'), 'no')
                self.assertEqual(matches[0].findtext('defaults/allow_any'), 'no')

    def test_mutations_require_admin_authentication(self):
        for command in ('enroll', 'remove', 'clear', 'enable', 'disable', 'configure'):
            with self.subTest(command=command):
                matches = self.matches(command)
                self.assertEqual(len(matches), 1)
                self.assertEqual(matches[0].findtext('defaults/allow_active'), 'auth_admin_keep')

    def test_app_launch_delegates_authentication_to_password_checker(self):
        matches = self.matches('authenticate')
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].findtext('defaults/allow_active'), 'yes')
        self.assertEqual(matches[0].findtext('defaults/allow_inactive'), 'no')
        self.assertEqual(matches[0].findtext('defaults/allow_any'), 'no')

    def test_password_service_uses_normal_pam_stack(self):
        service = (ROOT / 'data/pam-password').read_text()
        self.assertIn('@include common-auth', service)
        self.assertIn('@include common-account', service)
        profile = (ROOT / 'data/pam-config').read_text()
        self.assertTrue(profile.startswith('Name: Face Unlock'))

    def test_unknown_commands_have_no_custom_grant(self):
        self.assertEqual(self.matches('unknown'), [])
