# app.py
from abc import ABC, abstractmethod
from pymongo import MongoClient, errors
import streamlit as st
import pandas as pd
from typing import Optional

# --------- CONFIG: điền URI thực tế từ Atlas ở đây ----------
MONGO_URI = "mongodb+srv://<username>:<password>@<your-cluster-host>/classmanager?retryWrites=true&w=majority"
DB_NAME = "classmanager"
# ------------------------------------------------------------

# ---------- MongoDB client (kết nối an toàn) ----------
def get_db(uri: str, db_name: str):
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=8000)
        # force connection on a request as the
        # connect=True parameter of MongoClient seems not reliable
        client.admin.command("ping")
        db = client[db_name]
        return db
    except errors.ConfigurationError as e:
        st.error(f"Configuration Error: {e}")
        return None
    except errors.ServerSelectionTimeoutError as e:
        st.error(f"Connection timeout / server selection error: {e}")
        return None
    except Exception as e:
        st.error(f"Unknown connection error: {e}")
        return None

db = get_db(MONGO_URI, DB_NAME)

if db:
    students_col = db["students"]
    teachers_col = db["teachers"]
    courses_col = db["courses"]
else:
    students_col = teachers_col = courses_col = None

# ---------------- OOP model ----------------
class Person(ABC):
    def __init__(self, person_id: str, name: str, email: str):
        self.person_id = person_id
        self.name = name
        self.email = email

    @abstractmethod
    def to_dict(self):
        pass

class Student(Person):
    def __init__(self, person_id: str, name: str, email: str, grade_level: int):
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
    def __init__(self, person_id: str, name: str, email: str, specialization: str):
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
    def __init__(self, code: str, title: str, schedule: str):
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

# ---------------- Controller (ClassManager) ----------------
class ClassManager:
    def __init__(self, students_col, teachers_col, courses_col):
        self.students_col = students_col
        self.teachers_col = teachers_col
        self.courses_col = courses_col

    # --- Student CRUD ---
    def create_student(self, student: Student):
        if not self.students_col:
            return False, "No DB connection"
        if self.students_col.find_one({"student_id": student.person_id}):
            return False, "student_id already exists"
        self.students_col.insert_one(student.to_dict())
        return True, "Inserted"

    def read_students(self):
        if not self.students_col: return []
        return list(self.students_col.find({}, {"_id": 0}))

    def update_student(self, student_id: str, update_fields: dict):
        if not self.students_col:
            return False, "No DB connection"
        res = self.students_col.update_one({"student_id": student_id}, {"$set": update_fields})
        return res.matched_count > 0, "Updated" if res.matched_count > 0 else "Not found"

    def delete_student(self, student_id: str):
        if not self.students_col:
            return False, "No DB connection"
        # Remove student from courses' students arrays
        self.courses_col.update_many({}, {"$pull": {"students": student_id}})
        res = self.students_col.delete_one({"student_id": student_id})
        return res.deleted_count > 0, "Deleted" if res.deleted_count > 0 else "Not found"

    # --- Teacher CRUD ---
    def create_teacher(self, teacher: Teacher):
        if not self.teachers_col: return False, "No DB connection"
        if self.teachers_col.find_one({"teacher_id": teacher.person_id}):
            return False, "teacher_id already exists"
        self.teachers_col.insert_one(teacher.to_dict())
        return True, "Inserted"

    def read_teachers(self):
        if not self.teachers_col: return []
        return list(self.teachers_col.find({}, {"_id": 0}))

    def update_teacher(self, teacher_id: str, update_fields: dict):
        if not self.teachers_col:
            return False, "No DB connection"
        res = self.teachers_col.update_one({"teacher_id": teacher_id}, {"$set": update_fields})
        return res.matched_count > 0, "Updated" if res.matched_count > 0 else "Not found"

    def delete_teacher(self, teacher_id: str):
        if not self.teachers_col:
            return False, "No DB connection"
        # Unassign teacher from courses
        self.courses_col.update_many({"teacher_id": teacher_id}, {"$set": {"teacher_id": None}})
        res = self.teachers_col.delete_one({"teacher_id": teacher_id})
        return res.deleted_count > 0, "Deleted" if res.deleted_count > 0 else "Not found"

    # --- Course CRUD ---
    def create_course(self, course: Course):
        if not self.courses_col: return False, "No DB connection"
        if self.courses_col.find_one({"course_code": course.code}):
            return False, "course_code already exists"
        self.courses_col.insert_one(course.to_dict())
        return True, "Inserted"

    def read_courses(self):
        if not self.courses_col: return []
        return list(self.courses_col.find({}, {"_id": 0}))

    def update_course(self, course_code: str, update_fields: dict):
        if not self.courses_col:
            return False, "No DB connection"
        res = self.courses_col.update_one({"course_code": course_code}, {"$set": update_fields})
        return res.matched_count > 0, "Updated" if res.matched_count > 0 else "Not found"

    def delete_course(self, course_code: str):
        if not self.courses_col:
            return False, "No DB connection"
        # Remove course_code from students' enrollments
        self.students_col.update_many({}, {"$pull": {"enrollments": course_code}})
        res = self.courses_col.delete_one({"course_code": course_code})
        return res.deleted_count > 0, "Deleted" if res.deleted_count > 0 else "Not found"

    # --- Relationships ---
    def assign_teacher(self, teacher_id: str, course_code: str):
        t = self.teachers_col.find_one({"teacher_id": teacher_id})
        c = self.courses_col.find_one({"course_code": course_code})
        if not t or not c:
            return False, "Teacher or Course not found"

        # update course doc
        self.courses_col.update_one({"course_code": course_code}, {"$set": {"teacher_id": teacher_id}})
        # update teacher doc (add course if not present)
        if course_code not in t.get("courses", []):
            self.teachers_col.update_one({"teacher_id": teacher_id}, {"$push": {"courses": course_code}})
        return True, "Assigned"

    def enroll_student(self, student_id: str, course_code: str):
        s = self.students_col.find_one({"student_id": student_id})
        c = self.courses_col.find_one({"course_code": course_code})
        if not s or not c:
            return False, "Student or Course not found"

        # add student to course
        if student_id not in c.get("students", []):
            self.courses_col.update_one({"course_code": course_code}, {"$push": {"students": student_id}})
        # add course to student enrollments
        if course_code not in s.get("enrollments", []):
            self.students_col.update_one({"student_id": student_id}, {"$push": {"enrollments": course_code}})
        return True, "Enrolled"

