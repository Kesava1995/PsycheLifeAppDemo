"""
Migration script to add tapering columns to medication_entries table.
"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'instance', 'psychelife.db')


def column_exists(cursor, table_name, column_name):
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        return column_name in columns
    except sqlite3.OperationalError:
        return False


def migrate():
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}. Please check the path.")
        return

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        if not column_exists(cursor, 'medication_entries', 'is_tapering'):
            print("Adding 'is_tapering' column...")
            cursor.execute("ALTER TABLE medication_entries ADD COLUMN is_tapering BOOLEAN DEFAULT 0")
            print("  + Added is_tapering")
        else:
            print("  - is_tapering already exists")

        if not column_exists(cursor, 'medication_entries', 'taper_plan'):
            print("Adding 'taper_plan' column...")
            cursor.execute("ALTER TABLE medication_entries ADD COLUMN taper_plan TEXT")
            print("  + Added taper_plan")
        else:
            print("  - taper_plan already exists")

        conn.commit()
        print("\n[OK] Migration successful! Tapering columns added to medication_entries table.")

    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("[!] Columns already exist. No migration needed.")
        else:
            print(f"[ERROR] An error occurred: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    migrate()
