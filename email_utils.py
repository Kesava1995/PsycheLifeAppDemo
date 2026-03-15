"""
Dynamic SMTP email helper for per-doctor email sending.
Uses the doctor's own email provider (Gmail, Zoho, Outlook, etc.) and app password.
Also provides a system-level sender for password resets (uses env vars).
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def get_smtp_config(email_address):
    """Detect the correct SMTP server based on the doctor's email domain."""
    if not email_address:
        return None

    domain = email_address.split('@')[-1].lower()

    smtp_map = {
        'gmail.com': 'smtp.gmail.com',
        'zoho.com': 'smtp.zoho.com',
        'zoho.in': 'smtp.zoho.in',
        'zohomail.in': 'smtp.zoho.in',
        'zohomail.com': 'smtp.zoho.com',
        'outlook.com': 'smtp-mail.outlook.com',
        'hotmail.com': 'smtp-mail.outlook.com',
        'yahoo.com': 'smtp.mail.yahoo.com',
        'icloud.com': 'smtp.mail.me.com',
        'mac.com': 'smtp.mail.me.com',
        'me.com': 'smtp.mail.me.com',
        'aol.com': 'smtp.aol.com',
    }

    server = smtp_map.get(domain)
    if not server:
        return None

    return {
        'server': server,
        'port': 587,
    }


def send_dynamic_email(doctor, patient_email, subject, body_text, smtp_password=None):
    """
    Sends an email using the doctor's SMTP credentials.
    smtp_password: plain password for SMTP login (decrypt stored value before calling if encrypted).
    If not provided, doctor.smtp_app_password is used as-is (legacy plain storage).
    """
    password = smtp_password if smtp_password is not None else (doctor.smtp_app_password or None)
    if not doctor.email or not password or not patient_email:
        print(f"Missing email credentials for Doctor: {doctor.full_name}")
        return False

    config = get_smtp_config(doctor.email)
    if not config:
        print(f"Unsupported or custom email domain for: {doctor.email}")
        return False

    msg = MIMEMultipart()
    msg['From'] = f"{doctor.full_name} <{doctor.email}>"
    msg['To'] = patient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body_text, 'plain'))

    try:
        with smtplib.SMTP(config['server'], config['port']) as server:
            server.starttls()
            server.login(doctor.email, password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Failed to send email for {doctor.email}: {str(e)}")
        return False


def send_system_email(to_email, subject, body_text):
    """Sends an email from the system account (e.g., for password resets)."""
    system_email = os.environ.get('SYSTEM_EMAIL')
    system_password = os.environ.get('SYSTEM_EMAIL_PASSWORD')
    smtp_server = os.environ.get('SYSTEM_SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SYSTEM_SMTP_PORT', '587'))

    if not system_email or not system_password:
        print("System email credentials not configured.")
        return False

    msg = MIMEMultipart()
    msg['From'] = system_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body_text, 'plain'))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(system_email, system_password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Failed to send system email: {str(e)}")
        return False
