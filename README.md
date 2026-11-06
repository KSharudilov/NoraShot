# NoraShot

NoraShot — Windows screenshot utility written in Python using PySide6. Capture a screen area, the active window, or the monitor under your mouse pointer; annotate an image and copy or save the result.

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

**Not implemented yet:** the `Поделиться` button (cloud upload), a window picker for capturing any selected application, autostart implementation, and a tested production EXE/installer build. The settings window is currently a placeholder; configuration is primarily managed via YAML.

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
logs:
  level: INFO
  retention_days: 30
```

The `upload` section is **reserved for upcoming functionality**. Setting `upload.enabled: true` alone will not enable sharing. Do not place access keys or secret keys in this YAML file. S3 credentials and a secure sharing flow will be designed separately.

Some configuration options are scaffolded but not yet wired into behavior (e.g., `app.start_with_windows`, `capture.open_editor_after_capture`, clipboard preferences, and `logs.retention_days`). The current log retention is hard-coded to 30 days.

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
│   └── hotkeys.py
└── ui/
    ├── editor.py
    ├── graphics_editor.py
    ├── selector.py
    ├── tray.py
    └── settings_window.py
```

## Roadmap

1. S3-compatible private screenshot sharing via an upload action and expiring links, with credentials stored outside YAML.
2. Better settings UX and handling for upload configuration.
3. Automated tests, reproducible Windows EXE/installer packaging, and startup support.
4. Optional picker for capturing a chosen application/window.
5. Optional managed link service for revocable, longer-lived share URLs.

See [CHANGELOG.md](CHANGELOG.md) for the implementation history.

## License

MIT
