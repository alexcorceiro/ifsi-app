from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, constr, Field

Code = constr(strip_whitespace=True, to_lower=True, pattern=r"^[a-z0-9_.-]+$")

class UECreateIn(BaseModel):
    program_id: int
    code: Code
    title: constr(min_length=1)
    year_no: int = Field(..., ge=1, le=3)
    sem_no: int = Field(..., ge=1, le=6)
    ects: Optional[float] = None
    description: Optional[str] = None

class UEUpdateIn(BaseModel):
    title: Optional[str] = None
    year_no: Optional[int] = Field(None, ge=1, le=3)
    sem_no: Optional[int] = Field(None, ge=1, le=6)
    ects: Optional[float] = None
    description: Optional[str] = None

class UEOut(BaseModel):
    id: int
    program_id: int
    code: str
    title: str
    year_no: int
    sem_no: int
    ects: Optional[float] = None
    description: Optional[str] = None
    created_at: datetime

class UEListOut(BaseModel):
    items: List[UEOut]
    limit: int
    offset: int
    total: int
