from pydantic import BaseModel, Field
from typing import List, Optional

class UserLogin(BaseModel):
    username: str
    password: str

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class ForgotPasswordReq(BaseModel):
    username: str
    
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=20)
    password: str = Field(..., min_length=6)
    role: str = Field(..., pattern="^(Student|Professor|Manager)$")
    name: str

class CourseCreate(BaseModel):
    id: str = Field(..., min_length=2, max_length=10)
    name: str = Field(..., min_length=3)
    credits: int = Field(..., ge=1, le=5)
    professor_id: Optional[int] = Field(None, alias="professorId")
    selection_deadline: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    exam_day: Optional[str] = None
    is_active: bool = True
    is_hidden: bool = False

class GradeSubmit(BaseModel):
    student_username: str
    course_id: str
    grade: float = Field(..., ge=0, le=20) 

class Token(BaseModel):
    access_token: str
    token_type: str

class GradeEntry(BaseModel):
    studentId: int
    grade: float = Field(..., ge=0, le=20)

class BulkGradePayload(BaseModel):
    grades: List[GradeEntry]