from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from sqlalchemy import func
from datetime import datetime
from app.core.database import (
    get_db, User, Course, Enrollment, SignupRequest, 
    CourseSession, PasswordResetRequest
)
from app.core.schemas import (
    UserCreate, GradeSubmit, Token, 
    BulkGradePayload, PasswordChange
)
from app.core.security import (
    hash_password, verify_password, 
    create_access_token, get_current_user_token
)
from pydantic import BaseModel, Field

# Inline schemas and base models
# ==========================================
class UserLogin(BaseModel):
    username: str
    password: str

class CourseEnrollList(BaseModel):
    course_ids: List[str]

class StudentSignupParams(BaseModel):
    national_id: str
    name: str
    phone_number: Optional[str] = None
    address: Optional[str] = None
    date_of_birth: Optional[str] = None

class ForgotPasswordReq(BaseModel):
    username: str

class AdminStudentCreate(BaseModel):
    username: str  
    national_id: str
    name: str
    password: Optional[str] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    date_of_birth: Optional[str] = None

class AdminCourseCreate(BaseModel):
    id: str
    name: str
    credits: int
    professor_id: Optional[int] = None
    selection_deadline: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    exam_day: Optional[str] = None
    is_active: bool = True
    is_hidden: bool = False

class AdminProfessorCreate(BaseModel):
    username: str
    name: str
    password: Optional[str] = None
    national_id: Optional[str] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    date_of_birth: Optional[str] = None
class SessionCreate(BaseModel):
    course_id: str
    day: str
    start_time: str
    end_time: str
    location: str
    session_type: str

router = APIRouter()


# Auth part
# ==========================================
@router.get("/auth/profile", tags=["Auth"])
def get_user_profile(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    username = current_user.get("sub") or current_user.get("username")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "username": user.username,
        "name": user.name,
        "role": user.role,
        "national_id": user.national_id or "N/A",
        "phone_number": user.phone_number or "N/A",
        "address": user.address or "N/A",
        "date_of_birth": user.date_of_birth or "N/A"
    }

