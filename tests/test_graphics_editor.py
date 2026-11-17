"""Offscreen Qt regression tests for the object editor and full-resolution export."""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PIL import Image
from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

from norashot.ui.graphics_editor import AnnotationItem, CreateCommand, ScreenshotCanvas


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_annotation_create_undo_redo_and_export(qt_app):
    canvas = ScreenshotCanvas(Image.new("RGB", (160, 100), "white"))
    item = AnnotationItem("rectangle", QPointF(20, 20), QPointF(100, 75), canvas)
    canvas.history.push(CreateCommand(canvas, item))
    assert item.scene() is canvas.canvas_scene
    assert canvas.history.canUndo()
    export = canvas.render_image()
    assert export.size == (160, 100)
    assert export.getpixel((20, 20)) != (255, 255, 255)

    canvas.history.undo()
    assert item.scene() is None
    assert canvas.render_image().getpixel((20, 20)) == (255, 255, 255)
    canvas.history.redo()
    assert item.scene() is canvas.canvas_scene
    canvas.close()


def test_redaction_is_opaque_in_saved_image(qt_app):
    canvas = ScreenshotCanvas(Image.new("RGB", (100, 70), "white"))
    item = AnnotationItem("redact", QPointF(10, 10), QPointF(70, 55), canvas)
    canvas.history.push(CreateCommand(canvas, item))
    result = canvas.render_image()
    assert result.getpixel((30, 30)) == (0, 0, 0)
    assert result.getpixel((90, 60)) == (255, 255, 255)
    canvas.close()


def test_text_styles_are_undoable(qt_app):
    canvas = ScreenshotCanvas(Image.new("RGB", (300, 150), "white"))
    item = AnnotationItem("text", QPointF(15, 15), QPointF(15, 15), canvas)
    item.set_text_value("NoraShot")
    canvas.history.push(CreateCommand(canvas, item))
    assert item.font.pointSize() == 22
    canvas.set_text_style(size=30, bold=True)
    assert item.font.pointSize() == 30
    assert item.font.bold() is True
    canvas.history.undo()
    assert item.font.pointSize() == 22
    canvas.history.undo()
    assert item.font.bold() is False
    canvas.close()


def test_color_and_thickness_are_undoable(qt_app):
    canvas = ScreenshotCanvas(Image.new("RGB", (160, 100), "white"))
    item = AnnotationItem("arrow", QPointF(10, 20), QPointF(100, 75), canvas)
    canvas.history.push(CreateCommand(canvas, item))
    canvas.set_drawing_style(color=QColor("blue"))
    assert item.color.name() == "#0000ff"
    canvas.history.undo()
    assert item.color.name() != "#0000ff"
    canvas.close()
