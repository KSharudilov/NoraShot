# NoraShot

NoraShot — Windows screenshot utility written in Python using PySide6. Capture a screen area, active window, or monitor under the cursor; annotate, copy, save, or share the result via a private S3-compatible bucket.

> **Status:** active development. The published package version is `0.1.0`, but the current `main` branch already contains improvements beyond the original MVP. These changes are not yet an installer or a formal release. The last user-tested editor snapshot is preserved in branch [`stable-editor-2026-11-06`](https://github.com/KSharudilov/NoraShot/tree/stable-editor-2026-11-06).

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

**Not implemented yet:** a managed NoraShot upload server, a window picker for selecting a non-active application, Windows autostart, and a tested production EXE/installer build. The S3 integration is new and **has not yet been verified against a live Selectel bucket on Windows**.

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

The current client sends the entire PNG in one upload. Network errors produce a user-friendly message and a log entry without keys or signed URL. There is no managed backend or centralized account storage yet; the future server adapter can implement the same `StorageProvider` contract.

Security caveat: **redact sensitive information before clicking Share**. Access to S3 keys from the Windows user session and a compromised machine remain security risks. The local upload credential is scoped by S3 permissions, not by the NoraShot application itself.

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

1. Validate private S3 sharing on Windows/Selectel; improve connectivity diagnostics, retries and credential management.
2. Expand the Settings UI and add explicit connectivity checks.
3. Automated UI tests, reproducible Windows EXE/installer packaging, and startup support.
4. Optional picker for capturing a chosen application/window.
5. Optional managed NoraShot server provider with revocable, longer-lived links.

See [CHANGELOG.md](CHANGELOG.md) for the implementation history.

## License

MIT
