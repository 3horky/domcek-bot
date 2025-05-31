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
            SELECT id, typ, title, description, datetime, day, link, image, visible_from, visible_to
            FROM announcements
            ORDER BY datetime(created_at) DESC
        """)
        rows = cursor.fetchall()

        announcements = []
        for row in rows:
            announcements.append({
                "id": row[0],
                "typ": row[1],
                "title": row[2],
                "description": row[3],
                "datetime": row[4],
                "day": row[5],
                "link": row[6],
                "image": row[7],
                "visible_from": row[8],
                "visible_to": row[9]
            })
        return announcements

def get_announcement_by_id(announcement_id):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, typ, title, description, datetime, day, link, image, visible_from, visible_to, created_at
            FROM announcements
            WHERE id = ?
        """, (announcement_id,))
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "typ": row[1],
                "title": row[2],
                "description": row[3],
                "datetime": row[4],
                "day": row[5],
                "link": row[6],
                "image": row[7],
                "visible_from": row[8],
                "visible_to": row[9],
                "created_at": row[10]
            }
        return None

def delete_announcement_by_id(announcement_id):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM announcements WHERE id = ?", (announcement_id,))
        conn.commit()

def delete_expired_announcements():
    today = datetime.now().date()
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM announcements
            WHERE DATE(substr(visible_to, 7, 4) || '-' || substr(visible_to, 4, 2) || '-' || substr(visible_to, 1, 2)) < DATE(?)
        """, (today.isoformat(),))
        conn.commit()
