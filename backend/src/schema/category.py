from typing import Optional, List
from pydantic import BaseModel, Field

class CategoryIn(BaseModel):
    code: str = Field(..., min_length=1, max_length=120)
    label: str = Field(..., min_length=1, max_length=120)
    descritpion: Optional[str] = None

class CategoryUpdate(BaseModel):
    label: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None

class CategoryOut(BaseModel):
    id: int
    code: str
    label: str
    description: Optional[str]
    created_at: str
    updated_at: str

class CategoryListOut(BaseModel):
    total: int
    items: List[CategoryOut]
    limit: int
    affset: int