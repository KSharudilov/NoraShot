from __future__ import annotations

from botocore.exceptions import ClientError, EndpointConnectionError, SSLError
from norashot.core.sharing.diagnostics import classify_s3_error, raise_safe_s3_error
from norashot.core.sharing.base import SharingError


def test_tls_errors_have_safe_message():
    # The exception may include a signed URL: never repeat its raw string.
    error = SSLError(endpoint_url="https://example.test/?X-Amz-Signature=SECRET", error="SSL fail")
    result = classify_s3_error(error)
    assert result.category == "tls"
    assert "HTTPS" in result.message
    assert "SECRET" not in result.message


def test_s3_access_denied_reports_only_code():
    error = ClientError(
        {
            "Error": {"Code": "AccessDenied", "Message": "sensitive details"},
            "ResponseMetadata": {"HTTPStatusCode": 403},
        },
        "PutObject",
    )
    result = classify_s3_error(error)
    assert result.category == "s3_api"
    assert result.status == 403
    assert result.code == "AccessDenied"
    assert "sensitive" not in result.message


def test_network_endpoint_is_classified():
    error = EndpointConnectionError(endpoint_url="https://s3.example.test")
    assert classify_s3_error(error).category == "endpoint"


def test_safe_raise_does_not_expose_original_error(caplog):
    error = SSLError(endpoint_url="https://example.test/?X-Amz-Signature=PRIVATE", error="SSL fail")
    try:
        raise_safe_s3_error(error, "upload")
    except SharingError as safe:
        assert "PRIVATE" not in str(safe)
        assert "SSL" not in str(safe)
    else:
        assert False, "SharingError should have been raised"


def test_unknown_error_is_generic():
    result = classify_s3_error(RuntimeError("secret"))
    assert result.category == "unknown"
    assert "secret" not in result.message
