from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ShareLinkCreate(BaseModel):
    file_id: str
    expires_at: datetime | None = None
    max_downloads: int | None = Field(default=None, ge=1)


class ShareLinkRead(BaseModel):
    id: str
    file_id: str
    owner_id: str
    token: str
    is_active: bool
    expires_at: datetime | None
    max_downloads: int | None
    download_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

