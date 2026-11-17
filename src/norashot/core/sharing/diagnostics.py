"""Safe S3 error messages and metadata for logs; never log exception strings.

Botocore exception representations may include presigned URLs and other credentials.
"""
from __future__ import annotations

from dataclasses import dataclass

from botocore.exceptions import (
    ClientError,
    ConnectTimeoutError,
    ConnectionClosedError,
    EndpointConnectionError,
    NoCredentialsError,
    PartialCredentialsError,
    ReadTimeoutError,
    SSLError,
)
from loguru import logger

from norashot.core.sharing.base import SharingError


@dataclass(frozen=True)
class S3Diagnostic:
    category: str
    message: str
    code: str = ""
    status: int | None = None


def classify_s3_error(exc: Exception) -> S3Diagnostic:
    if isinstance(exc, SSLError):
        return S3Diagnostic(
            "tls",
            "Ошибка проверки HTTPS-сертификата S3. Проверьте CA-сертификаты, "
            "системное время и HTTPS-инспекцию сети.",
        )
    if isinstance(exc, (ConnectTimeoutError, ReadTimeoutError)):
        return S3Diagnostic("timeout", "Превышено время ожидания S3. Проверьте сеть и доступность сервера.")
    if isinstance(exc, EndpointConnectionError):
        return S3Diagnostic("endpoint", "Не удалось подключиться к S3. Проверьте Endpoint, DNS и сеть.")
    if isinstance(exc, ConnectionClosedError):
        return S3Diagnostic("connection", "Сервер S3 закрыл соединение. Повторите попытку.")
    if isinstance(exc, (NoCredentialsError, PartialCredentialsError)):
        return S3Diagnostic("credentials", "Не найдены корректные S3-ключи. Проверьте настройки.")
    if isinstance(exc, ClientError):
        error = exc.response.get("Error", {})
        metadata = exc.response.get("ResponseMetadata", {})
        # Never include the original server response, headers, request URL or message.
        code = str(error.get("Code", ""))[:64]
        status = metadata.get("HTTPStatusCode")
        try:
            status = int(status) if status is not None else None
        except (TypeError, ValueError):
            status = None
        if code in ("AccessDenied", "InvalidAccessKeyId", "SignatureDoesNotMatch") or status == 403:
            message = "S3 отклонил запрос. Проверьте ключи, регион и права на бакет."
        elif code in ("NoSuchBucket", "404") or status == 404:
            message = "Бакет S3 не найден. Проверьте имя бакета и регион."
        else:
            message = "S3 вернул ошибку. Проверьте конфигурацию и журнал NoraShot."
        return S3Diagnostic("s3_api", message, code=code, status=status)
    return S3Diagnostic("unknown", "Не удалось выполнить операцию S3. Проверьте журнал NoraShot.")


def raise_safe_s3_error(exc: Exception, operation: str) -> None:
    diagnostic = classify_s3_error(exc)
    logger.error(
        "S3 operation failed | operation={} | category={} | code={} | status={} | exception_type={}",
        operation,
        diagnostic.category,
        diagnostic.code or "-",
        diagnostic.status if diagnostic.status is not None else "-",
        type(exc).__name__,
    )
    raise SharingError(diagnostic.message) from None
