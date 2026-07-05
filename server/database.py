import sqlite3
import os

DB_PATH = "uploads/chika.db"

def init_db():
    os.makedirs("uploads", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comics (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            file_path TEXT NOT NULL,
            total_pages INTEGER NOT NULL,
            progress_page INTEGER DEFAULT 0,
            progress_panel INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def get_db_connection():
    return sqlite3.connect(DB_PATH)
