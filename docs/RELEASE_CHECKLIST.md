# NoraShot v0.2.0 acceptance checklist

Run this checklist **before** manually publishing the first GitHub Release.

## Automated

- [ ] GitHub Actions [Test and build NoraShot](../.github/workflows/tests.yml) succeeds on `main` (Linux/Windows, Python 3.11/3.13).
- [ ] The Windows EXE smoke check succeeds.
- [ ] `NoraShot-Windows-portable` Actions artifact contains `NoraShot.exe` and `NoraShot.exe.sha256`.

## Manual on clean Windows

- [ ] Launch portable `NoraShot.exe` without a separate Python installation.
- [ ] NoraShot starts in the tray and **Выход** shuts it down.
- [ ] Area selection (`PrintScreen`) works across dual monitors; cancel with Escape.
- [ ] Active-window (`Alt+PrintScreen`) and cursor-monitor (`Ctrl+PrintScreen`) capture work.
- [ ] The editor fits large images and maximizes normally.
- [ ] Arrow, rectangle, blur, opaque redact, and editable text render correctly.
- [ ] Move/resize/delete plus Undo/Redo work and maintain correct layer order.
- [ ] Copy-to-clipboard and local Save produce full-resolution screenshots.
- [ ] Settings persist in `%LOCALAPPDATA%\NoraShot\NoraShot\config.yaml`.
- [ ] Logs appear in `%LOCALAPPDATA%\NoraShot\NoraShot\Logs\norashot.log`.

## S3 checks (use a private test bucket and disposable keys)

- [ ] Save credentials using Settings, close and reopen settings, then upload.
- [ ] `Проверить подключение` succeeds or clearly explains permissions/TLS failures.
- [ ] Upload a redacted test screenshot, open the presigned URL, check expiration value.
- [ ] Disconnect the network, attempt upload, verify that the editor stays open and diagnosis is safe.
- [ ] Make sure S3 credentials and signed URLs do not appear in logs.
- [ ] Delete test objects and set bucket Lifecycle retention separately if needed.

## Publish

1. Make sure the workflow above succeeded and the portable executable has been manually validated.
2. Open [Publish NoraShot Windows release](../.github/workflows/release.yml) in GitHub Actions.
3. Choose **Run workflow**, branch `main`, tag `v0.2.0`, and enable **Confirm publication**.
4. The release workflow repeats tests, builds the portable EXE, smoke-tests it, creates tag `v0.2.0`, and publishes GitHub Release assets including SHA-256.
5. Download the release asset, compare its SHA-256, and install on a second Windows machine.

Note: The EXE is **unsigned** and therefore may trigger Microsoft SmartScreen.
Never include real S3 keys in logs, issue reports, test fixtures, Git commits, or public screenshots.
