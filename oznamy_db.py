import sqlite3
from datetime import datetime

DB_PATH = "announcements.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                image_url TEXT,
                link_url TEXT,
                type TEXT CHECK(type IN ('general', 'event')) NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                event_day TEXT,
                event_datetime TEXT,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()

def add_announcement(title, description, image_url, link_url, type, start_date, end_date, event_day, event_datetime, created_by):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO announcements
            (title, description, image_url, link_url, type, start_date, end_date, event_day, event_datetime, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            title, description, image_url, link_url, type,
            start_date, end_date, event_day, event_datetime,
            created_by, datetime.utcnow().isoformat()
        ))
        conn.commit()
