"""
Migration script to update database schema for Phase 1 and Phase 2.
Phase 1: Adds new columns for Patient details, Doctor contact, and Clinical sliders.
Phase 2: Adds new tables for Stressors and Personality traits.
"""
from app import app, db
import sqlite3

def column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table."""
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        return column_name in columns
    except sqlite3.OperationalError:
        return False

def table_exists(cursor, table_name):
    """Check if a table exists."""
    try:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        return cursor.fetchone() is not None
    except sqlite3.OperationalError:
        return False

def migrate():
    """Add missing columns to tables."""
    with app.app_context():
        connection = db.engine.raw_connection()
        try:
            cursor = connection.cursor()
            print("--- Starting Phase 1 Migration ---")

            # 1. Update DOCTORS Table
            # New fields: phone, email
            print("\n[Doctors Table]")
            doctor_cols = [
                ('phone', 'TEXT'),
                ('email', 'TEXT'),
                # Ensure previous fields exist too just in case
                ('full_name', 'TEXT'), ('clinic_name', 'TEXT'),
                ('kmc_code', 'TEXT'), ('address_text', 'TEXT'),
                ('social_handle', 'TEXT'), ('signature_filename', 'TEXT')
            ]
            for col, dtype in doctor_cols:
                if not column_exists(cursor, 'doctors', col):
                    cursor.execute(f"ALTER TABLE doctors ADD COLUMN {col} {dtype}")
                    print(f"  + Added {col}")
                else:
                    print(f"  - {col} exists")

            # 2. Update PATIENTS Table
            # New fields: phone, attender details, personal_notes
            print("\n[Patients Table]")
            patient_cols = [
                ('phone', 'TEXT'),
                ('attender_name', 'TEXT'),
                ('attender_relation', 'TEXT'),
                ('attender_reliability', 'TEXT'),
                ('personal_notes', 'TEXT')
            ]
            for col, dtype in patient_cols:
                if not column_exists(cursor, 'patients', col):
                    cursor.execute(f"ALTER TABLE patients ADD COLUMN {col} {dtype}")
                    print(f"  + Added {col}")
                else:
                    print(f"  - {col} exists")

            # 3. Update MEDICATION_ENTRIES Table
            # New field: frequency
            print("\n[Medication Entries]")
            if not column_exists(cursor, 'medication_entries', 'frequency'):
                cursor.execute("ALTER TABLE medication_entries ADD COLUMN frequency TEXT")
                print("  + Added frequency")
            else:
                print("  - frequency exists")

            # 4. Update SIDE_EFFECT_ENTRIES Table
            # New fields: score_onset, score_progression, score_current, duration_text
            print("\n[Side Effect Entries]")
            se_cols = [
                ('score_onset', 'FLOAT'),
                ('score_progression', 'FLOAT'),
                ('score_current', 'FLOAT DEFAULT 0'),
                ('duration_text', 'TEXT')
            ]
            for col, dtype in se_cols:
                if not column_exists(cursor, 'side_effect_entries', col):
                    cursor.execute(f"ALTER TABLE side_effect_entries ADD COLUMN {col} {dtype}")
                    print(f"  + Added {col}")
                    
                    # MIGRATION LOGIC: Copy old 'score' to 'score_current' if it exists
                    if col == 'score_current' and column_exists(cursor, 'side_effect_entries', 'score'):
                        print("    > Migrating old data to score_current...")
                        cursor.execute("UPDATE side_effect_entries SET score_current = score WHERE score IS NOT NULL")
                else:
                    print(f"  - {col} exists")

            # 5. Update MSE_ENTRIES Table
            # New fields: score_onset, score_progression, score_current
            print("\n[MSE Entries]")
            mse_cols = [
                ('score_onset', 'FLOAT'),
                ('score_progression', 'FLOAT'),
                ('score_current', 'FLOAT DEFAULT 0')
            ]
            for col, dtype in mse_cols:
                if not column_exists(cursor, 'mse_entries', col):
                    cursor.execute(f"ALTER TABLE mse_entries ADD COLUMN {col} {dtype}")
                    print(f"  + Added {col}")

                    # MIGRATION LOGIC: Copy old 'score' to 'score_current'
                    if col == 'score_current' and column_exists(cursor, 'mse_entries', 'score'):
                        print("    > Migrating old data to score_current...")
                        cursor.execute("UPDATE mse_entries SET score_current = score WHERE score IS NOT NULL")
                else:
                    print(f"  - {col} exists")

            # 6. Update VISITS Table
            # New fields: next_visit_date, drug_allergies, medical_comorbidities, non_psychiatric_meds
            print("\n[Visits Table]")
            visit_cols = [
                ('next_visit_date', 'DATE'),
                ('drug_allergies', 'TEXT'),
                ('medical_comorbidities', 'TEXT'),
                ('non_psychiatric_meds', 'TEXT')
            ]
            for col, dtype in visit_cols:
                if not column_exists(cursor, 'visits', col):
                    cursor.execute(f"ALTER TABLE visits ADD COLUMN {col} {dtype}")
                    print(f"  + Added {col}")
                else:
                    print(f"  - {col} exists")

            # 7. Phase 2: Create STRESSOR_ENTRIES Table
            print("\n[Phase 2: Stressor Entries Table]")
            if not table_exists(cursor, 'stressor_entries'):
                cursor.execute("""
                    CREATE TABLE stressor_entries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        visit_id INTEGER NOT NULL,
                        stressor_type TEXT,
                        note TEXT,
                        FOREIGN KEY (visit_id) REFERENCES visits (id)
                    )
                """)
                print("  + Created stressor_entries table")
            else:
                print("  - stressor_entries table exists")

            # 8. Phase 2: Create PERSONALITY_ENTRIES Table
            print("\n[Phase 2: Personality Entries Table]")
            if not table_exists(cursor, 'personality_entries'):
                cursor.execute("""
                    CREATE TABLE personality_entries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        visit_id INTEGER NOT NULL,
                        trait TEXT,
                        note TEXT,
                        FOREIGN KEY (visit_id) REFERENCES visits (id)
                    )
                """)
                print("  + Created personality_entries table")
            else:
                print("  - personality_entries table exists")

            # 9. Phase 3: Create SAFETY_MEDICAL_PROFILES Table & Migrate Data
            print("\n[Phase 3: Safety Medical Profiles Table]")
            if not table_exists(cursor, 'safety_medical_profiles'):
                cursor.execute("""
                    CREATE TABLE safety_medical_profiles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        visit_id INTEGER NOT NULL,
                        drug_allergies TEXT,
                        medical_comorbidities TEXT,
                        non_psychiatric_meds TEXT,
                        FOREIGN KEY (visit_id) REFERENCES visits (id)
                    )
                """)
                print("  + Created safety_medical_profiles table")
                # Migrate existing data from visits if columns exist
                if column_exists(cursor, 'visits', 'drug_allergies'):
                    cursor.execute("""
                        INSERT INTO safety_medical_profiles (visit_id, drug_allergies, medical_comorbidities, non_psychiatric_meds)
                        SELECT id, drug_allergies, medical_comorbidities, non_psychiatric_meds
                        FROM visits
                        WHERE drug_allergies IS NOT NULL AND drug_allergies != ''
                           OR medical_comorbidities IS NOT NULL AND medical_comorbidities != ''
                           OR non_psychiatric_meds IS NOT NULL AND non_psychiatric_meds != ''
                    """)
                    migrated = cursor.rowcount
                    print(f"  > Migrated {migrated} visit(s) to safety_medical_profiles")
            else:
                print("  - safety_medical_profiles table exists")

            connection.commit()
            print("\n--- Migration Completed Successfully! ---")
            
        except Exception as e:
            connection.rollback()
            print(f"\nCRITICAL ERROR: {e}")
            import traceback
            traceback.print_exc()
        finally:
            connection.close()

if __name__ == '__main__':
    migrate()
