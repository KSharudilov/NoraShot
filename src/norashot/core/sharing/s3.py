from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4
from urllib.parse import urlsplit

import boto3
from botocore.config import Config
from loguru import logger

from norashot.config import UploadConfig
from norashot.core.sharing.base import ShareResult, SharingError, StorageProvider
from norashot.core.sharing.credentials import S3Credentials


class S3Provider(StorageProvider):
    """Private S3 upload and short-lived SigV4 GET URL. No public bucket required."""

    def __init__(self, settings: UploadConfig, credentials: S3Credentials) -> None:
        if not settings.bucket or not settings.bucket.strip():
            raise SharingError("Укажите имя бакета S3 в настройках.")
        endpoint = settings.endpoint.strip().rstrip("/")
        parsed = urlsplit(endpoint)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise SharingError("Для S3 требуется корректный HTTPS Endpoint.")
        if parsed.query or parsed.fragment or parsed.path not in ("", "/"):
            raise SharingError("Endpoint должен содержать только HTTPS-адрес сервера S3.")
        if not (60 <= settings.link_ttl_seconds <= 604800):
            raise SharingError("Срок ссылки должен быть от 60 секунд до 7 дней.")
        self.settings = settings
        self.s3 = boto3.client(
            "s3",
            endpoint_url=endpoint,
            region_name=settings.region or "us-east-1",
            aws_access_key_id=credentials.access_key,
            aws_secret_access_key=credentials.secret_key,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
                connect_timeout=10,
                read_timeout=45,
                retries={"mode": "standard", "max_attempts": 3},
            ),
        )

    def upload(self, png: bytes) -> ShareResult:
        if not png.startswith(b"\x89PNG\r\n\x1a\n"):
            raise SharingError("Ожидается изображение PNG.")
        now = datetime.now(timezone.utc)
        prefix = now.strftime(self.settings.prefix_template).strip("/")
        if ".." in prefix.split("/") or "\\" in prefix:
            raise SharingError("Некорректный префикс объектов S3.")
        filename = f"{uuid4().hex}.png"
        key = f"{prefix}/{filename}" if prefix else filename
        logger.info(
            "S3 upload started | bucket={} | key={} | size_bytes={}",
            self.settings.bucket, key, len(png),
        )
        try:
            self.s3.put_object(
                Bucket=self.settings.bucket,
                Key=key,
                Body=png,
                ContentType="image/png",
                CacheControl="private, no-store",
            )
            signed = self.s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.settings.bucket, "Key": key},
                ExpiresIn=self.settings.link_ttl_seconds,
                HttpMethod="GET",
            )
        except Exception as exc:
            logger.error(
                "S3 upload or link generation failed | key={} | error_type={}",
                key, type(exc).__name__,
            )
            raise SharingError(
                "Не удалось опубликовать скриншот. Проверьте S3, сеть и права доступа."
            ) from None
        logger.info(
            "S3 screenshot published | bucket={} | key={} | link_ttl_seconds={}",
            self.settings.bucket, key, self.settings.link_ttl_seconds,
        )
        # Never log a signed URL or secret.
        return ShareResult(key, signed, now + timedelta(seconds=self.settings.link_ttl_seconds))

    def delete(self, object_key: str) -> None:
        try:
            self.s3.delete_object(Bucket=self.settings.bucket, Key=object_key)
            logger.info("S3 object deleted | bucket={} | key={}", self.settings.bucket, object_key)
        except Exception as exc:
            logger.error("S3 deletion failed | error_type={}", type(exc).__name__)
            raise SharingError("Не удалось удалить объект из S3.") from None
