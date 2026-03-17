"""
Migration: Add patient_id to adherence_ranges and clinical_state_ranges.
Ranges are stored per patient so they are not deleted when a visit is deleted.
Backfill patient_id from visit_id; visit_id becomes optional (kept for audit).
"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'instance', 'psychelife.db')

def column_exists(cursor, table, col):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(r[1] == col for r in cursor.fetchall())

def run():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        for table, fk_col in [('adherence_ranges', 'patient_id'), ('clinical_state_ranges', 'patient_id')]:
            if not column_exists(cursor, table, fk_col):
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {fk_col} INTEGER REFERENCES patients(id)")
                print(f"Added {fk_col} to {table}.")
            else:
                print(f"{fk_col} already exists in {table}.")

        # Backfill patient_id from visit_id
        cursor.execute("""
            UPDATE adherence_ranges SET patient_id = (SELECT patient_id FROM visits WHERE visits.id = adherence_ranges.visit_id)
            WHERE visit_id IS NOT NULL AND (patient_id IS NULL OR patient_id = 0)
        """)
        cursor.execute("""
            UPDATE clinical_state_ranges SET patient_id = (SELECT patient_id FROM visits WHERE visits.id = clinical_state_ranges.visit_id)
            WHERE visit_id IS NOT NULL AND (patient_id IS NULL OR patient_id = 0)
        """)
        # SQLite: make visit_id nullable by recreating table (optional, complex). Leave as-is; app uses patient_id.
        conn.commit()
        print("Backfill completed.")
    finally:
        conn.close()

if __name__ == '__main__':
    run()