# instantiate manager
manager = ClassManager(students_col, teachers_col, courses_col)

# ---------------- Streamlit UI ----------------
st.set_page_config(page_title="Class Manager", layout="wide")
st.title("Class Manager — OOP + MongoDB (Streamlit)")

if not db:
    st.warning("Chưa kết nối được tới MongoDB. Hãy kiểm tra MONGO_URI, IP whitelist, và credential.")
    st.stop()

menu = st.sidebar.selectbox("Chọn thao tác", [
    "Dashboard",
    "Students - CRUD",
    "Teachers - CRUD",
    "Courses - CRUD",
    "Assign Teacher",
    "Enroll Student"
])

# Dashboard
if menu == "Dashboard":
    st.header("Dashboard")
    students = manager.read_students()
    teachers = manager.read_teachers()
    courses = manager.read_courses()

    st.markdown("### Tổng quan")
    col1, col2, col3 = st.columns(3)
    col1.metric("Students", len(students))
    col2.metric("Teachers", len(teachers))
    col3.metric("Courses", len(courses))

    st.markdown("### Students")
    if students:
        st.dataframe(pd.DataFrame(students))
    else:
        st.write("No students")

    st.markdown("### Teachers")
    if teachers:
        st.dataframe(pd.DataFrame(teachers))
    else:
        st.write("No teachers")

    st.markdown("### Courses")
    if courses:
        st.dataframe(pd.DataFrame(courses))
    else:
        st.write("No courses")

# Students CRUD
elif menu == "Students - CRUD":
    st.header("Students - Create / Read / Update / Delete")

    with st.expander("Create student"):
        with st.form("create_student"):
            sid = st.text_input("Student ID")
            sname = st.text_input("Name")
            semail = st.text_input("Email")
            sgrade = st.number_input("Grade level", min_value=1, max_value=20, value=10)
            submitted = st.form_submit_button("Create")
            if submitted:
                student = Student(sid, sname, semail, int(sgrade))
                ok, msg = manager.create_student(student)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

    st.markdown("### All students")
    students = manager.read_students()
    if students:
        df = pd.DataFrame(students)
        st.dataframe(df)
        with st.form("update_delete_student"):
            sel = st.selectbox("Chọn student_id", df["student_id"].tolist())
            action = st.selectbox("Action", ["Update", "Delete"])
            if action == "Update":
                new_name = st.text_input("New name")
                new_email = st.text_input("New email")
                new_grade = st.number_input("New grade", min_value=1, max_value=20, value=10, key="ng")
                if st.form_submit_button("Submit update"):
                    updates = {}
                    if new_name: updates["name"] = new_name
                    if new_email: updates["email"] = new_email
                    if new_grade: updates["grade_level"] = int(new_grade)
                    ok, msg = manager.update_student(sel, updates)
                    if ok: st.success(msg)
                    else: st.error(msg)
            else:
                if st.form_submit_button("Delete student"):
                    ok, msg = manager.delete_student(sel)
                    if ok: st.success(msg)
                    else: st.error(msg)
    else:
        st.write("No students yet.")

