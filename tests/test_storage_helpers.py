from app.application.services.object_keys import build_object_key
from app.infrastructure.storage.s3 import normalize_etag


def test_build_object_key_keeps_user_scope_and_sanitizes_filename() -> None:
    object_key = build_object_key("user-1", "../report.pdf")

    assert object_key.startswith("users/user-1/")
    assert object_key.endswith("/report.pdf")
    assert ".." not in object_key


def test_normalize_etag_preserves_existing_quotes() -> None:
    assert normalize_etag('"abc"') == '"abc"'


def test_normalize_etag_adds_quotes_when_missing() -> None:
    assert normalize_etag("abc") == '"abc"'

