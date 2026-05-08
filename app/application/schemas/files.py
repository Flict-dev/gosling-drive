from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FileRead(BaseModel):
    id: str
    owner_id: str
    folder_id: str | None
    name: str
    content_type: str
    size_bytes: int
    checksum_sha256: str | None
    bucket: str
    object_key: str
    status: str
    current_version_number: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FileUpdate(BaseModel):
    name: str | None = None
    folder_id: str | None = None


class FileDownloadUrl(BaseModel):
    url: str
    expires_in_seconds: int


class StorageStats(BaseModel):
    files_count: int
    total_size_bytes: int

