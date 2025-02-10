from app.auth.utils import *
import pandas as pd

import re
from datetime import datetime, timedelta

from config.config import Config

UPLOAD_FOLDER = Config.UPLOAD_FOLDER
EXTRACTED_FOLDER = Config.EXTRACTED_FOLDER
EXCEL_FILE = Config.EXCEL_FILE
REFERENCE_FOLDER=Config.REFERENCE_FOLDER
Excel_file_path=f"{REFERENCE_FOLDER}/{EXCEL_FILE}"



def read_excel_and_display():
    """
    Read the Excel file and return data for rendering.
    """
    try:
        df = pd.read_excel(Excel_file_path)
        data = df.to_dict(orient="records")
        return data
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return []




def standardize_date(date_str):
    """
    Convert various date string formats to a standard datetime object.
    Returns None if the date string cannot be parsed.
    """
    # Remove any leading/trailing whitespace
    date_str = str(date_str).strip()
    
    # List of possible date formats
    date_formats = [
        # Standard formats
        "%Y-%m-%d",          # 2024-12-23
        "%d-%m-%Y",          # 23-12-2024
        "%Y/%m/%d",          # 2024/12/23
        "%d/%m/%Y",          # 23/12/2024
        "%d.%m.%Y",          # 23.12.2024
        "%Y.%m.%d",          # 2024.12.23
        
        # With time
        "%Y-%m-%d %H:%M:%S",  # 2024-12-23 14:30:00
        "%d-%m-%Y %H:%M:%S",  # 23-12-2024 14:30:00
        "%Y/%m/%d %H:%M:%S",  # 2024/12/23 14:30:00
        "%d/%m/%Y %H:%M:%S",  # 23/12/2024 14:30:00
        "%d.%m.%Y %H:%M:%S",  # 23.12.2024 14:30:00
        
        # Month name formats
        "%d %b %Y",          # 23 Dec 2024
        "%d %B %Y",          # 23 December 2024
        "%b %d, %Y",         # Dec 23, 2024
        "%B %d, %Y",         # December 23, 2024
        
        # American format
        "%m/%d/%Y",          # 12/23/2024
        "%m-%d-%Y",          # 12-23-2024
        "%m.%d.%Y",          # 12.23.2024
    ]
    
    # Try to parse the date string using the defined formats
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    # Try to handle special cases with regex
    # Handle ISO format with timezone
    iso_pattern = r'(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})(?:\.\d+)?([+-]\d{2}:?\d{2}|Z)?'
    iso_match = re.match(iso_pattern, date_str)
    if iso_match:
        try:
            date_part = iso_match.group(1)
            return datetime.strptime(date_part, '%Y-%m-%d')
        except ValueError:
            pass
    
    return None
