from pydantic import BaseModel, Field
from typing import List, Optional

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=20)
    password: str = Field(..., min_length=6)
    role: str = Field(..., pattern="^(Student|Professor|Manager)$")
    name: str

class CourseCreate(BaseModel):
    id: str = Field(..., min_length=2, max_length=10)
    name: str = Field(..., min_length=3)
    credits: int = Field(..., ge=1, le=5)
    professor_id: int = Field(..., alias="professorId") # Catches the UI's camelCase payload

class GradeSubmit(BaseModel):
    student_username: str
    course_id: str
    grade: float = Field(..., ge=0, le=20) # Strict Iranian grading scale

class Token(BaseModel):
    access_token: str
    token_type: str

# --- New Schemas for Professor Dashboard ---

class GradeEntry(BaseModel):
    studentId: int
    grade: float = Field(..., ge=0, le=20) # Applied your strict scale here too

class BulkGradePayload(BaseModel):
    grades: List[GradeEntry]
