"""
Standalone script to run daily appointment + medication tapering reminders.
Use for PythonAnywhere Tasks (e.g. run daily at 8:00 AM) or: python cron_reminders.py
Uses existing email_utils, encryption_utils, and decrypt_smtp_password (same as schedule_test_email.py).
"""
from app import app, get_ist_now
from models import db, Doctor, Visit, Patient, MedicationEntry
from datetime import date, timedelta
import json
from medical_utils import parse_duration
from email_utils import send_dynamic_email
from encryption_utils import decrypt_smtp_password


def run_daily_reminders():
    # Subtract/Add timezone correction by using your get_ist_now() function
    today = get_ist_now().date()
    
    print(f"--- Starting cron job for IST Date: {today} ---")

    with app.app_context():
        today = date.today()

        # ---------------------------------------------------------
        # 1. APPOINTMENT REMINDERS
        # ---------------------------------------------------------
        print("Checking appointment reminders...")
        doctors = Doctor.query.all()

        for doctor in doctors:
            if not doctor.email or not getattr(doctor, 'smtp_app_password', None):
                continue

            smtp_password = decrypt_smtp_password(doctor.smtp_app_password)

            reminder_str = getattr(doctor, 'appointment_reminder_days', None) or "7,3,1"
            try:
                reminder_days = [int(d.strip()) for d in reminder_str.split(',') if d.strip()]
            except (ValueError, AttributeError):
                reminder_days = [7, 3, 1]

            for days_ahead in reminder_days:
                target_date = today + timedelta(days=days_ahead)

                upcoming_visits = Visit.query.join(Patient).filter(
                    Patient.doctor_id == doctor.id,
                    Visit.next_visit_date == target_date
                ).all()

                for visit in upcoming_visits:
                    patient = visit.patient
                    # Per-patient override (if set), else doctor default
                    effective_str = getattr(patient, 'appointment_reminder_days', None) or getattr(doctor, 'appointment_reminder_days', None) or "7,3,1"
                    try:
                        effective_days = [int(d.strip()) for d in effective_str.split(',') if d.strip()]
                    except (ValueError, AttributeError):
                        effective_days = [7, 3, 1]
                    if days_ahead not in effective_days:
                        continue

                    if getattr(patient, 'email', None):
                        subject = f"Appointment Reminder with {doctor.full_name or 'your Doctor'}"
                        body = (
                            f"Dear {patient.name},\n\n"
                            f"This is a reminder for your upcoming appointment with Dr.{doctor.full_name or 'your doctor'} "
                            f"on {target_date.strftime('%B %d, %Y')}.\n\n"
                            f"Best regards,\n{doctor.clinic_name or 'The Clinic'}"
                        )

                        if send_dynamic_email(doctor, patient.email, subject, body, smtp_password=smtp_password):
                            print(f"Sent appointment reminder to {patient.email}")

        # ---------------------------------------------------------
        # 2. MEDICATION TAPERING REMINDERS
        # ---------------------------------------------------------
        print("Checking medication tapering reminders...")
        active_tapering_meds = MedicationEntry.query.filter_by(is_tapering=True).all()

        for med in active_tapering_meds:
            if not med.taper_plan:
                continue

            try:
                plan_steps = json.loads(med.taper_plan)
            except json.JSONDecodeError:
                continue

            current_date = med.visit.date

            for index, step in enumerate(plan_steps):
                duration_delta = parse_duration(step.get('duration_text', ''))
                if not duration_delta:
                    continue

                step_end_date = current_date + duration_delta

                if step_end_date == today + timedelta(days=1):
                    if index + 1 < len(plan_steps):
                        next_step = plan_steps[index + 1]
                        patient = med.visit.patient
                        doctor = patient.doctor

                        if getattr(patient, 'email', None) and doctor.email and getattr(doctor, 'smtp_app_password', None):
                            smtp_password = decrypt_smtp_password(doctor.smtp_app_password)

                            subject = f"Medication Update: {med.drug_name}"
                            body = (
                                f"Dear {patient.name},\n\n"
                                f"As per your treatment plan, your dosage "
                                f"for {med.drug_name} changes tomorrow.\n\n"
                                f"New Instructions:\n"
                                f"- Dose: {next_step.get('dose_mg', 'N/A')}\n"
                                f"- Frequency: {next_step.get('frequency', 'N/A')}\n"
                                f"- Duration: {next_step.get('duration_text', 'N/A')}\n\n"
                                f"Best regards,\n{doctor.clinic_name or 'The Clinic'}"
                            )

                            if send_dynamic_email(doctor, patient.email, subject, body, smtp_password=smtp_password):
                                print(f"Sent medication update to {patient.email}")

                current_date = step_end_date

    print("--- Cron job finished successfully ---")


if __name__ == "__main__":
    run_daily_reminders()
