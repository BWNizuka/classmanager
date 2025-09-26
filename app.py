# app.py
from abc import ABC, abstractmethod
from pymongo import MongoClient, errors
import streamlit as st
import pandas as pd
from dotenv import dotenv_values

# -----------------------------
# Load biến môi trường từ .env
# -----------------------------
config = dotenv_values(".env")
MONGO_URI = config.get("MONGO_URI")
DB_NAME = config.get("DB_NAME", "classmanager")

# Debug hiển thị trong sidebar
st.sidebar.caption(f"🔌 Using DB: {DB_NAME}")

# -----------------------------
# Kết nối MongoDB
# -----------------------------
@st.cache_resource
def get_db():
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000)
        client.admin.command("ping")  # test kết nối
        return client[DB_NAME]
    except Exception as e:
        st.error(f"❌ MongoDB connection failed: {e}")
        return None

db = get_db()

if db is not None:
    students_col = db["students"]
    teachers_col = db["teachers"]
    courses_col = db["courses"]
else:
    students_col = teachers_col = courses_col = None

# -----------------------------
# OOP Classes
# -----------------------------
class Person(ABC):
    def __init__(self, person_id: str, name: str, email: str):
        self.person_id = person_id
        self.name = name
        self.email = email

    @abstractmethod
    def to_dict(self):
        pass

class Student(Person):
    def __init__(self, person_id, name, email, grade_level):
        super().__init__(person_id, name, email)
        self.grade_level = grade_level
        self.enrollments = []

    def to_dict(self):
        return {
            "student_id": self.person_id,
            "name": self.name,
            "email": self.email,
            "grade_level": self.grade_level,
            "enrollments": self.enrollments
        }

class Teacher(Person):
    def __init__(self, person_id, name, email, specialization):
        super().__init__(person_id, name, email)
        self.specialization = specialization
        self.courses = []

    def to_dict(self):
        return {
            "teacher_id": self.person_id,
            "name": self.name,
            "email": self.email,
            "specialization": self.specialization,
            "courses": self.courses
        }

class Course:
    def __init__(self, code, title, schedule):
        self.code = code
        self.title = title
        self.schedule = schedule
        self.teacher_id = None
        self.students = []

    def to_dict(self):
        return {
            "course_code": self.code,
            "title": self.title,
            "schedule": self.schedule,
            "teacher_id": self.teacher_id,
            "students": self.students
        }

# -----------------------------
# Controller (ClassManager)
# -----------------------------
class ClassManager:
    def __init__(self, students_col, teachers_col, courses_col):
        self.students_col = students_col
        self.teachers_col = teachers_col
        self.courses_col = courses_col

    # Student CRUD
    def create_student(self, student: Student):
        if self.students_col.find_one({"student_id": student.person_id}):
            return False, "Student ID already exists"
        self.students_col.insert_one(student.to_dict())
        return True, "Student created"

    def read_students(self):
        return list(self.students_col.find({}, {"_id": 0}))

    # Teacher CRUD
    def create_teacher(self, teacher: Teacher):
        if self.teachers_col.find_one({"teacher_id": teacher.person_id}):
            return False, "Teacher ID already exists"
        self.teachers_col.insert_one(teacher.to_dict())
        return True, "Teacher created"

    def read_teachers(self):
        return list(self.teachers_col.find({}, {"_id": 0}))

    # Course CRUD
    def create_course(self, course: Course):
        if self.courses_col.find_one({"course_code": course.code}):
            return False, "Course code already exists"
        self.courses_col.insert_one(course.to_dict())
        return True, "Course created"

    def read_courses(self):
        return list(self.courses_col.find({}, {"_id": 0}))

    # Assignments
    def assign_teacher(self, teacher_id, course_code):
        t = self.teachers_col.find_one({"teacher_id": teacher_id})
        c = self.courses_col.find_one({"course_code": course_code})
        if not t or not c:
            return False, "Teacher or course not found"
        self.courses_col.update_one({"course_code": course_code}, {"$set": {"teacher_id": teacher_id}})
        if course_code not in t.get("courses", []):
            self.teachers_col.update_one({"teacher_id": teacher_id}, {"$push": {"courses": course_code}})
        return True, "Teacher assigned"

    def enroll_student(self, student_id, course_code):
        s = self.students_col.find_one({"student_id": student_id})
        c = self.courses_col.find_one({"course_code": course_code})
        if not s or not c:
            return False, "Student or course not found"
        if student_id not in c.get("students", []):
            self.courses_col.update_one({"course_code": course_code}, {"$push": {"students": student_id}})
        if course_code not in s.get("enrollments", []):
            self.students_col.update_one({"student_id": student_id}, {"$push": {"enrollments": course_code}})
        return True, "Student enrolled"

