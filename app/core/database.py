from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

DATABASE_URL = "sqlite:///./uni_v3.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False) # Will store Bcrypt hash
    role = Column(String, nullable=False)
    name = Column(String, nullable=False)

class SignupRequest(Base):
    __tablename__ = "signup_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True) 
    name = Column(String)
    password = Column(String)
    status = Column(String, default="Pending")

class Course(Base):
    __tablename__ = "courses"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    credits = Column(Integer, nullable=False)
    professor_id = Column(Integer, ForeignKey("users.id"), nullable=True)

class Enrollment(Base):
    __tablename__ = "enrollments"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(String, ForeignKey("courses.id"), nullable=False)
    grade = Column(Float, nullable=True)

# --- NEW TABLE FOR SCHEDULES ---
class CourseSession(Base):
    __tablename__ = "course_sessions"
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(String, ForeignKey("courses.id"), nullable=False)
    day = Column(String, nullable=False)
    start_time = Column(String, nullable=False)
    end_time = Column(String, nullable=False)
    location = Column(String, nullable=False)
    session_type = Column(String, nullable=False) # e.g., Lecture, Lab

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
