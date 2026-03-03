from app import app, db
from sqlalchemy import text

def add_template_column():
    with app.app_context():
        try:
            # Execute raw SQL to add the column to the existing table
            db.session.execute(text('ALTER TABLE doctors ADD COLUMN active_template_id INTEGER'))
            db.session.commit()
            print("Successfully added 'active_template_id' to the doctors table!")
        except Exception as e:
            print(f"Error: {e}")
            print("The column might already exist, or there's a DB connection issue.")

if __name__ == '__main__':
    add_template_column()
