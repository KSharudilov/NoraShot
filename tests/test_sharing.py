from __future__ import annotations

from datetime import timezone

import pytest

from norashot.config import UploadConfig
from norashot.core.sharing.base import SharingError
from norashot.core.sharing.credentials import S3Credentials
from norashot.core.sharing.s3 import S3Provider


PNG_HEADER = b"\x89PNG\r\n\x1a\n"


class FakeS3:
    def __init__(self) -> None:
        self.uploads = []
        self.presign_args = None
        self.deleted = []

    def put_object(self, **kwargs):
        self.uploads.append(kwargs)

    def generate_presigned_url(self, operation, **kwargs):
        self.presign_args = (operation, kwargs)
        return "https://example.test/signed-result"

    def delete_object(self, **kwargs):
        self.deleted.append(kwargs)


def config(**kwargs):
    values = dict(
        enabled=True,
        provider="s3",
        endpoint="https://s3.example.test",
        bucket="screenshots",
        prefix_template="%Y/%m/%d",
        region="us-east-1",
        link_ttl_seconds=86400,
    )
    values.update(kwargs)
    return UploadConfig(**values)


def test_s3_private_upload_and_expiring_link(monkeypatch):
    fake = FakeS3()
    monkeypatch.setattr("norashot.core.sharing.s3.boto3.client", lambda *a, **kw: fake)
    provider = S3Provider(config(), S3Credentials("access", "secret"))
    result = provider.upload(PNG_HEADER + b"test")
    assert result.object_key.endswith(".png")
    assert result.object_key.count("/") == 3
    assert result.url == "https://example.test/signed-result"
    assert result.expires_at.tzinfo == timezone.utc
    assert fake.uploads[0]["ContentType"] == "image/png"
    assert fake.uploads[0]["CacheControl"] == "private, no-store"
    assert "ACL" not in fake.uploads[0]
    assert fake.presign_args[1]["ExpiresIn"] == 86400
    assert fake.presign_args[1]["HttpMethod"] == "GET"
    provider.delete(result.object_key)
    assert fake.deleted[0]["Key"] == result.object_key


@pytest.mark.parametrize("endpoint", [
    "http://s3.example.test",
    "https://user:password@s3.example.test",
    "https://s3.example.test/path",
])
def test_reject_insecure_endpoint(endpoint):
    with pytest.raises(SharingError):
        S3Provider(config(endpoint=endpoint), S3Credentials("a", "b"))


@pytest.mark.parametrize("seconds", [0, 30, 604801])
def test_reject_invalid_expiration(seconds):
    with pytest.raises(SharingError):
        S3Provider(config(link_ttl_seconds=seconds), S3Credentials("a", "b"))


def test_reject_invalid_image(monkeypatch):
    monkeypatch.setattr("norashot.core.sharing.s3.boto3.client", lambda *a, **kw: FakeS3())
    provider = S3Provider(config(), S3Credentials("a", "b"))
    with pytest.raises(SharingError):
        provider.upload(b"not PNG")


def test_reject_non_s3_provider():
    from norashot.core.sharing.manager import get_provider
    with pytest.raises(SharingError):
        get_provider(config(provider="norashot_server"))
