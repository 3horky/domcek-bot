import sqlite3
import sys
import os

DB_FILE = "oznamy.db"

def migrate():
    if not os.path.exists(DB_FILE):
        print(f"Database file {DB_FILE} not found. Nothing to migrate.")
        # If the DB doesn't exist, running the bot will create it with the correct schema via init_db()
        # But we can also just initialize it here.
        return

    print(f"Migrating database {DB_FILE}...")
    
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        
        # 1. Ensure bot_settings table exists
        print("Checking 'bot_settings' table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        # 2. Check columns in announcements table
        print("Checking 'announcements' table schema...")
        try:
            cursor.execute("PRAGMA table_info(announcements)")
            columns = [info[1] for info in cursor.fetchall()]
            
            if not columns:
                print("Table 'announcements' does not exist. It will be created by the bot on startup.")
            else:
                # List of expected columns and their types
                expected_columns = {
                    "visible_from": "TEXT",
                    "visible_to": "TEXT",
                    "created_at": "TEXT NOT NULL DEFAULT '2024-01-01T00:00:00'"
                }
                
                for col_name, col_def in expected_columns.items():
                    if col_name not in columns:
                        print(f"Adding missing column '{col_name}' to 'announcements'...")
                        try:
                            # SQLite doesn't support adding multiple columns in one statement easily or with complex constraints in older versions
                            # But ADD COLUMN is supported.
                            # For created_at, we need a default value for existing rows.
                            if "NOT NULL" in col_def and "DEFAULT" not in col_def:
                                # If we are adding a NOT NULL column without default, it will fail for existing rows
                                # So we strip NOT NULL for the migration or add a default
                                pass
                            
                            cursor.execute(f"ALTER TABLE announcements ADD COLUMN {col_name} {col_def}")
                            print(f"Column '{col_name}' added.")
                        except sqlite3.OperationalError as e:
                            print(f"Error adding column {col_name}: {e}")

        except sqlite3.OperationalError as e:
            print(f"Error checking announcements table: {e}")

        conn.commit()
        print("Migration completed successfully.")

if __name__ == "__main__":
    migrate()
