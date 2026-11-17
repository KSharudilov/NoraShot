from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import urlsplit

import keyring
from loguru import logger

from norashot.core.sharing.base import SharingError


SERVICE = "NoraShot S3"


@dataclass(frozen=True)
class S3Credentials:
    access_key: str
    secret_key: str


def _account(endpoint: str, bucket: str) -> str:
    hostname = urlsplit(endpoint.strip()).netloc.lower()
    if not hostname or not bucket.strip():
        raise SharingError("Укажите Endpoint и Bucket в настройках S3.")
    return f"{hostname}/{bucket.strip()}"


def _validate_backend() -> None:
    # Fail closed on missing or disabled keyring providers.
    backend = keyring.get_keyring()
    if getattr(backend, "priority", 0) <= 0:
        raise SharingError("Нет защищённого хранилища учётных данных Windows.")


def save_credentials(endpoint: str, bucket: str, access: str, secret: str) -> None:
    if not access.strip() or not secret.strip():
        raise SharingError("Access Key и Secret Key не могут быть пустыми.")
    _validate_backend()
    try:
        keyring.set_password(
            SERVICE, _account(endpoint, bucket),
            json.dumps({"access_key": access.strip(), "secret_key": secret.strip()}),
        )
    except Exception as exc:
        logger.warning("Unable to save S3 credentials | error_type={}", type(exc).__name__)
        raise SharingError("Не удалось сохранить ключи в диспетчере учётных данных.") from None
    logger.info("S3 credentials stored in Windows credential vault | bucket={}", bucket)


def load_credentials(endpoint: str, bucket: str) -> S3Credentials:
    _validate_backend()
    try:
        value = keyring.get_password(SERVICE, _account(endpoint, bucket))
        if not value:
            raise SharingError("Ключи S3 не сохранены. Откройте настройки хранилища.")
        data = json.loads(value)
        return S3Credentials(data["access_key"], data["secret_key"])
    except SharingError:
        raise
    except Exception as exc:
        logger.warning("Unable to access S3 credentials | error_type={}", type(exc).__name__)
        raise SharingError("Не удалось прочитать ключи S3 из хранилища Windows.") from None
