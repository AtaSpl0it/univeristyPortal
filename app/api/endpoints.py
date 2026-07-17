from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy import func
from app.core.database import get_db, User, Course, Enrollment, SignupRequest, CourseSession
from app.core.schemas import (
    UserCreate, CourseCreate, GradeSubmit, Token, 
    BulkGradePayload
)
from app.core.security import (
    hash_password, verify_password, 
    create_access_token, get_current_user_token
)
from pydantic import BaseModel
from typing import Optional

class CourseEnrollList(BaseModel):
    course_ids: List[str]
class StudentSignupParams(BaseModel):
    username: str
    name: str
    password: str
    
class AdminStudentCreate(BaseModel):
    username: str  # student number
    name: str
    password: Optional[str] = None

class AdminCourseCreate(BaseModel):
    id: str
    name: str
    credits: int
    professor_id: Optional[int] = None

class AdminProfessorCreate(BaseModel):
    username: str
    name: str
    password: str

# New Schema for Schedules
class SessionCreate(BaseModel):
    course_id: str
    day: str
    start_time: str
    end_time: str
    location: str
    session_type: str

router = APIRouter()

# ==========================================
# 1. AUTHENTICATION
# ==========================================
@router.post("/auth/signup", tags=["Auth"])
def submit_signup_request(req: StudentSignupParams, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="This National ID is already registered.")
        
    existing_req = db.query(SignupRequest).filter(
        SignupRequest.username == req.username, 
        SignupRequest.status == "Pending"
    ).first()
    
    if existing_req:
        raise HTTPException(status_code=400, detail="A pending request for this ID already exists.")
        
    new_request = SignupRequest(
        username=req.username,
        name=req.name,
        password=req.password,
        status="Pending"
    )
    db.add(new_request)
    db.commit()
    return {"message": "Signup request submitted successfully."}

