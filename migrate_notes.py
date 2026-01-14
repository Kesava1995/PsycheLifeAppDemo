"""
Migration script to add note columns and drug_type column.
"""
import sqlite3
import os

def column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns

def migrate():
    """Add note and drug_type columns."""
    db_path = os.path.join('instance', 'psychelife.db')
    
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Add note to symptom_entries
        if not column_exists(cursor, 'symptom_entries', 'note'):
            cursor.execute("ALTER TABLE symptom_entries ADD COLUMN note TEXT")
            print("[OK] Added note to symptom_entries")
        else:
            print("[SKIP] note column already exists in symptom_entries")
        
        # Add note to medication_entries
        if not column_exists(cursor, 'medication_entries', 'note'):
            cursor.execute("ALTER TABLE medication_entries ADD COLUMN note TEXT")
            print("[OK] Added note to medication_entries")
        else:
            print("[SKIP] note column already exists in medication_entries")
        
        # Add note to side_effect_entries
        if not column_exists(cursor, 'side_effect_entries', 'note'):
            cursor.execute("ALTER TABLE side_effect_entries ADD COLUMN note TEXT")
            print("[OK] Added note to side_effect_entries")
        else:
            print("[SKIP] note column already exists in side_effect_entries")
        
        # Add note to mse_entries
        if not column_exists(cursor, 'mse_entries', 'note'):
            cursor.execute("ALTER TABLE mse_entries ADD COLUMN note TEXT")
            print("[OK] Added note to mse_entries")
        else:
            print("[SKIP] note column already exists in mse_entries")
        
        # Add note to visits
        if not column_exists(cursor, 'visits', 'note'):
            cursor.execute("ALTER TABLE visits ADD COLUMN note TEXT")
            print("[OK] Added note to visits")
        else:
            print("[SKIP] note column already exists in visits")
        
        # Add drug_type to medication_entries
        if not column_exists(cursor, 'medication_entries', 'drug_type'):
            cursor.execute("ALTER TABLE medication_entries ADD COLUMN drug_type VARCHAR(50)")
            print("[OK] Added drug_type to medication_entries")
        else:
            print("[SKIP] drug_type column already exists in medication_entries")
        
        conn.commit()
        print("Migration successful")
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()

