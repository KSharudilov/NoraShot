from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger
from PySide6.QtWidgets import QApplication, QMessageBox

from norashot.config import load_config
from norashot.core.capture import ScreenshotService
from norashot.core.clipboard import copy_image_to_clipboard, copy_text_to_clipboard
from norashot.core.hotkeys import HotkeyManager
from norashot.core.storage import save_image
from norashot.logging_setup import setup_logging
from norashot.ui.tray import TrayController


class NoraShotApplication:
    def __init__(self) -> None:
        self.config = load_config()
        setup_logging(self.config.logs.level)
        self.qt_app = QApplication(sys.argv)
        self.qt_app.setQuitOnLastWindowClosed(False)
        self.capture = ScreenshotService()
        self.hotkeys = HotkeyManager()
        self.tray = TrayController(
            app=self.qt_app,
            config=self.config,
            on_capture_area=self.capture_area,
            on_capture_fullscreen=self.capture_fullscreen,
            on_capture_active_window=self.capture_active_window,
        )
        self.qt_app.aboutToQuit.connect(self.shutdown)
        self.setup_hotkeys()
        logger.info("NoraShot application initialized")

    def setup_hotkeys(self) -> None:
        logger.info("Configuring screenshot hotkeys")
        self.hotkeys.register(self.config.hotkeys.area, self.capture_area)
        self.hotkeys.register(self.config.hotkeys.fullscreen, self.capture_fullscreen)
        self.hotkeys.register(self.config.hotkeys.active_window, self.capture_active_window)
        self.hotkeys.start()

    def run(self) -> int:
        self.tray.show()
        self.tray.show_message("NoraShot", "Application started")
        logger.info("NoraShot event loop started")
        return self.qt_app.exec()

    def shutdown(self) -> None:
        logger.info("NoraShot shutdown started")
        self.hotkeys.stop()
        logger.info("NoraShot shutdown completed")

    def process_image(self, image) -> None:
        saved_path: Path | None = None
        if self.config.save.enabled:
            saved_path = save_image(image, self.config.save)
        if self.config.clipboard.copy_image:
            copy_image_to_clipboard(image)
        if self.config.clipboard.copy_file_path and saved_path:
            copy_text_to_clipboard(str(saved_path))
        if saved_path:
            self.tray.show_message("NoraShot", "Screenshot saved: " + saved_path.name)
        else:
            self.tray.show_message("NoraShot", "Screenshot copied to clipboard")

    def capture_area(self) -> None:
        logger.info("Area screenshot requested")
        QMessageBox.information(None, "NoraShot", "Region selector will be added in the next stage.")
        self.capture_fullscreen()

    def capture_fullscreen(self) -> None:
        logger.info("Fullscreen screenshot requested")
        try:
            image = self.capture.capture_fullscreen()
            self.process_image(image)
        except Exception:
            logger.exception("Fullscreen screenshot failed")
            QMessageBox.critical(None, "NoraShot", "Failed to create screenshot. Check logs.")

    def capture_active_window(self) -> None:
        logger.info("Active window screenshot requested")
        try:
            image = self.capture.capture_active_window()
            if image is None:
                QMessageBox.warning(None, "NoraShot", "Could not capture active window.")
                return
            self.process_image(image)
        except Exception:
            logger.exception("Active window screenshot failed")
            QMessageBox.critical(None, "NoraShot", "Failed to capture active window. Check logs.")


def main() -> None:
    app = NoraShotApplication()
    exit_code = app.run()
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
