from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class CategoryIn(BaseModel):
    code: str
    label: str
    description: Optional[str] = None

class CategoryUpdate(BaseModel):
    label: Optional[str] = None
    description: Optional[str] = None

class CategoryOut(BaseModel):
    id: int
    code: str
    label: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class CategoryListOut(BaseModel):
    items: list[CategoryOut]
    limit: int
    offset: int
    total: int
