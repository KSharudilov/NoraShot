from __future__ import annotations

from io import BytesIO

from PIL import Image
from loguru import logger

from norashot.config import UploadConfig
from norashot.core.sharing.base import ShareResult, SharingError, StorageProvider
from norashot.core.sharing.credentials import load_credentials
from norashot.core.sharing.s3 import S3Provider


def get_provider(config: UploadConfig) -> StorageProvider:
    """Central provider switch point; managed NoraShot API is intentionally unavailable."""
    if config.provider != "s3":
        raise SharingError("Выбранный способ публикации пока не поддерживается.")
    return S3Provider(config, load_credentials(config.endpoint, config.bucket))


def share_image(image: Image.Image, config: UploadConfig) -> ShareResult:
    if not config.enabled:
        raise SharingError("Включите загрузку в разделе «Хранилище» настроек.")
    buffer = BytesIO()
    image.convert("RGB").save(buffer, format="PNG")
    payload = buffer.getvalue()
    logger.info("Screenshot prepared for cloud upload | bytes={} | provider={}", len(payload), config.provider)
    return get_provider(config).upload(payload)
