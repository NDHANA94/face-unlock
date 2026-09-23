# Author: WM Nipun Dhananjaya
# Date:   24/09/2026
#
# Licensed under the MIT License. See the project LICENSE file for details.
"""System state (cameras, config, PAM) and the privileged helper client."""

import configparser
import fcntl
import json
import os
import re
import struct
from dataclasses import dataclass

from gi.repository import Gio, GLib

from .i18n import _

HELPER = os.environ.get("FACE_UNLOCK_HELPER", "/usr/libexec/face-unlock/face-unlock-helper")
# Development only: run HELPER directly (e.g. tests/mock-helper) instead of via pkexec
NO_PKEXEC = os.environ.get("FACE_UNLOCK_DEV_NO_PKEXEC") == "1"
CONFIG_FILE = os.environ.get("FACE_UNLOCK_CONFIG", "/etc/face-unlock/config.ini")
COMMON_AUTH = os.environ.get("FACE_UNLOCK_COMMON_AUTH", "/etc/pam.d/common-auth")
SYSFS_V4L = "/sys/class/video4linux"

# V4L2 ioctls and constants (linux/videodev2.h)
VIDIOC_QUERYCAP = 0x80685600
VIDIOC_ENUM_FMT = 0xC0405602
V4L2_CAP_VIDEO_CAPTURE = 0x00000001
V4L2_CAP_DEVICE_CAPS = 0x80000000
V4L2_BUF_TYPE_VIDEO_CAPTURE = 1
# Monochrome formats used by IR cameras
IR_FORMATS = {"GREY", "Y4  ", "Y6  ", "Y10 ", "Y12 ", "Y16 ", "Y10B", "Y8I ", "Y12I"}

# pkexec exit codes when the user dismisses or fails authentication
PKEXEC_NOT_AUTHORIZED = 126


@dataclass
class Camera:
    path: str       # stable path stored in the config
    node: str       # /dev/videoN
    name: str
    is_ir: bool


def _capture_formats(fd):
    formats = set()
    for index in range(32):
        buf = bytearray(struct.pack("<III32sII3I", index, V4L2_BUF_TYPE_VIDEO_CAPTURE,
                                    0, b"", 0, 0, 0, 0, 0))
        try:
            fcntl.ioctl(fd, VIDIOC_ENUM_FMT, buf)
        except OSError:
            break
        fourcc = struct.unpack_from("<I", buf, 44)[0]
        formats.add(fourcc.to_bytes(4, "little").decode("ascii", "replace"))
    return formats


def _is_capture_device(fd):
    buf = bytearray(104)
    try:
        fcntl.ioctl(fd, VIDIOC_QUERYCAP, buf)
    except OSError:
        return False
    caps, device_caps = struct.unpack_from("<II", buf, 84)
    effective = device_caps if caps & V4L2_CAP_DEVICE_CAPS else caps
    return bool(effective & V4L2_CAP_VIDEO_CAPTURE)


def _stable_paths():
    """Map /dev/videoN to its /dev/v4l/by-id (preferred) or by-path link."""
    links = {}
    for folder in ("/dev/v4l/by-path", "/dev/v4l/by-id"):  # by-id wins
        try:
            names = os.listdir(folder)
        except FileNotFoundError:
            continue
        for name in names:
            link = os.path.join(folder, name)
            links[os.path.realpath(link)] = link
    return links


def list_cameras():
    """Return capture devices, IR cameras first."""
    cameras = []
    links = _stable_paths()
    try:
        entries = os.listdir(SYSFS_V4L)
    except FileNotFoundError:
        return cameras
    for entry in sorted(entries, key=lambda e: int(re.sub(r"\D", "", e) or 0)):
        node = f"/dev/{entry}"
        try:
            with open(os.path.join(SYSFS_V4L, entry, "name")) as f:
                name = f.read().strip()
            fd = os.open(node, os.O_RDWR | os.O_NONBLOCK)
        except OSError:
            continue
        try:
            if not _is_capture_device(fd):
                continue
            formats = _capture_formats(fd)
        finally:
            os.close(fd)
        is_ir = bool(formats & IR_FORMATS) or re.search(r"\bIR\b|infrared", name, re.I) is not None
        # Names are often "<model>: <function>"; the function part reads better.
        label = name.split(":", 1)[-1].strip() or name
        # sysfs names are cut at 31 characters, which often clips "Camera"
        label = re.sub(r"\bCamer$", "Camera", label)
        cameras.append(Camera(links.get(node, node), node, label, is_ir))
    cameras.sort(key=lambda c: not c.is_ir)
    return cameras


def read_config():
    config = configparser.ConfigParser(interpolation=None)
    config.read(CONFIG_FILE)
    return config


def engine_installed():
    return os.path.exists(HELPER) and os.path.exists(CONFIG_FILE)


def face_unlock_enabled():
    try:
        with open(COMMON_AUTH) as f:
            return any("pam_howdy.so" in line and not line.lstrip().startswith("#") for line in f)
    except OSError:
        return False


class Helper:
    """Runs face-unlock-helper through pkexec without blocking the UI."""

    def run(self, args, callback):
        """Call callback(result) with the helper's JSON result.

        On a dismissed password prompt the result is {"ok": False, "cancelled": True}.
        """
        try:
            proc = Gio.Subprocess.new(
                ([] if NO_PKEXEC else ["pkexec"]) + [HELPER, *args],
                Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE)
        except GLib.Error as err:
            error = {"ok": False, "error": err.message}
            GLib.idle_add(lambda: callback(error) and False)
            return
        proc.communicate_utf8_async(None, None, self._finish, callback)

    @staticmethod
    def _finish(proc, task, callback):
        try:
            _finished, stdout, stderr = proc.communicate_utf8_finish(task)
        except GLib.Error as err:
            callback({"ok": False, "error": err.message})
            return
        status = proc.get_exit_status()
        try:
            result = json.loads(stdout.strip().splitlines()[-1])
        except (IndexError, ValueError):
            if status == PKEXEC_NOT_AUTHORIZED:
                result = {"ok": False, "cancelled": True}
            else:
                result = {"ok": False, "error": (stderr or "").strip() or _("The helper failed to run.")}
        callback(result)
