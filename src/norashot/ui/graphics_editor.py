from __future__ import annotations

import math
from uuid import uuid4

from loguru import logger
from PIL import Image, ImageFilter
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush, QColor, QImage, QPainter, QPainterPath, QPainterPathStroker,
    QPen, QPixmap, QPolygonF, QUndoCommand, QUndoStack, QFont, QFontMetricsF,
)
from PySide6.QtWidgets import (
    QGraphicsEllipseItem, QGraphicsItem, QGraphicsPixmapItem,
    QGraphicsScene, QGraphicsView, QInputDialog,
)

from norashot.core.clipboard import pil_to_qimage


RED = QColor(255, 42, 42)
BLUE = QColor(45, 137, 239)
State = tuple[float, float, float, float, float, float]


class ResizeHandle(QGraphicsEllipseItem):
    """Drag an endpoint or rectangle corner without creating dozens of undo entries."""

    def __init__(self, owner: "AnnotationItem", role: str) -> None:
        super().__init__(-6, -6, 12, 12, owner)
        self.owner = owner
        self.role = role
        self.before: State | None = None
        self.setPen(QPen(BLUE, 2))
        self.setBrush(QBrush(QColor("white")))
        self.setZValue(10)
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.hide()

    def mousePressEvent(self, event) -> None:
        self.owner.setSelected(True)
        self.before = self.owner.snapshot()
        logger.debug("Resize started | id={} | handle={}", self.owner.object_id, self.role)
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self.before is not None:
            self.owner.resize_endpoint(self.role, self.mapToParent(event.pos()))
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if self.before is not None:
            self.owner.resize_endpoint(self.role, self.mapToParent(event.pos()))
            self.owner.record_transform(self.before, "Resize")
            self.before = None
        event.accept()


