from __future__ import annotations

import os
import subprocess
from pathlib import Path

from loguru import logger
from PIL import Image
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from norashot.config import SaveConfig
from norashot.core.clipboard import copy_image_to_clipboard, pil_to_qimage
from norashot.core.storage import save_image


class ScreenshotEditor(QDialog):
    closed = Signal()

    def __init__(self, image: Image.Image, save_config: SaveConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.image = image.copy()
        self.save_config = save_config
        self.saved_path: Path | None = None

        self.setWindowTitle("NoraShot")
        self.setMinimumSize(900, 600)
        self.resize(1100, 760)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.preview_label.setStyleSheet("background-color: #202020;")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll.setWidget(self.preview_label)

        main_layout.addWidget(scroll, 1)

        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch(1)

        copy_button = QPushButton("Копировать")
        save_button = QPushButton("Сохранить")
        share_button = QPushButton("Поделиться")
        close_button = QPushButton("Закрыть")

        copy_button.setMinimumHeight(34)
        save_button.setMinimumHeight(34)
        share_button.setMinimumHeight(34)
        close_button.setMinimumHeight(34)

        share_button.setEnabled(False)
        share_button.setToolTip("Загрузка в облако будет добавлена позже")

        copy_button.clicked.connect(self.copy_to_clipboard)
        save_button.clicked.connect(self.save_to_disk)
        close_button.clicked.connect(self.close)

        bottom_layout.addWidget(copy_button)
        bottom_layout.addWidget(save_button)
        bottom_layout.addWidget(share_button)
        bottom_layout.addWidget(close_button)

        main_layout.addLayout(bottom_layout)
        self.setLayout(main_layout)

        self.update_preview()
        logger.info("Screenshot editor opened | width=" + str(self.image.width) + " | height=" + str(self.image.height))

    def update_preview(self) -> None:
        qimage = pil_to_qimage(self.image)
        pixmap = QPixmap.fromImage(qimage)
        self.preview_label.setPixmap(pixmap)
        self.preview_label.resize(pixmap.size())

    def copy_to_clipboard(self) -> None:
        try:
            copy_image_to_clipboard(self.image)
            logger.info("Screenshot copied from editor, closing editor")
            self.close()
        except Exception:
            logger.exception("Failed to copy screenshot from editor")
            QMessageBox.critical(self, "NoraShot", "Не удалось скопировать скриншот в буфер.")

    def save_to_disk(self) -> None:
        try:
            self.saved_path = save_image(self.image, self.save_config)
            logger.info("Screenshot saved from editor | path=" + str(self.saved_path))
            self.open_saved_file_folder()
            self.close()
        except Exception:
            logger.exception("Failed to save screenshot from editor")
            QMessageBox.critical(self, "NoraShot", "Не удалось сохранить скриншот.")

    def open_saved_file_folder(self) -> None:
        if self.saved_path is None:
            return

        try:
            if os.name == "nt":
                subprocess.Popen(["explorer", "/select,", str(self.saved_path)])
            else:
                os.startfile(str(self.saved_path.parent))
            logger.info("Opened saved screenshot folder | path=" + str(self.saved_path))
        except Exception:
            logger.exception("Failed to open saved screenshot folder")

    def closeEvent(self, event: QCloseEvent) -> None:
        self.closed.emit()
        super().closeEvent(event)
