from pydantic import BaseModel, Field
from datetime import datetime

class LessonProgressIn(BaseModel):
    status: str = Field(..., pattern=r"^(started|completed)$")

class LessonProgressOut(BaseModel):
    user_id: int
    lesson_id: int
    status: str
    updated_at: datetime