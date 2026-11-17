"""Application entry point and headless-friendly packaging smoke check."""
from __future__ import annotations

import sys


def main() -> None:
    from norashot import __version__

    if "--version" in sys.argv:
        if sys.stdout is not None:
            print(f"NoraShot {__version__}")
        return

    if "--self-test" in sys.argv:
        # Packaging smoke check with no hotkey registration, S3 network or account access.
        import boto3
        import certifi
        import keyring
        import mss
        from PIL import Image
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QImage
        from norashot.core.sharing.diagnostics import classify_s3_error
        from norashot.ui.editor import ScreenshotEditor
        from norashot import app
        from norashot.logging_setup import setup_logging
        from loguru import logger

        # Exercise the actual startup logging path in a frozen --windowed build.
        # PyInstaller runw.exe provides sys.stderr=None (no attached terminal).
        log_file = setup_logging("INFO", 30)
        logger.info("Portable EXE self-test | log_file={}", log_file)
        logger.complete()
        assert log_file.is_file()
        assert certifi.where()
        assert QImage(2, 2, QImage.Format.Format_RGB32).width() == 2
        assert Image.new("RGB", (2, 2)).size == (2, 2)
        assert callable(classify_s3_error)
        assert callable(app.main)
        if sys.stdout is not None:
            print(f"NoraShot {__version__}: self-test OK")
        return

    from norashot.app import main as run_app
    run_app()


if __name__ == "__main__":
    main()
