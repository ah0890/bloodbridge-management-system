from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Role


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=1, max_length=200)


class BloodBankRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    city: str
    provenance: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    full_name: str
    role: Role
    blood_bank: BloodBankRef | None = None
    is_active: bool
    is_demo: bool
    last_login_at: datetime | None = None


class SessionOut(BaseModel):
    user: UserOut
    permissions: list[str]
    csrf_token: str
    expires_at: datetime | None = None
