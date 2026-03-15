"""
One-off script: schedule a test email from doctor id 2 to patient id 3
in 2.5 minutes, then exit. Run with: python schedule_test_email.py
"""
import time
import threading

# Import after we're in the right directory
from app import app
from models import db, Doctor, Patient
from email_utils import send_dynamic_email
from encryption_utils import decrypt_smtp_password


def send_test_email():
    with app.app_context():
        doctor = db.session.get(Doctor, 2)
        patient = db.session.get(Patient, 3)
        if not doctor:
            print("Doctor id 2 not found.")
            return
        if not patient:
            print("Patient id 3 not found.")
            return
        if not patient.email:
            print("Patient id 3 has no email in DB.")
            return
        if not doctor.email or not doctor.smtp_app_password:
            print("Doctor id 2 has no email or SMTP app password in DB.")
            return
        subject = "Visit Reminder"
        body = "Your visit is due on 18-03-2026"
        smtp_password = decrypt_smtp_password(doctor.smtp_app_password)
        ok = send_dynamic_email(doctor, patient.email, subject, body, smtp_password=smtp_password)
        if ok:
            print(f"Email sent to {patient.email}.")
        else:
            print("Send failed. If you see '535 Authentication Failed': use the doctor's App Password from")
            print("  Profile (not the normal login password). For Zoho: Zoho Mail → Settings → Security → App Passwords.")


if __name__ == "__main__":
    delay_seconds = 15  # 2.5 minutes
    print(f"Scheduling test email in {delay_seconds} seconds ({delay_seconds/60:.1f} min)...")
    print("From: Doctor id 2 -> To: Patient id 3")
    print("Message: Your visit is due on 18-03-2026")
    print("(Keep this window open until 'Email sent' appears.)\n")
    timer = threading.Timer(delay_seconds, send_test_email)
    timer.daemon = False
    timer.start()
    time.sleep(delay_seconds + 5)
    print("Done.")
