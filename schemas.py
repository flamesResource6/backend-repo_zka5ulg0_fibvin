"""
Database Schemas for School Management

Each Pydantic model represents a MongoDB collection. The collection name is the
lowercase of the class name (User -> "user").

These schemas are used for validation on create/update operations in the backend.
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Literal
from datetime import date

# Authentication and admin session
class User(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    role: Literal["admin", "viewer"] = "viewer"

class Session(BaseModel):
    email: EmailStr
    token: str
    active: bool = True

# Content models
class NewsArticle(BaseModel):
    title: str
    content: str
    author: Optional[str] = None
    tags: Optional[List[str]] = None
    cover_image: Optional[str] = None
    published_at: Optional[str] = None

class Announcement(BaseModel):
    title: str
    content: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    audience: Optional[List[str]] = None

class GalleryItem(BaseModel):
    title: Optional[str] = None
    image_url: str
    category: Optional[str] = None
    caption: Optional[str] = None

class AdmissionInfo(BaseModel):  # PPDB
    year: str
    description: str
    requirements: Optional[List[str]] = None
    important_dates: Optional[List[str]] = None
    registration_link: Optional[str] = None

class AcademicCalendarEvent(BaseModel):
    title: str
    date: str
    description: Optional[str] = None
    category: Optional[str] = Field(None, description="e.g., libur, ujian, kegiatan")

class ScheduleEntry(BaseModel):
    type: Literal["pelajaran", "ujian", "piket_guru"]
    day: Optional[str] = Field(None, description="e.g., Senin, Selasa")
    time: Optional[str] = None
    subject: Optional[str] = None
    class_name: Optional[str] = None
    teacher: Optional[str] = None
    notes: Optional[str] = None

class OrgNode(BaseModel):
    title: str
    name: Optional[str] = None
    parent_id: Optional[str] = Field(None, description="ObjectId string of parent node")
    order: Optional[int] = 0

class Staff(BaseModel):
    name: str
    role: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    photo_url: Optional[str] = None
    department: Optional[str] = None

class Extracurricular(BaseModel):
    name: str
    coach: Optional[str] = None
    description: Optional[str] = None
    schedule: Optional[str] = None
    photo_url: Optional[str] = None

class SchoolPage(BaseModel):
    key: Literal["sejarah", "visi_misi", "fasilitas", "kontak_alamat"]
    title: Optional[str] = None
    content: Optional[str] = None

class Achievement(BaseModel):
    title: str
    description: Optional[str] = None
    date: Optional[str] = None
    images: Optional[List[str]] = None
