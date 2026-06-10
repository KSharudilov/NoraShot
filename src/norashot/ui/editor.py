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
    QButtonGroup,
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


@dataclass
class RectangleAnnotation:
    left: int
    top: int
    right: int
    bottom: int


class ImageCanvas(QLabel):
    changed = Signal()

    def __init__(self, image: Image.Image, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.image = image.copy().convert("RGBA")
        self.tool = "none"
        self.drag_start: QPoint | None = None
        self.drag_end: QPoint | None = None
        self.arrows: list[ArrowAnnotation] = []
        self.rectangles: list[RectangleAnnotation] = []

        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setStyleSheet("background-color: #202020;")
        self.setMouseTracking(True)
        self.update_preview()

    def set_tool(self, tool: str) -> None:
        self.tool = tool
        self.drag_start = None
        self.drag_end = None
        if tool in ("arrow", "rectangle"):
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update_preview()
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

        for arrow in self.arrows:
            self.draw_arrow(draw, arrow.start_x, arrow.start_y, arrow.end_x, arrow.end_y)

        for rectangle in self.rectangles:
            self.draw_rectangle(draw, rectangle.left, rectangle.top, rectangle.right, rectangle.bottom)

        if include_temp and self.drag_start is not None and self.drag_end is not None:
            if self.tool == "arrow":
                self.draw_arrow(
                    draw,
                    self.drag_start.x(),
                    self.drag_start.y(),
                    self.drag_end.x(),
                    self.drag_end.y(),
                )
            if self.tool == "rectangle":
                left, top, right, bottom = self.normalized_rect_points(self.drag_start, self.drag_end)
                self.draw_rectangle(draw, left, top, right, bottom)

        return result.convert("RGB")

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self.tool not in ("arrow", "rectangle"):
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return

        point = event.position().toPoint()
        if not self.point_inside_image(point):
            return

        self.drag_start = point
        self.drag_end = point
        self.update_preview()
        logger.info("Drawing started | tool=" + self.tool)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.tool not in ("arrow", "rectangle"):
            return
        if self.drag_start is None:
            return

        point = event.position().toPoint()
        self.drag_end = self.clamp_point_to_image(point)
        self.update_preview()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self.tool not in ("arrow", "rectangle"):
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self.drag_start is None or self.drag_end is None:
            return

        end_point = self.clamp_point_to_image(event.position().toPoint())
        dx = end_point.x() - self.drag_start.x()
        dy = end_point.y() - self.drag_start.y()

        if abs(dx) < 4 and abs(dy) < 4:
            logger.info("Drawing ignored because selected object is too small")
            self.clear_drag()
            return

        if self.tool == "arrow":
            self.arrows.append(
                ArrowAnnotation(
                    start_x=self.drag_start.x(),
                    start_y=self.drag_start.y(),
                    end_x=end_point.x(),
                    end_y=end_point.y(),
                )
            )
            logger.info("Arrow annotation added")

        if self.tool == "rectangle":
            left, top, right, bottom = self.normalized_rect_points(self.drag_start, end_point)
            self.rectangles.append(RectangleAnnotation(left=left, top=top, right=right, bottom=bottom))
            logger.info("Rectangle annotation added")

        self.clear_drag()
        self.changed.emit()

    def clear_drag(self) -> None:
        self.drag_start = None
        self.drag_end = None
        self.update_preview()

    def point_inside_image(self, point: QPoint) -> bool:
        return 0 <= point.x() < self.image.width and 0 <= point.y() < self.image.height

    def clamp_point_to_image(self, point: QPoint) -> QPoint:
        x = min(max(point.x(), 0), self.image.width - 1)
        y = min(max(point.y(), 0), self.image.height - 1)
        return QPoint(x, y)

    def normalized_rect_points(self, start: QPoint, end: QPoint) -> tuple[int, int, int, int]:
        left = min(start.x(), end.x())
        top = min(start.y(), end.y())
        right = max(start.x(), end.x())
        bottom = max(start.y(), end.y())
        return left, top, right, bottom

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

    def draw_rectangle(self, draw: ImageDraw.ImageDraw, left: int, top: int, right: int, bottom: int) -> None:
        if right < left:
            left, right = right, left
        if bottom < top:
            top, bottom = bottom, top
        if right == left or bottom == top:
            return

        color = (255, 0, 0, 255)
        width = 5
        draw.rectangle((left, top, right, bottom), outline=color, width=width)


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
        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)

        self.arrow_button = QPushButton("Стрелка")
        self.arrow_button.setCheckable(True)
        self.arrow_button.setMinimumHeight(30)
        self.arrow_button.clicked.connect(lambda checked: self.select_tool("arrow", checked))
        self.tool_group.addButton(self.arrow_button)
        tools_layout.addWidget(self.arrow_button)

        self.rectangle_button = QPushButton("Прямоугольник")
        self.rectangle_button.setCheckable(True)
        self.rectangle_button.setMinimumHeight(30)
        self.rectangle_button.clicked.connect(lambda checked: self.select_tool("rectangle", checked))
        self.tool_group.addButton(self.rectangle_button)
        tools_layout.addWidget(self.rectangle_button)

        tools_layout.addStretch(1)
        main_layout.addLayout(tools_layout)

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

    def select_tool(self, tool: str, checked: bool) -> None:
        if checked:
            self.canvas.set_tool(tool)
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
