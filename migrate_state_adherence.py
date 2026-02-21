import sqlite3
import os

db_path = os.path.join('instance', 'psychelife.db')

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Add clinical_state column
    try:
        cursor.execute("ALTER TABLE visits ADD COLUMN clinical_state VARCHAR(50)")
        print("Added 'clinical_state' column successfully.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column 'clinical_state' already exists.")
        else:
            print(f"Error adding 'clinical_state': {e}")

    # Add medication_adherence column
    try:
        cursor.execute("ALTER TABLE visits ADD COLUMN medication_adherence VARCHAR(50)")
        print("Added 'medication_adherence' column successfully.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column 'medication_adherence' already exists.")
        else:
            print(f"Error adding 'medication_adherence': {e}")
            
    conn.commit()
    print("Database migration completed.")

except Exception as e:
    print(f"An error occurred: {e}")
finally:
    if 'conn' in locals():
        conn.close()