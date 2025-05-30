import sqlite3
from datetime import datetime

DB_FILE = "oznamy.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                typ TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                datetime TEXT,
                day TEXT,
                link TEXT,
                image TEXT,
                visible_from TEXT,
                visible_to TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()

def add_announcement(typ, title, description, datetime_str, day, link, image, visible_from, visible_to):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO announcements (
                typ, title, description, datetime, day, link, image, visible_from, visible_to, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            typ,
            title,
            description,
            datetime_str,
            day,
            link,
            image,
            visible_from,
            visible_to,
            datetime.now().isoformat()
        ))
        conn.commit()

def get_all_announcements():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT typ, title, description, datetime, day, link, image, visible_from, visible_to
            FROM announcements
            ORDER BY datetime(created_at) DESC
        """)
        rows = cursor.fetchall()

        announcements = []
        for row in rows:
            announcements.append({
                "typ": row[0],
                "title": row[1],
                "description": row[2],
                "datetime": row[3],
                "day": row[4],
                "link": row[5],
                "image": row[6],
                "visible_from": row[7],
                "visible_to": row[8]
            })
        return announcements
