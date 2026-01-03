from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator




DocMode= Literal["CLASSIC", "SLIDE","SEMI_MANUAL", "MANUAL","UNKNOWN"]
VersionStatus= Literal["draft", "published","archived"]



def _strip_or_none(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    v = v.strip()
    return v or None

class PageMeta(BaseModel):
    model_config = ConfigDict(extra="ignore")
    page_no: int = Field(..., ge=1)
    n_words: Optional[int] = Field(default=None, ge=0)
    n_drawings: Optional[int] = Field(default=None, ge=0)
    is_slide_like: Optional[bool] = None


class InspectPdfTypeResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    filename: Optional[str] = None
    size_bytes: Optional[int] = Field(default=None, ge=0)
    is_slide: bool = False

    slide_ratio: float = Field(default=0.0, ge=0, le=1.0)

    n_pages_total: int = Field(default=0, ge=0)
    n_pages_scanned: int = Field(default=0, ge=0)

    mean_aspect_ratio: float = Field(default=0.0, ge=0.0)
    mean_words_per_page: float = Field(default=0.0, ge=0.0)
    mean_drawing_per_page: float = Field(default=0.0, ge=0.0)

    error: Optional[str] = None
    pages: List[PageMeta] = Field(default_factory=list)


class CourseBase(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ue_id: int = Field(..., ge=1, description="academics.eu.id")
    code: str = Field(..., min_length=1, max_length=64)
    title: str = Field(..., min_length=1, max_digits=255)
    description: Optional[str] = Field(default=None, max_length=10_000)

    order_no: int = Field(default=0, ge=0)
    doc_mode: DocMode = Field(default="CLASSIC")

    @field_validator("code")
    @classmethod
    def normalize_code(cls, v: str) -> str:
        v = (v or "").strip()
        if not v: 
            raise ValueError("code ne peut pas etre vide")
        return v
    
    @field_validator("title")
    @classmethod
    def normalize_title(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("title ne peut pas etre vide ")
        return v
    
    @field_validator("description")
    @classmethod
    def normalise_desc(cls, v: Optional[str]) -> Optional[str]:
        return _strip_or_none(v)
    

class CourseCreate(CourseBase):
        pass


class CourseUpdate(BaseModel):

    model_config = ConfigDict(extra="forbid")

    ue_id: Optional[int] = Field(default=None, ge=1)
    code: Optional[str] = Field(default=None, min_length=1, max_length=64)
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=10_000)

    order_no: Optional[int] = Field(default=None, ge=0)
    doc_mode: Optional[DocMode] = None
    published_version_id: Optional[int] = Field(default=None, ge=1)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, v: Optional[str]) -> Optional[str]:
        return _strip_or_none(v)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, v: Optional[str]) -> Optional[str]:
        return _strip_or_none(v)

    @field_validator("description")
    @classmethod
    def normalize_desc(cls, v: Optional[str]) -> Optional[str]:
        return _strip_or_none(v)


class CourseOut(BaseModel):
   
    model_config = ConfigDict(from_attributes=True)

    id: int
    ue_id: int
    code: str
    title: str
    description: Optional[str]

    order_no: int
    doc_mode: DocMode

    published_version_id: Optional[int] = None

    created_at: datetime
    updated_at: datetime


class CourseVersionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version_label: str = Field(..., min_length=1, max_length=128)
    status: VersionStatus = Field(default="draft")

    @field_validator("version_label")
    @classmethod
    def normalize_label(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("version_label ne peut pas être vide")
        return v


class CourseVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    version_label: str
    status: VersionStatus
    created_at: datetime
    updated_at: datetime

class SectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    version_id: int
    parent_id: Optional[int]
    position: int
    title: str
    content_md: Optional[str]
    created_at: datetime
    updated_at: datetime


class CourseDetailOut(BaseModel):
    """
    Un "read" enrichi: course + versions + sections (optionnel).
    """
    model_config = ConfigDict(extra="ignore")

    course: CourseOut
    versions: List[CourseVersionOut] = Field(default_factory=list)
    sections: List[SectionOut] = Field(default_factory=list)

class IngestInspectInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    slide_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    mean_aspect_ratio: float = Field(default=0.0, ge=0.0)
    mean_words_per_page: float = Field(default=0.0, ge=0.0)
    mean_drawings_per_page: float = Field(default=0.0, ge=0.0)
    n_pages_total: Optional[int] = Field(default=None, ge=0)
    n_pages_scanned: Optional[int] = Field(default=None, ge=0)


class IngestResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ok: bool = True
    doc_mode: DocMode
    images_policy: Literal["AUTO", "SEMI_MANUAL", "PRUDENT"]

    slide_forced: Optional[bool] = None

    source_id: int
    course_id: Optional[int] = None
    version_id: Optional[int] = None

    pages_pdf: int = Field(..., ge=0)
    pages_db: int = Field(..., ge=0)
    images_db: int = Field(..., ge=0)

    coverage_ok: bool = False

    manual_images_received: int = Field(default=0, ge=0)
    manual_images_keys_detected: List[str] = Field(default_factory=list)

    inspect: IngestInspectInfo

class CoursesListQuery(BaseModel):
    """
    Tu peux l’utiliser comme dépendance FastAPI:
    query: CoursesListQuery = Depends()
    """
    model_config = ConfigDict(extra="forbid")

    q: Optional[str] = Field(default=None, description="Recherche texte (title/code)")
    ue_id: Optional[int] = Field(default=None, ge=1)
    doc_mode: Optional[DocMode] = None

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)

    sort: Literal["updated_at", "created_at", "title"] = "updated_at"
    order: Literal["asc", "desc"] = "desc"

    @field_validator("q")
    @classmethod
    def normalize_q(cls, v: Optional[str]) -> Optional[str]:
        return _strip_or_none(v)


class CoursesListResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    items: List[CourseOut]
    page: int
    page_size: int
    total: int