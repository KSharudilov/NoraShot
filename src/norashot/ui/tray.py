from __future__ import annotations

import os
from pathlib import Path

from loguru import logger
from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QColor, QCursor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from norashot.config import NoraShotConfig
from norashot.paths import get_default_screenshot_dir
from norashot.ui.settings_window import SettingsWindow


def create_default_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor("#2d89ef"))

    painter = QPainter(pixmap)
    painter.setPen(QColor("white"))

    font = QFont("Segoe UI", 26)
    font.setBold(True)
    painter.setFont(font)

    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "N")
    painter.end()

    return QIcon(pixmap)


class TrayPopupMenu(QDialog):
    def __init__(
        self,
        on_capture_area,
        on_capture_fullscreen,
        on_capture_active_window,
        on_open_folder,
        on_open_settings,
        on_show_about,
        on_exit,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.on_capture_area = on_capture_area
        self.on_capture_fullscreen = on_capture_fullscreen
        self.on_capture_active_window = on_capture_active_window
        self.on_open_folder = on_open_folder
        self.on_open_settings = on_open_settings
        self.on_show_about = on_show_about
        self.on_exit = on_exit

        self.setWindowTitle("NoraShot")
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setMinimumWidth(300)

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        title = QLabel("NoraShot")
        title_font = QFont("Segoe UI", 10)
        title_font.setBold(True)
        title.setFont(title_font)

        layout.addWidget(title)
        layout.addWidget(self.make_button("Скриншот области", self.capture_area))
        layout.addWidget(self.make_button("Скриншот всего экрана", self.capture_fullscreen))
        layout.addWidget(self.make_button("Скриншот активного окна", self.capture_active_window))
        layout.addWidget(self.make_button("Открыть папку скриншотов", self.open_folder))
        layout.addWidget(self.make_button("Настройки", self.open_settings))
        layout.addWidget(self.make_button("О программе", self.show_about))

        bottom_layout = QHBoxLayout()
        close_button = QPushButton("Закрыть меню")
        exit_button = QPushButton("Выход из NoraShot")
        close_button.clicked.connect(self.close)
        exit_button.clicked.connect(self.exit_app)
        bottom_layout.addWidget(close_button)
        bottom_layout.addWidget(exit_button)
        layout.addLayout(bottom_layout)

        self.setLayout(layout)

    def make_button(self, text: str, callback) -> QPushButton:
        button = QPushButton(text)
        button.setMinimumHeight(30)
        button.clicked.connect(callback)
        return button

    def capture_area(self) -> None:
        self.close()
        self.on_capture_area()

    def capture_fullscreen(self) -> None:
        self.close()
        self.on_capture_fullscreen()

    def capture_active_window(self) -> None:
        self.close()
        self.on_capture_active_window()

    def open_folder(self) -> None:
        self.close()
        self.on_open_folder()

    def open_settings(self) -> None:
        self.close()
        self.on_open_settings()

    def show_about(self) -> None:
        self.close()
        self.on_show_about()

    def exit_app(self) -> None:
        self.close()
        self.on_exit()


class TrayController(QObject):
    def __init__(
        self,
        app: QApplication,
        config: NoraShotConfig,
        on_capture_area,
        on_capture_fullscreen,
        on_capture_active_window,
    ) -> None:
        super().__init__()
        self.app = app
        self.config = config
        self.on_capture_area = on_capture_area
        self.on_capture_fullscreen = on_capture_fullscreen
        self.on_capture_active_window = on_capture_active_window
        self.settings_window: SettingsWindow | None = None
        self.popup_menu: TrayPopupMenu | None = None

        self.tray = QSystemTrayIcon()
        self.tray.setIcon(create_default_icon())
        self.tray.setToolTip("NoraShot")
        self.tray.activated.connect(self.on_activated)

    def show(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("System tray is not available on this system")
            QMessageBox.warning(None, "NoraShot", "Системный трей недоступен.")
            return

        self.tray.show()
        logger.info("Tray icon shown")

    def show_message(self, title: str, message: str) -> None:
        if self.config.app.show_notifications and self.tray.isVisible():
            self.tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 3000)
            logger.info("Tray notification shown")

    def show_tray_menu(self) -> None:
        logger.info("Opening NoraShot tray menu window")
        if self.popup_menu is not None:
            self.popup_menu.close()
            self.popup_menu = None

        self.popup_menu = TrayPopupMenu(
            on_capture_area=self.on_capture_area,
            on_capture_fullscreen=self.on_capture_fullscreen,
            on_capture_active_window=self.on_capture_active_window,
            on_open_folder=self.open_screenshot_folder,
            on_open_settings=self.open_settings,
            on_show_about=self.show_about,
            on_exit=self.exit,
        )
        self.popup_menu.adjustSize()
        self.move_popup_near_cursor(self.popup_menu)
        self.popup_menu.show()
        self.popup_menu.raise_()
        self.popup_menu.activateWindow()

    def move_popup_near_cursor(self, popup: TrayPopupMenu) -> None:
        cursor_pos = QCursor.pos()
        screen = QApplication.screenAt(cursor_pos) or QApplication.primaryScreen()
        available = screen.availableGeometry()

        width = popup.width()
        height = popup.height()
        margin = 12

        x = cursor_pos.x() - width + 30
        y = cursor_pos.y() - height - margin

        if y < available.top():
            y = cursor_pos.y() + margin

        if x < available.left():
            x = available.left() + margin
        if x + width > available.right():
            x = available.right() - width - margin
        if y + height > available.bottom():
            y = available.bottom() - height - margin

        popup.move(x, y)
        logger.info("Tray menu window moved | x=" + str(x) + " | y=" + str(y))

    def open_settings(self) -> None:
        logger.info("Opening settings window")
        if self.settings_window is not None and self.settings_window.isVisible():
            self.settings_window.raise_()
            self.settings_window.activateWindow()
            return

        self.settings_window = SettingsWindow(self.config)
        self.settings_window.config_saved.connect(lambda: self.show_message("NoraShot", "Настройки сохранены"))
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def open_screenshot_folder(self) -> None:
        folder = Path(self.config.save.folder or str(get_default_screenshot_dir())).expanduser()
        folder.mkdir(parents=True, exist_ok=True)
        logger.info("Opening screenshot folder")
        os.startfile(str(folder))

    def show_about(self) -> None:
        QMessageBox.information(None, "О программе NoraShot", "NoraShot 0.1.0-dev")

    def on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        logger.info("Tray activated | reason=" + str(reason))
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.Context,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.show_tray_menu()
            return

        if reason == QSystemTrayIcon.ActivationReason.MiddleClick:
            self.open_settings()
            return

    def exit(self) -> None:
        logger.info("Exiting NoraShot from tray menu")
        self.tray.hide()
        self.app.quit()
