from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.infrastructure.database.base import Base
from app.infrastructure.database.session import get_db
from app.main import app
from app.presentation.api.routers import files as files_router
from app.presentation.api.routers import public as public_router
from app.presentation.api.routers import uploads as uploads_router


class FakeStorage:
    def __init__(self) -> None:
        self.created_uploads: list[dict] = []
        self.completed_uploads: list[dict] = []
        self.aborted_uploads: list[dict] = []
        self.deleted_objects: list[str] = []

    def ensure_bucket(self) -> None:
        return None

    def create_multipart_upload(self, object_key: str, content_type: str) -> str:
        upload_id = f"upload-{len(self.created_uploads) + 1}"
        self.created_uploads.append(
            {
                "object_key": object_key,
                "content_type": content_type,
                "upload_id": upload_id,
            }
        )
        return upload_id

    def presign_upload_part(self, object_key: str, upload_id: str, part_number: int) -> str:
        return f"https://storage.test/{object_key}?uploadId={upload_id}&partNumber={part_number}"

    def complete_multipart_upload(
        self,
        object_key: str,
        upload_id: str,
        parts: list[dict],
    ) -> str:
        self.completed_uploads.append(
            {"object_key": object_key, "upload_id": upload_id, "parts": parts}
        )
        return f'"etag-{upload_id}"'

    def abort_multipart_upload(self, object_key: str, upload_id: str) -> None:
        self.aborted_uploads.append({"object_key": object_key, "upload_id": upload_id})

    def presign_download(self, object_key: str, filename: str | None = None) -> str:
        return f"https://storage.test/download/{object_key}?filename={filename or ''}"

    def delete_object(self, object_key: str) -> None:
        self.deleted_objects.append(object_key)


