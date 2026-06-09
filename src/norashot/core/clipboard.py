from loguru import logger
from PIL import Image
from PySide6.QtCore import QMimeData, QUrl
from PySide6.QtGui import QGuiApplication, QImage


def pil_to_qimage(image: Image.Image) -> QImage:
    rgba = image.convert("RGBA")
    data = rgba.tobytes("raw", "RGBA")
    qimage = QImage(data, rgba.width, rgba.height, QImage.Format.Format_RGBA8888)
    return qimage.copy()


def copy_image_to_clipboard(image: Image.Image) -> None:
    clipboard = QGuiApplication.clipboard()
    clipboard.setImage(pil_to_qimage(image))
    logger.info("Screenshot image copied to clipboard | size=%sx%s", image.width, image.height)


def copy_text_to_clipboard(text: str) -> None:
    clipboard = QGuiApplication.clipboard()
    clipboard.setText(text)
    logger.info("Text copied to clipboard | length=%s", len(text))


def copy_file_to_clipboard(path: str) -> None:
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(path)])
    QGuiApplication.clipboard().setMimeData(mime)
    logger.info("File path copied to clipboard as file URL | path=%s", path)
