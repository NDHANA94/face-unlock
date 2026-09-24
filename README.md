# Face Unlock

A Linux face authentication app with a Windows Hello-style setup flow. Select an
RGB webcam or infrared camera, enroll your face, and enable authentication through
PAM for login, screen unlock, sudo, and other PAM-based administrator prompts.
Passwords remain available as a fallback. Face models are stored locally.

The current package targets **Ubuntu 26.04 amd64 with Python 3.14**. Other Linux
distributions need their own packaging and PAM integration; they are not yet
validated. The appearance and timing of login prompts belong to your display
manager, so this does not replace the Linux login screen with Windows Hello UI.
Howdy/dlib recognition does not provide Windows Hello's hardware-backed security
or guaranteed liveness detection. RGB cameras need suitable lighting.

## Build

With Docker installed and accessible to your user:

```sh
make deb
```

The build verifies pinned vendor sources, compiles the engine and PAM module,
runs helper tests, and produces `dist/face-unlock-ubuntu26.04-amd64-1.2.3.deb`. The first build
needs network access and can take several minutes. A cached dlib wheel must match
the target Python version and architecture. `make deb-host` is also available
when all build dependencies are installed on the host.

## Install and set up

```sh
sudo apt install ./dist/face-unlock-ubuntu26.04-amd64-1.2.3.deb
face-unlock
```

1. Select your camera. IR cameras are listed first; RGB cameras also work.
2. Choose **Set Up Face Unlock**, authorize the change, and scan your face.
3. Use **Test Recognition** before trying the lock screen.
4. Keep your password available and test screen unlock before relying on login.

Installation registers a disabled PAM profile. Successful initial enrollment
requests activation. The Face Unlock switch controls activation system-wide;
face models belong to individual users. Accounts without a model use passwords.
Opening the settings app asks for your account password and uses system PAM
authentication with Face Unlock excluded, even when face unlock is enabled. An administrator password may also be required to change settings
or enroll faces.

To remove the app, run `sudo apt remove face-unlock`; the package removes its PAM
profile first. `sudo apt purge face-unlock` also deletes settings and face models.
The older scripts under `legacy/` are retained for reference and are not part of
the packaged installation.

## Appearance

Open the top-right menu and choose **Appearance → Light, Dark, or Follow system**.
The app remembers your choice. Both themes use glass-style cards and an animated
face guide. Animations pause when hidden and respect GTK's reduced-motion setting.
Camera preview capture pauses when its view is hidden or the app loses focus.
The scan graphic is decorative, not a face-tracking overlay or progress estimate.

## Development checks

```sh
make test
# With an available GTK display:
FACE_UNLOCK_UI_TESTS=1 make test
python3 scripts/ui-snapshot.py /tmp/face-unlock-snapshots
```

UI workflow tests and snapshots use mock helper calls and camera entries; they do
not enroll faces or change system authentication. The helper tests run without
root. Real camera recognition and login require an installed package and manual
enrollment. Headless GTK workflow tests can use `gtk4-broadwayd :5` with
`GDK_BACKEND=broadway BROADWAY_DISPLAY=:5`; rendering screenshots on Broadway
additionally requires a connected browser.
