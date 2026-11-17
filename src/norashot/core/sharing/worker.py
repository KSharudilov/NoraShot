from __future__ import annotations

from loguru import logger
from PIL import Image
from PySide6.QtCore import QThread, Signal

from norashot.config import UploadConfig
from norashot.core.sharing.base import ShareResult, SharingError
from norashot.core.sharing.manager import share_image, get_provider
from norashot.core.sharing.s3 import S3Provider


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


class S3CheckWorker(QThread):
    """Run network diagnostics away from the GUI event loop."""

    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, config: UploadConfig, parent=None) -> None:
        super().__init__(parent)
        self.config = config

    def run(self) -> None:
        try:
            provider = get_provider(self.config)
            if not isinstance(provider, S3Provider):
                raise SharingError("Текущий провайдер не поддерживает проверку S3.")
            result = provider.diagnose_connection()
        except SharingError as exc:
            logger.warning("S3 connectivity check failed | category=configuration")
            self.failed.emit(str(exc))
        except Exception as exc:
            logger.error("S3 connectivity check failed | exception_type={}", type(exc).__name__)
            self.failed.emit("Проверка подключения завершилась ошибкой. Подробности в журнале.")
        else:
            self.completed.emit(result)
