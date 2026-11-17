from __future__ import annotations

from loguru import logger
from PIL import Image
from PySide6.QtCore import QThread, Signal

from norashot.config import UploadConfig
from norashot.core.sharing.base import ShareResult, SharingError
from norashot.core.sharing.manager import share_image


class ShareWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, image: Image.Image, config: UploadConfig, parent=None) -> None:
        super().__init__(parent)
        self.image = image.copy()
        self.config = config

    def run(self) -> None:
        try:
            result: ShareResult = share_image(self.image, self.config)
        except SharingError as exc:
            logger.warning("Share failed | message={}", str(exc))
            self.failed.emit(str(exc))
        except Exception as exc:
            logger.error("Unexpected share failure | error_type={}", type(exc).__name__)
            self.failed.emit("Непредвиденная ошибка загрузки. Проверьте журнал NoraShot.")
        else:
            self.completed.emit(result)
