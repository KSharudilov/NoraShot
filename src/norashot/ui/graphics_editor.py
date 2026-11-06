from __future__ import annotations

import math
from uuid import uuid4

from loguru import logger
from PIL import Image
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QBrush, QImage, QPainter, QPainterPath, QPainterPathStroker, QPen, QPolygonF, QPixmap
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
)

from norashot.core.clipboard import pil_to_qimage


RED = QColor(255, 42, 42)
BLUE = QColor(45, 137, 239)


class ResizeHandle(QGraphicsEllipseItem):
    """A draggable endpoint/corner owned by its annotation."""

    def __init__(self, owner: "AnnotationItem", role: str) -> None:
        super().__init__(-6, -6, 12, 12, owner)
        self.owner = owner
        self.role = role
        self.setPen(QPen(BLUE, 2))
        self.setBrush(QBrush(QColor("white")))
        self.setZValue(10)
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.hide()

    def mousePressEvent(self, event) -> None:
        self.owner.setSelected(True)
        logger.debug("Annotation resize started | id={} | handle={}", self.owner.object_id, self.role)
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        self.owner.resize_endpoint(self.role, self.mapToParent(event.pos()))
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        logger.info("Annotation resized | id={} | kind={} | handle={}", self.owner.object_id, self.owner.kind, self.role)
        event.accept()


class AnnotationItem(QGraphicsItem):
    """One independent, movable, resizable graphical annotation."""

    def __init__(self, kind: str, start: QPointF, end: QPointF) -> None:
        super().__init__()
        if kind not in ("arrow", "rectangle"):
            raise ValueError(f"Unknown annotation kind: {kind}")
        self.object_id = uuid4().hex[:12]
        self.kind = kind
        self.start_point = QPointF(0, 0)
        self.end_point = end - start
        self.setPos(start)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.start_handle = ResizeHandle(self, "start")
        self.end_handle = ResizeHandle(self, "end")
        self._drag_origin = QPointF(self.pos())
        self._update_handles()

    def geometry_path(self) -> QPainterPath:
        path = QPainterPath()
        if self.kind == "rectangle":
            path.addRect(QRectF(self.start_point, self.end_point).normalized())
        else:
            path.moveTo(self.start_point)
            path.lineTo(self.end_point)
            angle = math.atan2(
                self.end_point.y() - self.start_point.y(),
                self.end_point.x() - self.start_point.x(),
            )
            length = 22
            spread = math.radians(28)
            for sign in (-1, 1):
                point = self.end_point - QPointF(
                    length * math.cos(angle + sign * spread),
                    length * math.sin(angle + sign * spread),
                )
                path.moveTo(self.end_point)
                path.lineTo(point)
        return path

    def boundingRect(self) -> QRectF:
        return self.geometry_path().boundingRect().adjusted(-9, -9, 9, 9)

    def shape(self) -> QPainterPath:
        stroker = QPainterPathStroker()
        stroker.setWidth(14)
        return stroker.createStroke(self.geometry_path())

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(RED, 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.Round, Qt.PenJoinStyle.Round))
        if self.kind == "rectangle":
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(QRectF(self.start_point, self.end_point).normalized())
        else:
            painter.drawLine(self.start_point, self.end_point)
            angle = math.atan2(
                self.end_point.y() - self.start_point.y(),
                self.end_point.x() - self.start_point.x(),
            )
            length = 22
            spread = math.radians(28)
            wing_a = self.end_point - QPointF(
                length * math.cos(angle - spread),
                length * math.sin(angle - spread),
            )
            wing_b = self.end_point - QPointF(
                length * math.cos(angle + spread),
                length * math.sin(angle + spread),
            )
            painter.setBrush(QBrush(RED))
            painter.drawPolygon(QPolygonF([self.end_point, wing_a, wing_b]))

    def _update_handles(self) -> None:
        if self.kind == "rectangle":
            rect = QRectF(self.start_point, self.end_point).normalized()
            self.start_handle.setPos(rect.topLeft())
            self.end_handle.setPos(rect.bottomRight())
        else:
            self.start_handle.setPos(self.start_point)
            self.end_handle.setPos(self.end_point)

    def set_geometry(self, a: QPointF, b: QPointF) -> None:
        self.prepareGeometryChange()
        self.start_point = QPointF(a)
        self.end_point = QPointF(b)
        self._update_handles()
        self.update()

    def resize_endpoint(self, role: str, point: QPointF) -> None:
        if self.kind == "rectangle":
            rect = QRectF(self.start_point, self.end_point).normalized()
            if role == "start":
                self.set_geometry(point, rect.bottomRight())
            else:
                self.set_geometry(rect.topLeft(), point)
        elif role == "start":
            self.set_geometry(point, self.end_point)
        else:
            self.set_geometry(self.start_point, point)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            selected = bool(value)
            self.start_handle.setVisible(selected)
            self.end_handle.setVisible(selected)
            logger.debug("Annotation selection changed | id={} | selected={}", self.object_id, selected)
        return super().itemChange(change, value)

    def mousePressEvent(self, event) -> None:
        self._drag_origin = QPointF(self.pos())
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        if self.pos() != self._drag_origin:
            logger.info(
                "Annotation moved | id={} | kind={} | x={:.1f} | y={:.1f}",
                self.object_id, self.kind, self.pos().x(), self.pos().y(),
            )


