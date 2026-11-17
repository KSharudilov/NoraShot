"""Connectivity diagnostics without real S3 calls or credentials."""
from __future__ import annotations

from botocore.exceptions import ClientError
from norashot.config import UploadConfig
from norashot.core.sharing.credentials import S3Credentials
from norashot.core.sharing.s3 import S3Provider


def _provider(monkeypatch, client):
    monkeypatch.setattr("norashot.core.sharing.s3.boto3.client", lambda *a, **kw: client)
    return S3Provider(
        UploadConfig(endpoint="https://s3.example.test", bucket="screenshots", region="us-east-1"),
        S3Credentials("test", "test"),
    )


def test_successful_bucket_check(monkeypatch):
    class Client:
        def head_bucket(self, **kwargs):
            assert kwargs["Bucket"] == "screenshots"

    diag = _provider(monkeypatch, Client()).diagnose_connection()
    assert diag.category == "ok"


def test_head_bucket_403_is_permission_ambiguity(monkeypatch):
    class Client:
        def head_bucket(self, **kwargs):
            raise ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "Denied"},
                 "ResponseMetadata": {"HTTPStatusCode": 403}}, "HeadBucket"
            )

    diag = _provider(monkeypatch, Client()).diagnose_connection()
    assert diag.category == "permissions_unknown"
    assert diag.status == 403


def test_missing_bucket_is_reported(monkeypatch):
    class Client:
        def head_bucket(self, **kwargs):
            raise ClientError(
                {"Error": {"Code": "NoSuchBucket", "Message": "No such bucket"},
                 "ResponseMetadata": {"HTTPStatusCode": 404}}, "HeadBucket"
            )

    diag = _provider(monkeypatch, Client()).diagnose_connection()
    assert diag.category == "s3_api"
    assert diag.status == 404
