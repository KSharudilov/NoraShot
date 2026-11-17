# NoraShot 0.2.0 — First public Windows release

NoraShot is a lightweight Windows screenshot editor built with Python and PySide6.

## Highlights

- Global hotkeys: area (`PrintScreen`), active window (`Alt+PrintScreen`), monitor under cursor (`Ctrl+PrintScreen`).
- Object-based annotation editor: arrows, rectangles, text, blur, opaque redaction.
- Move and resize annotations, undo/redo and full-resolution export.
- Copy screenshots to the clipboard or save locally.
- Share screenshots to your **own private S3-compatible bucket**, with expiring signed URLs and Windows credential storage.
- Secure TLS bundle and new connection diagnostics.

## Installation

Download `NoraShot.exe` from the release assets and run it on Windows 10/11.
A separate Python installation is not required for the portable EXE.

The executable is **not code-signed**. Windows SmartScreen may display a warning; verify the SHA-256 checksum provided in `NoraShot.exe.sha256` before execution.

Your configuration and S3 keys are stored per Windows user. Sharing requires a private S3 bucket and separately created limited-access S3 credentials.

## Security notes

- Signed S3 links are bearer links: anyone who receives the URL may access the image until the link expires.
- Expiration of a link does not delete the object from S3; configure bucket Lifecycle rules separately.
- Never share a screenshot containing secrets unless it has been securely redacted.
- No central NoraShot server is deployed in this release.

## Known limitations

- Portable Windows EXE; no installer or automatic update yet.
- Windows autostart and selecting inactive application windows are not implemented.
- No code signing or notarization.
- S3 access and some permissions vary by S3-compatible provider.
