from __future__ import annotations

import os
from pathlib import Path

from loguru import logger
from PySide6.QtCore import QObject
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from norashot.config import NoraShotConfig
from norashot.paths import get_default_screenshot_dir
from norashot.ui.settings_window import SettingsWindow


class TrayController(QObject):
    def __init__(self, app: QApplication, config: NoraShotConfig, on_capture_area, on_capture_fullscreen, on_capture_active_window) -> None:
        super().__init__()
        self.app = app
        self.config = config
        self.on_capture_area = on_capture_area
        self.on_capture_fullscreen = on_capture_fullscreen
        self.on_capture_active_window = on_capture_active_window
        self.settings_window = None
        self.tray = QSystemTrayIcon()
        self.tray.setIcon(QIcon())
        self.tray.setToolTip("NoraShot")
        self.menu = QMenu()
        self.build_menu()
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self.on_activated)

    def build_menu(self) -> None:
        action_area = QAction("Region screenshot")
        action_fullscreen = QAction("Fullscreen screenshot")
        action_active_window = QAction("Active window screenshot")
        action_open_folder = QAction("Open screenshots folder")
        action_settings = QAction("Settings")
        action_about = QAction("About")
        action_exit = QAction("Exit")
        action_area.triggered.connect(self.on_capture_area)
        action_fullscreen.triggered.connect(self.on_capture_fullscreen)
        action_active_window.triggered.connect(self.on_capture_active_window)
        action_open_folder.triggered.connect(self.open_screenshot_folder)
        action_settings.triggered.connect(self.open_settings)
        action_about.triggered.connect(self.show_about)
        action_exit.triggered.connect(self.exit)
        self.menu.addAction(action_area)
        self.menu.addAction(action_fullscreen)
        self.menu.addAction(action_active_window)
        self.menu.addSeparator()
        self.menu.addAction(action_open_folder)
        self.menu.addAction(action_settings)
        self.menu.addSeparator()
        self.menu.addAction(action_about)
        self.menu.addAction(action_exit)

    def show(self) -> None:
        self.tray.show()
        logger.info("Tray icon shown")

    def show_message(self, title: str, message: str) -> None:
        if self.config.app.show_notifications:
            self.tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 3000)
            logger.info("Tray notification shown")

    def open_settings(self) -> None:
        logger.info("Opening settings window")
        self.settings_window = SettingsWindow(self.config)
        self.settings_window.config_saved.connect(lambda: self.show_message("NoraShot", "Settings saved"))
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def open_screenshot_folder(self) -> None:
        folder = Path(self.config.save.folder or str(get_default_screenshot_dir())).expanduser()
        folder.mkdir(parents=True, exist_ok=True)
        logger.info("Opening screenshot folder")
        os.startfile(str(folder))

    def show_about(self) -> None:
        QMessageBox.information(None, "About NoraShot", "NoraShot 0.1.0-dev")

    def on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.open_settings()

    def exit(self) -> None:
        logger.info("Exiting NoraShot from tray menu")
        self.tray.hide()
        self.app.quit()
