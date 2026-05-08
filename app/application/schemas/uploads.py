from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UploadInitiateRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    size_bytes: int = Field(gt=0)
    content_type: str = Field(default="application/octet-stream", max_length=255)
    folder_id: str | None = None
    checksum_sha256: str | None = Field(default=None, min_length=64, max_length=64)


class UploadInitiateResponse(BaseModel):
    upload_session_id: str
    file_id: str
    provider_upload_id: str
    bucket: str
    object_key: str
    part_size: int
    total_parts: int


class UploadPartUrlRequest(BaseModel):
    part_numbers: list[int] = Field(min_length=1)


class UploadPartUrl(BaseModel):
    part_number: int
    method: str = "PUT"
    url: str


class UploadPartUrlResponse(BaseModel):
    upload_session_id: str
    urls: list[UploadPartUrl]


class CompletedUploadPart(BaseModel):
    part_number: int = Field(ge=1)
    etag: str = Field(min_length=1)


class UploadCompleteRequest(BaseModel):
    parts: list[CompletedUploadPart] = Field(min_length=1)


class UploadSessionRead(BaseModel):
    id: str
    file_id: str
    owner_id: str
    provider_upload_id: str
    bucket: str
    object_key: str
    part_size: int
    total_parts: int
    status: str
    created_at: datetime
    completed_at: datetime | None
    expires_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

