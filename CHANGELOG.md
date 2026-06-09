# Changelog

## 0.1.0 MVP - 2026-06-09

Stable MVP release.

Implemented and verified:

- Tray application with custom menu and safe exit.
- PrintScreen: select region.
- Alt + PrintScreen: capture active window.
- Ctrl + PrintScreen: capture full screen.
- Native Windows hotkeys with RegisterHotKey and low-level keyboard hook.
- Region selector overlay with mouse selection and Escape cancel.
- Screenshot preview editor.
- Copy to clipboard and close.
- Save to disk, open folder with saved file selected, and close.
- Close without saving.
- Disabled Share button placeholder for future upload/link support.

Next milestone:

- Drawing tools in editor: arrow, rectangle, text, marker, undo.

## 0.1.0-dev

Initial project skeleton:

- Added PySide6 app
- Added tray menu
- Added settings window
- Added YAML config
- Added logging
- Added basic screenshot capture service
- Added local storage and clipboard helpers
- Added build script placeholder
