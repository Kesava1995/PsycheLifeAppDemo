"""
Migration script to update database schema.
Adds missing columns to 'visits' and 'doctors' tables.
"""
from app import app, db

def column_exists(connection, table_name, column_name):
    """Check if a column exists in a table."""
    cursor = connection.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns

def migrate():
    """Add missing columns to tables."""
    with app.app_context():
        connection = db.engine.raw_connection()
        try:
            cursor = connection.cursor()
            
            print("--- Checking Visits Table ---")
            # 1. Add provisional_diagnosis to visits
            if not column_exists(connection, 'visits', 'provisional_diagnosis'):
                cursor.execute("ALTER TABLE visits ADD COLUMN provisional_diagnosis TEXT")
                print("[OK] Added provisional_diagnosis column")
            else:
                print("[SKIP] provisional_diagnosis column already exists")
            
            # 2. Add differential_diagnosis to visits
            if not column_exists(connection, 'visits', 'differential_diagnosis'):
                cursor.execute("ALTER TABLE visits ADD COLUMN differential_diagnosis TEXT")
                print("[OK] Added differential_diagnosis column")
            else:
                print("[SKIP] differential_diagnosis column already exists")
            
            print("\n--- Checking Doctors Table ---")
            # 3. Add new Doctor columns defined in models.py
            doctor_columns = [
                ('full_name', 'TEXT'),
                ('clinic_name', 'TEXT'),
                ('kmc_code', 'TEXT'),
                ('address_text', 'TEXT'),
                ('social_handle', 'TEXT'),
                ('signature_filename', 'TEXT')
            ]

            for col_name, col_type in doctor_columns:
                if not column_exists(connection, 'doctors', col_name):
                    cursor.execute(f"ALTER TABLE doctors ADD COLUMN {col_name} {col_type}")
                    print(f"[OK] Added {col_name} column")
                else:
                    print(f"[SKIP] {col_name} column already exists")
            
            connection.commit()
            print("\nMigration completed successfully!")
            
        except Exception as e:
            connection.rollback()
            print(f"\nError during migration: {e}")
        finally:
            connection.close()

if __name__ == '__main__':
    migrate()