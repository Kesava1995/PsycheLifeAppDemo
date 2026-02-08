from app import app, db, Doctor
from werkzeug.security import generate_password_hash

def reset_user_password(email, new_password):
    with app.app_context():
        # Find the user
        doctor = Doctor.query.filter_by(email=email).first()
        
        if doctor:
            print(f"User found: {doctor.username}")
            # Generate new hash
            hashed_pw = generate_password_hash(new_password, method='scrypt')
            doctor.password_hash = hashed_pw
            
            # Save to DB
            db.session.commit()
            print(f"Success! Password for '{email}' has been updated.")
        else:
            print(f"Error: No user found with email '{email}'")

if __name__ == "__main__":
    email_input = input("Enter the doctor's email address: ")
    password_input = input("Enter the new password: ")
    reset_user_password(email_input, password_input)