class AnnotationItem(QGraphicsItem):
    """Editable vector annotation; blur displays a crop of the blurred source image."""

    def __init__(
        self, kind: str, start: QPointF, end: QPointF,
        canvas: "ScreenshotCanvas", blurred: QPixmap | None = None,
    ) -> None:
        super().__init__()
        if kind not in ("arrow", "rectangle", "blur", "text"):
            raise ValueError(f"Unknown annotation type: {kind}")
        self.object_id = uuid4().hex[:12]
        self.kind = kind
        self.canvas = canvas
        self.blurred = blurred
        self.color = QColor(canvas.drawing_color)
        self.line_width = canvas.drawing_width
        self.text_value = ""
        self.font = QFont("Segoe UI", 22)
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
        self._drag_origin: State | None = None
        self._update_handles()
        if self.kind == "text":
            self.start_handle.hide()
            self.end_handle.hide()

    def set_text_value(self, value: str) -> None:
        self.prepareGeometryChange()
        self.text_value = value
        self.update()

    def apply_style(self, color: QColor, width: int) -> None:
        self.color = QColor(color)
        self.line_width = int(width)
        self.update()

    def style_snapshot(self) -> tuple[str, int]:
        return (self.color.name(), self.line_width)

    def snapshot(self) -> State:
        return (
            self.pos().x(), self.pos().y(),
            self.start_point.x(), self.start_point.y(),
            self.end_point.x(), self.end_point.y(),
        )

    def restore(self, state: State) -> None:
        x, y, ax, ay, bx, by = state
        self.setPos(QPointF(x, y))
        self.set_geometry(QPointF(ax, ay), QPointF(bx, by))

    def record_transform(self, before: State, action: str) -> None:
        after = self.snapshot()
        if before != after:
            self.canvas.history.push(TransformCommand(self, before, after, action))
            self.canvas.changed.emit()
            logger.info("Annotation {} | id={} | kind={}", action.lower(), self.object_id, self.kind)

    def geometry_path(self) -> QPainterPath:
        path = QPainterPath()
        if self.kind == "text":
            metrics = QFontMetricsF(self.font)
            lines = (self.text_value or " ").splitlines() or [" "]
            width = max(metrics.horizontalAdvance(line or " ") for line in lines)
            path.addRect(QRectF(0, 0, max(1, width + 8), max(1, metrics.height() * len(lines) + 8)))
        elif self.kind in ("rectangle", "blur"):
            path.addRect(QRectF(self.start_point, self.end_point).normalized())
        else:
            path.moveTo(self.start_point)
            path.lineTo(self.end_point)
            angle = math.atan2(
                self.end_point.y() - self.start_point.y(),
                self.end_point.x() - self.start_point.x(),
            )
            for sign in (-1, 1):
                a = angle + sign * math.radians(28)
                point = self.end_point - QPointF(22 * math.cos(a), 22 * math.sin(a))
                path.moveTo(self.end_point)
                path.lineTo(point)
        return path

    def boundingRect(self) -> QRectF:
        return self.geometry_path().boundingRect().adjusted(-9, -9, 9, 9)

    def shape(self) -> QPainterPath:
        if self.kind in ("blur", "text"):
            return self.geometry_path()
        stroker = QPainterPathStroker()
        stroker.setWidth(14)
        return stroker.createStroke(self.geometry_path())

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.start_point, self.end_point).normalized()
        if self.kind == "text":
            painter.setPen(QPen(self.color))
            painter.setFont(self.font)
            metrics = QFontMetricsF(self.font)
            for line_number, line in enumerate(self.text_value.splitlines()):
                painter.drawText(
                    QPointF(4, 4 + metrics.ascent() + line_number * metrics.height()),
                    line,
                )
            return
        if self.kind == "blur":
            if self.blurred is not None and not rect.isEmpty():
                # Source coordinates follow the moved/resized rectangle: never stretch pixels.
                painter.drawPixmap(rect, self.blurred, rect.translated(self.pos()))
            return
        painter.setPen(
            QPen(self.color, self.line_width, Qt.PenStyle.SolidLine,
                 Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        )
        if self.kind == "rectangle":
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)
            return
        painter.drawLine(self.start_point, self.end_point)
        angle = math.atan2(
            self.end_point.y() - self.start_point.y(),
            self.end_point.x() - self.start_point.x(),
        )
        spread = math.radians(28)
        a = self.end_point - QPointF(22 * math.cos(angle - spread), 22 * math.sin(angle - spread))
        b = self.end_point - QPointF(22 * math.cos(angle + spread), 22 * math.sin(angle + spread))
        painter.setBrush(QBrush(self.color))
        painter.drawPolygon(QPolygonF([self.end_point, a, b]))

    def _update_handles(self) -> None:
        if self.kind in ("rectangle", "blur"):
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
        if self.kind in ("rectangle", "blur"):
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
            self.start_handle.setVisible(selected and self.kind != 'text')
            self.end_handle.setVisible(selected and self.kind != 'text')
            logger.debug("Selection changed | id={} | selected={}", self.object_id, selected)
        return super().itemChange(change, value)

    def mouseDoubleClickEvent(self, event) -> None:
        if self.kind != "text":
            super().mouseDoubleClickEvent(event)
            return
        text, ok = QInputDialog.getMultiLineText(
            self.canvas, "NoraShot — текст", "Изменить подпись:", self.text_value
        )
        if ok and text.strip() and text != self.text_value:
            self.canvas.history.push(TextCommand(self, self.text_value, text))
            logger.info("Text annotation edited | id={}", self.object_id)
        event.accept()

    def mousePressEvent(self, event) -> None:
        self._drag_origin = self.snapshot()
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        if self._drag_origin is not None:
            self.record_transform(self._drag_origin, "Move")
            self._drag_origin = None


class CreateCommand(QUndoCommand):
    def __init__(self, canvas: "ScreenshotCanvas", item: AnnotationItem) -> None:
        super().__init__("Create " + item.kind)
        self.canvas, self.item = canvas, item

    def redo(self) -> None:
        if self.item.scene() is None:
            self.canvas.canvas_scene.addItem(self.item)
        self.canvas.canvas_scene.clearSelection()
        self.item.setSelected(True)
        logger.info("Redo create | id={} | kind={}", self.item.object_id, self.item.kind)

    def undo(self) -> None:
        if self.item.scene() is self.canvas.canvas_scene:
            self.canvas.canvas_scene.removeItem(self.item)
        logger.info("Undo create | id={}", self.item.object_id)


class DeleteCommand(QUndoCommand):
    def __init__(self, canvas: "ScreenshotCanvas", items: list[AnnotationItem]) -> None:
        super().__init__("Delete annotations")
        self.canvas, self.items = canvas, items

    def redo(self) -> None:
        for item in self.items:
            if item.scene() is self.canvas.canvas_scene:
                self.canvas.canvas_scene.removeItem(item)
        logger.info("Annotations deleted | count={}", len(self.items))

    def undo(self) -> None:
        for item in self.items:
            if item.scene() is None:
                self.canvas.canvas_scene.addItem(item)
        logger.info("Annotations restored | count={}", len(self.items))


