import os
from datetime import timedelta

class Config:
    SECRET_KEY = 'your_secret_key'
    UPLOAD_FOLDER = 'app/static/uploads'
    EXTRACTED_FOLDER = 'extracted_text'
    REFERENCE_FOLDER="Reference_files"
    EXCEL_TEMPLATE="Excel_template"
    EXCEL_FILE = 'queries.xlsx'
    
    # Session configuration
    SESSION_PERMANENT = False
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
        # # Database configuration
    DB_CONFIG = {
        "host": "localhost",
        "user": "root",
        "password": "root",
        "database": "vasp"
    }
