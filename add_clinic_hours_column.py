"""Add clinic_hours column to doctors table for storing clinic hours JSON."""
from app import app, db
from sqlalchemy import text

def add_clinic_hours_column():
    with app.app_context():
        try:
            db.session.execute(text('ALTER TABLE doctors ADD COLUMN clinic_hours TEXT'))
            db.session.commit()
            print("Successfully added 'clinic_hours' to the doctors table!")
        except Exception as e:
            print(f"Error: {e}")
            print("The column might already exist, or there's a DB connection issue.")

if __name__ == '__main__':
    add_clinic_hours_column()
