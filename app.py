import os
from dotenv import load_dotenv

load_dotenv()
print("DEBUG URI:", os.getenv("MONGO_URI"))

from pymongo import MongoClient, errors
import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "classmanager")

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

# app.py
from abc import ABC, abstractmethod
from pymongo import MongoClient, errors
import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv

# -----------------------------
# Load biến môi trường từ .env
# -----------------------------
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "classmanager")

# -----------------------------
# Kết nối MongoDB
# -----------------------------
def get_db(uri: str, db_name: str):
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=8000)
        client.admin.command("ping")  # test kết nối
        return client[db_name]
    except errors.ConfigurationError as e:
        st.error(f"Configuration Error: {e}")
    except errors.ServerSelectionTimeoutError as e:
        st.error(f"Server timeout: {e}")
    except Exception as e:
        st.error(f"Unknown error: {e}")
    return None

db = get_db(MONGO_URI, DB_NAME)

if db:
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

    def update_student(self, student_id, update_fields):
        res = self.students_col.update_one({"student_id": student_id}, {"$set": update_fields})
        return res.matched_count > 0, "Updated" if res.matched_count else "Not found"

    def delete_student(self, student_id):
        self.courses_col.update_many({}, {"$pull": {"students": student_id}})
        res = self.students_col.delete_one({"student_id": student_id})
        return res.deleted_count > 0, "Deleted" if res.deleted_count else "Not found"

    # Teacher CRUD
    def create_teacher(self, teacher: Teacher):
        if self.teachers_col.find_one({"teacher_id": teacher.person_id}):
            return False, "Teacher ID already exists"
        self.teachers_col.insert_one(teacher.to_dict())
        return True, "Teacher created"

    def read_teachers(self):
        return list(self.teachers_col.find({}, {"_id": 0}))

    def update_teacher(self, teacher_id, update_fields):
        res = self.teachers_col.update_one({"teacher_id": teacher_id}, {"$set": update_fields})
        return res.matched_count > 0, "Updated" if res.matched_count else "Not found"

    def delete_teacher(self, teacher_id):
        self.courses_col.update_many({"teacher_id": teacher_id}, {"$set": {"teacher_id": None}})
        res = self.teachers_col.delete_one({"teacher_id": teacher_id})
        return res.deleted_count > 0, "Deleted" if res.deleted_count else "Not found"

    # Course CRUD
    def create_course(self, course: Course):
        if self.courses_col.find_one({"course_code": course.code}):
            return False, "Course code already exists"
        self.courses_col.insert_one(course.to_dict())
        return True, "Course created"

    def read_courses(self):
        return list(self.courses_col.find({}, {"_id": 0}))

    def update_course(self, course_code, update_fields):
        res = self.courses_col.update_one({"course_code": course_code}, {"$set": update_fields})
        return res.matched_count > 0, "Updated" if res.matched_count else "Not found"

    def delete_course(self, course_code):
        self.students_col.update_many({}, {"$pull": {"enrollments": course_code}})
        res = self.courses_col.delete_one({"course_code": course_code})
        return res.deleted_count > 0, "Deleted" if res.deleted_count else "Not found"

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

manager = ClassManager(students_col, teachers_col, courses_col) if db else None

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="Class Manager", layout="wide")
st.title("📚 Class Manager — OOP + MongoDB + Streamlit")

if not db:
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
            st.success(msg) if ok else st.error(msg)
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
            st.success(msg) if ok else st.error(msg)
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
            st.success(msg) if ok else st.error(msg)
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
            st.success(msg) if ok else st.error(msg)
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
            st.success(msg) if ok else st.error(msg)
    else:
        st.info("Cần có student và course trước.")
