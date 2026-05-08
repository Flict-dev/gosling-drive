from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    id: str
    user_id: str | None
    action: str
    resource_type: str
    resource_id: str | None
    metadata_json: dict | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

