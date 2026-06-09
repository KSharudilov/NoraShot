# NoraShot

NoraShot is a Windows screenshot utility with hotkeys, tray menu, configurable settings, local saving, clipboard support, and planned private S3-compatible upload support.

## Current status

Version `0.1.0-dev` is the first application skeleton.

Implemented:

- PySide6 desktop application
- Windows tray menu
- Settings window
- YAML config stored in `%APPDATA%\NoraShot\config.yaml`
- Detailed logging to `%LOCALAPPDATA%\NoraShot\logs\norashot.log`
- Basic screenshot service
- Local screenshot saving
- Clipboard image copy
- Placeholder actions for region, fullscreen, active window screenshots
- Project structure ready for GitHub

Planned:

- Global hotkeys
- Region selector overlay
- Screenshot editor
- Screenshot history
- S3 / Selectel / MinIO upload
- Windows installer
- GitHub Actions release build

## Development run

```powershell
cd NoraShot
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
python -m norashot
```

## Build EXE

```powershell
.\scripts\build_exe.ps1
```

## Project layout

```text
src/norashot/
├─ app.py
├─ __main__.py
├─ config.py
├─ paths.py
├─ logging_setup.py
├─ core/
│  ├─ capture.py
│  ├─ clipboard.py
│  ├─ storage.py
│  └─ hotkeys.py
└─ ui/
   ├─ tray.py
   └─ settings_window.py
```

## Logging

Logs are written to:

```text
%LOCALAPPDATA%\NoraShot\logs\norashot.log
```

## License

MIT
