from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, constr

Code = constr(strip_whitespace=True, to_lower=True, pattern=r"^[a-z0-9_.-]+$")

class CategoryCreateIn(BaseModel):
    code: Code
    label: constr(min_length=1)
    description: Optional[str] = None

class CategoryOut(BaseModel):
    id: int
    code: str
    label: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class ProtocolCreateIn(BaseModel):
    category_id: Optional[int] = Field(None, description="NULL = sans catégorie")
    code: Code
    title: constr(min_length=1)
    summary: Optional[str] = None
    tags: List[str] = []
    is_published: bool = False
    external_url: Optional[str] = None

class ProtocolUpdateIn(BaseModel):
    category_id: Optional[int] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    tags: Optional[List[str]] = None
    is_published: Optional[bool] = None
    external_url: Optional[str] = None

class ProtocolOut(BaseModel):
    id: int
    category_id: Optional[int]
    code: str
    title: str
    summary: Optional[str]
    tags: List[str]
    is_published: bool
    created_at: datetime
    updated_at: datetime

class ProtocolVersionCreateIn(BaseModel):
    body_md: constr(min_length=1)
    changelog: Optional[str] = None
    publish: bool = False  # si True → published_at=NOW()

class ProtocolVersionOut(BaseModel):
    id: int
    protocol_id: int
    version: int
    body_md: str
    changelog: Optional[str]
    published_at: Optional[datetime]
    created_at: datetime
