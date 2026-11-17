# NoraShot

NoraShot — Windows screenshot utility written in Python using PySide6. Capture a screen area, active window, or monitor under the cursor; annotate, copy, save, or share the result via a private S3-compatible bucket.

> **Status:** preparing first formal portable Windows release, `0.2.0`. Source code and release automation are present, but do not treat the build as released until CI passes and the GitHub Release is published. The last independently user-tested editor snapshot is preserved in branch [`stable-editor-2026-11-06`](https://github.com/KSharudilov/NoraShot/tree/stable-editor-2026-11-06).

## Features

- Windows tray application with a custom menu and configurable hotkeys.
- `PrintScreen`: select a region (including a virtual desktop with multiple monitors).
- `Alt + PrintScreen`: capture the foreground window.
- `Ctrl + PrintScreen`: capture the monitor currently containing the mouse cursor.
- Object-based editor with arrows, rectangles, blur, opaque black redaction, and movable editable text.
- Select, move, resize, delete, and undo/redo annotation actions (`Ctrl+Z`, `Ctrl+Y`, `Ctrl+Shift+Z`, `Delete`).
- Color and line-width controls; text font, size, and bold options.
- Fit-to-window preview, maximizable editor, and full-resolution export.
- Copy finished screenshot to clipboard; or save locally and show the saved file in Explorer.
- Detailed rotating logs for diagnosis.
- **Experimental:** private S3-compatible upload with temporary signed HTTPS links; configurable per-user S3 storage and credentials stored outside YAML.

**Not implemented yet:** a managed NoraShot upload server, a picker for non-active application windows, Windows autostart, a signed installer, and automatic updates. S3 upload and opening a presigned Selectel URL have been tested manually on Windows; the release candidate still needs CI and portable EXE validation.

## Run from source on Windows

Python 3.11+ is required.

```powershell
git clone https://github.com/KSharudilov/NoraShot.git
cd NoraShot
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m norashot
```

For an existing checkout:

```powershell
git pull
python -m pip install -e ".[dev]"
python -m norashot
```

## Configuration

NoraShot creates its YAML configuration automatically on first run:

```text
%LOCALAPPDATA%\NoraShot\NoraShot\config.yaml
```

This path uses `platformdirs` with the application and author names both set to `NoraShot`. Note the two consecutive `NoraShot` directory names.

Selected configuration keys:

```yaml
hotkeys:
  area: print_screen
  fullscreen: ctrl+print_screen
  active_window: alt+print_screen
save:
  image_format: png
clipboard:
  copy_image: true
upload:
  enabled: false
  provider: s3
  endpoint: https://s3.ru-1.storage.selcloud.ru
  bucket: ""
  public_base_url: ""
  prefix_template: "%Y/%m/%d"
  region: ru-1
  link_ttl_seconds: 86400
logs:
  level: INFO
  retention_days: 30
```

The S3 upload section now controls the **Share** button. Endpoint must use HTTPS; region and bucket must match your S3 provider. Existing configs receive defaults for new keys at runtime; save settings to persist them. Do not put access keys or secret keys into this YAML file.

Some configuration options are scaffolded but not yet wired into behavior (e.g., `app.start_with_windows`, `capture.open_editor_after_capture`, clipboard preferences, and `logs.retention_days`). The current log retention is hard-coded to 30 days.

## Private S3 sharing (experimental)

1. Create your own **private S3 bucket** and a dedicated access key restricted to that bucket. Keep anonymous/public access disabled. The client does not modify bucket policies.
2. Open NoraShot tray **Настройки** → S3 configuration. Enter HTTPS endpoint (Selectel example: `https://s3.ru-1.storage.selcloud.ru`), bucket, region, and optional date prefix.
3. Enter Access Key and Secret Key, then click **Сохранить ключи**. They go into the Windows credential vault through `keyring`, not into `config.yaml`. The application does not display saved keys again.
4. Tick **Разрешить кнопку «Поделиться»** and click **Сохранить настройки**. Existing open editors refer to the current configuration; reopening the editor is recommended after settings changes.
5. Capture a screenshot, annotate it, then click **Поделиться**. The finished PNG uploads asynchronously; the generated SigV4 link is copied to the clipboard on success. The editor stays open after an error.

Default link expiration is **24 hours** (configurable from 1 to 168 hours). This does **not** delete the uploaded file. Configure an **S3 bucket lifecycle rule** for automatic cleanup if desired. Anyone possessing an unexpired presigned URL can view the uploaded image. A new URL can be issued only while the application has credentials; no long-lived public link is generated.

The current client sends the entire PNG in one upload. S3 failures are categorized (TLS, DNS/endpoint, timeout, S3 permissions) with sanitized logs: signed URLs and keys must not be logged. The Settings window includes a background **Проверить подключение** operation. A 403 from a read-only bucket check does **not** prove uploads will fail: restricted credentials may allow PutObject but prohibit HeadBucket. There is no managed backend or centralized account storage yet; the future server adapter can implement the same `StorageProvider` contract.

Security caveat: **redact sensitive information before clicking Share**. Access to S3 keys from the Windows user session and a compromised machine remain security risks. The local upload credential is scoped by S3 permissions, not by the NoraShot application itself.

## Automated tests and portable Windows EXE

All pushes to `main` and pull requests run [Test and build NoraShot](.github/workflows/tests.yml):
Python 3.11 and 3.13 on Windows/Linux, offline S3-mock tests, offscreen Qt editor regressions, source package smoke, and a PyInstaller Windows EXE. When all checks pass, the EXE and its SHA-256 checksum are available as the `NoraShot-Windows-portable` Actions artifact (retained 30 days).

To test and build locally on Windows:

```powershell
python -m pip install -e ".[dev]"
python -m pytest -q
python -m norashot --self-test
.\\scripts\\build_exe.ps1 -SkipInstall
```

Output is `dist/NoraShot.exe` and `dist/NoraShot.exe.sha256`. The EXE is portable and does not require Python on the target computer. It is not yet digitally signed.

### Publishing a formal release

After CI tests pass and a human verifies the EXE on Windows, open [GitHub Actions](https://github.com/KSharudilov/NoraShot/actions/workflows/release.yml), choose **Run workflow** from `main`, use tag `v0.2.0`, and check **Confirm publication**. The release workflow repeats the Windows tests, builds and smoke-tests the EXE, and creates a GitHub Release including the binary, checksum and [release notes](RELEASE_NOTES.md). It refuses a version mismatch or any failed check. Do not click publish before the portable binary has been tested.

## Logs

The actual current Windows log file location is:

```text
%LOCALAPPDATA%\NoraShot\NoraShot\Logs\norashot.log
```

For example: `C:\Users\<username>\AppData\Local\NoraShot\NoraShot\Logs\norashot.log`.

The log is rotated at 10 MB, archived with ZIP compression, and retained for 30 days by the current implementation. Log paths, capture events, and annotation actions are recorded; credentials should never be logged.

## Code layout

```text
src/norashot/
├── app.py
├── __main__.py
├── config.py
├── paths.py
├── logging_setup.py
├── core/
│   ├── capture.py
│   ├── clipboard.py
│   ├── storage.py
│   ├── hotkeys.py
│   └── sharing/
│       ├── base.py
│       ├── credentials.py
│       ├── manager.py
│       ├── s3.py
│       └── worker.py
└── ui/
    ├── editor.py
    ├── graphics_editor.py
    ├── selector.py
    ├── tray.py
    └── settings_window.py
```

## Roadmap

1. Verify release candidate EXE on Windows, finish CI and publish v0.2.0.
2. Improve retry policies, credential rotation and S3 provider integration tests.
3. Build a signed Windows installer, autostart support and automatic updates.
4. Optional picker for capturing a chosen application/window.
5. Optional managed NoraShot server provider with revocable, longer-lived links.

See [CHANGELOG.md](CHANGELOG.md) for the implementation history.

## License

MIT
