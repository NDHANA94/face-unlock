# Author: WM Nipun Dhananjaya
# Date:   24/09/2026
#
# Licensed under the MIT License. See the project LICENSE file for details.
"""Exercise the real launcher with sudo-style credentials in a root container."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


@unittest.skipUnless(os.geteuid() == 0, 'credential tests require a disposable root container')
class EngineWrapperTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        root.chmod(0o755)
        self.wrapper = root / 'python3'
        shutil.copyfile(Path(__file__).resolve().parents[1] / 'src/helper/python3', self.wrapper)
        self.wrapper.chmod(0o755)
        self.model = root / 'private-model'
        self.model.write_text('synthetic model')
        self.model.chmod(0o600)

    def launch(self, real_uid, effective_uid):
        # Change credentials only in a separate process, never in the test runner.
        bootstrap = '''
import os, subprocess, sys
os.setresuid(int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[2]))
result = subprocess.run(sys.argv[3:])
sys.exit(result.returncode)
'''
        probe = '''
import json, os, sys
print(json.dumps([os.getuid(), os.geteuid()]), flush=True)
assert '/usr/lib/face-unlock/python' in sys.path
print(open(sys.argv[1]).read())
'''
        return subprocess.run(['/usr/bin/python3', '-c', bootstrap,
                               str(real_uid), str(effective_uid), str(self.wrapper),
                               '-c', probe, str(self.model)],
                              capture_output=True, text=True, env={'PATH': '/usr/bin:/bin'})

    def test_sudo_credentials_can_read_private_model(self):
        result = self.launch(1000, 0)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout.splitlines()[0]), [1000, 0])
        self.assertIn('synthetic model', result.stdout)

    def test_root_login_credentials_still_work(self):
        result = self.launch(0, 0)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_unprivileged_launcher_cannot_read_private_model(self):
        result = self.launch(1000, 1000)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout.splitlines()[0]), [1000, 1000])
        self.assertIn('PermissionError', result.stderr)