class TransformCommand(QUndoCommand):
    def __init__(self, item: AnnotationItem, before: State, after: State, action: str) -> None:
        super().__init__(action + " " + item.kind)
        self.item, self.before, self.after = item, before, after

    def undo(self) -> None:
        self.item.restore(self.before)
        logger.info("Undo transform | id={} | kind={}", self.item.object_id, self.item.kind)

    def redo(self) -> None:
        self.item.restore(self.after)
        logger.info("Redo transform | id={} | kind={}", self.item.object_id, self.item.kind)


class StyleCommand(QUndoCommand):
    def __init__(self, item: AnnotationItem, before: tuple[str, int], after: tuple[str, int]) -> None:
        super().__init__("Change annotation style")
        self.item, self.before, self.after = item, before, after

    def undo(self) -> None:
        self.item.apply_style(QColor(self.before[0]), self.before[1])
        logger.info("Undo style | id={}", self.item.object_id)

    def redo(self) -> None:
        self.item.apply_style(QColor(self.after[0]), self.after[1])
        logger.info("Redo style | id={}", self.item.object_id)


class TextCommand(QUndoCommand):
    def __init__(self, item: AnnotationItem, before: str, after: str) -> None:
        super().__init__("Edit text")
        self.item, self.before, self.after = item, before, after

    def undo(self) -> None:
        self.item.set_text_value(self.before)
        logger.info("Undo text edit | id={}", self.item.object_id)

    def redo(self) -> None:
        self.item.set_text_value(self.after)
        logger.info("Redo text edit | id={}", self.item.object_id)