manager = ClassManager(students_col, teachers_col, courses_col) if db is not None else None

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="Class Manager", layout="wide")
st.title("📚 Class Manager — OOP + MongoDB + Streamlit")

if db is None:
    st.warning("❌ Không kết nối được tới MongoDB. Kiểm tra file .env và chuỗi MONGO_URI.")
    st.stop()

menu = st.sidebar.selectbox("Menu", [
    "Dashboard", "Students", "Teachers", "Courses", "Assign Teacher", "Enroll Student"
])

# Dashboard
if menu == "Dashboard":
    st.subheader("📊 Dashboard")
    st.metric("Students", len(manager.read_students()))
    st.metric("Teachers", len(manager.read_teachers()))
    st.metric("Courses", len(manager.read_courses()))

# Students
elif menu == "Students":
    st.subheader("👩‍🎓 Students CRUD")
    with st.form("create_student"):
        sid = st.text_input("ID")
        name = st.text_input("Name")
        email = st.text_input("Email")
        grade = st.number_input("Grade level", 1, 20, 10)
        if st.form_submit_button("Add"):
            ok, msg = manager.create_student(Student(sid, name, email, int(grade)))
            if ok:
                st.success(msg)
            else:
                st.error(msg)
    st.dataframe(pd.DataFrame(manager.read_students()))

# Teachers
elif menu == "Teachers":
    st.subheader("👨‍🏫 Teachers CRUD")
    with st.form("create_teacher"):
        tid = st.text_input("ID")
        name = st.text_input("Name")
        email = st.text_input("Email")
        spec = st.text_input("Specialization")
        if st.form_submit_button("Add"):
            ok, msg = manager.create_teacher(Teacher(tid, name, email, spec))
            if ok:
                st.success(msg)
            else:
                st.error(msg)
    st.dataframe(pd.DataFrame(manager.read_teachers()))

# Courses
elif menu == "Courses":
    st.subheader("📘 Courses CRUD")
    with st.form("create_course"):
        code = st.text_input("Course Code")
        title = st.text_input("Title")
        schedule = st.text_input("Schedule")
        if st.form_submit_button("Add"):
            ok, msg = manager.create_course(Course(code, title, schedule))
            if ok:
                st.success(msg)
            else:
                st.error(msg)
    st.dataframe(pd.DataFrame(manager.read_courses()))

# Assign Teacher
elif menu == "Assign Teacher":
    st.subheader("👨‍🏫➡️📘 Assign Teacher to Course")
    teachers = manager.read_teachers()
    courses = manager.read_courses()
    if teachers and courses:
        tid = st.selectbox("Teacher", [t["teacher_id"] for t in teachers])
        cid = st.selectbox("Course", [c["course_code"] for c in courses])
        if st.button("Assign"):
            ok, msg = manager.assign_teacher(tid, cid)
            if ok:
                st.success(msg)
            else:
                st.error(msg)
    else:
        st.info("Cần có teacher và course trước.")

# Enroll Student
elif menu == "Enroll Student":
    st.subheader("👩‍🎓➡️📘 Enroll Student in Course")
    students = manager.read_students()
    courses = manager.read_courses()
    if students and courses:
        sid = st.selectbox("Student", [s["student_id"] for s in students])
        cid = st.selectbox("Course", [c["course_code"] for c in courses])
        if st.button("Enroll"):
            ok, msg = manager.enroll_student(sid, cid)
            if ok:
                st.success(msg)
            else:
                st.error(msg)
    else:
        st.info("Cần có student và course trước.")
