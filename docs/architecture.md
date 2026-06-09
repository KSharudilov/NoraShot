# NoraShot architecture

## Goals

NoraShot should be a small and maintainable Windows screenshot tool.

Main goals:

- Fast screenshot capture
- Hotkey-driven workflow
- Simple screenshot editor
- Local save
- Clipboard copy
- Optional private upload
- Detailed logs
- GUI settings

## Modules

### UI

- Tray controller
- Settings window
- Region selector
- Screenshot editor
- History window

### Core

- Capture service
- Clipboard service
- Storage service
- Upload service
- Hotkey service
- History service

## Data locations

```text
Config:      APPDATA/NoraShot/config.yaml
Data:        APPDATA/NoraShot
Logs:        LOCALAPPDATA/NoraShot/logs
Screenshots: USERPROFILE/Pictures/NoraShot
```

## Logging policy

Every important operation must write logs:

- app startup and shutdown
- config load and save
- hotkey register or failure
- screenshot capture start and end
- save start and end
- clipboard copy
- upload start and end
- exceptions with stack trace