class ScreenshotCanvas(QGraphicsView):
    """Screenshot + separate editable objects + one undo stack."""

    changed = Signal()
    tool_changed = Signal(str)

    def __init__(self, image: Image.Image, parent=None) -> None:
        super().__init__(parent)
        self.image = image.copy().convert("RGBA")
        self.tool = "select"
        self.drawing_color = QColor(RED)
        self.drawing_width = 5
        self.drag_start: QPointF | None = None
        self.draft: AnnotationItem | None = None
        self.history = QUndoStack(self)
        self._blurred: QPixmap | None = None

        self.canvas_scene = QGraphicsScene(self)
        self.canvas_scene.setSceneRect(0, 0, self.image.width, self.image.height)
        self.setScene(self.canvas_scene)
        self.background_item = QGraphicsPixmapItem(
            QPixmap.fromImage(pil_to_qimage(self.image))
        )
        self.background_item.setZValue(-10000)
        self.canvas_scene.addItem(self.background_item)

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setBackgroundBrush(QColor("#202020"))
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        logger.info("Editable canvas ready | width={} | height={}", self.image.width, self.image.height)

    def set_tool(self, tool: str) -> None:
        if tool not in ("select", "arrow", "rectangle", "blur", "text"):
            raise ValueError(f"Unknown editor tool: {tool}")
        self.tool = tool
        self.viewport().setCursor(
            Qt.CursorShape.ArrowCursor if tool == "select" else Qt.CursorShape.CrossCursor
        )
        logger.info("Editor tool selected | tool={}", tool)
        self.tool_changed.emit(tool)

    def set_drawing_style(self, color: QColor | None = None, width: int | None = None) -> None:
        """Apply style to selected vector objects; otherwise update defaults."""
        if color is not None:
            self.drawing_color = QColor(color)
        if width is not None:
            self.drawing_width = int(width)
        for item in self.canvas_scene.selectedItems():
            if not isinstance(item, AnnotationItem) or item.kind == "blur":
                continue
            before = item.style_snapshot()
            after = (self.drawing_color.name(), self.drawing_width)
            if before != after:
                self.history.push(StyleCommand(item, before, after))
                self.changed.emit()
                logger.info(
                    "Annotation style updated | id={} | color={} | width={}",
                    item.object_id, after[0], after[1],
                )
        logger.info(
            "Default drawing style | color={} | width={}",
            self.drawing_color.name(), self.drawing_width,
        )

    def fit_screenshot(self) -> None:
        """Fit the full screenshot inside the available viewport without changing export resolution."""
        if self.image.width < 1 or self.image.height < 1:
            return
        self.resetTransform()
        self.fitInView(self.canvas_scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        logger.debug(
            "Screenshot fitted to editor | image={}x{} | viewport={}x{} | scale={:.3f}",
            self.image.width, self.image.height,
            self.viewport().width(), self.viewport().height(),
            self.transform().m11(),
        )

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.fit_screenshot()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.fit_screenshot()

    def _annotation_at(self, point):
        """Look through resize handles to find their parent annotation."""
        hit = self.itemAt(point)
        while hit is not None:
            if isinstance(hit, AnnotationItem):
                return hit
            hit = hit.parentItem()
        return None

    def _clamp(self, point: QPointF) -> QPointF:
        return QPointF(
            max(0, min(point.x(), self.image.width - 1)),
            max(0, min(point.y(), self.image.height - 1)),
        )

    def _blur_pixmap(self) -> QPixmap:
        if self._blurred is None:
            logger.info("Preparing Gaussian blur background | radius=16")
            blurred_image = self.image.filter(ImageFilter.GaussianBlur(radius=16))
            self._blurred = QPixmap.fromImage(pil_to_qimage(blurred_image))
        return self._blurred

    def mousePressEvent(self, event) -> None:
        if self.tool == "select" or event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        # Clicking an existing object is always editing, even when a draw tool is active.
        # QGraphicsView performs item picking in viewport coordinates, including scaling.
        existing = self._annotation_at(event.position().toPoint())
        if existing is not None:
            logger.info(
                "Switching to selection after object click | id={} | kind={} | previous_tool={}",
                existing.object_id, existing.kind, self.tool,
            )
            self.set_tool("select")
            super().mousePressEvent(event)
            return
        point = self.mapToScene(event.position().toPoint())
        if not self.canvas_scene.sceneRect().contains(point):
            event.ignore()
            return
        self.canvas_scene.clearSelection()
        if self.tool == "text":
            value, ok = QInputDialog.getMultiLineText(
                self, "NoraShot — текст", "Введите подпись:"
            )
            if ok and value.strip():
                item = AnnotationItem("text", self._clamp(point), self._clamp(point), self)
                item.set_text_value(value)
                self.history.push(CreateCommand(self, item))
                self.changed.emit()
                logger.info("Text annotation created | id={} | chars={}", item.object_id, len(value))
            event.accept()
            return
        self.drag_start = self._clamp(point)
        self.draft = AnnotationItem(
            self.tool, self.drag_start, self.drag_start, self,
            self._blur_pixmap() if self.tool == "blur" else None,
        )
        self.draft.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.draft.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.canvas_scene.addItem(self.draft)
        logger.debug("Drawing started | kind={}", self.tool)
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
        item = self.draft
        self.draft = None
        self.drag_start = None
        if (item.kind in ("rectangle", "blur") and (dx < 4 or dy < 4)) or (
            item.kind == "arrow" and dx < 4 and dy < 4
        ):
            self.canvas_scene.removeItem(item)
            logger.debug("Tiny annotation ignored | kind={}", item.kind)
        else:
            item.set_geometry(QPointF(0, 0), end - item.pos())
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
            self.canvas_scene.removeItem(item)
            self.history.push(CreateCommand(self, item))
            self.changed.emit()
            logger.info("Annotation created | id={} | kind={}", item.object_id, item.kind)
        event.accept()

    def delete_selected(self) -> None:
        items = [
            item for item in self.canvas_scene.selectedItems()
            if isinstance(item, AnnotationItem)
        ]
        if items:
            self.history.push(DeleteCommand(self, items))
            self.changed.emit()

    def render_image(self) -> Image.Image:
        """Export at native resolution, excluding editor handles and draft drawings."""
        selected = [
            item for item in self.canvas_scene.selectedItems()
            if isinstance(item, AnnotationItem)
        ]
        self.canvas_scene.clearSelection()
        if self.draft is not None:
            self.draft.hide()
        try:
            output = QImage(self.image.width, self.image.height, QImage.Format.Format_RGBA8888)
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
            # Force a Python-owned copy before the QImage is freed.
            result = Image.frombytes(
                "RGBA", (self.image.width, self.image.height), bytes(output.bits())
            ).convert("RGB")
            logger.info(
                "Screenshot exported | width={} | height={} | objects={}",
                result.width, result.height,
                sum(isinstance(item, AnnotationItem) for item in self.canvas_scene.items()),
            )
            return result
        finally:
            if self.draft is not None:
                self.draft.show()
            for item in selected:
                if item.scene() is self.canvas_scene:
                    item.setSelected(True)
