import sqlite3
import os

DB_PATH = "uploads/AGAM.db"

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
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS panel_audio (
        id TEXT PRIMARY KEY,
        comic_id TEXT NOT NULL,
        page_number INTEGER NOT NULL,
        panel_index INTEGER NOT NULL,
        dialogue_text TEXT,
        sfx_description TEXT,
        audio_path TEXT,
        sfx_path TEXT,
        FOREIGN KEY(comic_id) REFERENCES comics(id) ON DELETE CASCADE
    );
    """)
    conn.commit()
    conn.close()

def get_db_connection():
    os.makedirs("uploads", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

