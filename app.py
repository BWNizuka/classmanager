# app.py
from abc import ABC, abstractmethod
from pymongo import MongoClient, errors
import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from typing import Optional

# ---------- Load biến môi trường từ .env ----------
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "classmanager")

# ---------- MongoDB client ----------
def get_db(uri: str, db_name: str):
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=8000)
        client.admin.command("ping")  # test connection
        db = client[db_name]
        return db
    except errors.ConfigurationError as e:
        st.error(f"Configuration Error: {e}")
        return None
    except errors.ServerSelectionTimeoutError as e:
        st.error(f"Connection timeout: {e}")
        return None
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
