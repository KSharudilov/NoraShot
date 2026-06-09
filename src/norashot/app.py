from __future__ import annotations

import sys

from loguru import logger
from PySide6.QtWidgets import QApplication, QMessageBox

from norashot.config import load_config
from norashot.core.capture import Region, ScreenshotService
from norashot.core.hotkeys import HotkeyManager
from norashot.logging_setup import setup_logging
from norashot.ui.editor import ScreenshotEditor
from norashot.ui.selector import RegionSelector
from norashot.ui.tray import TrayController


class NoraShotApplication:
    def __init__(self) -> None:
        self.config = load_config()
        setup_logging(self.config.logs.level)
        self.qt_app = QApplication(sys.argv)
        self.qt_app.setQuitOnLastWindowClosed(False)
        self.capture = ScreenshotService()
        self.hotkeys = HotkeyManager()
        self.selector: RegionSelector | None = None
        self.editors: list[ScreenshotEditor] = []
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

    def open_editor(self, image) -> None:
        editor = ScreenshotEditor(image=image, save_config=self.config.save)
        editor.closed.connect(lambda: self.remove_editor(editor))
        self.editors.append(editor)
        editor.show()
        editor.raise_()
        editor.activateWindow()
        logger.info("Screenshot sent to editor")

    def remove_editor(self, editor: ScreenshotEditor) -> None:
        if editor in self.editors:
            self.editors.remove(editor)
        logger.info("Screenshot editor closed")

    def capture_area(self) -> None:
        logger.info("Area screenshot requested")
        try:
            if self.selector is not None and self.selector.isVisible():
                self.selector.raise_()
                self.selector.activateWindow()
                return

            self.selector = RegionSelector()
            self.selector.region_selected.connect(self.capture_selected_region)
            self.selector.canceled.connect(lambda: logger.info("Region selection canceled"))
            self.selector.show_selector()
        except Exception:
            logger.exception("Region selector failed")
            QMessageBox.critical(None, "NoraShot", "Failed to start region selector. Check logs.")

    def capture_selected_region(self, left: int, top: int, width: int, height: int) -> None:
        logger.info(
            "Selected region capture requested | left=" + str(left)
            + " | top=" + str(top)
            + " | width=" + str(width)
            + " | height=" + str(height)
        )
        try:
            image = self.capture.capture_region(Region(left=left, top=top, width=width, height=height))
            self.open_editor(image)
        except Exception:
            logger.exception("Selected region screenshot failed")
            QMessageBox.critical(None, "NoraShot", "Failed to capture selected region. Check logs.")

    def capture_fullscreen(self) -> None:
        logger.info("Fullscreen screenshot requested")
        try:
            image = self.capture.capture_fullscreen()
            self.open_editor(image)
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
            self.open_editor(image)
        except Exception:
            logger.exception("Active window screenshot failed")
            QMessageBox.critical(None, "NoraShot", "Failed to capture active window. Check logs.")


def main() -> None:
    app = NoraShotApplication()
    exit_code = app.run()
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