@router.put("/auth/change-password", tags=["Auth"])
def change_password(req: PasswordChange, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    username = current_user.get("sub") or current_user.get("username")
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if not verify_password(req.current_password, user.password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
        
    user.password = hash_password(req.new_password)
    db.commit()
    return {"message": "Password updated successfully"}

@router.post("/auth/forgot-password", tags=["Auth"])
def request_password_reset(req: ForgotPasswordReq, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user:
        return {"message": "If the account exists, a reset request has been sent to the admin."}
        
    existing = db.query(PasswordResetRequest).filter(
        PasswordResetRequest.user_id == user.id, 
        PasswordResetRequest.status == "Pending"
    ).first()
    
    if not existing:
        new_req = PasswordResetRequest(user_id=user.id)
        db.add(new_req)
        db.commit()
        
    return {"message": "Password reset request sent to admin."}
    
@router.post("/auth/signup", tags=["Auth"])
def submit_signup_request(req: StudentSignupParams, db: Session = Depends(get_db)):
    if db.query(User).filter(User.national_id == req.national_id).first():
        raise HTTPException(status_code=400, detail="This National ID is already registered.")
        
    existing_req = db.query(SignupRequest).filter(
        SignupRequest.national_id == req.national_id, 
        SignupRequest.status == "Pending"
    ).first()
    
    if existing_req:
        raise HTTPException(status_code=400, detail="A pending request for this ID already exists.")
        
    new_request = SignupRequest(
        national_id=req.national_id,
        name=req.name,
        phone_number=req.phone_number,
        address=req.address,
        date_of_birth=req.date_of_birth,
        status="Pending"
    )
    db.add(new_request)
    db.commit()
    return {"message": "Signup request submitted successfully."}

@router.post("/auth/login", response_model=Token, tags=["Auth"])
def login(req: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    
    if not user or not verify_password(req.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="نام کاربری یا رمز عبور اشتباه است"
        )
        
    token = create_access_token(data={"sub": user.username, "role": user.role})
    return {"access_token": token, "token_type": "bearer"}

#adminDashoard
# ==========================================
@router.get("/admin/stats", tags=["Admin"])
def get_admin_stats(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"].lower() not in ["manager", "admin"]: 
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        
    total_courses = db.query(Course).filter(Course.is_active == True).count()
    total_students = db.query(User).filter(User.role == "Student").count()
    avg_grade = db.query(func.avg(Enrollment.grade)).scalar() or 0.0
    
    return {
        "activeCourses": total_courses,
        "totalStudents": total_students,
        "averageGrade": round(avg_grade, 2),
        "attendanceRate": 92.5 
    }

# Requests management
@router.get("/admin/signup-requests", tags=["Admin"])
def get_signup_requests(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"].lower() not in ["manager", "admin"]:
        raise HTTPException(status_code=403)
        
    requests = db.query(SignupRequest).filter(SignupRequest.status == "Pending").all()
    return [{"id": r.id, "username": r.national_id, "name": r.name, "status": r.status} for r in requests]

@router.get("/admin/recent-requests", tags=["Admin"])
def get_recent_requests(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"].lower() not in ["manager", "admin"]:
        raise HTTPException(status_code=403)
        
    requests = db.query(SignupRequest).filter(SignupRequest.status == "Pending").order_by(SignupRequest.id.desc()).limit(4).all()
    return [{"id": r.id, "name": r.name, "username": r.national_id} for r in requests]

@router.post("/admin/signup-requests/{req_id}/approve", tags=["Admin"])
def approve_request(req_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"].lower() not in ["manager", "admin"]:
        raise HTTPException(status_code=403)
        
    signup_req = db.query(SignupRequest).filter(SignupRequest.id == req_id).first()
    if not signup_req or signup_req.status != "Pending":
        raise HTTPException(status_code=404, detail="Valid pending request not found")
        
    if db.query(User).filter(User.national_id == signup_req.national_id).first():
        raise HTTPException(status_code=400, detail="This National ID is already registered")
        
    student_id = f"99{signup_req.id:04d}" 
    
    new_user = User(
        username=student_id,
        password=hash_password(signup_req.national_id), 
        name=signup_req.name,
        role="Student",
        national_id=signup_req.national_id,
        phone_number=signup_req.phone_number,
        address=signup_req.address,
        date_of_birth=signup_req.date_of_birth
    )
    db.add(new_user)
    
    signup_req.status = "Approved"
    db.commit()
    return {"message": f"Student approved. Assigned ID: {student_id}"}

@router.post("/admin/signup-requests/{req_id}/reject", tags=["Admin"])
def reject_request(req_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"].lower() not in ["manager", "admin"]:
        raise HTTPException(status_code=403)
        
    signup_req = db.query(SignupRequest).filter(SignupRequest.id == req_id).first()
    if not signup_req:
        raise HTTPException(status_code=404, detail="Request not found")
        
    signup_req.status = "Rejected"
    db.commit()
    return {"message": "Request successfully rejected"}

#Password Reset
@router.get("/admin/password-requests", tags=["Admin"])
def get_password_requests(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"].lower() not in ["manager", "admin"]:
        raise HTTPException(status_code=403)
        
    requests = db.query(PasswordResetRequest, User).join(User, PasswordResetRequest.user_id == User.id)\
                 .filter(PasswordResetRequest.status == "Pending").all()
    
    return [{
        "request_id": req.id,
        "username": user.username,
        "name": user.name,
        "national_id": user.national_id
    } for req, user in requests]

@router.post("/admin/password-requests/{req_id}/approve", tags=["Admin"])
def approve_password_reset(req_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"].lower() not in ["manager", "admin"]:
        raise HTTPException(status_code=403)
        
    reset_req = db.query(PasswordResetRequest).filter(PasswordResetRequest.id == req_id).first()
    if not reset_req or reset_req.status != "Pending":
        raise HTTPException(status_code=404, detail="Valid request not found")
        
    user = db.query(User).filter(User.id == reset_req.user_id).first()
    if not user or not user.national_id:
        raise HTTPException(status_code=400, detail="User lacks a National ID to reset to.")
        
    user.password = hash_password(user.national_id)
    reset_req.status = "Approved"
    
    db.commit()
    return {"message": "Password has been reset to the user's National ID."}

#Student management
@router.get("/admin/students", tags=["Admin"])
def get_all_students(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"].lower() not in ["manager", "admin"]: 
        raise HTTPException(status_code=403)
        
    students = db.query(User).filter(User.role == "Student").all()
    
    result = []
    for student in students:
        enrollments = db.query(Enrollment).filter(Enrollment.student_id == student.id).all()
        valid_grades = [e.grade for e in enrollments if e.grade is not None]
        gpa = sum(valid_grades) / len(valid_grades) if valid_grades else 0.0
        
        result.append({
            "db_id": student.id,
            "student_number": student.username,
            "name": student.name,
            "national_id": student.national_id,
            "enrolled_courses": len(enrollments),
            "gpa": round(gpa, 2),
            "status": "Active"
        })
    return result

@router.post("/admin/students", tags=["Admin"])
def create_student(req: AdminStudentCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"].lower() not in ["manager", "admin"]:
        raise HTTPException(status_code=403)
        
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="Student number already exists")
        
    new_student = User(
        username=req.username,
        password=hash_password(req.password or req.national_id), 
        name=req.name,
        role="Student",
        national_id=req.national_id,
        phone_number=req.phone_number,
        address=req.address,
        date_of_birth=req.date_of_birth
    )
    db.add(new_student)
    db.commit()
    return {"message": "Student created successfully"}

@router.put("/admin/students/{student_id}", tags=["Admin"])
def update_student(student_id: int, req: AdminStudentCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"].lower() not in ["manager", "admin"]:
        raise HTTPException(status_code=403)
        
    student = db.query(User).filter(User.id == student_id, User.role == "Student").first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    if req.username != student.username and db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="Student number already exists")
            
    student.username = req.username
    student.name = req.name
    student.national_id = req.national_id
    if req.password: 
        student.password = hash_password(req.password)
        
    db.commit()
    return {"message": "Student updated successfully"}

@router.delete("/admin/students/{student_id}", tags=["Admin"])
def delete_student(student_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"].lower() not in ["manager", "admin"]:
        raise HTTPException(status_code=403)
        
    student = db.query(User).filter(User.id == student_id, User.role == "Student").first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    db.query(Enrollment).filter(Enrollment.student_id == student_id).delete()
    db.delete(student)
    db.commit()
    return {"message": "Student deleted successfully"}

#Professor management
@router.get("/admin/professors", tags=["Admin"])
def get_professors(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"].lower() not in ["manager", "admin"]: 
        raise HTTPException(status_code=403)
        
    professors = db.query(User).filter(User.role == "Professor").all()
    return [{"id": prof.id, "name": prof.name, "username": prof.username} for prof in professors]

@router.post("/admin/professors", tags=["Admin"])
def create_professor(req: AdminProfessorCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"].lower() not in ["manager", "admin"]:
        raise HTTPException(status_code=403)
        
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="Username is already taken")
        
    new_prof = User(
        username=req.username,
        password=hash_password(req.password),
        name=req.name,
        role="Professor",
        national_id=req.national_id,
        phone_number=req.phone_number,
        address=req.address,
        date_of_birth=req.date_of_birth
    )
    db.add(new_prof)
    db.commit()
    return {"message": "Professor created successfully"}

@router.put("/admin/professors/{prof_id}", tags=["Admin"])
def update_professor(prof_id: int, req: AdminProfessorCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"].lower() not in ["manager", "admin"]:
        raise HTTPException(status_code=403)
        
    prof = db.query(User).filter(User.id == prof_id, User.role == "Professor").first()
    if not prof:
        raise HTTPException(status_code=404, detail="Professor not found")
        
    if req.username != prof.username and db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
            
    prof.username = req.username
    prof.name = req.name
    prof.national_id = req.national_id
    prof.phone_number = req.phone_number
    prof.address = req.address
    prof.date_of_birth = req.date_of_birth
    if req.password: 
        prof.password = hash_password(req.password)
        
    db.commit()
    return {"message": "Professor updated successfully"}
@router.delete("/admin/professors/{prof_id}", tags=["Admin"])
def delete_professor(prof_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"].lower() not in ["manager", "admin"]:
        raise HTTPException(status_code=403)
        
    prof = db.query(User).filter(User.id == prof_id, User.role == "Professor").first()
    if not prof:
        raise HTTPException(status_code=404, detail="Professor not found")
        
    db.query(Course).filter(Course.professor_id == prof_id).update({"professor_id": None})
    db.delete(prof)
    db.commit()
    return {"message": "Professor deleted successfully"}

# Course mnagement
@router.get("/admin/all-courses", tags=["Admin"])
def get_all_courses(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"].lower() not in ["manager", "admin"]: 
        raise HTTPException(status_code=403)
        
    courses = db.query(Course, User.name.label("professor_name"))\
                .outerjoin(User, Course.professor_id == User.id).all()
                
    result = []
    for course, prof_name in courses:
        student_count = db.query(Enrollment).filter(Enrollment.course_id == course.id).count()
        result.append({
            "id": course.id,
            "name": course.name,
            "credits": course.credits,
            "professor": prof_name or "Unassigned",
            "students": student_count,
            "selection_deadline": course.selection_deadline,
            "start_date": course.start_date,
            "end_date": course.end_date,
            "exam_day": course.exam_day,
            "is_active": course.is_active,
            "is_hidden": course.is_hidden
        })
    return result

@router.get("/admin/recent-courses", tags=["Admin"])
def get_recent_courses(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"].lower() not in ["manager", "admin"]: 
        raise HTTPException(status_code=403)

    courses = db.query(Course, User.name.label("professor_name"))\
                .outerjoin(User, Course.professor_id == User.id)\
                .filter(Course.is_active == True, Course.is_hidden == False)\
                .limit(3).all()
                
    result = []
    for course, prof_name in courses:
        student_count = db.query(Enrollment).filter(Enrollment.course_id == course.id).count()
        result.append({
            "code": course.id,
            "name": course.name,
            "professor": prof_name or "Unassigned",
            "students_count": student_count
        })
    return result

@router.post("/admin/courses", tags=["Admin"])
def create_course_admin(req: AdminCourseCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"].lower() not in ["manager", "admin"]:
        raise HTTPException(status_code=403)
    
    if db.query(Course).filter(Course.id == req.id).first():
        raise HTTPException(status_code=400, detail="A course with this code already exists")
        
    new_course = Course(
        id=req.id,
        name=req.name,
        credits=req.credits,
        professor_id=req.professor_id,
        selection_deadline=req.selection_deadline,
        start_date=req.start_date,
        end_date=req.end_date,
        exam_day=req.exam_day,
        is_active=req.is_active,
        is_hidden=req.is_hidden
    )
    db.add(new_course)
    db.commit()
    return {"message": "Course created successfully"}

@router.put("/admin/courses/{course_id}", tags=["Admin"])
def update_course(course_id: str, req: AdminCourseCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"].lower() not in ["manager", "admin"]: 
        raise HTTPException(status_code=403)
        
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    course.name = req.name
    course.credits = req.credits
    course.professor_id = req.professor_id
    course.selection_deadline = req.selection_deadline
    course.start_date = req.start_date
    course.end_date = req.end_date
    course.exam_day = req.exam_day
    course.is_active = req.is_active
    course.is_hidden = req.is_hidden
    
    db.commit()
    return {"message": "Course updated successfully"}

@router.delete("/admin/courses/{course_id}", tags=["Admin"])
def delete_course(course_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"].lower() not in ["manager", "admin"]: 
        raise HTTPException(status_code=403)
        
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    db.query(Enrollment).filter(Enrollment.course_id == course_id).delete()
    db.query(CourseSession).filter(CourseSession.course_id == course_id).delete()
    db.delete(course)
    db.commit()
    return {"message": "Course successfully deleted"}


# 3. Professor dashboard
# ==========================================
@router.get("/professor/stats", tags=["Professor"])
def get_professor_stats(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"] != "Professor":
        raise HTTPException(status_code=403)

    prof = db.query(User).filter(User.username == (current_user.get("sub") or current_user.get("username"))).first()
    courses = db.query(Course).filter(Course.professor_id == prof.id).all()
    course_ids = [c.id for c in courses]

    if not course_ids:
        return {"totalCourses": 0, "totalStudents": 0, "averageGrade": 0.0, "attendanceRate": 0}

    enrollments = db.query(Enrollment).filter(Enrollment.course_id.in_(course_ids)).all()
    valid_grades = [e.grade for e in enrollments if e.grade is not None]
    avg = sum(valid_grades) / len(valid_grades) if valid_grades else 0.0

    return {
        "totalCourses": len(courses),
        "totalStudents": len(enrollments),
        "averageGrade": round(avg, 2),
        "attendanceRate": 0 
    }

@router.get("/professor/courses", tags=["Professor"])
def get_professor_courses(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"] != "Professor": 
        raise HTTPException(status_code=403)
    
    prof_username = current_user.get("sub") or current_user.get("username")
    prof = db.query(User).filter(User.username == prof_username).first()
    courses = db.query(Course).filter(Course.professor_id == prof.id).all()
    
    return [{
        "id": c.id, 
        "name": c.name, 
        "code": c.id,
        "is_active": c.is_active
    } for c in courses]

@router.get("/professor/courses/{course_id}/students", tags=["Professor"])
def get_course_roster(course_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"] != "Professor": 
        raise HTTPException(status_code=403)

    roster = db.query(Enrollment, User).join(User, Enrollment.student_id == User.id)\
               .filter(Enrollment.course_id == course_id).all()

    return [{
        "id": student.id,
        "studentCode": student.username, 
        "name": student.name,
        "currentGrade": enrollment.grade
    } for enrollment, student in roster]

@router.post("/professor/courses/{course_id}/grades", tags=["Professor"])
def submit_bulk_grades(course_id: str, payload: BulkGradePayload, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"] != "Professor": 
        raise HTTPException(status_code=403)

    for entry in payload.grades:
        enrollment = db.query(Enrollment).filter(
            Enrollment.course_id == course_id,
            Enrollment.student_id == entry.studentId
        ).first()
        
        if enrollment:
            enrollment.grade = entry.grade

    db.commit()
    return {"message": "Grades submitted successfully."}

@router.post("/professor/schedule", tags=["Professor"])
def add_schedule_session(req: SessionCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"] != "Professor":
        raise HTTPException(status_code=403)

    new_session = CourseSession(
        course_id=req.course_id, day=req.day,
        start_time=req.start_time, end_time=req.end_time,
        location=req.location, session_type=req.session_type
    )
    db.add(new_session)
    db.commit()
    return {"message": "Session added successfully"}

@router.get("/professor/schedule", tags=["Professor"])
def get_schedule(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"] != "Professor":
        raise HTTPException(status_code=403)

    prof_username = current_user.get("sub") or current_user.get("username")
    prof = db.query(User).filter(User.username == prof_username).first()
    
    courses = db.query(Course).filter(Course.professor_id == prof.id).all()
    course_ids = [c.id for c in courses]
    sessions = db.query(CourseSession).filter(CourseSession.course_id.in_(course_ids)).all()

    return [{
        "id": s.id, "course_id": s.course_id, "day": s.day,
        "start_time": s.start_time, "end_time": s.end_time,
        "location": s.location, "type": s.session_type
    } for s in sessions]

@router.delete("/professor/schedule/{session_id}", tags=["Professor"])
def delete_schedule_session(session_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"] != "Professor":
        raise HTTPException(status_code=403)

    session_to_delete = db.query(CourseSession).filter(CourseSession.id == session_id).first()
    if not session_to_delete:
        raise HTTPException(status_code=404, detail="Session not found")

    db.delete(session_to_delete)
    db.commit()
    return {"message": "Session deleted successfully"}


# 4.Student dashboard
# ==========================================
@router.get("/student/stats", tags=["Student"])
def get_student_stats(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"] != "Student": 
        raise HTTPException(status_code=403)
        
    student_username = current_user.get("sub") or current_user.get("username")
    student = db.query(User).filter(User.username == student_username).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    enrollments = db.query(Enrollment).filter(Enrollment.student_id == student.id).all()
    valid_grades = [e.grade for e in enrollments if e.grade is not None]
    avg = sum(valid_grades) / len(valid_grades) if valid_grades else 0.0
    
    total_credits = sum(db.query(Course).filter(Course.id == e.course_id).first().credits for e in enrollments if db.query(Course).filter(Course.id == e.course_id).first())
    completed_credits = sum(db.query(Course).filter(Course.id == e.course_id).first().credits for e in enrollments if e.grade is not None and e.grade >= 10 and db.query(Course).filter(Course.id == e.course_id).first())
                
    return {
        "activeCourses": len(enrollments),
        "averageGrade": round(avg, 2),
        "creditsCompleted": completed_credits,
        "totalCredits": total_credits
    }

@router.get("/student/courses", tags=["Student"])
def get_student_courses(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"] != "Student": 
        raise HTTPException(status_code=403)
        
    student_username = current_user.get("sub") or current_user.get("username")
    student = db.query(User).filter(User.username == student_username).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    enrollments = db.query(Enrollment).filter(Enrollment.student_id == student.id).all()
    
    results = []
    for e in enrollments:
        course = db.query(Course).filter(Course.id == e.course_id).first()
        if course:
            prof = db.query(User).filter(User.id == course.professor_id).first()
            results.append({
                "course_id": course.id,
                "name": course.name,
                "credits": course.credits,
                "professor": prof.name if prof else "Unassigned",
                "grade": e.grade
            })
    return results

@router.get("/student/available-courses", tags=["Student"])
def get_available_courses(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"] != "Student": 
        raise HTTPException(status_code=403)
        
    student_username = current_user.get("sub") or current_user.get("username")
    student = db.query(User).filter(User.username == student_username).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    enrolled_ids = [e.course_id for e in db.query(Enrollment).filter(Enrollment.student_id == student.id).all()]
    available = db.query(Course).filter(
        ~Course.id.in_(enrolled_ids),
        Course.is_active == True,
        Course.is_hidden == False
    ).all()
    
    results = []
    for c in available:
        prof = db.query(User).filter(User.id == c.professor_id).first()
        results.append({
            "id": c.id,
            "name": c.name,
            "credits": c.credits,
            "professor": prof.name if prof else "Unassigned",
            "selection_deadline": c.selection_deadline,
            "exam_day": c.exam_day
        })
    return results

@router.post("/student/enroll", tags=["Student"])
def enroll_in_courses(payload: CourseEnrollList, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"] != "Student": 
        raise HTTPException(status_code=403)
        
    student_username = current_user.get("sub") or current_user.get("username")
    student = db.query(User).filter(User.username == student_username).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    current_date = datetime.now().date()
    
    for cid in payload.course_ids:
        course = db.query(Course).filter(Course.id == cid).first()
        if not course or not course.is_active:
            raise HTTPException(status_code=400, detail=f"Course {cid} is not active for enrollment.")
            
        if course.selection_deadline:
            try:
                deadline_date = datetime.strptime(course.selection_deadline, "%Y-%m-%d").date()
                if current_date > deadline_date:
                    raise HTTPException(status_code=400, detail=f"The enrollment deadline for {cid} has passed.")
            except ValueError:
                pass 
            
        existing = db.query(Enrollment).filter(Enrollment.student_id == student.id, Enrollment.course_id == cid).first()
        if not existing:
            new_enrollment = Enrollment(student_id=student.id, course_id=cid, grade=None)
            db.add(new_enrollment)
            
    db.commit()
    return {"message": "Successfully enrolled in selected courses"}

@router.get("/student/schedule", tags=["Student"])
def get_student_schedule(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"] != "Student": 
        raise HTTPException(status_code=403)
        
    student_username = current_user.get("sub") or current_user.get("username")
    student = db.query(User).filter(User.username == student_username).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    enrolled_ids = [e.course_id for e in db.query(Enrollment).filter(Enrollment.student_id == student.id).all()]
    sessions = db.query(CourseSession).filter(CourseSession.course_id.in_(enrolled_ids)).all()
    
    return [{
        "id": s.id,
        "course_id": s.course_id,
        "day": s.day,
        "start_time": s.start_time,
        "end_time": s.end_time,
        "location": s.location,
        "type": s.session_type
    } for s in sessions]