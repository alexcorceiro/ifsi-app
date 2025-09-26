from typing import Optional, List
from datetime import datetime
from  pydantic import BaseModel, Field, constr


Code = constr(strip_whitespace= True, to_lower= True, pattern=r"^[a-z0-9_.-]+^$")

class RoleCreateIn(BaseModel):
    code: Code = Field(..., description="Code unique du rôle (ex: admin, editor)")
    label: constr(min_length=1)
    description: Optional[str] = None

class RoleUpdateIn(BaseModel):
    label: Optional[str] = None
    description: Optional[str] = None

class PermissionBrief(BaseModel):
    id: int
    code: str
    label: str

class RoleOut(BaseModel):
    id: int
    code: str
    label: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    permissions: List[PermissionBrief] = []

class RolesListOut(BaseModel):
    items: List[RoleOut]
    limit: int
    offset: int
    total: int