class ScreenshotCanvas(QGraphicsView):
    """Canvas with a fixed screenshot background and independent vector annotations."""

    changed = Signal()

    def __init__(self, image: Image.Image, parent=None) -> None:
        super().__init__(parent)
        self.image = image.copy().convert("RGBA")
        self.tool = "select"
        self.drag_start: QPointF | None = None
        self.draft: AnnotationItem | None = None

        self.canvas_scene = QGraphicsScene(self)
        self.canvas_scene.setSceneRect(0, 0, self.image.width, self.image.height)
        self.setScene(self.canvas_scene)
        base_pixmap = QPixmap.fromImage(pil_to_qimage(self.image))
        self.background_item = QGraphicsPixmapItem(base_pixmap)
        self.background_item.setZValue(-10000)
        self.canvas_scene.addItem(self.background_item)

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setBackgroundBrush(QColor("#202020"))
        logger.info("Object canvas initialized | width={} | height={}", self.image.width, self.image.height)

    def set_tool(self, tool: str) -> None:
        if tool not in ("select", "arrow", "rectangle"):
            raise ValueError(f"Unknown tool: {tool}")
        self.tool = tool
        self.viewport().setCursor(
            Qt.CursorShape.ArrowCursor if tool == "select" else Qt.CursorShape.CrossCursor
        )
        logger.info("Editor tool selected | tool={}", tool)

    def _clamp(self, point: QPointF) -> QPointF:
        return QPointF(
            max(0, min(point.x(), self.image.width - 1)),
            max(0, min(point.y(), self.image.height - 1)),
        )

    def mousePressEvent(self, event) -> None:
        if self.tool == "select" or event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        point = self.mapToScene(event.position().toPoint())
        if not self.canvas_scene.sceneRect().contains(point):
            return
        self.canvas_scene.clearSelection()
        self.drag_start = self._clamp(point)
        self.draft = AnnotationItem(self.tool, self.drag_start, self.drag_start)
        self.draft.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.draft.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.canvas_scene.addItem(self.draft)
        logger.debug("Annotation drawing started | kind={}", self.tool)
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self.draft is None or self.drag_start is None:
            super().mouseMoveEvent(event)
            return
        end = self._clamp(self.mapToScene(event.position().toPoint()))
        self.draft.set_geometry(QPointF(0, 0), end - self.drag_start)
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if self.draft is None or self.drag_start is None or event.button() != Qt.MouseButton.LeftButton:
            super().mouseReleaseEvent(event)
            return
        end = self._clamp(self.mapToScene(event.position().toPoint()))
        dx, dy = abs(end.x() - self.drag_start.x()), abs(end.y() - self.drag_start.y())
        draft = self.draft
        self.draft = None
        self.drag_start = None
        if (draft.kind == "rectangle" and (dx < 4 or dy < 4)) or (
            draft.kind == "arrow" and dx < 4 and dy < 4
        ):
            self.canvas_scene.removeItem(draft)
            logger.debug("Tiny annotation ignored | kind={}", draft.kind)
        else:
            draft.set_geometry(QPointF(0, 0), end - draft.pos())
            draft.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
            draft.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
            draft.setSelected(True)
            logger.info("Annotation created | id={} | kind={}", draft.object_id, draft.kind)
            self.changed.emit()
        event.accept()

    def render_image(self) -> Image.Image:
        """Render at original pixel resolution, without selection handles."""
        selected = [item for item in self.canvas_scene.selectedItems() if isinstance(item, AnnotationItem)]
        self.canvas_scene.clearSelection()
        if self.draft is not None:
            self.draft.hide()
        try:
            output = QImage(
                self.image.width, self.image.height, QImage.Format.Format_RGBA8888
            )
            output.fill(Qt.GlobalColor.transparent)
            painter = QPainter(output)
            try:
                self.canvas_scene.render(
                    painter,
                    QRectF(0, 0, self.image.width, self.image.height),
                    QRectF(0, 0, self.image.width, self.image.height),
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                )
            finally:
                painter.end()
            result = Image.frombytes(
                "RGBA",
                (self.image.width, self.image.height),
                bytes(output.bits()),
            ).convert("RGB")
            logger.info(
                "Screenshot rendered with annotations | width={} | height={} | count={}",
                result.width,
                result.height,
                sum(isinstance(item, AnnotationItem) for item in self.canvas_scene.items()),
            )
            return result
        finally:
            if self.draft is not None:
                self.draft.show()
            for item in selected:
                item.setSelected(True)