@pytest.fixture()
def api_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[TestClient, FakeStorage]]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Iterator[Session]:
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    fake_storage = FakeStorage()
    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(uploads_router, "storage", fake_storage)
    monkeypatch.setattr(files_router, "storage", fake_storage)
    monkeypatch.setattr(public_router, "storage", fake_storage)
    monkeypatch.setattr("app.main.storage", fake_storage)

    with TestClient(app) as client:
        yield client, fake_storage

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def register_and_login(client: TestClient, email: str, password: str = "password123") -> str:
    register_response = client.post(
        "/api/auth/register",
        json={"email": email, "full_name": "Test User", "password": password},
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def complete_one_part_upload(client: TestClient, token: str, upload_session_id: str) -> dict:
    part_response = client.post(
        f"/api/uploads/{upload_session_id}/parts",
        headers=auth(token),
        json={"part_numbers": [1]},
    )
    assert part_response.status_code == 200
    assert part_response.json()["urls"][0]["method"] == "PUT"

    complete_response = client.post(
        f"/api/uploads/{upload_session_id}/complete",
        headers=auth(token),
        json={"parts": [{"part_number": 1, "etag": "part-etag"}]},
    )
    assert complete_response.status_code == 200
    return complete_response.json()


def test_auth_file_share_and_version_upload_flow(api_client) -> None:
    client, fake_storage = api_client
    token = register_and_login(client, "owner@example.com")

    assert client.get("/api/auth/me").status_code == 401
    assert client.post(
        "/api/auth/login",
        json={"email": "owner@example.com", "password": "wrong-password"},
    ).status_code == 401

    folder_response = client.post(
        "/api/folders/",
        headers=auth(token),
        json={"name": "Reports"},
    )
    assert folder_response.status_code == 201

    initiate_response = client.post(
        "/api/uploads/initiate",
        headers=auth(token),
        json={
            "filename": "report.txt",
            "size_bytes": 12,
            "content_type": "text/plain",
            "folder_id": folder_response.json()["id"],
        },
    )
    assert initiate_response.status_code == 201
    initial_session = initiate_response.json()
    assert initial_session["target_version_number"] == 1

    file_payload = complete_one_part_upload(client, token, initial_session["upload_session_id"])
    file_id = file_payload["id"]
    assert file_payload["status"] == "ready"
    assert file_payload["current_version_number"] == 1

    list_response = client.get(
        "/api/files/",
        headers=auth(token),
        params={"folder_id": folder_response.json()["id"]},
    )
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [file_id]

    download_response = client.get(f"/api/files/{file_id}/download-url", headers=auth(token))
    assert download_response.status_code == 200
    assert download_response.json()["url"].startswith("https://storage.test/download/")

    share_response = client.post(
        "/api/shares/",
        headers=auth(token),
        json={"file_id": file_id, "max_downloads": 1},
    )
    assert share_response.status_code == 201

    public_response = client.get(f"/api/public/{share_response.json()['token']}")
    assert public_response.status_code == 200
    assert public_response.json()["url"].startswith("https://storage.test/download/")

    version_response = client.post(
        f"/api/files/{file_id}/versions/uploads",
        headers=auth(token),
        json={"size_bytes": 24, "content_type": "text/markdown"},
    )
    assert version_response.status_code == 201
    version_session = version_response.json()
    assert version_session["target_version_number"] == 2

    updated_file = complete_one_part_upload(client, token, version_session["upload_session_id"])
    assert updated_file["current_version_number"] == 2
    assert updated_file["size_bytes"] == 24
    assert updated_file["content_type"] == "text/markdown"

    versions_response = client.get(f"/api/files/{file_id}/versions", headers=auth(token))
    assert versions_response.status_code == 200
    assert [item["version_number"] for item in versions_response.json()] == [1, 2]

    first_version_download_response = client.get(
        f"/api/files/{file_id}/versions/1/download-url",
        headers=auth(token),
    )
    assert first_version_download_response.status_code == 200
    assert first_version_download_response.json()["url"].startswith(
        "https://storage.test/download/"
    )

    stats_response = client.get("/api/files/stats/me", headers=auth(token))
    assert stats_response.status_code == 200
    assert stats_response.json() == {"files_count": 1, "total_size_bytes": 24}

    storage_stats_response = client.get("/api/storage/stats", headers=auth(token))
    assert storage_stats_response.status_code == 200
    assert storage_stats_response.json() == {"files_count": 1, "total_size_bytes": 24}
    assert [item["upload_id"] for item in fake_storage.completed_uploads] == [
        "upload-1",
        "upload-2",
    ]


def test_version_upload_needs_write_access_and_abort_keeps_current_file(api_client) -> None:
    client, _ = api_client
    owner_token = register_and_login(client, "owner@example.com")
    reader_token = register_and_login(client, "reader@example.com")

    initiate_response = client.post(
        "/api/uploads/initiate",
        headers=auth(owner_token),
        json={"filename": "plan.pdf", "size_bytes": 10, "content_type": "application/pdf"},
    )
    assert initiate_response.status_code == 201
    file_payload = complete_one_part_upload(
        client,
        owner_token,
        initiate_response.json()["upload_session_id"],
    )
    file_id = file_payload["id"]

    blocked_response = client.post(
        f"/api/files/{file_id}/versions/uploads",
        headers=auth(reader_token),
        json={"size_bytes": 20, "content_type": "application/pdf"},
    )
    assert blocked_response.status_code == 404

    grant_response = client.post(
        "/api/access/",
        headers=auth(owner_token),
        json={
            "file_id": file_id,
            "grantee_email": "reader@example.com",
            "permission": "read",
        },
    )
    assert grant_response.status_code == 201

    readable_response = client.get(f"/api/files/{file_id}", headers=auth(reader_token))
    assert readable_response.status_code == 200

    still_blocked_response = client.post(
        f"/api/files/{file_id}/versions/uploads",
        headers=auth(reader_token),
        json={"size_bytes": 20, "content_type": "application/pdf"},
    )
    assert still_blocked_response.status_code == 404

    version_response = client.post(
        f"/api/files/{file_id}/versions/uploads",
        headers=auth(owner_token),
        json={"size_bytes": 20, "content_type": "application/pdf"},
    )
    assert version_response.status_code == 201

    abort_response = client.post(
        f"/api/uploads/{version_response.json()['upload_session_id']}/abort",
        headers=auth(owner_token),
    )
    assert abort_response.status_code == 200
    assert abort_response.json()["status"] == "aborted"

    file_after_abort = client.get(f"/api/files/{file_id}", headers=auth(owner_token)).json()
    assert file_after_abort["status"] == "ready"
    assert file_after_abort["current_version_number"] == 1
    assert file_after_abort["size_bytes"] == 10
