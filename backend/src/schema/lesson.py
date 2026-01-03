from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, constr, Field

Code = constr(strip_whitespace=True, to_lower=True, pattern=r"^[a-z0-9_.-]+$")

class LessonCreateIn(BaseModel):
    course_id: Optional[int] = Field(None, description="Cours parent (peut etre null)")
    code: Code
    title: constr(min_length=1)
    summary: Optional[str] = None
    body_md: Optional[str] = None

class LessonUpdate(BaseModel):
    course_id: Optional[int] = None
    title: Optional[str] = None
    summary: Optional[str] =  None
    body_md: Optional[str] = None

class LessonOut(BaseModel):
    id: int
    course_id: Optional[int]
    code: str
    title: str
    summary: Optional[str] = None
    body_md: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class LessonListOut(BaseModel):
    items: List[LessonOut]
    limit: int
    offset: int
    total: int 