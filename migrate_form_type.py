import sqlite3
import os

def migrate():
    # Make sure we're targeting the correct database path
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'psychelife.db')
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Add the new column to the medication_entries table
        cursor.execute("ALTER TABLE medication_entries ADD COLUMN form_type VARCHAR(50) DEFAULT 'Tablet'")
        print("Successfully added 'form_type' column to medication_entries!")
    except sqlite3.OperationalError as e:
        # If it throws an error, it might mean the column is already there
        print(f"Error or column already exists: {e}")

    conn.commit()
    conn.close()

if __name__ == '__main__':
    migrate()
