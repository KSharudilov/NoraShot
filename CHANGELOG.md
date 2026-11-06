# Changelog

## Next milestones (planned)

- Choose a specific application/window from a list and capture it even if it is not foreground.
- Prefer distinct windows over process names when applications have multiple windows.
- Add user-facing window titles and preview to the window picker.
- Continue editor improvements: safe opaque redaction and text font controls (implemented; pending Windows validation).
- Regression-test multi-monitor capture, DPI scaling and screen coordinate mapping.

## Unreleased (after 0.1.0 MVP)

- Text font family, size and bold controls with undo/redo per text object.
- Editable opaque black redaction rectangles for sensitive information.
- Preserved tested editor baseline on branch `stable-editor-2026-11-06`.
- Next release work: build reproducible Windows EXE, startup toggle and automated UI checks.
- Editable text annotations with double-click editing and multiline text.
- Per-object color and line-width settings with Undo/Redo.
- Two-row toolbar for smaller editor windows.
- Editable arrow, rectangle and blur annotations.
- Undo/redo for create, move, resize and delete.
- Clicking an existing object in drawing mode switches to select/move.
- Fit screenshots into the editor viewport while keeping native export resolution.
- Enable standard Windows maximize/minimize buttons on the editor.
- Full-screen capture defaults to the display under the mouse pointer.

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