@router.post("/auth/login", response_model=Token, tags=["Auth"])
def login(req: UserCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    
    if not user or not verify_password(req.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="نام کاربری یا رمز عبور اشتباه است"
        )
        
    token = create_access_token(data={"sub": user.username, "role": user.role})
    return {"access_token": token, "token_type": "bearer"}

# ==========================================
# 2. MANAGER DASHBOARD
# ==========================================
@router.get("/admin/signup-requests", tags=["Admin"])
def get_signup_requests(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"].lower() not in ["manager", "admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
        
    requests = db.query(SignupRequest).filter(SignupRequest.status == "Pending").all()
    return [{"id": r.id, "username": r.username, "name": r.name, "status": r.status} for r in requests]

@router.post("/admin/signup-requests/{req_id}/approve", tags=["Admin"])
def approve_request(req_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"].lower() not in ["manager", "admin"]:
        raise HTTPException(status_code=403)
        
    signup_req = db.query(SignupRequest).filter(SignupRequest.id == req_id).first()
    if not signup_req or signup_req.status != "Pending":
        raise HTTPException(status_code=404, detail="Valid pending request not found")
        
    if db.query(User).filter(User.username == signup_req.username).first():
        raise HTTPException(status_code=400, detail="This ID is already registered")
        
    new_user = User(
        username=signup_req.username,
        password=hash_password(signup_req.password),
        name=signup_req.name,
        role="Student"
    )
    db.add(new_user)
    
    signup_req.status = "Approved"
    db.commit()
    return {"message": "Student successfully approved and created"}

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

@router.get("/admin/students", tags=["Admin"])
def get_all_students(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"].lower() not in ["manager", "admin"]: 
        raise HTTPException(status_code=403, detail="Admin access required")
        
    students = db.query(User).filter(User.role == "Student").all()
    
    result = []
    for student in students:
        enrollments = db.query(Enrollment).filter(Enrollment.student_id == student.id).all()
        total_courses = len(enrollments)
        
        valid_grades = [e.grade for e in enrollments if e.grade is not None]
        gpa = sum(valid_grades) / len(valid_grades) if valid_grades else 0.0
        
        result.append({
            "db_id": student.id,
            "student_number": student.username,
            "name": student.name,
            "enrolled_courses": total_courses,
            "gpa": round(gpa, 2),
            "status": "Active"
        })
        
    return result

@router.post("/admin/students", tags=["Admin"])
def create_student(req: AdminStudentCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"].lower() not in ["manager", "admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
        
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="Student number already exists")
        
    new_student = User(
        username=req.username,
        password=hash_password(req.password or "student123"), 
        name=req.name,
        role="Student"
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
        
    if req.username != student.username:
        if db.query(User).filter(User.username == req.username).first():
            raise HTTPException(status_code=400, detail="Student number already exists")
            
    student.username = req.username
    student.name = req.name
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

@router.post("/admin/courses", tags=["Admin"])
def create_course_admin(req: AdminCourseCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"].lower() not in ["manager", "admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    existing = db.query(Course).filter(Course.id == req.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="A course with this code already exists")
        
    new_course = Course(
        id=req.id,
        name=req.name,
        credits=req.credits,
        professor_id=req.professor_id
    )
    db.add(new_course)
    db.commit()
    return {"message": "Course created successfully"}

@router.post("/admin/professors", tags=["Admin"])
def create_professor(req: AdminProfessorCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"].lower() not in ["manager", "admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
        
    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username is already taken")
        
    new_prof = User(
        username=req.username,
        password=hash_password(req.password),
        name=req.name,
        role="Professor"
    )
    db.add(new_prof)
    db.commit()
    return {"message": "Professor created successfully"}

@router.get("/admin/all-courses", tags=["Admin"])
def get_all_courses(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"].lower() not in ["manager", "admin"]: 
        raise HTTPException(status_code=403, detail="Admin access required")
        
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
            "status": "Active"
        })
    return result

@router.delete("/admin/courses/{course_id}", tags=["Admin"])
def delete_course(course_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"].lower() not in ["manager", "admin"]: 
        raise HTTPException(status_code=403)
        
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    db.query(Enrollment).filter(Enrollment.course_id == course_id).delete()
    db.delete(course)
    db.commit()
    return {"message": "Course successfully deleted"}

@router.put("/admin/courses/{course_id}", tags=["Admin"])
def update_course(course_id: str, req: CourseCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"].lower() not in ["manager", "admin"]: 
        raise HTTPException(status_code=403)
        
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    course.name = req.name
    course.credits = req.credits
    course.professor_id = req.professor_id
    
    db.commit()
    return {"message": "Course updated successfully"}

@router.get("/admin/professors", tags=["Admin"])
def get_professors(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"].lower() not in ["manager", "admin"]: 
        raise HTTPException(status_code=403, detail="Admin access required")
        
    professors = db.query(User).filter(User.role == "Professor").all()
    return [{"id": prof.id, "name": prof.name} for prof in professors]

@router.get("/admin/stats", tags=["Admin"])
def get_admin_stats(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"].lower() not in ["manager", "admin"]: 
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
        
    total_courses = db.query(Course).count()
    total_students = db.query(User).filter(User.role == "Student").count()
    avg_grade = db.query(func.avg(Enrollment.grade)).scalar() or 0.0
    attendance_rate = 92.5 
    
    return {
        "activeCourses": total_courses,
        "totalStudents": total_students,
        "averageGrade": round(avg_grade, 2),
        "attendanceRate": attendance_rate
    }

@router.get("/admin/recent-requests", tags=["Admin"])
def get_recent_requests(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"].lower() not in ["manager", "admin"]:
        raise HTTPException(status_code=403)
        
    requests = db.query(SignupRequest).filter(SignupRequest.status == "Pending").order_by(SignupRequest.id.desc()).limit(4).all()
    return [{"id": r.id, "name": r.name, "username": r.username} for r in requests]

@router.get("/admin/recent-courses", tags=["Admin"])
def get_recent_courses(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"].lower() not in ["manager", "admin"]: 
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    courses = db.query(Course, User.name.label("professor_name"))\
                .outerjoin(User, Course.professor_id == User.id)\
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

# ==========================================
# 3. PROFESSOR DASHBOARD
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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Professor access required")
    
    prof_username = current_user.get("sub") or current_user.get("username")
    prof = db.query(User).filter(User.username == prof_username).first()
    if not prof: 
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    courses = db.query(Course).filter(Course.professor_id == prof.id).all()
    return [{"id": c.id, "name": c.name, "code": c.id} for c in courses]

@router.get("/professor/courses/{course_id}/students", tags=["Professor"])
def get_course_roster(course_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"] != "Professor": 
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    roster = db.query(Enrollment, User).join(User, Enrollment.student_id == User.id)\
               .filter(Enrollment.course_id == course_id).all()

    students_list = []
    for enrollment, student in roster:
        students_list.append({
            "id": student.id,
            "studentCode": student.username, 
            "name": student.name,
            "currentGrade": enrollment.grade
        })
    
    return students_list

@router.post("/professor/courses/{course_id}/grades", tags=["Professor"])
def submit_bulk_grades(course_id: str, payload: BulkGradePayload, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"] != "Professor": 
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    for entry in payload.grades:
        enrollment = db.query(Enrollment).filter(
            Enrollment.course_id == course_id,
            Enrollment.student_id == entry.studentId
        ).first()
        
        if enrollment:
            enrollment.grade = entry.grade

    db.commit()
    return {"message": "نمرات با موفقیت روی سرور ثبت شدند."}

@router.post("/professor/schedule", tags=["Professor"])
def add_schedule_session(req: SessionCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user_token)):
    if current_user["role"] != "Professor":
        raise HTTPException(status_code=403)

    new_session = CourseSession(
        course_id=req.course_id,
        day=req.day,
        start_time=req.start_time,
        end_time=req.end_time,
        location=req.location,
        session_type=req.session_type
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
        "id": s.id,
        "course_id": s.course_id,
        "day": s.day,
        "start_time": s.start_time,
        "end_time": s.end_time,
        "location": s.location,
        "type": s.session_type
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
# ==========================================
# 4. STUDENT DASHBOARD
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
    
    total_credits = 0
    completed_credits = 0
    
    for e in enrollments:
        course = db.query(Course).filter(Course.id == e.course_id).first()
        if course:
            total_credits += course.credits
            if e.grade is not None and e.grade >= 10:
                completed_credits += course.credits
                
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
    available = db.query(Course).filter(~Course.id.in_(enrolled_ids)).all()
    
    results = []
    for c in available:
        prof = db.query(User).filter(User.id == c.professor_id).first()
        results.append({
            "id": c.id,
            "name": c.name,
            "credits": c.credits,
            "professor": prof.name if prof else "Unassigned"
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
    
    for cid in payload.course_ids:
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