# Teachers CRUD
elif menu == "Teachers - CRUD":
    st.header("Teachers - Create / Read / Update / Delete")

    with st.expander("Create teacher"):
        with st.form("create_teacher"):
            tid = st.text_input("Teacher ID")
            tname = st.text_input("Name")
            temail = st.text_input("Email")
            tspec = st.text_input("Specialization")
            if st.form_submit_button("Create"):
                teacher = Teacher(tid, tname, temail, tspec)
                ok, msg = manager.create_teacher(teacher)
                if ok: st.success(msg)
                else: st.error(msg)

    st.markdown("### All teachers")
    teachers = manager.read_teachers()
    if teachers:
        df = pd.DataFrame(teachers)
        st.dataframe(df)
        with st.form("update_delete_teacher"):
            sel = st.selectbox("Chọn teacher_id", df["teacher_id"].tolist())
            action = st.selectbox("Action", ["Update", "Delete"])
            if action == "Update":
                new_name = st.text_input("New name")
                new_email = st.text_input("New email")
                new_spec = st.text_input("New specialization")
                if st.form_submit_button("Submit update"):
                    updates = {}
                    if new_name: updates["name"] = new_name
                    if new_email: updates["email"] = new_email
                    if new_spec: updates["specialization"] = new_spec
                    ok, msg = manager.update_teacher(sel, updates)
                    if ok: st.success(msg)
                    else: st.error(msg)
            else:
                if st.form_submit_button("Delete teacher"):
                    ok, msg = manager.delete_teacher(sel)
                    if ok: st.success(msg)
                    else: st.error(msg)
    else:
        st.write("No teachers yet.")

# Courses CRUD
elif menu == "Courses - CRUD":
    st.header("Courses - Create / Read / Update / Delete")

    with st.expander("Create course"):
        with st.form("create_course"):
            code = st.text_input("Course code")
            title = st.text_input("Title")
            schedule = st.text_input("Schedule")
            if st.form_submit_button("Create"):
                course = Course(code, title, schedule)
                ok, msg = manager.create_course(course)
                if ok: st.success(msg)
                else: st.error(msg)

    st.markdown("### All courses")
    courses = manager.read_courses()
    if courses:
        df = pd.DataFrame(courses)
        st.dataframe(df)
        with st.form("update_delete_course"):
            sel = st.selectbox("Chọn course_code", df["course_code"].tolist())
            action = st.selectbox("Action", ["Update", "Delete"])
            if action == "Update":
                new_title = st.text_input("New Title")
                new_schedule = st.text_input("New Schedule")
                if st.form_submit_button("Submit update"):
                    updates = {}
                    if new_title: updates["title"] = new_title
                    if new_schedule: updates["schedule"] = new_schedule
                    ok, msg = manager.update_course(sel, updates)
                    if ok: st.success(msg)
                    else: st.error(msg)
            else:
                if st.form_submit_button("Delete course"):
                    ok, msg = manager.delete_course(sel)
                    if ok: st.success(msg)
                    else: st.error(msg)
    else:
        st.write("No courses yet.")

# Assign teacher
elif menu == "Assign Teacher":
    st.header("Assign teacher to course")
    teachers = manager.read_teachers()
    courses = manager.read_courses()
    if not teachers or not courses:
        st.info("Cần có ít nhất 1 teacher và 1 course.")
    else:
        t_df = pd.DataFrame(teachers)
        c_df = pd.DataFrame(courses)
        teacher_sel = st.selectbox("Teacher", t_df["teacher_id"].tolist())
        course_sel = st.selectbox("Course", c_df["course_code"].tolist())
        if st.button("Assign"):
            ok, msg = manager.assign_teacher(teacher_sel, course_sel)
            if ok: st.success(msg)
            else: st.error(msg)

# Enroll student
elif menu == "Enroll Student":
    st.header("Enroll student into course")
    students = manager.read_students()
    courses = manager.read_courses()
    if not students or not courses:
        st.info("Cần có ít nhất 1 student và 1 course.")
    else:
        s_df = pd.DataFrame(students)
        c_df = pd.DataFrame(courses)
        student_sel = st.selectbox("Student", s_df["student_id"].tolist())
        course_sel = st.selectbox("Course", c_df["course_code"].tolist())
        if st.button("Enroll"):
            ok, msg = manager.enroll_student(student_sel, course_sel)
            if ok: st.success(msg)
            else: st.error(msg)
