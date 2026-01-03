from typing import Optional, List 
from datetime import datetime
from pydantic import BaseModel, constr

Code = constr(strip_whitespace=True, to_lower=True, pattern=r"^[a-z0-9_.-]+$")

class ProgramCreateIn(BaseModel):
    code: Code
    label: constr(min_length=1)
    ects_total: Optional[int] = None

class ProgramUpdateIn(BaseModel):
    label: Optional[str] = None
    ects_total: Optional[int] = None

class ProgramOut(BaseModel):
    id: int
    code: str
    label: str
    ects_total: Optional[int] = None
    created_at: datetime

class ProgramListOut(BaseModel):
    items: List[ProgramOut]
    limit: int 
    offset: int
    total: int