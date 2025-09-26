from pydantic import BaseModel, Field
from typing import Optional, List


class PermissionOut(BaseModel):
    id: int
    code: str
    label: str
    description: Optional[str] = None

class PermissionListOut(BaseModel):
    items: List[PermissionOut]
    limit: int
    offset: int
    total: int

class PermissionCreateIn(BaseModel):
    code: str = Field(..., pattern=r"^[a-z0-9_.:-]+$", min_length=3, max_length=64)
    label: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)

class PermissionUpdateIn(BaseModel):
    label: Optional[str] = None
    description: Optional[str] = None