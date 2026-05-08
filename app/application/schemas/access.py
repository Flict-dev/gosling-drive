from pydantic import BaseModel, ConfigDict, EmailStr


class AccessGrantCreate(BaseModel):
    file_id: str
    grantee_email: EmailStr
    permission: str


class AccessGrantRead(BaseModel):
    id: str
    file_id: str
    owner_id: str
    grantee_id: str
    permission: str

    model_config = ConfigDict(from_attributes=True)

