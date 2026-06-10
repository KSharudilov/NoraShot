from __future__ import annotations

import math
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from loguru import logger
from PIL import Image, ImageDraw
from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QCloseEvent, QMouseEvent, QPixmap
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


@dataclass
class ArrowAnnotation:
    start_x: int
    start_y: int
    end_x: int
    end_y: int


class ImageCanvas(QLabel):
    changed = Signal()

    def __init__(self, image: Image.Image, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.image = image.copy().convert("RGBA")
        self.tool = "none"
        self.arrow_start: QPoint | None = None
        self.arrow_end: QPoint | None = None
        self.annotations: list[ArrowAnnotation] = []

        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setStyleSheet("background-color: #202020;")
        self.setMouseTracking(True)
        self.update_preview()

    def set_tool(self, tool: str) -> None:
        self.tool = tool
        if tool == "arrow":
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        logger.info("Editor tool selected | tool=" + tool)

    def update_preview(self) -> None:
        preview = self.render_image(include_temp=True)
        qimage = pil_to_qimage(preview.convert("RGB"))
        pixmap = QPixmap.fromImage(qimage)
        self.setPixmap(pixmap)
        self.resize(pixmap.size())

    def render_image(self, include_temp: bool = False) -> Image.Image:
        result = self.image.copy()
        draw = ImageDraw.Draw(result)

        for annotation in self.annotations:
            self.draw_arrow(
                draw,
                annotation.start_x,
                annotation.start_y,
                annotation.end_x,
                annotation.end_y,
            )

        if include_temp and self.arrow_start is not None and self.arrow_end is not None:
            self.draw_arrow(
                draw,
                self.arrow_start.x(),
                self.arrow_start.y(),
                self.arrow_end.x(),
                self.arrow_end.y(),
            )

        return result.convert("RGB")

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self.tool != "arrow":
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return

        point = event.position().toPoint()
        if not self.point_inside_image(point):
            return

        self.arrow_start = point
        self.arrow_end = point
        self.update_preview()
        logger.info("Arrow drawing started")

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.tool != "arrow":
            return
        if self.arrow_start is None:
            return

        point = event.position().toPoint()
        self.arrow_end = self.clamp_point_to_image(point)
        self.update_preview()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self.tool != "arrow":
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self.arrow_start is None or self.arrow_end is None:
            return

        end_point = self.clamp_point_to_image(event.position().toPoint())
        dx = end_point.x() - self.arrow_start.x()
        dy = end_point.y() - self.arrow_start.y()

        if abs(dx) < 4 and abs(dy) < 4:
            logger.info("Arrow drawing ignored because arrow is too small")
            self.arrow_start = None
            self.arrow_end = None
            self.update_preview()
            return

        self.annotations.append(
            ArrowAnnotation(
                start_x=self.arrow_start.x(),
                start_y=self.arrow_start.y(),
                end_x=end_point.x(),
                end_y=end_point.y(),
            )
        )
        logger.info("Arrow annotation added")

        self.arrow_start = None
        self.arrow_end = None
        self.update_preview()
        self.changed.emit()

    def point_inside_image(self, point: QPoint) -> bool:
        return 0 <= point.x() < self.image.width and 0 <= point.y() < self.image.height

    def clamp_point_to_image(self, point: QPoint) -> QPoint:
        x = min(max(point.x(), 0), self.image.width - 1)
        y = min(max(point.y(), 0), self.image.height - 1)
        return QPoint(x, y)

    def draw_arrow(self, draw: ImageDraw.ImageDraw, start_x: int, start_y: int, end_x: int, end_y: int) -> None:
        color = (255, 0, 0, 255)
        width = 5
        draw.line((start_x, start_y, end_x, end_y), fill=color, width=width)

        angle = math.atan2(end_y - start_y, end_x - start_x)
        head_length = 22
        head_angle = math.radians(28)

        point1 = (
            end_x - head_length * math.cos(angle - head_angle),
            end_y - head_length * math.sin(angle - head_angle),
        )
        point2 = (
            end_x - head_length * math.cos(angle + head_angle),
            end_y - head_length * math.sin(angle + head_angle),
        )

        draw.polygon([(end_x, end_y), point1, point2], fill=color)


class ScreenshotEditor(QDialog):
    closed = Signal()

    def __init__(self, image: Image.Image, save_config: SaveConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.save_config = save_config
        self.saved_path: Path | None = None

        self.setWindowTitle("NoraShot")
        self.setMinimumSize(900, 600)
        self.resize(1100, 760)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        tools_layout = QHBoxLayout()
        arrow_button = QPushButton("Стрелка")
        arrow_button.setCheckable(True)
        arrow_button.setMinimumHeight(30)
        arrow_button.clicked.connect(lambda checked: self.select_arrow_tool(checked))
        tools_layout.addWidget(arrow_button)
        tools_layout.addStretch(1)
        main_layout.addLayout(tools_layout)

        self.arrow_button = arrow_button
        self.canvas = ImageCanvas(image=image)

        scroll = QScrollArea()
        scroll.setWidgetResizable(False)
        scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll.setWidget(self.canvas)

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

        logger.info("Screenshot editor opened | width=" + str(image.width) + " | height=" + str(image.height))

    def select_arrow_tool(self, checked: bool) -> None:
        if checked:
            self.canvas.set_tool("arrow")
        else:
            self.canvas.set_tool("none")

    def current_image(self) -> Image.Image:
        return self.canvas.render_image(include_temp=False)

    def copy_to_clipboard(self) -> None:
        try:
            copy_image_to_clipboard(self.current_image())
            logger.info("Screenshot copied from editor, closing editor")
            self.close()
        except Exception:
            logger.exception("Failed to copy screenshot from editor")
            QMessageBox.critical(self, "NoraShot", "Не удалось скопировать скриншот в буфер.")

    def save_to_disk(self) -> None:
        try:
            self.saved_path = save_image(self.current_image(), self.save_config)
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
