from __future__ import annotations

import os
import subprocess
from pathlib import Path

from loguru import logger
from PIL import Image
from PySide6.QtCore import Signal
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from norashot.config import SaveConfig
from norashot.core.clipboard import copy_image_to_clipboard
from norashot.core.storage import save_image
from norashot.ui.graphics_editor import ScreenshotCanvas


class ScreenshotEditor(QDialog):
    closed = Signal()

    def __init__(self, image: Image.Image, save_config: SaveConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.save_config = save_config
        self.saved_path: Path | None = None

        self.setWindowTitle("NoraShot")
        self.setMinimumSize(900, 600)
        self.resize(1100, 760)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        tools_layout = QHBoxLayout()
        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)
        self.canvas = ScreenshotCanvas(image=image)

        for label, tool in (
            ("Выбрать / переместить", "select"),
            ("Стрелка", "arrow"),
            ("Прямоугольник", "rectangle"),
            ("Размытие", "blur"),
        ):
            button = QPushButton(label)
            button.setCheckable(True)
            button.setMinimumHeight(30)
            button.setChecked(tool == "select")
            button.clicked.connect(lambda checked, name=tool: self.select_tool(name))
            self.tool_group.addButton(button)
            tools_layout.addWidget(button)
            if tool == "select":
                self.select_button = button
            if tool == "arrow":
                self.arrow_button = button
            if tool == "rectangle":
                self.rectangle_button = button

        tools_layout.addStretch(1)
        undo_button = QPushButton("↶ Отменить")
        redo_button = QPushButton("↷ Повторить")
        undo_button.setMinimumHeight(30)
        redo_button.setMinimumHeight(30)
        undo_button.setEnabled(False)
        redo_button.setEnabled(False)
        undo_button.clicked.connect(self.canvas.history.undo)
        redo_button.clicked.connect(self.canvas.history.redo)
        self.canvas.history.canUndoChanged.connect(undo_button.setEnabled)
        self.canvas.history.canRedoChanged.connect(redo_button.setEnabled)
        tools_layout.addWidget(undo_button)
        tools_layout.addWidget(redo_button)
        self.undo_button = undo_button
        self.redo_button = redo_button

        for sequence, callback in (
            ("Ctrl+Z", self.canvas.history.undo),
            ("Ctrl+Y", self.canvas.history.redo),
            ("Ctrl+Shift+Z", self.canvas.history.redo),
            ("Delete", self.canvas.delete_selected),
        ):
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.activated.connect(callback)

        main_layout.addLayout(tools_layout)
        main_layout.addWidget(self.canvas, 1)

        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch(1)

        copy_button = QPushButton("Копировать")
        save_button = QPushButton("Сохранить")
        share_button = QPushButton("Поделиться")
        close_button = QPushButton("Закрыть")

        for button in (copy_button, save_button, share_button, close_button):
            button.setMinimumHeight(34)

        share_button.setEnabled(False)
        share_button.setToolTip("Загрузка в облако будет добавлена позже")
        copy_button.clicked.connect(self.copy_to_clipboard)
        save_button.clicked.connect(self.save_to_disk)
        close_button.clicked.connect(self.close)

        for button in (copy_button, save_button, share_button, close_button):
            bottom_layout.addWidget(button)

        main_layout.addLayout(bottom_layout)
        logger.info("Object screenshot editor opened | width={} | height={}", image.width, image.height)

    def select_tool(self, tool: str) -> None:
        self.canvas.set_tool(tool)

    def current_image(self) -> Image.Image:
        return self.canvas.render_image()

    def copy_to_clipboard(self) -> None:
        try:
            copy_image_to_clipboard(self.current_image())
            logger.info("Screenshot copied from object editor, closing editor")
            self.close()
        except Exception:
            logger.exception("Failed to copy screenshot from object editor")
            QMessageBox.critical(self, "NoraShot", "Не удалось скопировать скриншот в буфер.")

    def save_to_disk(self) -> None:
        try:
            self.saved_path = save_image(self.current_image(), self.save_config)
            logger.info("Screenshot saved from object editor | path={}", self.saved_path)
            self.open_saved_file_folder()
            self.close()
        except Exception:
            logger.exception("Failed to save screenshot from object editor")
            QMessageBox.critical(self, "NoraShot", "Не удалось сохранить скриншот.")

    def open_saved_file_folder(self) -> None:
        if self.saved_path is None:
            return
        try:
            if os.name == "nt":
                subprocess.Popen(["explorer", "/select,", str(self.saved_path)])
            else:
                subprocess.Popen(["xdg-open", str(self.saved_path.parent)])
            logger.info("Opened saved screenshot folder | path={}", self.saved_path)
        except Exception:
            logger.exception("Failed to open saved screenshot folder")

    def closeEvent(self, event: QCloseEvent) -> None:
        self.closed.emit()
        super().closeEvent(event)
