# Implementation checkpoint — 2026-09-23

The recovered project already contained a GTK settings app, privileged helper,
Howdy/dlib engine packaging, pinned vendor downloads, a compiled dlib wheel,
and 20 helper tests. There was no Git history or implementation handoff. The
first package build had not been completed; RGB cameras were filtered out.

Completed in this continuation:

- Exposed RGB and IR cameras in setup and settings, retaining IR-first ordering.
- Added first-run camera selection and carried the selected device into enrollment.
- Updated preview status, errors, and app descriptions for both camera types.
- Added four GTK workflow regression checks, including RGB-only machines and
  cancellation of camera configuration authorization.
- Fixed the build script executable bit and explicit container working/output
  directories. Built `dist/face-unlock_1.0.0_amd64.deb` using the cached Ubuntu
  build image with a writable `/build` tmpfs. A full Dockerfile rebuild was
  cancelled during dependency installation; that fresh-image path is unverified.
- Made UI snapshots use a mock camera, resolve the app icon, and fail promptly
  if the display cannot render a frame. Added build and setup documentation.

Fresh verification:

- `FACE_UNLOCK_UI_TESTS=1 GDK_BACKEND=broadway BROADWAY_DISPLAY=:17 make test`:
  24 tests passed.
- Python compilation and shell syntax checks passed.
- Welcome, settings, and enrollment screenshots rendered on X11 with mock state;
  welcome and enrollment layouts were visually inspected.
- Debian package built successfully (Ubuntu 26.04, amd64, Python 3.14).
- Disposable-container installation imported dlib, OpenCV, and NumPy, listed
  models, enabled PAM face authentication, verified `pam_unix.so` remained in
  the stack, disabled face authentication, and purged the package successfully.

Remaining validation and limitations:

- No host installation, face enrollment, real recognition, login, or screen-unlock
  test was performed. Those are the next manual acceptance steps in README.md.
- Other distributions, display managers, and hardware are not validated.
- This implements a Windows Hello-style interaction using Howdy/PAM, not Windows
  Hello's hardware-backed authentication or guaranteed anti-spoofing.
- Lintian reports embedded libjpeg/libpng/zlib in the existing dlib wheel, an
  AppStream warning (no homepage supplied), and a missing manual page. The package
  is locally buildable/installable but is not distribution-lint clean.
- Purge removed config/model directories in the container, but imported Python
  bytecode left a residual engine directory. No face data was created in testing.

## Enrollment fix — version 1.0.1

The installed configuration was still `device_path = none`. The settings-page
Add Face path opened enrollment without saving its displayed fallback camera.
The engine returned code 14 for the absent camera, but the helper displayed a
generic scan failure. Reproduced engine initialization with temporary paths and
no camera access; added three regression checks that failed before the fix.

All enrollment entry points now persist the selected camera before opening the
scan dialog and stop if configuration is cancelled or fails. Missing-camera
errors are mapped explicitly; other engine diagnostics are shown in the dialog.
All 27 helper/GTK tests pass. Install the 1.0.1 package and restart the app before
retrying enrollment. Real face enrollment remains a user acceptance check.

## sudo authentication fix — version 1.0.2

Reproduced the reported PermissionError using a synthetic root-only file and
sudo-style credentials (real UID 1000, effective UID 0) in a disposable container.
The engine's `/bin/sh` wrapper dropped its effective UID to 1000. It now uses
`/bin/sh -p` to preserve the privileges PAM already supplies. No model permissions
are widened, and the launcher does not grant privileges to ordinary callers.

Three credential regression tests pass: sudo-style access, all-root login access,
and denial of unprivileged access. The existing 27 helper/GTK checks also pass.
A checked-in build patch fixes upstream's unknown-error string pointer arithmetic
so numeric engine exit codes are displayed correctly. Install 1.0.2 and test
`sudo -k` followed by `sudo true`; existing enrolled faces are retained.

## Glass UI redesign — version 1.1.0

Added light and dark glass-style palettes, a saved Light/Dark/Follow system menu,
rounded translucent cards, a status dashboard, and animated enrollment guides.
The default is light. Preferences are stored per user under
`$XDG_CONFIG_HOME/face-unlock/appearance.json` (normally `~/.config`).

Verification: 28 helper/GTK tests passed (three root-only credential tests were
skipped in the host run); theme switching and saving were exercised. Rendered
welcome, dashboard, enrollment, scanning and compact layouts in both palettes.
Confirmed scan motion changes over time, stops when hidden, and remains static
when GTK animations are disabled. Built `dist/face-unlock_1.1.0_amd64.deb`.
Existing package lint findings remain unchanged. Authentication and face models
were not modified by this visual update. Glass is drawn inside the application;
this does not depend on compositor-specific desktop background blur.

## Startup authorization fix — version 1.1.1

Host logs showed startup `list` selecting the management authorization prompt.
The policy had a generic helper-path action overlapping its command-specific
read-only actions. Replaced that catch-all with explicit rules for each mutation;
list/verify retain password-free access only for an active local session.
Management operations still require administrator authorization.

The enabled PAM module also attempted recognition with an unavailable camera,
then polkit's password conversation failed. Added a native preflight that returns
PAM_AUTHINFO_UNAVAIL quietly when the configured device is unset, absent or not a
character device, allowing the remaining authentication stack to proceed.

Verification: policy regression checks failed before the fix and passed after it;
31 helper/policy/GTK tests passed, with three root-only tests skipped on the host.
The native preflight probe failed against the 1.1.0 package and passed against the
newly compiled module (unset/missing/invalid camera, present character device,
and absent face model). Built 1.1.1 successfully; prior lint findings remain.
The desktop authentication prompt needs confirmation after installing the update.
No host PAM or face-model state was changed during this fix.

Native preflight test (disposable root build container only): compile
`tests/pam-preflight.cc` against the staged `pam_howdy.so` and `-lINIReader`, with
an rpath to the module's directory. The test creates a synthetic model under the
package's model directory, so never run it against a live host setup.
