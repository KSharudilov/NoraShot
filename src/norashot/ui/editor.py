from __future__ import annotations

import os
import subprocess
from pathlib import Path

from loguru import logger
from PIL import Image
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut, QColor, QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QColorDialog,
    QSpinBox,
    QLabel,
    QFontComboBox,
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from norashot.config import SaveConfig, UploadConfig
from norashot.core.clipboard import copy_image_to_clipboard, copy_text_to_clipboard
from norashot.core.sharing.base import ShareResult
from norashot.core.sharing.worker import ShareWorker
from norashot.core.storage import save_image
from norashot.ui.graphics_editor import ScreenshotCanvas


class ScreenshotEditor(QDialog):
    closed = Signal()

    def __init__(self, image: Image.Image, save_config: SaveConfig, upload_config: UploadConfig | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.save_config = save_config
        self.upload_config = upload_config or UploadConfig()
        self.share_worker: ShareWorker | None = None
        self.share_result: ShareResult | None = None
        self.saved_path: Path | None = None

        self.setWindowTitle("NoraShot")
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowMinMaxButtonsHint
            | Qt.WindowType.WindowCloseButtonHint
        )
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
            ("Скрыть", "redact"),
            ("Текст", "text"),
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

        self.canvas.tool_changed.connect(self._sync_tool_buttons)
        tools_layout.addStretch(1)

        # Keep drawing controls on a separate row so narrow windows remain usable.
        style_layout = QHBoxLayout()
        self.color_button = QPushButton("Цвет: красный")
        self.color_button.setToolTip("Выбор цвета для новых и выделенных фигур")
        self.color_button.clicked.connect(self.choose_color)
        style_layout.addWidget(self.color_button)

        width_label = QLabel("Толщина:")
        style_layout.addWidget(width_label)
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 20)
        self.width_spin.setValue(5)
        self.width_spin.setToolTip("Толщина линий для новых и выделенных фигур")
        self.width_spin.valueChanged.connect(self.change_width)
        style_layout.addWidget(self.width_spin)
        style_layout.addSpacing(12)
        style_layout.addWidget(QLabel("Шрифт:"))
        self.font_box = QFontComboBox()
        self.font_box.setCurrentFont(QFont(self.canvas.text_font))
        self.font_box.setMaximumWidth(190)
        self.font_box.currentFontChanged.connect(self.change_font_family)
        style_layout.addWidget(self.font_box)
        style_layout.addWidget(QLabel("Размер:"))
        self.font_size = QSpinBox()
        self.font_size.setRange(6, 144)
        self.font_size.setValue(self.canvas.text_size)
        self.font_size.valueChanged.connect(self.change_font_size)
        style_layout.addWidget(self.font_size)
        self.bold_check = QCheckBox("Жирный")
        self.bold_check.setChecked(self.canvas.text_bold)
        self.bold_check.toggled.connect(self.change_font_bold)
        style_layout.addWidget(self.bold_check)
        style_layout.addStretch(1)

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
        main_layout.addLayout(style_layout)
        main_layout.addWidget(self.canvas, 1)

        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch(1)

        copy_button = QPushButton("Копировать")
        save_button = QPushButton("Сохранить")
        share_button = QPushButton("Поделиться")
        close_button = QPushButton("Закрыть")

        for button in (copy_button, save_button, share_button, close_button):
            button.setMinimumHeight(34)

        self.share_button = share_button
        share_button.setToolTip("Загрузить PNG в приватный S3 и скопировать временную ссылку")
        share_button.clicked.connect(self.share_to_s3)
        copy_button.clicked.connect(self.copy_to_clipboard)
        save_button.clicked.connect(self.save_to_disk)
        close_button.clicked.connect(self.close)

        for button in (copy_button, save_button, share_button, close_button):
            bottom_layout.addWidget(button)

        main_layout.addLayout(bottom_layout)
        logger.info("Object screenshot editor opened | width={} | height={}", image.width, image.height)

    def select_tool(self, tool: str) -> None:
        self.canvas.set_tool(tool)

    def _sync_tool_buttons(self, tool: str) -> None:
        buttons = {
            "select": self.select_button,
            "arrow": self.arrow_button,
            "rectangle": self.rectangle_button,
        }
        for special_tool, label in (("blur", "Размытие"), ("text", "Текст"), ("redact", "Скрыть")):
            if tool == special_tool:
                for candidate in self.tool_group.buttons():
                    if candidate.text() == label:
                        buttons[special_tool] = candidate
                        break
        button = buttons.get(tool)
        if button is not None:
            button.setChecked(True)
        logger.debug("Editor tool button synchronized | tool={}", tool)

    def choose_color(self) -> None:
        color = QColorDialog.getColor(self.canvas.drawing_color, self, "Цвет аннотаций")
        if not color.isValid():
            return
        self.canvas.set_drawing_style(color=color)
        self.color_button.setText("Цвет: " + color.name())
        self.color_button.setStyleSheet(
            "border-bottom: 3px solid " + color.name() + ";"
        )
        logger.info("Annotation color chosen | color={}", color.name())

    def change_width(self, width: int) -> None:
        self.canvas.set_drawing_style(width=width)
        logger.info("Annotation line width chosen | width={}", width)

    def change_font_family(self, font) -> None:
        self.canvas.set_text_style(family=font.family())

    def change_font_size(self, size: int) -> None:
        self.canvas.set_text_style(size=size)

    def change_font_bold(self, bold: bool) -> None:
        self.canvas.set_text_style(bold=bold)

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

    def share_to_s3(self) -> None:
        if self.share_worker is not None:
            logger.warning("Share requested while another upload is active")
            return
        if not self.upload_config.enabled or not self.upload_config.bucket:
            QMessageBox.information(
                self, "NoraShot",
                "Сначала включите загрузку и задайте S3 в меню «Настройки» трея.",
            )
            return
        try:
            # Render the Qt scene only in the GUI thread. Network I/O runs separately.
            image = self.current_image()
        except Exception:
            logger.exception("Cannot prepare screenshot for sharing")
            QMessageBox.critical(self, "NoraShot", "Не удалось подготовить скриншот.")
            return

        self.share_result = None
        self.share_button.setEnabled(False)
        self.share_button.setText("Загрузка…")
        self.share_worker = ShareWorker(image, self.upload_config, parent=self)
        self.share_worker.completed.connect(self._share_completed)
        self.share_worker.failed.connect(self._share_failed)
        self.share_worker.finished.connect(self._share_finished)
        self.share_worker.start()
        logger.info("Screenshot sharing started | width={} | height={}", image.width, image.height)

    def _share_completed(self, result: ShareResult) -> None:
        self.share_result = result
        copy_text_to_clipboard(result.url)
        logger.info(
            "Screenshot link copied to clipboard | object_key={} | expires_at={}",
            result.object_key, result.expires_at.isoformat(),
        )
        self.share_button.setText("Ссылка скопирована")

    def _share_failed(self, message: str) -> None:
        logger.warning("Screenshot sharing failed")
        QMessageBox.warning(self, "NoraShot — загрузка", message)

    def _share_finished(self) -> None:
        worker = self.share_worker
        self.share_worker = None
        if worker is not None:
            worker.deleteLater()
        self.share_button.setEnabled(True)
        if self.share_result is not None:
            logger.info("Sharing finished successfully, closing editor")
            self.close()
        else:
            self.share_button.setText("Поделиться")

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
        if self.share_worker is not None and self.share_worker.isRunning():
            logger.warning("Editor close deferred because S3 upload is active")
            QMessageBox.information(
                self, "NoraShot", "Загрузка в S3 ещё выполняется. Дождитесь её завершения."
            )
            event.ignore()
            return
        self.closed.emit()
        super().closeEvent(event)
