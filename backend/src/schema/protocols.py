from typing import Optional, List
from pydantic import BaseModel, Field

class ProtocolCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=120)
    title: str = Field(..., min_length=1, max_length=300)
    summary: Optional[str] = None
    category_id: Optional[int] = None
    tags: List[str] = Field(default_factory=list)
    body_md: Optional[str] = None
    publish_now: bool = False

class ProtocolUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    summary: Optional[str] = None
    category_id: Optional[int] = None
    tags: Optional[List[str]] = None
    is_published: Optional[bool] = None

class ProtocolNewVersion(BaseModel):
    body_md: str
    changelog: Optional[str] = None
    publish_now: bool = False


class ProtocolVersionOut(BaseModel):
    id: int 
    version: int
    body_md: str
    changelog: Optional[str]
    published_at: Optional[str]
    created_at: str

class ProtocolOut(BaseModel):
    id: int
    code: str
    title: str
    summary: Optional[str]
    category_id: Optional[int]
    tags: List[str]
    is_published: bool
    created_by: Optional[int]
    created_at: str
    updated_at: str
    latest_version: Optional[ProtocolVersionOut] = None

class ProtocolListOut(BaseModel):
    total: int
    items: List[ProtocolOut]
    limit: int
    offset: int
    