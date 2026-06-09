from __future__ import annotations

from loguru import logger
from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QApplication, QLabel, QWidget


class RegionSelector(QWidget):
    region_selected = Signal(int, int, int, int)
    canceled = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.start_pos: QPoint | None = None
        self.current_pos: QPoint | None = None
        self.selection_rect = QRect()

        self.setWindowTitle("NoraShot region selector")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self.hint = QLabel("Выделите область мышкой. Esc — отмена", self)
        self.hint.setStyleSheet(
            "background: rgba(0, 0, 0, 180);"
            "color: white;"
            "padding: 8px 12px;"
            "border-radius: 4px;"
            "font-size: 13px;"
        )
        self.hint.adjustSize()

        self.set_geometry_to_all_screens()
        logger.info(
            "Region selector initialized | x=" + str(self.geometry().x())
            + " | y=" + str(self.geometry().y())
            + " | width=" + str(self.geometry().width())
            + " | height=" + str(self.geometry().height())
        )

    def set_geometry_to_all_screens(self) -> None:
        screens = QApplication.screens()
        if not screens:
            screen = QApplication.primaryScreen()
            self.setGeometry(screen.geometry())
            return

        geometry = screens[0].geometry()
        for screen in screens[1:]:
            geometry = geometry.united(screen.geometry())

        self.setGeometry(geometry)
        self.hint.move(20, 20)

    def show_selector(self) -> None:
        self.start_pos = None
        self.current_pos = None
        self.selection_rect = QRect()
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()
        logger.info("Region selector shown")

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        overlay_color = QColor(0, 0, 0, 120)
        painter.fillRect(self.rect(), overlay_color)

        if not self.selection_rect.isNull():
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(self.selection_rect, QColor(0, 0, 0, 0))

            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            pen = QPen(QColor(45, 137, 239), 2)
            painter.setPen(pen)
            painter.drawRect(self.selection_rect.adjusted(0, 0, -1, -1))

            size_text = str(self.selection_rect.width()) + " x " + str(self.selection_rect.height())
            text_rect = QRect(
                self.selection_rect.left(),
                max(0, self.selection_rect.top() - 28),
                120,
                24,
            )
            painter.fillRect(text_rect, QColor(0, 0, 0, 180))
            painter.setPen(QColor("white"))
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, size_text)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return

        self.start_pos = event.position().toPoint()
        self.current_pos = self.start_pos
        self.selection_rect = QRect(self.start_pos, self.current_pos).normalized()
        self.update()
        logger.info("Region selection started")

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.start_pos is None:
            return

        self.current_pos = event.position().toPoint()
        self.selection_rect = QRect(self.start_pos, self.current_pos).normalized()
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self.start_pos is None:
            return

        self.current_pos = event.position().toPoint()
        self.selection_rect = QRect(self.start_pos, self.current_pos).normalized()

        if self.selection_rect.width() < 3 or self.selection_rect.height() < 3:
            logger.info("Region selection canceled because selected area is too small")
            self.close()
            self.canceled.emit()
            return

        global_top_left = self.mapToGlobal(self.selection_rect.topLeft())
        left = global_top_left.x()
        top = global_top_left.y()
        width = self.selection_rect.width()
        height = self.selection_rect.height()

        logger.info(
            "Region selected | left=" + str(left)
            + " | top=" + str(top)
            + " | width=" + str(width)
            + " | height=" + str(height)
        )

        self.close()
        self.region_selected.emit(left, top, width, height)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            logger.info("Region selector canceled by Escape")
            self.close()
            self.canceled.emit()
            return
        super().keyPressEvent(event)
