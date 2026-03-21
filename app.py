"""
PsycheLife - Medical web app for psychiatric patient management.
"""

from dotenv import load_dotenv
import os as _os
# Load .env from the same directory as app.py (project root), not from cwd
_env_path = _os.path.join(_os.path.abspath(_os.path.dirname(__file__)), '.env')
load_dotenv(_env_path)

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, make_response, session, abort
from functools import wraps
from datetime import datetime, date, timedelta, timezone
import re

IST = timezone(timedelta(hours=5, minutes=30))


def get_ist_now():
    """Returns the exact current time in IST as a naive datetime (safe for SQLite)."""
    return datetime.utcnow() + timedelta(hours=5, minutes=30)


# Default clinic hours (morning / evening) for dashboard badges and edit modal
DEFAULT_CLINIC_HOURS = {
    "morning": {"start": "09:00", "end": "17:00"},
    "evening": {"start": "17:00", "end": "22:00"},
}


def _time_to_display(s):
    """Convert 24h 'HH:MM' to display e.g. '9:00 AM', '5:00 PM'."""
    if not s or len(s) < 5:
        return s or ""
    h, m = int(s[:2]), s[3:5]
    if h == 0:
        return "12:" + m + " AM"
    if h < 12:
        return str(h) + ":" + m + " AM"
    if h == 12:
        return "12:" + m + " PM"
    return str(h - 12) + ":" + m + " PM"


def get_clinic_hours(doctor):
    """Return clinic hours dict for template: morning_start/end, evening_start/end, morning_display, evening_display."""
    raw = DEFAULT_CLINIC_HOURS.copy()
    if doctor and getattr(doctor, "clinic_hours", None):
        try:
            raw = json.loads(doctor.clinic_hours)
        except (TypeError, ValueError):
            pass
    m = raw.get("morning", {})
    e = raw.get("evening", {})
    m_start = m.get("start", "09:00")
    m_end = m.get("end", "17:00")
    e_start = e.get("start", "17:00")
    e_end = e.get("end", "22:00")
    return {
        "morning_start": m_start,
        "morning_end": m_end,
        "evening_start": e_start,
        "evening_end": e_end,
        "morning_display": _time_to_display(m_start) + "\u2013" + _time_to_display(m_end),
        "evening_display": _time_to_display(e_start) + "\u2013" + _time_to_display(e_end),
    }


from models import db, Doctor, Patient, Visit, SymptomEntry, MedicationEntry, SideEffectEntry, MSEEntry, GuestShare, StressorEntry, PersonalityEntry, SafetyMedicalProfile, MajorEvent, AdherenceRange, ClinicalStateRange, DefaultTemplate, CustomTemplate, SubstanceUseEntry, ScaleAssessment, Appointment, DashboardNote, Notification, ScheduleTemplate, Feedback
from medical_utils import get_unified_dose, compute_med_chart_value, calculate_start_date, parse_duration, calculate_midpoint_date, format_frequency, process_scale_submission, duration_to_days, format_timedelta_as_duration
from email_utils import send_dynamic_email, send_system_email
from encryption_utils import encrypt_smtp_password, decrypt_smtp_password
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from werkzeug.security import generate_password_hash
from flask_apscheduler import APScheduler
import io
import os
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import qrcode
from urllib.parse import urljoin, unquote, quote_plus
from werkzeug.utils import secure_filename
import base64
import uuid
import json
import time
import requests
from difflib import SequenceMatcher
from sqlalchemy import text

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
basedir = os.path.abspath(os.path.dirname(__file__))
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# Lifechart: consider symptom "same" if case-insensitive partial match >= threshold (default 0.85)
def _symptom_name_matches(name1, name2, threshold=0.85):
    if not (name1 and name2):
        return False
    a, b = name1.lower().strip(), name2.lower().strip()
    return SequenceMatcher(None, a, b).ratio() >= threshold


def parse_diagnosis_values(value):
    """Return a de-duplicated list of diagnosis items from legacy text or JSON."""
    if value is None:
        return []

    raw_items = value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                raw_items = parsed
            elif isinstance(parsed, dict):
                raw_items = [parsed]
            elif isinstance(parsed, str):
                raw_items = [parsed]
            else:
                raw_items = [text]
        except (TypeError, ValueError):
            raw_items = [part.strip() for part in re.split(r'[\r\n,]+', text) if part.strip()]
    elif isinstance(value, dict):
        raw_items = [value]
    elif not isinstance(value, list):
        raw_items = [value]

    normalized = []
    seen = set()
    for item in raw_items:
        if isinstance(item, dict):
            label = str(item.get('label') or item.get('title') or item.get('name') or item.get('value') or '').strip()
            code = str(item.get('code') or '').strip()
            system = str(item.get('system') or '').strip()
        else:
            label = str(item).strip()
            code = ''
            system = ''

        if not label:
            continue

        key = (label.lower(), code.lower(), system.lower())
        if key in seen:
            continue
        seen.add(key)
        normalized.append({
            'label': label,
            'code': code,
            'system': system,
        })

    return normalized


def serialize_diagnosis_values(value):
    return json.dumps(parse_diagnosis_values(value), ensure_ascii=True)


def format_diagnosis_values(value):
    return ', '.join(item['label'] for item in parse_diagnosis_values(value))


def diagnosis_json_filter(value):
    return parse_diagnosis_values(value)


def diagnosis_display_filter(value):
    return format_diagnosis_values(value)


app.add_template_filter(diagnosis_json_filter, 'diagnosis_json')
app.add_template_filter(diagnosis_display_filter, 'diagnosis_display')

# Use absolute path for DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'psychelife.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Prevent 'database is locked' errors by adding a 15-second timeout
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "connect_args": {
        "timeout": 15
    }
}

# Use absolute path for Uploads
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'static', 'signatures')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

os.makedirs(os.path.join(basedir, 'instance'), exist_ok=True)
db.init_app(app)

# --- WHO ICD-11 API (token cache + search proxy; use ICD11_CLIENT_ID / ICD11_CLIENT_SECRET in .env) ---
_who_token_cache = {'token': None, 'expires_at': 0}


def get_who_access_token():
    """Return OAuth access token for WHO ICD API (in-memory cache, ~60s before expiry)."""
    now = time.time()
    if _who_token_cache['token'] and now < _who_token_cache['expires_at']:
        return _who_token_cache['token']
    client_id = os.environ.get('ICD11_CLIENT_ID')
    client_secret = os.environ.get('ICD11_CLIENT_SECRET')
    if not client_id or client_id == 'your_client_id_here' or not client_secret:
        return None
    try:
        r = requests.post(
            'https://icdaccessmanagement.who.int/connect/token',
            data={
                'client_id': client_id,
                'client_secret': client_secret,
                'scope': 'icdapi_access',
                'grant_type': 'client_credentials',
            },
            timeout=30,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        token = data.get('access_token')
        if not token:
            return None
        expires_in = int(data.get('expires_in', 3600))
        _who_token_cache['token'] = token
        _who_token_cache['expires_at'] = now + max(expires_in - 60, 60)
        return token
    except (requests.exceptions.RequestException, ValueError, TypeError):
        return None


@app.route('/icd11token')
def icd11_token():
    client_id = os.environ.get('ICD11_CLIENT_ID')
    client_secret = os.environ.get('ICD11_CLIENT_SECRET')
    if not client_id or client_id == 'your_client_id_here' or not client_secret:
        return jsonify({'error': 'ICD-11 API credentials not configured. Set ICD11_CLIENT_ID and ICD11_CLIENT_SECRET in .env'}), 503
    token = get_who_access_token()
    if not token:
        return jsonify({'error': 'Cannot obtain WHO access token. Check credentials and network.'}), 503
    return jsonify({'access_token': token, 'token_type': 'Bearer', 'expires_in': 3600})


@app.route('/api/search_icd11')
def search_icd11():
    """Proxy search to WHO ICD-11 MMS (no API keys in the browser)."""
    query = (request.args.get('q') or '').strip()
    if len(query) < 2:
        return jsonify([])

    token = get_who_access_token()
    if not token:
        return jsonify([])

    search_url = (
        'https://id.who.int/icd/release/11/2024-01/mms/search?q='
        + quote_plus(query)
        + '&flatResults=true'
    )
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json',
        'Accept-Language': 'en',
        'API-Version': 'v2',
    }
    try:
        res = requests.get(search_url, headers=headers, timeout=30)
        if res.status_code == 401:
            _who_token_cache['token'] = None
            _who_token_cache['expires_at'] = 0
            token = get_who_access_token()
            if token:
                headers['Authorization'] = f'Bearer {token}'
                res = requests.get(search_url, headers=headers, timeout=30)
        if res.status_code != 200:
            return jsonify([])
        data = res.json()
        results = []
        for item in data.get('destinationEntities') or []:
            code = item.get('theCode')
            title = item.get('title') or ''
            if not code:
                continue
            clean_title = re.sub(r'<[^>]+>', '', str(title)).strip()
            results.append({'code': code, 'name': clean_title, 'system': 'ICD-11'})
            if len(results) >= 25:
                break
        return jsonify(results)
    except (requests.exceptions.RequestException, ValueError, TypeError):
        return jsonify([])


# Ensure tables are created (especially new Phase 2 tables)
with app.app_context():
    db.create_all()
    # Add clinical_state and medication_adherence to visits if missing (existing DBs)
    try:
        db.session.execute(text('ALTER TABLE visits ADD COLUMN clinical_state VARCHAR(50)'))
        db.session.commit()
    except Exception:
        db.session.rollback()
    try:
        db.session.execute(text('ALTER TABLE visits ADD COLUMN medication_adherence VARCHAR(50)'))
        db.session.commit()
    except Exception:
        db.session.rollback()
    try:
        db.session.execute(text('ALTER TABLE stressor_entries ADD COLUMN duration VARCHAR(50)'))
        db.session.commit()
    except Exception:
        db.session.rollback()
    # Doctor: SMTP app password and reminder days
    for col, spec in [('smtp_app_password', 'VARCHAR(255)'), ('appointment_reminder_days', 'VARCHAR(50)')]:
        try:
            db.session.execute(text(f'ALTER TABLE doctors ADD COLUMN {col} {spec}'))
            db.session.commit()
        except Exception:
            db.session.rollback()
    # Doctor: profile picture (BLOB in DB)
    for col, spec in [('profile_photo', 'BLOB'), ('profile_photo_mimetype', 'VARCHAR(80)'), ('designation', 'VARCHAR(255)')]:
        try:
            db.session.execute(text(f'ALTER TABLE doctors ADD COLUMN {col} {spec}'))
            db.session.commit()
        except Exception:
            db.session.rollback()
    # Patient: email and per-patient reminder days override
    for col, spec in [('email', 'VARCHAR(120)'), ('appointment_reminder_days', 'VARCHAR(50)')]:
        try:
            db.session.execute(text(f'ALTER TABLE patients ADD COLUMN {col} {spec}'))
            db.session.commit()
        except Exception:
            db.session.rollback()
    # Appointment: patient email for reminders
    try:
        db.session.execute(text('ALTER TABLE appointments ADD COLUMN email VARCHAR(120)'))
        db.session.commit()
    except Exception:
        db.session.rollback()

# --- Scheduler for daily reminders ---
scheduler = APScheduler()


@scheduler.task('cron', id='send_reminders', hour=8, minute=0)
def send_daily_reminders():
    """Background task that runs every day at 8:00 AM."""
    with app.app_context():
        today = date.today()

        # ---------------------------------------------------------
        # 1. APPOINTMENT REMINDERS (Dynamic per doctor; per-patient override)
        # ---------------------------------------------------------
        doctors = Doctor.query.all()

        for doctor in doctors:
            reminder_str = doctor.appointment_reminder_days or "7,3,1"
            try:
                reminder_days = [int(d.strip()) for d in reminder_str.split(',') if d.strip()]
            except ValueError:
                reminder_days = [7, 3, 1]

            for days_ahead in reminder_days:
                target_date = today + timedelta(days=days_ahead)

                upcoming_visits = Visit.query.join(Patient).filter(
                    Patient.doctor_id == doctor.id,
                    Visit.next_visit_date == target_date
                ).all()

                for visit in upcoming_visits:
                    patient = visit.patient
                    # Use patient override if set, else doctor default
                    effective_str = patient.appointment_reminder_days or doctor.appointment_reminder_days or "7,3,1"
                    try:
                        effective_days = [int(d.strip()) for d in effective_str.split(',') if d.strip()]
                    except ValueError:
                        effective_days = [7, 3, 1]
                    if days_ahead not in effective_days:
                        continue

                    if patient.email:
                        subject = f"Appointment Reminder with {doctor.full_name}"
                        body = (
                            f"Dear {patient.name},\n\n"
                            f"This is a reminder for your upcoming appointment with {doctor.full_name} "
                            f"on {target_date.strftime('%B %d, %Y')}.\n\n"
                            f"Best regards,\n{doctor.clinic_name}"
                        )
                        smtp_password = decrypt_smtp_password(doctor.smtp_app_password)
                        send_dynamic_email(doctor, patient.email, subject, body, smtp_password=smtp_password)

        # ---------------------------------------------------------
        # 2. MEDICATION TAPERING / TITRATION REMINDERS
        # ---------------------------------------------------------
        active_tapering_meds = MedicationEntry.query.filter_by(is_tapering=True).all()

        for med in active_tapering_meds:
            if not med.taper_plan:
                continue

            plan_steps = json.loads(med.taper_plan)
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

                        if patient.email:
                            subject = f"Medication Update: {med.drug_name}"
                            body = (
                                f"Dear {patient.name},\n\n"
                                f"As per your treatment plan with {doctor.full_name}, your dosage "
                                f"for {med.drug_name} changes tomorrow.\n\n"
                                f"New Instructions:\n"
                                f"- Dose: {next_step.get('dose_mg')}\n"
                                f"- Frequency: {next_step.get('frequency')}\n"
                                f"- Duration: {next_step.get('duration_text')}\n\n"
                                f"Best regards,\n{doctor.clinic_name}"
                            )
                            smtp_password = decrypt_smtp_password(doctor.smtp_app_password)
                            send_dynamic_email(doctor, patient.email, subject, body, smtp_password=smtp_password)

                current_date = step_end_date


scheduler.init_app(app)
# On PythonAnywhere, in-process scheduler may not run reliably; set RUN_SCHEDULER=1 to enable, or use Tasks to hit /cron/send_reminders
if _os.environ.get('RUN_SCHEDULER', '').strip().lower() in ('1', 'true', 'yes'):
    scheduler.start()


@app.route('/cron/send_reminders')
def cron_send_reminders():
    """Call from PythonAnywhere Tasks (or external cron) to run daily reminders. Requires CRON_SECRET in env."""
    if request.args.get('key') != _os.environ.get('CRON_SECRET', ''):
        return 'Unauthorized', 401
    send_daily_reminders()
    return 'OK', 200


# --- Register Helper for Templates ---
@app.context_processor
def utility_processor():
    """Register utility functions for use in templates."""
    current_doctor = None
    try:
        if session.get('logged_in') and session.get('doctor_id'):
            current_doctor = Doctor.query.get(session.get('doctor_id'))
    except Exception:
        current_doctor = None

    return dict(format_frequency=format_frequency, current_doctor=current_doctor)


@app.template_filter('format_comorbidities')
def format_comorbidities_filter(val):
    """Display medical_comorbidities: if JSON array, join with ', '; else return as-is (legacy text)."""
    if not val or not str(val).strip():
        return ''
    try:
        arr = json.loads(val)
        if isinstance(arr, list):
            return ', '.join(str(x) for x in arr)
    except (TypeError, json.JSONDecodeError):
        pass
    return val


@app.template_filter('from_json')
def from_json(value):
    """Parse JSON string in templates. Returns empty list on invalid/empty."""
    try:
        if not value or value == '[]' or value == '':
            return []
        return json.loads(value)
    except (TypeError, ValueError):
        return []

# Hardcoded credentials (for demo - replace with database lookup in production)
VALID_CREDENTIALS = {
    'admin@hospital.com': 'doctor'
}


def login_required(f):
    """Decorator to protect routes that require login (allows guest mode)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session and 'guest' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('landing'))
        return f(*args, **kwargs)
    return decorated_function


def doctor_required(f):
    """Decorator to protect routes that require doctor login (no guest mode)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session.get('logged_in'):
            flash('This action requires a registered doctor account.', 'error')
            return redirect(url_for('landing'))
        return f(*args, **kwargs)
    return decorated_function


def init_db():
    """Initialize database tables."""
    with app.app_context():
        db.create_all()
        
        # Create default doctor if doesn't exist
        if not Doctor.query.filter_by(username='admin').first():
            from werkzeug.security import generate_password_hash
            default_doctor = Doctor(
                username='admin',
                email='admin@hospital.com',
                password_hash=generate_password_hash('doctor')
            )
            db.session.add(default_doctor)
            db.session.commit()

        # Populate Default Templates
        if not DefaultTemplate.query.first():
            defaults = {
                "Schizophrenia": ["Suspiciousness", "Talking to self", "Poor self-care", "Verbally abusive", "Hearing non-existent voices", "Irritability", "Aggressive behavior", "Sleep disturbances"],
                "Bipolar Disorder (Mania)": ["Increased talkativeness", "Over-familiarity", "Grandiose ideas", "Excessive spending", "Irritability", "Risk-taking behaviors", "Hyperreligious ideas", "Decreased need for sleep"],
                "Depressive Disorder": ["Persistent low mood", "No interest in work", "Social withdrawal", "No interest in previously pleasurable activities", "Suicidal ideation", "Crying spells", "Decreased appetite", "Multiple somatic complaints", "Sleep disturbances"],
                "Generalized Anxiety Disorder": ["Excessive worry", "Anxiousness", "Restlessness", "Palpitations", "Difficulty falling asleep"],
                "Schizoaffective Disorder": ["Suspiciousness", "Grandiose ideas", "Over-familiarity", "Poor self-care", "Hearing non-existent voices", "Irritability", "Aggressive behavior", "Decreased need for sleep"],
                "Obsessive-Compulsive Disorder (OCD)": ["Repetitive thoughts", "Compulsive washing", "Repetitive checking", "Fear of contamination", "Counting compulsions", "Symmetry obsessions", "Sexual obsessions", "Time-consuming rituals"],
                "Panic Disorder": ["Breathlessness", "Palpitations", "Sweating", "Trembling", "Fear of dying", "Anticipatory anxiety", "Avoidance behavior", "Recurrent emergency room visits"],
                "Alcohol Dependence Syndrome": ["Alcohol consumption", "Excessive consumption", "Daily consumption", "Early morning consumption", "Trembling", "Hearing non-existent voices", "Suspiciousness", "Fearfulness", "Sleep disturbances"],
                "PTSD": ["Flashbacks", "Nightmares", "Hypervigilance", "Startle response", "Re-experiencing trauma", "Sleep disturbances"]
            }
            for name, syms in defaults.items():
                db.session.add(DefaultTemplate(name=name, symptoms=json.dumps(syms)))
            db.session.commit()


@app.route('/')
def landing():
    """Landing page - Facebook-style login/signup."""
    if 'logged_in' in session and session.get('logged_in'):
        return redirect(url_for('dashboard'))
    if 'guest' in session:
        return redirect(url_for('first_visit'))
    return render_template('landing.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login handler - processes login from landing page."""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check hardcoded credentials first (for backward compatibility)
        if email in VALID_CREDENTIALS and VALID_CREDENTIALS[email] == password:
            session['logged_in'] = True
            session['email'] = email
            session['role'] = 'doctor'
            # Always set doctor_id: match by email first, then fallback to username 'admin'
            # (in case admin record has email=None or typo like "gamil")
            doc = Doctor.query.filter_by(email=email).first()
            if not doc:
                doc = Doctor.query.filter_by(username='admin').first()
            if doc:
                session['doctor_id'] = doc.id
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        
        # Check database for doctor
        doctor = Doctor.query.filter_by(email=email).first()
        if doctor:
            from werkzeug.security import check_password_hash
            if check_password_hash(doctor.password_hash, password):
                session['logged_in'] = True
                session['email'] = email
                session['doctor_id'] = doctor.id
                session['role'] = 'doctor'
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
        
        flash('Invalid credentials. Please try again.', 'error')
        return redirect(url_for('landing'))
    
    # GET request - redirect to landing
    return redirect(url_for('landing'))


@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        doctor = Doctor.query.filter_by(email=email).first()

        if doctor:
            token = serializer.dumps(email, salt='password-reset-salt')
            reset_url = url_for('reset_password_with_token', token=token, _external=True)
            subject = "PsycheLife Password Reset Request"
            body = (
                f"Hello {doctor.full_name or doctor.username},\n\n"
                f"To reset your password, please click the following link:\n{reset_url}\n\n"
                f"This link will expire in 1 hour. If you did not request this, please ignore this email."
            )
            send_system_email(email, subject, body)

        flash('If an account with that email exists, a password reset link has been sent.', 'info')
        return redirect(url_for('landing'))

    return render_template('forgot_password.html')


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password_with_token(token):
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=3600)
    except SignatureExpired:
        flash('The password reset link has expired. Please request a new one.', 'error')
        return redirect(url_for('forgot_password'))
    except BadSignature:
        flash('Invalid password reset link.', 'error')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_password = request.form.get('password', '')
        doctor = Doctor.query.filter_by(email=email).first()
        if doctor:
            doctor.password_hash = generate_password_hash(new_password)
            db.session.commit()
            flash('Your password has been reset successfully! You can now log in.', 'success')
            return redirect(url_for('landing'))
        flash('Account not found.', 'error')
        return redirect(url_for('landing'))

    return render_template('reset_password_form.html', token=token)


@app.route('/guest/lifechart', methods=['GET', 'POST'])
def guest_lifechart():
    """
    Generate Life Chart for Guest Mode.
    Now uses the DB + Shared View (same as QR code) for a consistent experience.
    """
    if not session.get('guest'):
        abort(403)

    # 1. Handle POST (Form Submission from Dashboard)
    if request.method == 'POST':
        # --- A. CLEANUP (Keep DB healthy) ---
        try:
            GuestShare.query.filter(GuestShare.expires_at < get_ist_now()).delete()
            db.session.commit()
        except Exception:
            db.session.rollback()

        # --- B. CAPTURE DATA (Exact logic from guest_both) ---
        now_ist = get_ist_now()
        today = now_ist.date()
        today_iso = now_ist.isoformat()

        # 1. Symptoms
        symptoms = []
        names = request.form.getlist('symptom_name[]')
        onsets = request.form.getlist('symptom_onset[]')
        progressions = request.form.getlist('symptom_progression[]')
        currents = request.form.getlist('symptom_current[]')
        sym_notes = request.form.getlist('symptom_note[]')
        durations = request.form.getlist('duration_text[]')

        for i, name in enumerate(names):
            dur_text = durations[i] if i < len(durations) else ""
            if not (name or "").strip() and not (dur_text or "").strip():
                continue
            # Helper for safe integers
            def safe_int(val_list, idx, default=5):
                try: return int(val_list[idx]) if idx < len(val_list) else default
                except (ValueError, TypeError): return default

            onset = safe_int(onsets, i)
            prog = safe_int(progressions, i)
            curr = safe_int(currents, i)
            note = sym_notes[i] if i < len(sym_notes) else ""
            
            # Date Calculation
            try:
                delta = parse_duration(dur_text) if dur_text else timedelta(days=14)
            except:
                delta = timedelta(days=14)
                
            d_onset = today - delta
            total_days = (today - d_onset).days
            d_prog = d_onset + timedelta(days=total_days // 2)
            
            # Add points with specific dates
            symptoms.append({"name": name, "score": onset, "phase": "Onset", "note": note, "date": d_onset.isoformat()})
            symptoms.append({"name": name, "score": prog, "phase": "Progression", "note": note, "date": d_prog.isoformat()})
            symptoms.append({"name": name, "score": curr, "phase": "Current", "note": note, "date": today_iso})

        # 2. MSE Findings (Onset & Progression)
        def safe_float(val_list, idx, default=None):
            try:
                v = val_list[idx] if idx < len(val_list) else None
                return float(v) if v not in (None, '') else default
            except (ValueError, TypeError):
                return default

        mse = []
        mse_cats = request.form.getlist('mse_category[]')
        mse_findings = request.form.getlist('mse_finding_name[]')
        mse_onsets = request.form.getlist('mse_onset[]')
        mse_progs = request.form.getlist('mse_progression[]')
        mse_currs = request.form.getlist('mse_current[]') or request.form.getlist('mse_score[]')
        mse_notes = request.form.getlist('mse_note[]')
        mse_durs = request.form.getlist('mse_duration[]')

        for i, cat in enumerate(mse_cats):
            finding_name = (mse_findings[i] if i < len(mse_findings) else "").strip()
            if not cat or not finding_name:
                continue
            onset = safe_float(mse_onsets, i)
            prog = safe_float(mse_progs, i)
            curr = safe_float(mse_currs, i, 0.0)
            note = mse_notes[i] if i < len(mse_notes) else ""
            dur_text = mse_durs[i] if i < len(mse_durs) else ""
            try:
                delta = parse_duration(dur_text) if dur_text else timedelta(days=14)
            except Exception:
                delta = timedelta(days=14)
            d_onset = now_ist - delta
            d_prog = d_onset + timedelta(days=(now_ist - d_onset).days // 2)
            if onset is not None:
                mse.append({"cat": cat, "name": finding_name, "score": onset, "phase": "Onset", "note": note, "date": d_onset.isoformat()})
            if prog is not None:
                mse.append({"cat": cat, "name": finding_name, "score": prog, "phase": "Progression", "note": note, "date": d_prog.isoformat()})
            mse.append({"cat": cat, "name": finding_name, "score": curr, "phase": "Current", "note": note, "date": today_iso})

        # 3. Medications (Upgraded for Tapering & Duration support)
        meds_chart = []
        drug_names = request.form.getlist('drug_name[]')
        dose_mgs = request.form.getlist('dose_full[]') or request.form.getlist('dose_mg[]')
        d_freqs = request.form.getlist('frequency[]')
        d_durs = request.form.getlist('med_duration[]') or request.form.getlist('med_duration_text[]')
        med_notes = request.form.getlist('med_note[]')
        d_forms = request.form.getlist('med_form[]')

        last_med = None
        for i, name in enumerate(drug_names):
            dose_str = dose_mgs[i] if i < len(dose_mgs) else ""
            dur = d_durs[i] if i < len(d_durs) else ""
            if not (name or "").strip() and not (dose_str or "").strip() and not (dur or "").strip():
                continue
            dose_str = dose_str or ""
            dur = dur or ""
            freq = d_freqs[i] if i < len(d_freqs) else ""
            note = med_notes[i] if i < len(med_notes) else ""
            score_val = 0.0
            if dose_str:
                nums = re.findall(r"[-+]?\d*\.\d+|\d+", dose_str)
                if nums:
                    score_val = float(nums[0])
            if last_med and last_med["name"].strip().lower() == (name or "").strip().lower():
                if (dose_str.strip() or dur.strip()):
                    last_med["is_tapering"] = True
                    if not last_med.get("taper_plan"):
                        last_med["taper_plan"] = [{
                            "dose_mg": last_med["dose"],
                            "frequency": last_med.get("frequency", ""),
                            "duration_text": last_med.get("duration", ""),
                            "note": last_med.get("note", "")
                        }]
                    last_med["taper_plan"].append({
                        "dose_mg": dose_str,
                        "frequency": freq,
                        "duration_text": dur,
                        "note": note
                    })
            elif (name or "").strip():
                new_med = {
                    "name": (name or "").strip(),
                    "score": score_val,
                    "phase": "Current",
                    "dose": dose_str,
                    "frequency": freq,
                    "duration": dur,
                    "note": note,
                    "date": today_iso,
                    "is_tapering": False,
                    "taper_plan": None,
                    "form_type": d_forms[i] if i < len(d_forms) else 'Tablet'
                }
                meds_chart.append(new_med)
                last_med = new_med

        # 4. Side Effects (Onset & Progression)
        se_chart = []
        se_names = request.form.getlist('side_effect_name[]')
        se_onsets = request.form.getlist('side_effect_onset[]')
        se_progs = request.form.getlist('side_effect_progression[]')
        se_currs = request.form.getlist('side_effect_current[]') or request.form.getlist('side_effect_score[]')
        se_notes = request.form.getlist('side_effect_note[]')
        se_durs = request.form.getlist('side_effect_duration[]')

        for i, name in enumerate(se_names):
            dur_text = se_durs[i] if i < len(se_durs) else ""
            if not (name or "").strip() and not (dur_text or "").strip():
                continue
            name = (name or "").strip() or ""
            if name:
                onset = safe_float(se_onsets, i)
                prog = safe_float(se_progs, i)
                curr = safe_float(se_currs, i, 0.0)
                note = se_notes[i] if i < len(se_notes) else ""
                dur_text = se_durs[i] if i < len(se_durs) else ""
                try:
                    delta = parse_duration(dur_text) if dur_text else timedelta(days=14)
                except Exception:
                    delta = timedelta(days=14)
                d_onset = now_ist - delta
                d_prog = d_onset + timedelta(days=(now_ist - d_onset).days // 2)
                if onset is not None:
                    se_chart.append({"name": name, "score": onset, "phase": "Onset", "note": note, "date": d_onset.isoformat()})
                if prog is not None:
                    se_chart.append({"name": name, "score": prog, "phase": "Progression", "note": note, "date": d_prog.isoformat()})
                se_chart.append({"name": name, "score": curr, "phase": "Current", "note": note, "date": today_iso, "duration": dur_text})

        # --- C. SAVE TO DB (session-aware token reuse) ---
        patient_details = {
            "name": request.form.get('patient_name', 'Guest Patient'),
            "age": request.form.get('age', '') or request.form.get('patient_age', ''),
            "sex": request.form.get('sex', '') or request.form.get('patient_sex', ''),
            "address": request.form.get('address', '') or request.form.get('patient_address', ''),
            "date": today_iso
        }
        doctor_details = {
            "name": request.form.get('doc_name', 'Doctor'),
            "qual": request.form.get('doc_qual', ''),
            "reg": request.form.get('doc_reg', ''),
            "clinic": request.form.get('doc_clinic', ''),
            "address": request.form.get('doc_address', ''),
            "phone": request.form.get('doc_phone', ''),
            "email": request.form.get('doc_email', ''),
            "social": request.form.get('doc_social', '')
        }
        sig_b64 = session.get('guest_signature_b64', '')
        sig_file = request.files.get('doc_signature')
        if sig_file and sig_file.filename != '':
            sig_b64 = base64.b64encode(sig_file.read()).decode('utf-8')
            session['guest_signature_b64'] = sig_b64

        chart_data = {
            "patient": patient_details,
            "doctor": doctor_details,
            "signature_b64": sig_b64,
            "chief_complaints": request.form.get('chief_complaints', ''),
            "stressors": request.form.get('stressors_data', ''),
            "personality": request.form.get('personality_data', ''),
            "major_events": request.form.get('major_events_data', ''),
            "scales": request.form.get('scales_data', ''),
            "substance_use": request.form.get('substance_use_data', ''),
            "adherence": request.form.get('adherence_data', ''),
            "provisional_diagnosis": request.form.get('provisional_diagnosis', ''),
            "differential_diagnosis": request.form.get('differential_diagnosis', ''),
            "follow_up_date": request.form.get('follow_up_date', ''),
            "note": request.form.get('visit_note') or request.form.get('note', ''),
            "symptoms": symptoms,
            "mse": mse,
            "meds": meds_chart,
            "se": se_chart
        }

        token = session.get('guest_token')
        share_entry = None

        if token:
            share_entry = GuestShare.query.filter_by(token=token).first()
            if share_entry and share_entry.is_expired():
                share_entry = None

        expiry = get_ist_now() + timedelta(minutes=30)

        if share_entry:
            share_entry.data_json = json.dumps(chart_data)
            share_entry.expires_at = expiry
        else:
            token = str(uuid.uuid4())
            session['guest_token'] = token
            share_entry = GuestShare(
                token=token,
                data_json=json.dumps(chart_data),
                expires_at=expiry,
                created_at=get_ist_now()
            )
            db.session.add(share_entry)

        db.session.commit()

        # --- D. REDIRECT TO SHARED VIEW ---
        return redirect(url_for('guest_share_view', token=token))

    # 2. Handle GET (Legacy / Fallback)
    # If someone tries to access /guest/lifechart directly without posting data
    return redirect(url_for('first_visit'))
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Doctor registration."""
    if request.method == 'POST':
        # 1. Capture Full Name from landing.html
        full_name = request.form.get('fullname', '').strip()
        email = request.form.get('email', '').strip()
        mobile = request.form.get('mobile', '').strip()
        specialty = request.form.get('specialty', '').strip()
        password = request.form.get('password', '')
        
        if not all([full_name, email, password]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('landing'))
        
        # 2. Generate a username from Full Name (remove spaces, lowercase)
        # e.g., "John Doe" -> "johndoe"
        username = "".join(full_name.split()).lower()
        
        # Check if email or username exists
        if Doctor.query.filter((Doctor.username == username) | (Doctor.email == email)).first():
            flash('Account already exists.', 'error')
            return redirect(url_for('landing'))
        
        # 3. Create Doctor with full_name
        from werkzeug.security import generate_password_hash
        doctor = Doctor(
            username=username,
            full_name=full_name,
            email=email,
            phone=mobile,
            password_hash=generate_password_hash(password)
        )
        db.session.add(doctor)
        db.session.commit()
        
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('landing'))
    
    return redirect(url_for('landing'))


@app.route('/logout')
def logout():
    """Logout route."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('landing'))


DESIGNATION_MAX_LEN = 255
DESIGNATION_CHOICES = (
    'Junior Resident (JR)',
    'Senior Resident (SR)',
    'Assistant Professor / Consultant',
    'Associate Professor / Associate Consultant',
    'Senior Consultant / Professor',
    'Head of Department (HOD)',
    'Medical Director / Chief Medical Officer',
)


@app.route('/profile/picture')
@doctor_required
def serve_profile_picture():
    """Serve the logged-in doctor's profile photo from DB (BLOB)."""
    doctor = Doctor.query.get(session.get('doctor_id'))
    if not doctor or not doctor.profile_photo:
        abort(404)
    return send_file(
        io.BytesIO(doctor.profile_photo),
        mimetype=doctor.profile_photo_mimetype or 'image/jpeg',
        max_age=3600,
    )


@app.route('/profile', methods=['GET', 'POST'])
@doctor_required
def profile():
    """Doctor profile settings."""
    doctor = Doctor.query.get(session.get('doctor_id'))
    if not doctor:
        flash('Doctor not found.', 'error')
        return redirect(url_for('first_visit'))
    
    if request.method == 'POST':
        uploaded_photo = False
        if 'profile_photo' in request.files:
            pfile = request.files['profile_photo']
            if pfile and pfile.filename:
                ext = os.path.splitext(pfile.filename)[1].lower()
                if ext not in PROFILE_PHOTO_ALLOWED_EXT:
                    flash('Profile photo must be JPG, PNG, GIF, or WebP.', 'error')
                else:
                    pdata = pfile.read()
                    if len(pdata) > PROFILE_PHOTO_MAX_BYTES:
                        flash('Profile photo must be 2MB or smaller.', 'error')
                    else:
                        doctor.profile_photo = pdata
                        doctor.profile_photo_mimetype = (pfile.mimetype or 'image/jpeg')[:80]
                        uploaded_photo = True
        if not uploaded_photo and request.form.get('remove_profile_photo'):
            doctor.profile_photo = None
            doctor.profile_photo_mimetype = None

        doctor.full_name = request.form.get('full_name', '').strip()
        desig = (request.form.get('designation') or '').strip()
        if len(desig) > DESIGNATION_MAX_LEN:
            desig = desig[:DESIGNATION_MAX_LEN]
        doctor.designation = desig if desig else None
        doctor.clinic_name = request.form.get('clinic_name', '').strip()
        doctor.kmc_code = request.form.get('kmc_code', '').strip()
        doctor.address_text = request.form.get('address_text', '').strip()
        
        # --- PHASE 1 UPDATES: Phone & Email ---
        doctor.phone = request.form.get('phone', '').strip()
        doctor.email = request.form.get('email', '').strip()

        # SMTP app password: encrypt before storing (only update if non-empty so we don't clear it)
        smtp_pw = request.form.get('smtp_app_password', '').strip()
        if smtp_pw:
            doctor.smtp_app_password = encrypt_smtp_password(smtp_pw)
        doctor.appointment_reminder_days = request.form.get('appointment_reminder_days', '').strip() or "7,3,1"
        
        doctor.social_handle = request.form.get('social_handle', '').strip()

        # Active appointment template
        active_template = request.form.get('active_template')
        if active_template and active_template != 'default':
            try:
                doctor.active_template_id = int(active_template)
            except (TypeError, ValueError):
                doctor.active_template_id = None
        else:
            doctor.active_template_id = None
        
        # Handle Signature Upload
        if 'signature' in request.files:
            file = request.files['signature']
            if file and file.filename:
                filename = secure_filename(f"sig_{doctor.id}_{file.filename}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                doctor.signature_filename = filename
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        next_url = request.args.get('next') or url_for('dashboard')
        return redirect(next_url)

    schedule_templates = ScheduleTemplate.query.filter_by(doctor_id=doctor.id).all() if doctor else []
    return render_template(
        'profile.html',
        doctor=doctor,
        schedule_templates=schedule_templates,
        designation_choices=DESIGNATION_CHOICES,
    )


# Root route is now handled by landing()


@app.route('/dashboard')
@doctor_required
def dashboard():
    """Renders the main dashboard view with dynamic data."""
    doctor_id = session.get('doctor_id')
    doctor = Doctor.query.get(doctor_id)
    today = get_ist_now().date()

    # Get Patients
    patients = Patient.query.filter_by(doctor_id=doctor_id).order_by(Patient.id).all()
    num_patients = len(patients)

    # Resolve target date (selected date for appointments and notes)
    target_date_str = request.args.get('date')
    if target_date_str:
        try:
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        except ValueError:
            target_date = today
    else:
        target_date = today

    # Notes for the selected date (so notes for 16 Mar show when viewing 16 Mar, not today)
    notes = DashboardNote.query.filter_by(doctor_id=doctor_id, date=target_date).all()

    appointments = Appointment.query.filter_by(doctor_id=doctor_id, date=target_date).order_by(Appointment.start_time).all()

    # JSON-serializable list for JS slot calculation (id, start_time, slot_duration, name)
    appointments_for_day = [{"id": a.id, "start_time": a.start_time or "", "slot_duration": a.slot_duration or 15, "name": a.name or ""} for a in appointments]

    # Prepare patient data for the table (including latest diagnosis, last visit, visit count)
    patient_data = []
    for p in patients:
        visits = Visit.query.filter_by(patient_id=p.id).order_by(Visit.date.desc()).all()
        latest_visit = visits[0] if visits else None
        diagnosis = format_diagnosis_values(latest_visit.provisional_diagnosis) if latest_visit else "N/A"
        last_visit_date = latest_visit.date.strftime("%d %b %y") if latest_visit and getattr(latest_visit, 'date', None) else "—"
        patient_data.append({
            'id': p.id,
            'name': p.name,
            'age': p.age,
            'sex': p.sex,
            'diagnosis': diagnosis,
            'note': p.personal_notes or "None",
            'last_visit': last_visit_date,
            'visit_count': len(visits)
        })

    clinic_name = (doctor.clinic_name or "") if doctor else ""
    clinic_hours = get_clinic_hours(doctor)

    return render_template('dashboard.html',
                           doctor=doctor,
                           patients=patient_data,
                           num_patients=num_patients,
                           today=today,
                           target_date=target_date,
                           notes=notes,
                           appointments=appointments,
                           appointments_for_day=appointments_for_day,
                           top_5_patients=patients[:5],
                           clinic_name=clinic_name,
                           clinic_hours=clinic_hours,
                           getattr=getattr)


FEEDBACK_MAX_BYTES = 5 * 1024 * 1024
FEEDBACK_ALLOWED_EXT = frozenset({'.pdf', '.jpg', '.jpeg', '.png'})

PROFILE_PHOTO_MAX_BYTES = 2 * 1024 * 1024
PROFILE_PHOTO_ALLOWED_EXT = frozenset({'.jpg', '.jpeg', '.png', '.gif', '.webp'})


@app.route('/submit_feedback', methods=['POST'])
@doctor_required
def submit_feedback():
    doctor_id = session.get('doctor_id')
    if not doctor_id:
        flash('Please sign in as a doctor to submit feedback.', 'error')
        return redirect(url_for('landing'))

    issue_type = (request.form.get('issue_type') or '').strip()
    if not issue_type:
        flash('Please select an issue type.', 'error')
        return redirect(url_for('dashboard'))

    other_issue_type = None
    if issue_type.lower() == 'others':
        other_issue_type = (request.form.get('other_issue_type') or '').strip() or None
        if not other_issue_type:
            flash('Please specify the issue type.', 'error')
            return redirect(url_for('dashboard'))

    priority = (request.form.get('priority') or 'Minor').strip()
    if priority not in ('Minor', 'Important', 'Urgent'):
        priority = 'Minor'

    description = (request.form.get('description') or '').strip()
    if not description:
        flash('Please describe the issue.', 'error')
        return redirect(url_for('dashboard'))

    screenshot_data = None
    screenshot_name = None
    screenshot_mimetype = None
    file = request.files.get('screenshot_file')
    if file and file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in FEEDBACK_ALLOWED_EXT:
            flash('Please upload a PDF, JPG, or PNG file (max 5MB).', 'error')
            return redirect(url_for('dashboard'))
        screenshot_name = secure_filename(file.filename) or 'upload'
        screenshot_mimetype = (file.mimetype or 'application/octet-stream')[:80]
        screenshot_data = file.read()
        if len(screenshot_data) > FEEDBACK_MAX_BYTES:
            flash('File is too large (max 5MB).', 'error')
            return redirect(url_for('dashboard'))

    db.session.add(Feedback(
        doctor_id=doctor_id,
        issue_type=issue_type,
        other_issue_type=other_issue_type,
        priority=priority,
        description=description,
        screenshot=screenshot_data,
        screenshot_name=screenshot_name,
        screenshot_mimetype=screenshot_mimetype,
    ))
    db.session.commit()
    flash('Thank you! Your feedback has been submitted.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/api/clinic_hours', methods=['POST'])
@doctor_required
def save_clinic_hours():
    """Save clinic hours for the current doctor. Expects JSON or form: morning_start, morning_end, evening_start, evening_end (HH:MM)."""
    doctor_id = session.get('doctor_id')
    doctor = Doctor.query.get(doctor_id)
    if not doctor:
        return jsonify({"ok": False, "error": "Doctor not found"}), 400

    if request.is_json:
        data = request.get_json()
        morning = data.get("morning", {})
        evening = data.get("evening", {})
        m_start = morning.get("start") or data.get("morning_start", "09:00")
        m_end = morning.get("end") or data.get("morning_end", "17:00")
        e_start = evening.get("start") or data.get("evening_start", "17:00")
        e_end = evening.get("end") or data.get("evening_end", "22:00")
    else:
        m_start = request.form.get("morning_start", "09:00")
        m_end = request.form.get("morning_end", "17:00")
        e_start = request.form.get("evening_start", "17:00")
        e_end = request.form.get("evening_end", "22:00")

    # Normalize to HH:MM (strip seconds if present)
    def norm(t):
        if not t:
            return "09:00"
        s = str(t).strip()
        if len(s) >= 5:
            return s[:5]
        return s

    payload = {
        "morning": {"start": norm(m_start), "end": norm(m_end)},
        "evening": {"start": norm(e_start), "end": norm(e_end)},
    }
    doctor.clinic_hours = json.dumps(payload)
    db.session.commit()
    return jsonify({"ok": True, "clinic_hours": get_clinic_hours(doctor)})


@app.route('/api/add_note', methods=['POST'])
@doctor_required
def add_note():
    doctor_id = session.get('doctor_id')
    content = request.form.get('note_content')
    note_date = parse_date(request.form.get('note_date')) if request.form.get('note_date') else get_ist_now().date()
    if content:
        note = DashboardNote(doctor_id=doctor_id, date=note_date, content=content)
        db.session.add(note)
        db.session.commit()
    return redirect(url_for('dashboard'))


@app.route('/api/delete_note', methods=['POST'])
@doctor_required
def delete_note():
    """Delete a dashboard note by id. Expects JSON body: { \"note_id\": <id> } or form note_id."""
    doctor_id = session.get('doctor_id')
    if request.is_json:
        note_id = request.get_json().get('note_id')
    else:
        note_id = request.form.get('note_id')
    try:
        note_id = int(note_id)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Invalid note id"}), 400
    note = DashboardNote.query.filter_by(id=note_id, doctor_id=doctor_id).first()
    if not note:
        return jsonify({"ok": False, "error": "Note not found"}), 404
    db.session.delete(note)
    db.session.commit()
    return jsonify({"ok": True})


@app.route('/add_appointment', methods=['POST'])
@doctor_required
def add_appointment():
    """Handle form POST from Add New Appointment modal; redirects back to dashboard with optional date."""
    doctor_id = session.get('doctor_id')
    date_str = request.form.get('appt_date')
    start_time = request.form.get('appt_time')
    duration = int(request.form.get('appt_duration', 15))

    appt_date = parse_date(date_str)
    if not appt_date:
        flash("Invalid date.", "error")
        return redirect(url_for('dashboard'))

    # Basic overlap check
    existing = Appointment.query.filter_by(doctor_id=doctor_id, date=appt_date, start_time=start_time).first()
    if existing:
        flash("Time slot already booked!", "error")
        return redirect(url_for('dashboard'))

    appt_email = (request.form.get('appt_email') or request.form.get('appt_email_sent') or '').strip()
    appt = Appointment(
        doctor_id=doctor_id,
        date=appt_date,
        name=request.form.get('appt_name'),
        age=request.form.get('appt_age'),
        sex=request.form.get('appt_sex'),
        start_time=start_time,
        slot_duration=duration,
        type=request.form.get('appt_type'),
        status=request.form.get('appt_status', 'Confirmed'),
        view_details=request.form.get('appt_details', ''),
        email=appt_email if appt_email else None,
    )
    db.session.add(appt)
    db.session.commit()
    flash("Appointment added successfully!", "success")
    return redirect(url_for('dashboard', date=date_str))


@app.route('/api/appointment/<int:appt_id>', methods=['DELETE'])
@doctor_required
def delete_appointment(appt_id):
    """Delete an appointment. Only the owning doctor can delete."""
    doctor_id = session.get('doctor_id')
    appt = Appointment.query.filter_by(id=appt_id, doctor_id=doctor_id).first()
    if not appt:
        return jsonify({"error": "Appointment not found"}), 404
    db.session.delete(appt)
    db.session.commit()
    return jsonify({"status": "success"})


@app.route('/api/update_appointment_time', methods=['POST'])
@doctor_required
def update_appointment_time():
    """Updates an existing appointment's date and time."""
    data = request.get_json()
    appt_id = data.get('id')
    new_date_str = data.get('date')
    new_time = data.get('time')

    doctor_id = session.get('doctor_id')
    appt = Appointment.query.filter_by(id=appt_id, doctor_id=doctor_id).first()
    if not appt:
        return jsonify({"error": "Appointment not found"}), 404

    try:
        appt.date = datetime.strptime(new_date_str, '%Y-%m-%d').date()
        appt.start_time = new_time
        db.session.commit()
        return jsonify({"status": "success", "message": "Appointment rescheduled"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route('/appointment/<int:appt_id>/details')
@doctor_required
def appt_details(appt_id):
    """View appointment details: redirect to patient if Follow-up and patient exists, else show dummy patient with registration prompt."""
    doctor_id = session.get('doctor_id')
    appt = Appointment.query.filter_by(id=appt_id, doctor_id=doctor_id).first()
    if not appt:
        abort(404)

    if appt.type == 'Follow-up':
        patient = Patient.query.filter_by(name=appt.name, doctor_id=doctor_id).first()
        if patient:
            return redirect(url_for('patient_detail', patient_id=patient.id))

    class DummyPatient:
        def __init__(self, name, age, sex):
            self.id = None
            self.name = name
            self.age = age or 0
            self.sex = sex or ''
            self.address = ''

    dummy_patient = DummyPatient(appt.name or '', appt.age, appt.sex or '')
    return render_template('patient_detail.html', patient=dummy_patient, visits=[], is_new_case=True, appt_id=appt.id)


@app.route('/api/notifications', methods=['GET'])
@doctor_required
def get_notifications():
    """Return past 7 days of notifications and unread count for the current doctor."""
    doctor_id = session.get('doctor_id')
    seven_days_ago = get_ist_now() - timedelta(days=7)
    notifications = Notification.query.filter(
        Notification.doctor_id == doctor_id,
        Notification.trigger_time >= seven_days_ago
    ).order_by(Notification.trigger_time.desc()).all()
    unread_count = sum(1 for n in notifications if not n.is_read)
    notif_list = [{
        "id": n.id,
        "appointment_id": n.appointment_id,
        "message": n.message,
        "trigger_time": n.trigger_time.isoformat() if n.trigger_time else None,
        "is_read": n.is_read
    } for n in notifications]
    return jsonify({"unread_count": unread_count, "notifications": notif_list})


@app.route('/api/notifications', methods=['POST'])
@doctor_required
def save_notification():
    """Save a new notification (e.g. when an appointment starts)."""
    doctor_id = session.get('doctor_id')
    data = request.get_json() or {}
    message = data.get('message', '').strip()
    if not message:
        return jsonify({"error": "Message required"}), 400
    appointment_id = data.get('appointment_id')
    trigger_time = get_ist_now()
    n = Notification(
        doctor_id=doctor_id,
        appointment_id=appointment_id,
        message=message[:255],
        trigger_time=trigger_time
    )
    db.session.add(n)
    db.session.commit()
    return jsonify({"status": "success", "id": n.id}), 201


@app.route('/api/notifications/read', methods=['PUT'])
@doctor_required
def mark_notifications_read():
    """Mark all notifications as read for the current doctor."""
    doctor_id = session.get('doctor_id')
    Notification.query.filter_by(doctor_id=doctor_id, is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify({"status": "success"})


@app.route('/first_visit', methods=['GET', 'POST'])
@login_required
def first_visit():
    """First Visit - New Patient & First Visit creation."""
    is_guest = session.get('role') == 'guest'

    doc_id = session.get('doctor_id')
    doctor = Doctor.query.get(doc_id) if doc_id is not None else None

    if not doctor and not is_guest:
        session.clear()
        flash('Session expired. Please log in.', 'error')
        return redirect(url_for('landing'))

    if request.method == 'POST':
        # --- CRITICAL FIX: Intercept Guest submissions immediately ---
        if is_guest:
            submit_action = request.form.get('submit_action')
            if submit_action == 'prescription':
                return guest_prescription()
            elif submit_action == 'both':
                return guest_both()
            else:
                return guest_lifechart()

        # --- DOCTOR FLOW CONTINUES BELOW ---
        # Get patient info
        patient_name = request.form.get('patient_name')
        age = request.form.get('age')
        sex = request.form.get('sex')
        address = request.form.get('address')
        visit_date_str = request.form.get('visit_date')
        
        if not all([patient_name, age, sex, visit_date_str]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('first_visit'))
        
        visit_date = parse_date(visit_date_str) or date.today()
        
        if not doctor:
            flash('Error: No doctor account identified. Please log in.', 'error')
            return redirect(url_for('logout'))

        # Capture Relation Logic: "Others" -> use custom text
        relation = request.form.get('attender_relation')
        if relation == 'Others':
            other_rel = request.form.get('attender_relation_other')
            if other_rel and other_rel.strip():
                relation = other_rel.strip()

        # Create patient
        patient = Patient(
            name=patient_name,
            age=int(age),
            sex=sex,
            address=address,
            phone=request.form.get('phone'),
            email=request.form.get('email', '').strip() or None,
            attender_name=request.form.get('attender_name'),
            attender_relation=relation,
            attender_reliability=request.form.get('attender_reliability'),
            personal_notes=request.form.get('personal_notes'),
            doctor_id=doctor.id # This is now the CORRECT ID
        )
        db.session.add(patient)
        db.session.flush()
        
        # Create visit
        visit = Visit(
            patient_id=patient.id,
            date=visit_date,
            visit_type='First',
            provisional_diagnosis=serialize_diagnosis_values(request.form.get('provisional_diagnosis', '')),
            differential_diagnosis=serialize_diagnosis_values(request.form.get('differential_diagnosis', '')),
            next_visit_date=parse_date(request.form.get('next_visit_date'))
        )
        db.session.add(visit)
        db.session.flush()
        
        # Process form data
        process_visit_form_data(visit, request.form)
        
        db.session.commit()
        
        # Handle workflow
        submit_action = request.form.get('submit_action')
        if submit_action == 'prescription':
            return redirect(url_for('preview_prescription', visit_id=visit.id))
        elif submit_action == 'lifechart':
            return redirect(url_for('life_chart', patient_id=patient.id, visit_id=visit.id))
        elif submit_action == 'both':
            return redirect(url_for('preview_prescription', visit_id=visit.id, include_qr='true'))
        else:
            return redirect(url_for('patient_detail', patient_id=patient.id))
    
    # GET request - show first visit (patients scoped to logged-in doctor only)
    patients = []
    if not is_guest and doctor:
        patients = Patient.query.filter_by(doctor_id=doctor.id).all()

    today = date.today()
    templates = DefaultTemplate.query.all() if is_guest else []

    # --- NEW: Fetch Appointment Data if present in URL ---
    appt = None
    appt_id = request.args.get('appt_id')
    if appt_id:
        appt = Appointment.query.get(appt_id)

    # --- NEW: Added appt=appt to the render_template ---
    return render_template('first_visit.html',
                           patients=patients,
                           today=today,
                           is_guest=is_guest,
                           doctor=doctor,
                           templates=templates,
                           appt=appt)


@app.route('/api/templates', methods=['GET'])
@doctor_required
def get_templates():
    doctor_id = session.get('doctor_id')
    defaults = DefaultTemplate.query.all()
    customs = CustomTemplate.query.filter_by(doctor_id=doctor_id).all()

    template_dict = {}

    for dt in defaults:
        template_dict[dt.name] = {
            "symptoms": json.loads(dt.symptoms),
            "is_default": True,
            "is_modified": False
        }

    for ct in customs:
        if ct.name in template_dict:
            template_dict[ct.name]["symptoms"] = json.loads(ct.symptoms)
            template_dict[ct.name]["is_modified"] = True
        else:
            template_dict[ct.name] = {
                "symptoms": json.loads(ct.symptoms),
                "is_default": False,
                "is_modified": False
            }

    return jsonify(template_dict)


@app.route('/api/templates', methods=['POST'])
@doctor_required
def save_template():
    doctor_id = session.get('doctor_id')
    data = request.json
    name = data.get('name')
    symptoms = data.get('symptoms')

    if not name or not symptoms:
        return jsonify({"error": "Missing data"}), 400

    custom = CustomTemplate.query.filter_by(doctor_id=doctor_id, name=name).first()
    if custom:
        custom.symptoms = json.dumps(symptoms)
    else:
        custom = CustomTemplate(doctor_id=doctor_id, name=name, symptoms=json.dumps(symptoms))
        db.session.add(custom)

    db.session.commit()
    return jsonify({"success": True})


@app.route('/api/templates/<path:name>', methods=['DELETE'])
@doctor_required
def delete_template(name):
    doctor_id = session.get('doctor_id')
    custom = CustomTemplate.query.filter_by(doctor_id=doctor_id, name=name).first()
    if custom:
        db.session.delete(custom)
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"error": "Template not found"}), 404


@app.route('/api/submit_scale', methods=['POST'])
@doctor_required
def submit_scale():
    data = request.get_json() or {}
    visit_id = data.get('visit_id')
    scale_id = data.get('scale_id')
    scale_name = data.get('scale_name')
    responses = data.get('responses')

    if not visit_id or not scale_id or not scale_name or responses is None:
        return jsonify({"status": "error", "message": "Missing visit_id, scale_id, scale_name, or responses"}), 400

    try:
        total_score, severity_label = process_scale_submission(scale_id, responses)

        new_assessment = ScaleAssessment(
            visit_id=int(visit_id),
            scale_id=scale_id,
            scale_name=scale_name,
            total_score=total_score,
            severity_label=severity_label,
            raw_responses=responses
        )
        db.session.add(new_assessment)
        db.session.commit()

        return jsonify({
            "status": "success",
            "total_score": total_score,
            "severity_label": severity_label
        }), 200

    except ValueError as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 400


def update_guest_share(token, redirect_to_prescription=False):
    """Update existing GuestShare with meds from life_chart form; preserve symptoms."""
    entry = GuestShare.query.filter_by(token=token).first()
    if not entry or entry.is_expired():
        flash("Link expired. Please start a new session.", "error")
        return redirect(url_for('first_visit'))

    data = json.loads(entry.data_json)

    # Update ONLY meds from the life_chart form (Upgraded for Tapering & Duration)
    meds_chart = []
    drug_names = request.form.getlist('drug_name[]')
    dose_mgs = request.form.getlist('dose_full[]') or request.form.getlist('dose_mg[]')
    d_freqs = request.form.getlist('frequency[]')
    d_durs = request.form.getlist('med_duration[]') or request.form.getlist('med_duration_text[]')
    med_notes = request.form.getlist('med_note[]')
    d_forms = request.form.getlist('med_form[]')

    now_ist = get_ist_now()
    today_iso = now_ist.isoformat()

    last_med = None
    for i, name in enumerate(drug_names):
        if name.strip():
            dose_str = dose_mgs[i] if i < len(dose_mgs) else ""
            freq = d_freqs[i] if i < len(d_freqs) else ""
            dur = d_durs[i] if i < len(d_durs) else ""
            note = med_notes[i] if i < len(med_notes) else ""
            score_val = 0.0
            if dose_str:
                nums = re.findall(r"[-+]?\d*\.\d+|\d+", dose_str)
                if nums:
                    score_val = float(nums[0])
            if last_med and last_med["name"].strip().lower() == name.strip().lower():
                last_med["is_tapering"] = True
                if not last_med.get("taper_plan"):
                    last_med["taper_plan"] = [{
                        "dose_mg": last_med["dose"],
                        "frequency": last_med.get("frequency", ""),
                        "duration_text": last_med.get("duration", ""),
                        "note": last_med.get("note", "")
                    }]
                last_med["taper_plan"].append({
                    "dose_mg": dose_str,
                    "frequency": freq,
                    "duration_text": dur,
                    "note": note
                })
            else:
                new_med = {
                    "name": name, "score": score_val, "phase": "Current",
                    "dose": dose_str, "frequency": freq, "duration": dur,
                    "note": note, "date": today_iso,
                    "is_tapering": False, "taper_plan": None,
                    "form_type": d_forms[i] if i < len(d_forms) else 'Tablet'
                }
                meds_chart.append(new_med)
                last_med = new_med

    data['meds'] = meds_chart

    # 1. Update text fields securely
    data['provisional_diagnosis'] = request.form.get('provisional_diagnosis', data.get('provisional_diagnosis', ''))
    data['differential_diagnosis'] = request.form.get('differential_diagnosis', data.get('differential_diagnosis', ''))
    data['follow_up_date'] = request.form.get('follow_up_date', data.get('follow_up_date', ''))
    data['note'] = request.form.get('visit_note') or request.form.get('note', data.get('note', ''))

    # 2. Update Doctor modal details (if provided)
    if request.form.get('doc_name'):
        data['doctor'] = {
            "name": request.form.get('doc_name', ''),
            "qualification": request.form.get('doc_qual', ''),
            "registration": request.form.get('doc_reg', ''),
            "clinic": request.form.get('doc_clinic', ''),
            "address": request.form.get('doc_address', ''),
            "phone": request.form.get('doc_phone', ''),
            "email": request.form.get('doc_email', ''),
            "social": request.form.get('doc_social', '')
        }

    sig_file = request.files.get('doc_signature')
    if sig_file and sig_file.filename != '':
        sig_b64 = base64.b64encode(sig_file.read()).decode('utf-8')
        data['signature_b64'] = sig_b64
        session['guest_signature_b64'] = sig_b64

    entry.data_json = json.dumps(data)
    entry.expires_at = entry.expires_at + timedelta(minutes=15)

    try:
        db.session.flush()
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Guest DB Commit Error: {e}")

    if redirect_to_prescription:
        guest_doctor = data.get('doctor', {})
        # Normalize keys for template (template expects qualification/registration)
        guest_doctor = {
            **guest_doctor,
            "qualification": guest_doctor.get("qualification") or guest_doctor.get("qual", ""),
            "registration": guest_doctor.get("registration") or guest_doctor.get("reg", ""),
        }
        guest_patient = data.get('patient', {"name": "Guest Patient"})

        # Mimic SQLAlchemy Objects that preview_prescription.html expects
        current_symps = [{"symptom_name": s.get("name", ""), "duration_text": s.get("duration", "")} for s in data.get("symptoms", []) if s.get("phase") == "Current"]
        current_ses = [{"side_effect_name": s.get("name", ""), "duration_text": s.get("duration", "")} for s in data.get("se", []) if s.get("phase") == "Current"]
        current_mses = [{"category": m.get("cat", ""), "finding_name": m.get("name", "")} for m in data.get("mse", []) if m.get("phase") == "Current"]

        # Safely convert Follow-Up string to Date object
        fu_date_str = data.get('follow_up_date')
        fu_date = None
        if fu_date_str:
            try:
                fu_date = datetime.strptime(fu_date_str, '%Y-%m-%d').date()
            except Exception:
                pass

        visit_obj = {
            "id": "Guest",
            "date": get_ist_now().date(),
            "provisional_diagnosis": data.get('provisional_diagnosis', ''),
            "differential_diagnosis": data.get('differential_diagnosis', ''),
            "next_visit_date": fu_date,
            "note": data.get('note', ''),
            "symptom_entries": current_symps,
            "side_effect_entries": current_ses,
            "mse_entries": current_mses,
            "medication_entries": []
        }

        for med in data.get('meds', []):
            visit_obj['medication_entries'].append({
                'drug_name': med.get('name', ''),
                'drug_type': 'Generic',
                'dose_mg': med.get('dose', ''),
                'frequency': med.get('frequency', ''),
                'duration_text': med.get('duration', ''),
                'note': med.get('note', ''),
                'form_type': med.get('form_type', 'Tablet'),
                'is_tapering': med.get('is_tapering', False),
                'taper_plan': json.dumps(med.get('taper_plan', [])) if med.get('taper_plan') else None
            })

        chief_complaints_sorted = []
        for s in current_symps:
            name = s.get("symptom_name", "")
            dur = s.get("duration_text", "")
            chief_complaints_sorted.append({"name": name, "duration_display": dur, "sort_days": duration_to_days(dur)})
        chief_complaints_sorted.sort(key=lambda x: x["sort_days"], reverse=True)
        chief_complaints_sorted = [{"name": x["name"], "duration_display": x["duration_display"]} for x in chief_complaints_sorted]

        lifchart_url = f"{request.url_root.rstrip('/')}/guest/share/{token}"
        return render_template(
            "preview_prescription.html",
            visit=visit_obj, patient=None, guest=True,
            guest_patient=guest_patient, lifchart_url=lifchart_url,
            guest_doctor=guest_doctor, guest_signature_b64=data.get('signature_b64'),
            chief_complaints_sorted=chief_complaints_sorted
        )
    return redirect(url_for('guest_share_view', token=token))


@app.route('/guest/lifechart_proxy', methods=['POST'])
def guest_lifechart_proxy():
    if not session.get('guest'):
        abort(403)

    token = session.get('guest_token')
    submit_action = request.form.get('submit_action')

    # If a token exists, the user is actively updating an existing chart from the sidebar
    if token:
        # Route to prescription view if they clicked 'Prescription' or 'Both'
        redirect_to_rx = submit_action in ['prescription', 'both']
        return update_guest_share(token, redirect_to_prescription=redirect_to_rx)

    # Fallback for brand new creations
    return guest_lifechart()



def parse_date(date_str):
    """Helper to parse date strings safely."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return None


def calc_event_date(visit_date, duration_text):
    """Compute event date from visit date and duration text (e.g. '2 weeks' -> date 2 weeks before)."""
    if not duration_text:
        return visit_date.strftime('%Y-%m-%d')
    try:
        delta = parse_duration(duration_text)
        return (visit_date - delta).strftime('%Y-%m-%d')
    except Exception:
        return visit_date.strftime('%Y-%m-%d')


def process_visit_form_data(visit, form_data):
    """Helper function to process and save visit form data."""
    # State and Adherence
    visit.clinical_state = form_data.get('clinical_state', '')
    visit.medication_adherence = form_data.get('medication_adherence', '')
    
    # NEW: Next Visit Date
    next_date = form_data.get('next_visit_date')
    if next_date:
        visit.next_visit_date = parse_date(next_date)
    
    # Type of Next Follow up
    t = (form_data.get('type_of_next_follow_up') or '').strip()
    visit.type_of_next_follow_up = t if t else None

    visit.note = form_data.get('visit_note', '')
    
    # Helper for Duration (Single Field Now)
    def get_duration(index, prefix):
        # Prefer 'symptom_duration[]' / 'side_effect_duration[]' etc.; fallback to 'duration_text[]' for compatibility
        dur_list = form_data.getlist(f'{prefix}_duration[]')
        if not dur_list and prefix == 'symptom':
            dur_list = form_data.getlist('duration_text[]')
        return dur_list[index] if index < len(dur_list) else ""

    # 1. Stressors (Phase 2) – from modal JSON
    stressors_json = form_data.get('stressors_data', '')
    if stressors_json:
        try:
            for se in StressorEntry.query.filter_by(visit_id=visit.id).all():
                db.session.delete(se)
            for item in json.loads(stressors_json):
                if isinstance(item, dict) and item.get('stressor_type'):
                    db.session.add(StressorEntry(
                        visit_id=visit.id,
                        stressor_type=item['stressor_type'],
                        duration=item.get('duration') or None,
                        note=item.get('note') or None
                    ))
        except (json.JSONDecodeError, TypeError):
            pass

    # 1b. Major Events (from modal JSON)
    major_events_json = form_data.get('major_events_data', '')
    if major_events_json:
        try:
            for me in MajorEvent.query.filter_by(visit_id=visit.id).all():
                db.session.delete(me)
            for item in json.loads(major_events_json):
                if isinstance(item, dict) and item.get('event_type'):
                    db.session.add(MajorEvent(
                        visit_id=visit.id,
                        event_type=item['event_type'],
                        duration=item.get('duration') or None,
                        note=item.get('note') or None
                    ))
                elif isinstance(item, str) and item.strip():
                    db.session.add(MajorEvent(visit_id=visit.id, event_type=item.strip(), duration=None, note=None))
        except (json.JSONDecodeError, TypeError):
            pass

    # 1c. Adherence Ranges (from modal JSON) — stored per patient, not per visit
    patient_id = visit.patient_id
    adherence_json = form_data.get('adherence_data', '')
    try:
        for ar in AdherenceRange.query.filter_by(patient_id=patient_id).all():
            db.session.delete(ar)
        if adherence_json:
            for item in json.loads(adherence_json):
                if isinstance(item, dict) and item.get('status'):
                    start_d = parse_date(item.get('start')) if item.get('start') else None
                    end_d = parse_date(item.get('end')) if item.get('end') else None
                    db.session.add(AdherenceRange(
                        patient_id=patient_id,
                        visit_id=visit.id,
                        status=item['status'],
                        start_date=start_d,
                        end_date=end_d
                    ))
    except (json.JSONDecodeError, TypeError):
        pass

    # 1d. Clinical State Ranges (from modal JSON) — stored per patient, not per visit
    clinical_state_json = form_data.get('clinical_state_data', '')
    try:
        for csr in ClinicalStateRange.query.filter_by(patient_id=patient_id).all():
            db.session.delete(csr)
        if clinical_state_json:
            for item in json.loads(clinical_state_json):
                if isinstance(item, dict) and item.get('state'):
                    start_d = parse_date(item.get('start')) if item.get('start') else None
                    end_d = parse_date(item.get('end')) if item.get('end') else None
                    db.session.add(ClinicalStateRange(
                        patient_id=patient_id,
                        visit_id=visit.id,
                        state=item['state'],
                        start_date=start_d,
                        end_date=end_d
                    ))
    except (json.JSONDecodeError, TypeError):
        pass

    # 1e. Adverse childhood experiences (ACE) – from modal JSON
    ace_json = form_data.get('ace_data', '')
    if ace_json:
        try:
            json.loads(ace_json)  # validate
            visit.ace_data = ace_json
        except (json.JSONDecodeError, TypeError):
            visit.ace_data = None
    else:
        visit.ace_data = None

    # 1e2. Family history of psychiatric illness – JSON {"present": bool, "items": [...]}
    fh_json = form_data.get('family_history_psychiatric', '')
    if fh_json:
        try:
            data = json.loads(fh_json)
            if isinstance(data, dict):
                visit.family_history_psychiatric = fh_json
            else:
                visit.family_history_psychiatric = None
        except (json.JSONDecodeError, TypeError):
            visit.family_history_psychiatric = None
    else:
        visit.family_history_psychiatric = None

    # 1e3. History of Developmental Milestone Delay – JSON {"status": "...", "types": [...], "notes": ""}
    dm_json = form_data.get('developmental_milestone_delay', '')
    if dm_json:
        try:
            data = json.loads(dm_json)
            if isinstance(data, dict) and 'status' in data:
                visit.developmental_milestone_delay = dm_json
            else:
                visit.developmental_milestone_delay = None
        except (json.JSONDecodeError, TypeError):
            visit.developmental_milestone_delay = None
    else:
        visit.developmental_milestone_delay = None

    # 1f. Scales (Phase 2) - from modal JSON
    scales_json = form_data.get('scales_data', '')
    if scales_json:
        try:
            for sa in ScaleAssessment.query.filter_by(visit_id=visit.id).all():
                db.session.delete(sa)
            for item in json.loads(scales_json):
                if isinstance(item, dict) and item.get('scale_id'):
                    db.session.add(ScaleAssessment(
                        visit_id=visit.id,
                        scale_id=item['scale_id'],
                        scale_name=item['scale_name'],
                        total_score=int(item['total_score']),
                        severity_label=item['severity_label'],
                        raw_responses=item.get('raw_responses', {})
                    ))
        except (json.JSONDecodeError, TypeError, Exception) as e:
            print(f"Error parsing Scales Data: {e}")
            pass

    # 2. Personality (Phase 2)
    traits = form_data.getlist('personality[]')
    pers_note = form_data.get('personality_note', '')
    for t in traits:
        if t.strip():
            db.session.add(PersonalityEntry(visit_id=visit.id, trait=t, note=pers_note))

    # Helper to safely parse floats from form fields that may contain '', None, or 'None'
    def _safe_float(val, default=None):
        try:
            if val is None:
                return default
            s = str(val).strip()
            if not s or s.lower() == "none":
                return default
            return float(s)
        except (TypeError, ValueError):
            return default

    # 3. SYMPTOMS
    s_names = form_data.getlist('symptom_name[]')
    s_onsets = form_data.getlist('symptom_onset[]')
    s_progs = form_data.getlist('symptom_progression[]')
    s_currs = form_data.getlist('symptom_current[]')
    s_notes = form_data.getlist('symptom_note[]')
    
    for i, name in enumerate(s_names):
        s_dur = get_duration(i, 'symptom')
        if not (name or '').strip() and not (s_dur or '').strip():
            continue
        if name.strip():
            entry = SymptomEntry(
                visit_id=visit.id,
                symptom_name=name,
                score_onset=_safe_float(s_onsets[i]) if i < len(s_onsets) else None,
                score_progression=_safe_float(s_progs[i]) if i < len(s_progs) else None,
                score_current=_safe_float(s_currs[i], default=0) if i < len(s_currs) else 0,
                duration_text=get_duration(i, 'symptom'),  # Helper
                note=s_notes[i] if i < len(s_notes) else ''
            )
            db.session.add(entry)
    
    # 4. Medications (backed groups consecutive same-name rows into taper_plan)
    d_names = form_data.getlist('drug_name[]')
    d_types = form_data.getlist('drug_type[]')
    d_forms = form_data.getlist('med_form[]')
    d_full_doses = form_data.getlist('dose_full[]')
    d_freqs = form_data.getlist('frequency[]')
    d_notes = form_data.getlist('med_note[]')
    d_durs = form_data.getlist('med_duration[]')

    last_med = None
    for i, name in enumerate(d_names):
        dose = (d_full_doses[i] if i < len(d_full_doses) else '').strip()
        dur = (d_durs[i] if i < len(d_durs) else '').strip()
        if not (name or '').strip() and not dose and not dur:
            continue
        name = (name or '').strip()
        dose = d_full_doses[i] if i < len(d_full_doses) else ''
        freq = d_freqs[i] if i < len(d_freqs) else ''
        dur = d_durs[i] if i < len(d_durs) else ''
        note = d_notes[i] if i < len(d_notes) else ''

        if last_med and last_med.drug_name.strip().lower() == name.strip().lower():
            if (dose or '').strip() or (dur or '').strip():
                last_med.is_tapering = True
                taper_plan = json.loads(last_med.taper_plan) if last_med.taper_plan else []
                if not taper_plan:
                    taper_plan.append({
                        "dose_mg": last_med.dose_mg or '',
                        "frequency": last_med.frequency or '',
                        "duration_text": last_med.duration_text or '',
                        "note": last_med.note or ''
                    })
                taper_plan.append({
                    "dose_mg": dose,
                    "frequency": freq,
                    "duration_text": dur,
                    "note": note
                })
                last_med.taper_plan = json.dumps(taper_plan)
        elif name:
            entry = MedicationEntry(
                visit_id=visit.id,
                drug_name=name,
                drug_type=d_types[i] if i < len(d_types) else 'Generic',
                form_type=d_forms[i] if i < len(d_forms) else 'Tablet',
                dose_mg=dose,
                frequency=freq,
                duration_text=dur,
                note=note,
                is_tapering=False,
                taper_plan=None
            )
            db.session.add(entry)
            last_med = entry

    # 5. Side Effects
    se_names = form_data.getlist('side_effect_name[]')
    se_onsets = form_data.getlist('side_effect_onset[]')
    se_progs = form_data.getlist('side_effect_progression[]')
    se_currs = form_data.getlist('side_effect_current[]')
    se_notes = form_data.getlist('side_effect_note[]')

    # Fallback for old field name (backward compatibility)
    if not se_currs or all(not x for x in se_currs):
        se_scores_old = form_data.getlist('side_effect_score[]')
        se_currs = se_scores_old

    for i, name in enumerate(se_names):
        se_dur = get_duration(i, 'side_effect')
        if not (name or '').strip() and not (se_dur or '').strip():
            continue
        if name.strip():
            # Handle float/int conversion safely
            curr_val = _safe_float(se_currs[i], default=0) if i < len(se_currs) else 0
            
            entry = SideEffectEntry(
                visit_id=visit.id,
                side_effect_name=name,
                score_onset=_safe_float(se_onsets[i]) if i < len(se_onsets) else None,
                score_progression=_safe_float(se_progs[i]) if i < len(se_progs) else None,
                score_current=curr_val,
                duration_text=get_duration(i, 'side_effect'),  # New Duration
                note=se_notes[i] if i < len(se_notes) else '',
                # CRITICAL FIX: Populate legacy score column
                score=int(curr_val)
            )
            db.session.add(entry)

    # 6. MSE
    mse_cats = form_data.getlist('mse_category[]')
    mse_findings = form_data.getlist('mse_finding_name[]')
    mse_onsets = form_data.getlist('mse_onset[]')
    mse_progs = form_data.getlist('mse_progression[]')
    mse_currs = form_data.getlist('mse_current[]')
    mse_notes = form_data.getlist('mse_note[]')

    # New: single-visit Insight + Additional MSE findings (applied to all MSE rows for this visit)
    insight_status = form_data.get('insight_status') or None
    insight_grade_raw = form_data.get('insight_grade') or None
    try:
        insight_grade_val = int(insight_grade_raw) if insight_grade_raw else None
    except (TypeError, ValueError):
        insight_grade_val = None
    addl_mse_f_note = form_data.get('addl_mse_f_note', '').strip()
    
    # Fallback for old field name (backward compatibility)
    if not mse_currs or all(not x for x in mse_currs):
        mse_scores_old = form_data.getlist('mse_score[]')
        mse_currs = mse_scores_old
    
    for i, cat in enumerate(mse_cats):
        if cat and i < len(mse_findings) and mse_findings[i].strip():
            curr_val = _safe_float(mse_currs[i], default=0) if i < len(mse_currs) else 0
            
            entry = MSEEntry(
                visit_id=visit.id,
                category=cat,
                finding_name=mse_findings[i],
                score_onset=_safe_float(mse_onsets[i]) if i < len(mse_onsets) else None,
                score_progression=_safe_float(mse_progs[i]) if i < len(mse_progs) else None,
                score_current=curr_val,
                duration=get_duration(i, 'mse'),  # Helper (Maps to mse_duration_val[])
                note=mse_notes[i] if i < len(mse_notes) else '',
                # New Insight + Additional MSE fields (same for all rows of this visit)
                insight_status=insight_status,
                insight_grade=insight_grade_val,
                addl_mse_f_note=addl_mse_f_note,
                # CRITICAL FIX: Populate legacy score column
                score=int(curr_val)
            )
            db.session.add(entry)

    # 7. Safety and Medical Profile (separate table)
    drug_alg = form_data.get('drug_allergies', '').strip()
    med_comorb = form_data.get('medical_comorbidities', '').strip()
    non_psych_meds = form_data.get('non_psychiatric_meds', '').strip()
    if drug_alg or med_comorb or non_psych_meds:
        profile = SafetyMedicalProfile(
            visit_id=visit.id,
            drug_allergies=drug_alg,
            medical_comorbidities=med_comorb,
            non_psychiatric_meds=non_psych_meds
        )
        db.session.add(profile)

    # 8. Substance Use History; dates computed from duration (e.g. "Since 12 days") when provided
    sub_names = form_data.getlist('substance_name[]')
    sub_patterns = form_data.getlist('substance_pattern[]')
    sub_usually = form_data.getlist('substance_usually[]')  # legacy field; may be empty with new UI
    sub_notes = form_data.getlist('substance_note[]')

    # New structured fields from enhanced UI
    sub_age_first_use = form_data.getlist('substance_age_first_use[]')
    sub_current_status = form_data.getlist('substance_current_status[]')
    sub_has_abstinence_history = form_data.getlist('substance_has_abstinence_history[]')
    sub_longest_abs_value = form_data.getlist('substance_longest_abstinence_value[]')
    sub_longest_abs_unit = form_data.getlist('substance_longest_abstinence_unit[]')
    sub_abstinent_since_month = form_data.getlist('substance_abstinent_since_month[]')
    sub_abstinent_since_year = form_data.getlist('substance_abstinent_since_year[]')
    SubstanceUseEntry.query.filter_by(visit_id=visit.id).delete()
    visit_date = visit.date
    for i, name in enumerate(sub_names):
        if name.strip():
            usually = (sub_usually[i] or '').strip() if i < len(sub_usually) else ''
            extra_note = (sub_notes[i] or '').strip() if i < len(sub_notes) else ''
            note_parts = []
            if usually:
                note_parts.append('Usually: ' + usually)
            if extra_note:
                note_parts.append(extra_note)
            note_str = ' | '.join(note_parts) if note_parts else None

            # Derive legacy duration-based dates if "usually" string is present
            start_date = None
            end_date = None
            if usually:
                delta = parse_duration(usually)
                if delta:
                    start_date = visit_date - delta
                    end_date = visit_date

            # Map new structured fields safely by index
            def _get_int(lst, idx):
                try:
                    v = (lst[idx] or '').strip()
                    return int(v) if v else None
                except (IndexError, ValueError, TypeError):
                    return None

            def _get_str(lst, idx):
                try:
                    return (lst[idx] or '').strip() or None
                except IndexError:
                    return None

            age_first_use = _get_int(sub_age_first_use, i)
            current_status = _get_str(sub_current_status, i)

            raw_has_abs = _get_str(sub_has_abstinence_history, i)
            has_abstinence_history = None
            if raw_has_abs is not None:
                if raw_has_abs.lower() == 'yes':
                    has_abstinence_history = True
                elif raw_has_abs.lower() == 'no':
                    has_abstinence_history = False

            # Normalize longest abstinence to months
            longest_abs_value = _get_int(sub_longest_abs_value, i) or 0
            longest_abs_unit = (_get_str(sub_longest_abs_unit, i) or '').lower()
            longest_abs_months = None
            if longest_abs_value > 0:
                if 'year' in longest_abs_unit:
                    longest_abs_months = longest_abs_value * 12
                else:
                    longest_abs_months = longest_abs_value

            # Abstinent since: interpret Month + Year as first of month
            abstinent_since = None
            month_str = _get_str(sub_abstinent_since_month, i)
            year_str = _get_str(sub_abstinent_since_year, i)
            if month_str and year_str:
                try:
                    y = int(year_str)
                    m = int(month_str)
                    abstinent_since = date(y, m, 1)
                except ValueError:
                    abstinent_since = None

            db.session.add(SubstanceUseEntry(
                visit_id=visit.id,
                substance_name=name,
                pattern=sub_patterns[i] if i < len(sub_patterns) else 'Occasional',
                start_date=start_date,
                end_date=end_date,
                note=note_str,
                age_at_first_use=age_first_use,
                current_status=current_status,
                has_abstinence_history=has_abstinence_history,
                longest_abstinence_months=longest_abs_months,
                abstinent_since=abstinent_since
            ))


def _aggregate_badge_data(visits):
    """Build aggregated stressors, major_events, personality, ACE from all visits for the profile badge."""
    badge_stressors = []
    badge_major_events = []
    badge_personality = []
    badge_ace = []
    seen_traits = set()
    for v in visits:
        visit_date_str = v.date.strftime('%d-%b-%Y') if v.date else ''
        for s in getattr(v, 'stressor_entries', []):
            if s.stressor_type:
                badge_stressors.append({
                    'stressor_type': s.stressor_type,
                    'duration': s.duration or '',
                    'note': s.note or '',
                    'visit_date': visit_date_str
                })
        for m in getattr(v, 'major_events', []):
            if m.event_type:
                badge_major_events.append({
                    'event_type': m.event_type,
                    'duration': m.duration or '',
                    'note': m.note or '',
                    'visit_date': visit_date_str
                })
        for p in getattr(v, 'personality_entries', []):
            if p.trait and p.trait not in seen_traits:
                seen_traits.add(p.trait)
                badge_personality.append({
                    'trait': p.trait,
                    'note': p.note or '',
                    'visit_date': visit_date_str
                })
        if getattr(v, 'ace_data', None) and v.ace_data.strip():
            try:
                data = json.loads(v.ace_data)
                badge_ace.append({'visit_date': visit_date_str, 'data': data})
            except (TypeError, ValueError):
                pass
    return badge_stressors, badge_major_events, badge_personality, badge_ace


@app.route('/patient/<int:patient_id>')
@login_required
def patient_detail(patient_id):
    """Patient detail page showing all visits and profile badge (stressors, events, personality, ACE)."""
    patient = Patient.query.get_or_404(patient_id)
    visits = Visit.query.filter_by(patient_id=patient_id).order_by(Visit.date.desc()).all()
    badge_stressors, badge_major_events, badge_personality, badge_ace = _aggregate_badge_data(visits)
    is_new_case = len(visits) == 0
    default_email_message = ""
    if not is_new_case and patient.doctor:
        doc = patient.doctor
        doc_name = doc.full_name or doc.username
        default_email_message = f"Dear {patient.name},\n\nThis is a reminder from {doc_name}"
        if doc.clinic_name:
            default_email_message += f" at {doc.clinic_name}"
        default_email_message += ".\n\nPlease get in touch if you have any questions.\n\nBest regards,\n"
        default_email_message += (doc.clinic_name or doc_name)
    adherence_data = json.dumps([{'status': a.status, 'start': a.start_date.strftime('%Y-%m-%d') if a.start_date else None, 'end': a.end_date.strftime('%Y-%m-%d') if a.end_date else None} for a in AdherenceRange.query.filter_by(patient_id=patient.id).all()])
    clinical_state_data = json.dumps([{'state': c.state, 'start': c.start_date.strftime('%Y-%m-%d') if c.start_date else None, 'end': c.end_date.strftime('%Y-%m-%d') if c.end_date else None} for c in ClinicalStateRange.query.filter_by(patient_id=patient.id).all()])
    return render_template('patient_detail.html',
                          patient=patient,
                          visits=visits,
                          is_new_case=is_new_case,
                          badge_stressors=badge_stressors,
                          badge_major_events=badge_major_events,
                          badge_personality=badge_personality,
                          badge_ace=badge_ace,
                          default_email_message=default_email_message,
                          adherence_data=adherence_data,
                          clinical_state_data=clinical_state_data)


@app.route('/patient/<int:patient_id>/save_ranges', methods=['POST'])
@doctor_required
def save_patient_ranges(patient_id):
    """Save Clinical State or Adherence ranges from patient_detail modals (same scope as in visits)."""
    patient = Patient.query.get_or_404(patient_id)
    if patient.doctor_id != session.get('doctor_id'):
        abort(403)
    range_type = request.form.get('range_type')  # 'clinical_state' or 'adherence'

    # PythonAnywhere SQLite may already have older NOT NULL constraints on visit_id.
    # Always attach ranges to the patient's latest visit.
    latest_visit = Visit.query.filter_by(patient_id=patient_id).order_by(Visit.date.desc()).first()
    if not latest_visit:
        flash('Add at least one visit (e.g. New Patient Registration or Follow-up) before saving ranges.', 'error')
        return redirect(url_for('patient_detail', patient_id=patient_id))
    v_id = latest_visit.id

    if range_type == 'adherence':
        for ar in AdherenceRange.query.filter_by(patient_id=patient_id).all():
            db.session.delete(ar)
        raw = request.form.get('adherence_data', '')
        if raw:
            try:
                for item in json.loads(raw):
                    if isinstance(item, dict) and item.get('status'):
                        start_d = parse_date(item.get('start')) if item.get('start') else None
                        end_d = parse_date(item.get('end')) if item.get('end') else None
                        db.session.add(
                            AdherenceRange(
                                patient_id=patient_id,
                                visit_id=v_id,
                                status=item['status'],
                                start_date=start_d,
                                end_date=end_d
                            )
                        )
            except (json.JSONDecodeError, TypeError):
                pass
        db.session.commit()
        flash('Adherence ranges updated.', 'success')
    elif range_type == 'clinical_state':
        for csr in ClinicalStateRange.query.filter_by(patient_id=patient_id).all():
            db.session.delete(csr)
        raw = request.form.get('clinical_state_data', '')
        if raw:
            try:
                for item in json.loads(raw):
                    if isinstance(item, dict) and item.get('state'):
                        start_d = parse_date(item.get('start')) if item.get('start') else None
                        end_d = parse_date(item.get('end')) if item.get('end') else None
                        db.session.add(
                            ClinicalStateRange(
                                patient_id=patient_id,
                                visit_id=v_id,
                                state=item['state'],
                                start_date=start_d,
                                end_date=end_d
                            )
                        )
            except (json.JSONDecodeError, TypeError):
                pass
        db.session.commit()
        flash('Clinical state ranges updated.', 'success')
    else:
        flash('Invalid range type.', 'error')
    return redirect(url_for('patient_detail', patient_id=patient_id))


@app.route('/patient/<int:patient_id>/delete_ranges', methods=['POST'])
@doctor_required
def delete_patient_ranges(patient_id):
    """Delete all Clinical State or Adherence ranges for this patient."""
    patient = Patient.query.get_or_404(patient_id)
    if patient.doctor_id != session.get('doctor_id'):
        abort(403)
    range_type = request.form.get('range_type')  # 'clinical_state' or 'adherence'
    if range_type == 'adherence':
        AdherenceRange.query.filter_by(patient_id=patient_id).delete()
        db.session.commit()
        flash('Adherence ranges deleted.', 'success')
    elif range_type == 'clinical_state':
        ClinicalStateRange.query.filter_by(patient_id=patient_id).delete()
        db.session.commit()
        flash('Clinical state ranges deleted.', 'success')
    else:
        flash('Invalid range type.', 'error')
    return redirect(url_for('patient_detail', patient_id=patient_id))


@app.route('/patient/<int:patient_id>/update_contact', methods=['POST'])
@doctor_required
def update_patient_contact(patient_id):
    """Update patient email and appointment reminder days (patient-specific override)."""
    patient = Patient.query.get_or_404(patient_id)
    if patient.doctor_id != session.get('doctor_id'):
        abort(403)
    patient.email = (request.form.get('email') or '').strip() or None
    patient.appointment_reminder_days = (request.form.get('appointment_reminder_days') or '').strip() or None
    db.session.commit()
    flash('Contact and reminder settings updated.', 'success')
    return redirect(url_for('patient_detail', patient_id=patient_id))


@app.route('/patient/<int:patient_id>/send_email', methods=['POST'])
@doctor_required
def send_patient_email(patient_id):
    """Send an instant email from the logged-in doctor to this patient's email."""
    patient = Patient.query.get_or_404(patient_id)
    if patient.doctor_id != session.get('doctor_id'):
        abort(403)
    doctor = patient.doctor
    if not patient.email:
        flash('Add and save the patient\'s email in Contact & reminder settings first.', 'error')
        return redirect(url_for('patient_detail', patient_id=patient_id))
    if not doctor.email or not doctor.smtp_app_password:
        flash('Set your Email and SMTP App Password in Profile to send emails.', 'error')
        return redirect(url_for('patient_detail', patient_id=patient_id))
    subject = f"Reminder from {doctor.full_name or doctor.username}"
    body = (request.form.get('email_body') or '').strip()
    if not body:
        doctor_name = doctor.full_name or doctor.username
        body = f"Dear {patient.name},\n\nThis is a reminder from {doctor_name}"
        if doctor.clinic_name:
            body += f" at {doctor.clinic_name}"
        body += ".\n\nPlease get in touch if you have any questions.\n\nBest regards,\n"
        body += (doctor.clinic_name or doctor.full_name or doctor.username)
    smtp_password = decrypt_smtp_password(doctor.smtp_app_password)
    if send_dynamic_email(doctor, patient.email, subject, body, smtp_password=smtp_password):
        flash(f'Email sent to {patient.email}.', 'success')
    else:
        flash('Failed to send email. Check your SMTP App Password in Profile.', 'error')
    return redirect(url_for('patient_detail', patient_id=patient_id))


def _patient_latest_visit_or_abort(patient_id):
    """Return (patient, latest_visit) for add-badge-entry routes; abort with redirect if no visit or wrong doctor."""
    patient = Patient.query.get_or_404(patient_id)
    doctor_id = session.get('doctor_id')
    if not doctor_id or patient.doctor_id != doctor_id:
        flash('You can only add entries for your own patients.', 'error')
        return None, None
    latest = Visit.query.filter_by(patient_id=patient_id).order_by(Visit.date.desc()).first()
    if not latest:
        flash('Add at least one visit (e.g. New Patient Registration or Follow-up) before adding to the profile.', 'error')
        return None, None
    return patient, latest


@app.route('/patient/<int:patient_id>/add_stressor', methods=['POST'])
@doctor_required
def add_stressor_to_patient(patient_id):
    """Add a new stressor entry to the patient's latest visit (badge add-new; form is blank)."""
    patient, latest = _patient_latest_visit_or_abort(patient_id)
    if not latest:
        return redirect(url_for('patient_detail', patient_id=patient_id))
    stressor_type = (request.form.get('stressor_type') or '').strip()
    if not stressor_type:
        flash('Stressor type is required.', 'error')
        return redirect(url_for('patient_detail', patient_id=patient_id))
    duration = (request.form.get('duration') or '').strip() or None
    note = (request.form.get('note') or '').strip() or None
    db.session.add(StressorEntry(visit_id=latest.id, stressor_type=stressor_type, duration=duration, note=note))
    db.session.commit()
    flash('Stressor added to profile.', 'success')
    return redirect(url_for('patient_detail', patient_id=patient_id))


@app.route('/patient/<int:patient_id>/add_major_event', methods=['POST'])
@doctor_required
def add_major_event_to_patient(patient_id):
    """Add a new major event entry to the patient's latest visit (badge add-new; form is blank)."""
    patient, latest = _patient_latest_visit_or_abort(patient_id)
    if not latest:
        return redirect(url_for('patient_detail', patient_id=patient_id))
    event_type = (request.form.get('event_type') or '').strip()
    if not event_type:
        flash('Event type is required.', 'error')
        return redirect(url_for('patient_detail', patient_id=patient_id))
    duration = (request.form.get('duration') or '').strip() or None
    note = (request.form.get('note') or '').strip() or None
    db.session.add(MajorEvent(visit_id=latest.id, event_type=event_type, duration=duration, note=note))
    db.session.commit()
    flash('Major event added to profile.', 'success')
    return redirect(url_for('patient_detail', patient_id=patient_id))


@app.route('/patient/<int:patient_id>/add_personality', methods=['POST'])
@doctor_required
def add_personality_to_patient(patient_id):
    """Add a new personality trait entry to the patient's latest visit (badge add-new; form is blank)."""
    patient, latest = _patient_latest_visit_or_abort(patient_id)
    if not latest:
        return redirect(url_for('patient_detail', patient_id=patient_id))
    trait = (request.form.get('trait') or '').strip()
    if not trait:
        flash('Trait is required.', 'error')
        return redirect(url_for('patient_detail', patient_id=patient_id))
    note = (request.form.get('note') or '').strip() or None
    db.session.add(PersonalityEntry(visit_id=latest.id, trait=trait, note=note))
    db.session.commit()
    flash('Personality trait added to profile.', 'success')
    return redirect(url_for('patient_detail', patient_id=patient_id))


@app.route('/patient/<int:patient_id>/add_ace', methods=['POST'])
@doctor_required
def add_ace_to_patient(patient_id):
    """Merge new ACE data with the latest visit's ace_data (badge add-new; form is blank)."""
    patient, latest = _patient_latest_visit_or_abort(patient_id)
    if not latest:
        return redirect(url_for('patient_detail', patient_id=patient_id))
    ace_json = request.form.get('ace_data') or (request.get_json(silent=True) or {}).get('ace_data', '')
    if not ace_json or not ace_json.strip():
        flash('No ACE data to add.', 'error')
        return redirect(url_for('patient_detail', patient_id=patient_id))
    try:
        new_data = json.loads(ace_json)
    except (TypeError, ValueError):
        flash('Invalid ACE data.', 'error')
        return redirect(url_for('patient_detail', patient_id=patient_id))
    new_items = (new_data.get('items') or []) if isinstance(new_data, dict) else []
    if not new_items and not (new_data.get('ageOfExposure') or new_data.get('traumaBurden')):
        flash('Select at least one item or enter age/burden to add.', 'error')
        return redirect(url_for('patient_detail', patient_id=patient_id))
    existing = latest.ace_data
    if existing and existing.strip():
        try:
            existing_data = json.loads(existing)
            new_items = (new_data.get('items') or []) if isinstance(new_data, dict) else []
            existing_items = (existing_data.get('items') or []) if isinstance(existing_data, dict) else []
            merged_items = existing_items + new_items
            merged = dict(existing_data) if isinstance(existing_data, dict) else {}
            merged['items'] = merged_items
            if new_data.get('ageOfExposure'):
                merged['ageOfExposure'] = new_data.get('ageOfExposure', merged.get('ageOfExposure', ''))
            if new_data.get('traumaBurden'):
                merged['traumaBurden'] = new_data.get('traumaBurden', merged.get('traumaBurden', ''))
            latest.ace_data = json.dumps(merged)
        except (TypeError, ValueError):
            latest.ace_data = ace_json
    else:
        latest.ace_data = ace_json
    db.session.commit()
    flash('Adverse childhood experiences added to profile.', 'success')
    return redirect(url_for('patient_detail', patient_id=patient_id))


@app.route('/patient/<int:patient_id>/add_visit', methods=['GET', 'POST'])
@doctor_required
def add_visit(patient_id):
    """Add a new follow-up visit."""
    patient = Patient.query.get_or_404(patient_id)
    
    if request.method == 'POST':
        # 1. Update Patient Attender Details
        if request.form.get('attender_name'):
            patient.attender_name = request.form.get('attender_name')
        if request.form.get('attender_relation'):
            relation = request.form.get('attender_relation')
            if relation == 'Others':
                other_rel = request.form.get('attender_relation_other')
                if other_rel and other_rel.strip():
                    relation = other_rel.strip()
            patient.attender_relation = relation
        if request.form.get('attender_reliability'):
            patient.attender_reliability = request.form.get('attender_reliability')
        
        # 2. Create Visit
        visit_date = parse_date(request.form.get('date')) or date.today()
        visit = Visit(
            patient_id=patient.id,
            date=visit_date,
            visit_type='Follow-up',
            next_visit_date=parse_date(request.form.get('next_visit_date'))
        )
        # Save diagnosis if provided (from life chart or add visit)
        if request.form.get('provisional_diagnosis'):
            visit.provisional_diagnosis = serialize_diagnosis_values(request.form.get('provisional_diagnosis'))
        if request.form.get('differential_diagnosis'):
            visit.differential_diagnosis = serialize_diagnosis_values(request.form.get('differential_diagnosis'))
        
        db.session.add(visit)
        db.session.flush()
        
        # Process form data
        process_visit_form_data(visit, request.form)
        
        db.session.commit()
        
        # Handle submit_action
        submit_action = request.form.get('submit_action')
        if submit_action == 'prescription':
            return redirect(url_for('preview_prescription', visit_id=visit.id))
        elif submit_action == 'lifechart':
            return redirect(url_for('life_chart', patient_id=patient.id, visit_id=visit.id))
        elif submit_action == 'both':
            return redirect(url_for('preview_prescription', visit_id=visit.id, include_qr='true'))
        else:
            return redirect(url_for('patient_detail', patient_id=patient.id))
        
    # GET Request - Auto-fill logic
    today = date.today()
    
    # Fetch the most recent visit to copy data from
    last_visit = Visit.query.filter_by(patient_id=patient.id).order_by(Visit.date.desc()).first()
    
    doctor = Doctor.query.get(session.get('doctor_id'))
    ace_data = (last_visit.ace_data or '') if last_visit and getattr(last_visit, 'ace_data', None) else ''
    adherence_data = json.dumps([{'status': a.status, 'start': a.start_date.strftime('%Y-%m-%d') if a.start_date else None, 'end': a.end_date.strftime('%Y-%m-%d') if a.end_date else None} for a in AdherenceRange.query.filter_by(patient_id=patient.id).all()])
    clinical_state_data = json.dumps([{'state': c.state, 'start': c.start_date.strftime('%Y-%m-%d') if c.start_date else None, 'end': c.end_date.strftime('%Y-%m-%d') if c.end_date else None} for c in ClinicalStateRange.query.filter_by(patient_id=patient.id).all()])
    return render_template('add_visit.html', patient=patient, today=today, last_visit=last_visit, doctor=doctor, ace_data=ace_data, adherence_data=adherence_data, clinical_state_data=clinical_state_data)


@app.route('/visit/<int:visit_id>/edit', methods=['GET', 'POST'])
@doctor_required
def edit_visit(visit_id):
    """Edit an existing visit and update patient details."""
    visit = Visit.query.get_or_404(visit_id)
    patient = visit.patient
    
    if request.method == 'POST':
        # --- 1. Update Patient Details (Conditional Check) ---
        # FIX: Only update these fields if they exist in the form.
        # This prevents the LifeChart form (which lacks these fields) from wiping data.
        
        if 'age' in request.form:
            try:
                patient.age = int(request.form.get('age'))
            except (ValueError, TypeError):
                pass  # Keep old age if invalid

        if 'sex' in request.form:
            patient.sex = request.form.get('sex')
            
        if 'address' in request.form:
            patient.address = request.form.get('address')
            
        if 'phone' in request.form:
            patient.phone = request.form.get('phone')

        if 'email' in request.form:
            patient.email = (request.form.get('email') or '').strip() or None

        if 'appointment_reminder_days' in request.form:
            patient.appointment_reminder_days = (request.form.get('appointment_reminder_days') or '').strip() or None
            
        if 'attender_name' in request.form:
            patient.attender_name = request.form.get('attender_name')
            
        if 'attender_relation' in request.form:
            relation = request.form.get('attender_relation')
            if relation == 'Others':
                other_rel = request.form.get('attender_relation_other')
                if other_rel and other_rel.strip():
                    relation = other_rel.strip()
            patient.attender_relation = relation
            
        if 'attender_reliability' in request.form:
            patient.attender_reliability = request.form.get('attender_reliability')
            
        if 'personal_notes' in request.form:
            patient.personal_notes = request.form.get('personal_notes')

        # --- 2. Update Visit Data ---
        visit.date = parse_date(request.form.get('date')) or visit.date
        visit.next_visit_date = parse_date(request.form.get('next_visit_date'))  # NEW
        
        visit.provisional_diagnosis = serialize_diagnosis_values(request.form.get('provisional_diagnosis', ''))
        visit.differential_diagnosis = serialize_diagnosis_values(request.form.get('differential_diagnosis', ''))
        
        # --- 3. Replace Entries (Delete Old -> Add New) ---
        SymptomEntry.query.filter_by(visit_id=visit.id).delete()
        MedicationEntry.query.filter_by(visit_id=visit.id).delete()
        SideEffectEntry.query.filter_by(visit_id=visit.id).delete()
        MSEEntry.query.filter_by(visit_id=visit.id).delete()
        
        # Phase 2: Clear new tables
        StressorEntry.query.filter_by(visit_id=visit.id).delete()
        PersonalityEntry.query.filter_by(visit_id=visit.id).delete()
        SafetyMedicalProfile.query.filter_by(visit_id=visit.id).delete()
        
        # Use the updated helper from Phase 1
        process_visit_form_data(visit, request.form)
        
        db.session.commit()
        
        # --- 4. Redirection Logic ---
        submit_action = request.form.get('submit_action')
        if submit_action == 'prescription':
            return redirect(url_for('preview_prescription', visit_id=visit.id))
        elif submit_action == 'lifechart':
            return redirect(url_for('life_chart', patient_id=patient.id, visit_id=visit.id))
        elif submit_action == 'both':
            return redirect(url_for('preview_prescription', visit_id=visit.id, include_qr='true'))
        else:
            return redirect(url_for('patient_detail', patient_id=patient.id))
    
    # --- FIND PREVIOUS VISIT (Carry-Forward Logic) ---
    # Find the visit that happened immediately before the current one
    previous_visit = Visit.query.filter(
        Visit.patient_id == patient.id,
        Visit.date < visit.date
    ).order_by(Visit.date.desc()).first()
    
    # If same date, use ID to distinguish order
    if not previous_visit:
        previous_visit = Visit.query.filter(
            Visit.patient_id == patient.id,
            Visit.date == visit.date,
            Visit.id < visit.id
        ).order_by(Visit.id.desc()).first()
    
    doctor = Doctor.query.get(session.get('doctor_id'))
    major_events_data = json.dumps([{'event_type': e.event_type, 'duration': e.duration or '', 'note': e.note or ''} for e in visit.major_events])
    stressors_data = json.dumps([{'stressor_type': s.stressor_type, 'duration': s.duration or '', 'note': s.note or ''} for s in visit.stressor_entries])
    # Load ranges from patient so they persist across visits and are not lost when a visit is deleted
    adherence_data = json.dumps([{'status': a.status, 'start': a.start_date.strftime('%Y-%m-%d') if a.start_date else None, 'end': a.end_date.strftime('%Y-%m-%d') if a.end_date else None} for a in AdherenceRange.query.filter_by(patient_id=visit.patient_id).all()])
    clinical_state_data = json.dumps([{'state': c.state, 'start': c.start_date.strftime('%Y-%m-%d') if c.start_date else None, 'end': c.end_date.strftime('%Y-%m-%d') if c.end_date else None} for c in ClinicalStateRange.query.filter_by(patient_id=visit.patient_id).all()])
    substances_data = json.dumps([{
        'substance': su.substance_name,
        'pattern': su.pattern or 'Occasional',
        'start_date': su.start_date.strftime('%Y-%m-%d') if su.start_date else None,
        'end_date': su.end_date.strftime('%Y-%m-%d') if su.end_date else None,
        'note': su.note or ''
    } for su in getattr(visit, 'substance_use_entries', [])])
    scales_data = json.dumps([{
        'scale_id': sa.scale_id,
        'scale_name': sa.scale_name,
        'total_score': sa.total_score,
        'severity_label': sa.severity_label,
        'raw_responses': sa.raw_responses or {}
    } for sa in getattr(visit, 'scale_assessments', [])])
    ace_data = (visit.ace_data or '') if getattr(visit, 'ace_data', None) else ''
    return render_template('edit_visit.html', visit=visit, patient=patient, previous_visit=previous_visit, doctor=doctor, major_events_data=major_events_data, stressors_data=stressors_data, adherence_data=adherence_data, clinical_state_data=clinical_state_data, substances_data=substances_data, scales_data=scales_data, ace_data=ace_data)


@app.route('/visit/<int:visit_id>/delete', methods=['POST'])
@doctor_required
def delete_visit(visit_id):
    """Delete a patient visit and all related records. No DB-level ON DELETE CASCADE, so we delete child rows explicitly."""
    visit = Visit.query.get_or_404(visit_id)
    patient_id = visit.patient_id
    # Delete all child records that reference this visit (no ondelete=CASCADE in DB)
    SymptomEntry.query.filter_by(visit_id=visit.id).delete()
    MedicationEntry.query.filter_by(visit_id=visit.id).delete()
    SideEffectEntry.query.filter_by(visit_id=visit.id).delete()
    MSEEntry.query.filter_by(visit_id=visit.id).delete()
    StressorEntry.query.filter_by(visit_id=visit.id).delete()
    PersonalityEntry.query.filter_by(visit_id=visit.id).delete()
    SafetyMedicalProfile.query.filter_by(visit_id=visit.id).delete()
    MajorEvent.query.filter_by(visit_id=visit.id).delete()
    # Adherence/Clinical state ranges are stored per patient — do not delete
    SubstanceUseEntry.query.filter_by(visit_id=visit.id).delete()
    ScaleAssessment.query.filter_by(visit_id=visit.id).delete()
    db.session.delete(visit)
    db.session.commit()
    return redirect(url_for('patient_detail', patient_id=patient_id))


@app.route('/visit/<int:visit_id>/update_clinical', methods=['POST'])
@login_required
def update_clinical(visit_id):
    """
    Lightweight update for the Life Chart view.
    Updates ONLY: Diagnosis, Notes, Next Date, and Medications.
    Preserves: Symptoms, MSE, Side Effects, Stressors, Personality.
    """
    visit = Visit.query.get_or_404(visit_id)
    
    # 1. Update Basic Visit Fields
    visit.note = request.form.get('visit_note', '')
    visit.provisional_diagnosis = serialize_diagnosis_values(request.form.get('provisional_diagnosis', ''))
    visit.differential_diagnosis = serialize_diagnosis_values(request.form.get('differential_diagnosis', ''))
    visit.clinical_state = request.form.get('clinical_state', '')
    visit.medication_adherence = request.form.get('medication_adherence', '')
    
    next_date = request.form.get('next_visit_date')
    if next_date:
        visit.next_visit_date = parse_date(next_date)
    t = (request.form.get('type_of_next_follow_up') or '').strip()
    visit.type_of_next_follow_up = t if t else None

    if 'ace_data' in request.form:
        ace_json = request.form.get('ace_data', '')
        try:
            if ace_json:
                json.loads(ace_json)
                visit.ace_data = ace_json
            else:
                visit.ace_data = None
        except (json.JSONDecodeError, TypeError):
            visit.ace_data = None

    # --- RANGES UPDATES (Clinical State & Adherence — stored per patient) ---
    patient_id = visit.patient_id
    adherence_json = request.form.get('adherence_data', '')
    try:
        for ar in AdherenceRange.query.filter_by(patient_id=patient_id).all():
            db.session.delete(ar)
        if adherence_json:
            for item in json.loads(adherence_json):
                if isinstance(item, dict) and item.get('status'):
                    start_d = parse_date(item.get('start')) if item.get('start') else None
                    end_d = parse_date(item.get('end')) if item.get('end') else None
                    db.session.add(AdherenceRange(
                        patient_id=patient_id, visit_id=visit.id, status=item['status'], start_date=start_d, end_date=end_d
                    ))
    except (json.JSONDecodeError, TypeError):
        pass

    clinical_state_json = request.form.get('clinical_state_data', '')
    try:
        for csr in ClinicalStateRange.query.filter_by(patient_id=patient_id).all():
            db.session.delete(csr)
        if clinical_state_json:
            for item in json.loads(clinical_state_json):
                if isinstance(item, dict) and item.get('state'):
                    start_d = parse_date(item.get('start')) if item.get('start') else None
                    end_d = parse_date(item.get('end')) if item.get('end') else None
                    db.session.add(ClinicalStateRange(
                        patient_id=patient_id, visit_id=visit.id, state=item['state'], start_date=start_d, end_date=end_d
                    ))
    except (json.JSONDecodeError, TypeError):
        pass
    # --- END RANGES UPDATES ---

    # 2. Update Medications ONLY (Wipe old meds for this visit, write new ones)
    # We do NOT touch SymptomEntry, MSEEntry, SideEffectEntry here.
    MedicationEntry.query.filter_by(visit_id=visit.id).delete()

    d_types = request.form.getlist('drug_type[]')
    d_names = request.form.getlist('drug_name[]')
    d_forms = request.form.getlist('med_form[]')
    d_full_doses = request.form.getlist('dose_full[]')
    d_freqs = request.form.getlist('frequency[]')
    d_durs = request.form.getlist('med_duration[]')
    d_notes = request.form.getlist('med_note[]')

    last_med = None
    for i, name in enumerate(d_names):
        dose = (d_full_doses[i] if i < len(d_full_doses) else '').strip()
        dur = (d_durs[i] if i < len(d_durs) else '').strip()
        if not (name or '').strip() and not dose and not dur:
            continue
        name = (name or '').strip()
        dose = d_full_doses[i] if i < len(d_full_doses) else ''
        freq = d_freqs[i] if i < len(d_freqs) else ''
        dur = d_durs[i] if i < len(d_durs) else ''
        note = d_notes[i] if i < len(d_notes) else ''

        if last_med and last_med.drug_name.strip().lower() == name.strip().lower():
            if (dose or '').strip() or (dur or '').strip():
                last_med.is_tapering = True
                taper_plan = json.loads(last_med.taper_plan) if last_med.taper_plan else []
                if not taper_plan:
                    taper_plan.append({
                        "dose_mg": last_med.dose_mg or '',
                        "frequency": last_med.frequency or '',
                        "duration_text": last_med.duration_text or '',
                        "note": last_med.note or ''
                    })
                taper_plan.append({
                    "dose_mg": dose,
                    "frequency": freq,
                    "duration_text": dur,
                    "note": note
                })
                last_med.taper_plan = json.dumps(taper_plan)
        elif name:
            entry = MedicationEntry(
                visit_id=visit.id,
                drug_type=d_types[i] if i < len(d_types) else 'Generic',
                drug_name=name,
                form_type=d_forms[i] if i < len(d_forms) else 'Tablet',
                dose_mg=dose,
                frequency=freq,
                duration_text=dur,
                note=note,
                is_tapering=False,
                taper_plan=None
            )
            db.session.add(entry)
            last_med = entry

    # 3. Commit Changes
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f"Error saving changes: {str(e)}", "error")

    # 4. Handle Redirection
    submit_action = request.form.get('submit_action')
    
    if submit_action == 'prescription':
        return redirect(url_for('preview_prescription', visit_id=visit.id))
    elif submit_action == 'lifechart':
        # Refresh the same page
        return redirect(url_for('life_chart', patient_id=visit.patient_id, visit_id=visit.id))
    
    return redirect(url_for('life_chart', patient_id=visit.patient_id, visit_id=visit.id))


def prepare_chart_data(patient_id: int) -> dict:
    """
    Transform database rows into Chart.js datasets with Unified averages.
    """
    patient = Patient.query.get(patient_id)
    visits = Visit.query.filter_by(patient_id=patient_id).order_by(Visit.date).all()
    
    if not visits:
        return {
            'symptom_datasets': [], 'symptom_unified': None,
            'medication_datasets': [], 'med_unified': None,
            'side_effect_datasets': [], 'se_unified': None,
            'mse_datasets': [], 'mse_unified': None,
            'scale_datasets': [], 'scale_unified': None, 'scale_names': [],
            'symptom_names': [], 'med_names': [], 'se_names': [], 'mse_categories': [],
            'visit_details': {},
            'stressors': [], 'events': [], 'substances': []
        }
    
    # --- Helper: Calculate Unified (Average) Lines ---
    def calculate_unified(data_dict, label, color):
        # Dictionaries to hold data for aggregation
        date_breakdown = {}    # Stores list of {name, score} for each date
        date_visit_ids = {}
        date_phases = {}
        date_reported_on = {}

        for item_name, points in data_dict.items():
            for point in points:
                date_key = point['x'][:10] 
                val = point['y']
                
                # 1. Capture Breakdown Data (Name & Score)
                if val is not None:
                    if date_key not in date_breakdown: date_breakdown[date_key] = []
                    date_breakdown[date_key].append({'name': item_name, 'score': val})
                
                # 2. Capture Metadata (from the first valid point found)
                if 'visit_id' in point:
                    date_visit_ids[date_key] = point['visit_id']
                if 'phase' in point:
                    date_phases[date_key] = point['phase']
                if 'reported_on' in point:
                    date_reported_on[date_key] = point['reported_on']
        
        unified_points = []
        for d, details in sorted(date_breakdown.items()):
            if details:
                # Calculate Average
                avg = sum(item['score'] for item in details) / len(details)
                
                # Create point
                pt = {'x': d + 'T00:00:00', 'y': round(avg, 2)}
                
                # Attach the breakdown list to the point
                pt['breakdown'] = details
                
                # Attach metadata
                if d in date_visit_ids: pt['visit_id'] = date_visit_ids[d]
                if d in date_phases: pt['phase'] = date_phases[d]
                if d in date_reported_on: pt['reported_on'] = date_reported_on[d]
                
                # Title for the modal
                pt['symptom_name'] = "Combined Symptom Details" 
                    
                unified_points.append(pt)
                
        if not unified_points:
            return None
            
        return {
            'label': label,
            'data': unified_points,
            'borderColor': color,
            'backgroundColor': color.replace('1)', '0.1)'),
            'borderWidth': 4,
            'borderDash': [],
            'fill': False,
            'pointRadius': 0, 
            'pointHitRadius': 10,
            'tension': 0.4,
            'isUnified': True
        }

    # --- 1. Process Symptoms ---
    symptom_data = {}
    previous_symptom_names = set()  # names from earlier visits; if current symptom matches, skip onset/progression
    for visit in visits:
        visit_date = datetime.combine(visit.date, datetime.min.time())
        visit_date_str = visit_date.isoformat() # Store original visit date string
        
        for entry in visit.symptom_entries:
            name = entry.symptom_name
            if name not in symptom_data: symptom_data[name] = []
            
            points = []
            if visit.visit_type == 'First':
                # Only plot onset and progression if this symptom did not exist in a previous visit (case-insensitive, partial match > 85%)
                seen_in_previous = any(_symptom_name_matches(name, prev) for prev in previous_symptom_names)
                if not seen_in_previous:
                    duration = parse_duration(entry.duration_text or '') or timedelta(0)
                    onset = visit_date - duration
                    mid = calculate_midpoint_date(onset, visit_date)
                    points = [
                        {
                            'x': onset.isoformat(),
                            'y': entry.score_onset,
                            'phase': 'Onset',
                            'symptom_name': name,
                            'reported_on': visit_date_str
                        },
                        {
                            'x': mid.isoformat(),
                            'y': entry.score_progression,
                            'phase': 'Progression',
                            'symptom_name': name,
                            'reported_on': visit_date_str
                        },
                        {
                            'x': visit_date.isoformat(),
                            'y': entry.score_current,
                            'phase': 'Current',
                            'symptom_name': name,
                            'reported_on': visit_date_str
                        }
                    ]
                else:
                    points = [{
                        'x': visit_date_str,
                        'y': entry.score_current,
                        'phase': 'Current',
                        'symptom_name': name,
                        'reported_on': visit_date_str
                    }]
            else:
                points = [{
                    'x': visit_date_str,
                    'y': entry.score_current,
                    'phase': 'Current',
                    'symptom_name': name,
                    'reported_on': visit_date_str
                }]

            for p in points:
                if p['y'] is not None:
                    p['visit_id'] = visit.id
                    p['detail'] = entry.note or ''
                    symptom_data[name].append(p)

        for entry in visit.symptom_entries:
            previous_symptom_names.add(entry.symptom_name)
    symptom_datasets = []
    for name, points in symptom_data.items():
        symptom_datasets.append({
            'label': name,
            'data': sorted(points, key=lambda x: x['x']),
            'tension': 0.3,
            'hidden': True
        })
    
    # Calculate unified average for symptoms
    symptom_unified = calculate_unified(symptom_data, 'Unified Symptoms (Avg)', 'rgba(0, 0, 0, 1)')

    # --- 2. Process Medications ---
    med_data = {}
    for visit in visits:
        v_date = datetime.combine(visit.date, datetime.min.time())
        for entry in visit.medication_entries:
            name = entry.drug_name
            if name not in med_data:
                med_data[name] = []

            # --- Tapering: RTP/RTI for chart Y; actual dose for tooltips only ---
            if entry.is_tapering and entry.taper_plan:
                try:
                    plan = json.loads(entry.taper_plan)
                    current_date = v_date
                    for step in plan:
                        y_val, actual_dose = compute_med_chart_value(name, step.get('dose_mg', ''), step.get('frequency', ''), 'rtp')
                        med_data[name].append({
                            'x': current_date.isoformat(),
                            'y': y_val,
                            'actualDose': actual_dose,
                            'visit_id': visit.id
                        })
                        dur_delta = parse_duration(step.get('duration_text', ''))
                        if dur_delta:
                            current_date += dur_delta
                    continue
                except Exception:
                    pass

            # --- Standard: RTP/RTI for line chart; tooltips show actual dose only ---
            y_val, actual_dose = compute_med_chart_value(name, entry.dose_mg, entry.frequency or '', 'rtp')
            med_data[name].append({'x': v_date.isoformat(), 'y': y_val, 'actualDose': actual_dose, 'visit_id': visit.id})

    medication_datasets = []
    for name, points in med_data.items():
        medication_datasets.append({
            'label': name,
            'data': sorted(points, key=lambda x: x['x']),
            'tension': 0.1,
            'hidden': True
        })
    med_unified = calculate_unified(med_data, 'Unified Meds (Avg Dose)', 'rgba(0, 0, 0, 1)')

    # --- 3. Process Side Effects ---
    se_data = {}
    for visit in visits:
        v_date = datetime.combine(visit.date, datetime.min.time()).isoformat()
        for entry in visit.side_effect_entries:
            name = entry.side_effect_name
            val = entry.score
            if name not in se_data: se_data[name] = []
            se_data[name].append({'x': v_date, 'y': val, 'visit_id': visit.id})
            
    side_effect_datasets = [] # RENAMED to match template
    for name, points in se_data.items():
        side_effect_datasets.append({
            'label': name,
            'data': sorted(points, key=lambda x: x['x']),
            'tension': 0.3,
            'hidden': True
        })
    se_unified = calculate_unified(se_data, 'Unified Side Effects (Avg)', 'rgba(0, 0, 0, 1)')

    # --- 4. Process MSE ---
    mse_data = {}
    for visit in visits:
        v_date = datetime.combine(visit.date, datetime.min.time()).isoformat()
        for entry in visit.mse_entries:
            cat = entry.category
            val = entry.score
            if cat not in mse_data: mse_data[cat] = []
            mse_data[cat].append({
                'x': v_date, 
                'y': val, 
                'visit_id': visit.id,
                'detail': entry.finding_name or ''  # Add detail for tooltips
            })
            
    mse_datasets = []
    for cat, points in mse_data.items():
        mse_datasets.append({
            'label': cat,
            'data': sorted(points, key=lambda x: x['x']),
            'tension': 0.3,
            'hidden': False if cat == 'Unified MSE (Avg)' else True
        })
    mse_unified = calculate_unified(mse_data, 'Unified MSE (Avg)', 'rgba(0, 0, 0, 1)')

    # --- 4c. Process Scales ---
    scale_data = {}
    for visit in visits:
        v_date = datetime.combine(visit.date, datetime.min.time()).isoformat()
        for entry in getattr(visit, 'scale_assessments', []):
            name = entry.scale_name
            val = entry.total_score
            if name not in scale_data:
                scale_data[name] = []
            scale_data[name].append({
                'x': v_date,
                'y': val,
                'visit_id': visit.id,
                'detail': entry.severity_label or ''
            })
    scale_datasets = []
    for name, points in scale_data.items():
        scale_datasets.append({
            'label': name,
            'data': sorted(points, key=lambda x: x['x']),
            'tension': 0.3,
            'hidden': False if name == 'Unified Scales (Avg)' else True
        })
    scale_unified = calculate_unified(scale_data, 'Unified Scales (Avg)', 'rgba(0, 0, 0, 1)')

    # --- 4b. Stressors, Major Events, Substance Use (for chart markers/tracks) ---
    stressors_data = []
    events_data = []
    substances_data = []
    for visit in visits:
        v_date = datetime.combine(visit.date, datetime.min.time())
        str_date = visit.date.strftime('%Y-%m-%d')
        for st in getattr(visit, 'stressor_entries', []):
            stressors_data.append({
                'type': st.stressor_type, 'duration': st.duration or '', 'note': st.note or '',
                'date': calc_event_date(visit.date, st.duration)
            })
        for me in getattr(visit, 'major_events', []):
            events_data.append({
                'type': me.event_type, 'duration': me.duration or '', 'note': me.note or '',
                'date': calc_event_date(visit.date, me.duration)
            })
        for su in getattr(visit, 'substance_use_entries', []):
            # Life chart strip: same start/end logic as life_chart route
            patient_age = getattr(patient, 'age', None) if patient else None
            age_first = getattr(su, 'age_at_first_use', None)
            current_status = (getattr(su, 'current_status', None) or '').strip()
            abstinent_since = getattr(su, 'abstinent_since', None)
            start_str = None
            end_str = None
            if age_first is not None and patient_age is not None and age_first < patient_age:
                years_before_visit = patient_age - age_first
                try:
                    start_date = visit.date.replace(year=visit.date.year - years_before_visit)
                    start_str = start_date.strftime('%Y-%m-%d')
                except ValueError:
                    pass
            if not start_str and su.start_date:
                start_str = su.start_date.strftime('%Y-%m-%d')
            if not start_str:
                dur = parse_duration(su.note or '')
                if dur:
                    start_str = (visit.date - dur).strftime('%Y-%m-%d')
            if not start_str:
                start_str = str_date
            if current_status == 'Currently Abstinent' and abstinent_since:
                end_str = abstinent_since.strftime('%Y-%m-%d')
            if not end_str and su.end_date:
                end_str = su.end_date.strftime('%Y-%m-%d')
            if not end_str:
                end_str = str_date
            substances_data.append({
                'substance': su.substance_name,
                'pattern': su.pattern or 'Occasional',
                'start_date': start_str,
                'end_date': end_str,
                'note': su.note or ''
            })

    # --- 5. Visit Details for Modal ---
    visit_details_map = {}
    for visit in visits:
        visit_details_map[visit.id] = {
            'date': visit.date.strftime('%Y-%m-%d'),
            'type': visit.visit_type,
            'diagnosis': format_diagnosis_values(visit.provisional_diagnosis),
            'symptoms': [{'name': s.symptom_name, 'score': s.score_current, 'note': s.note} for s in visit.symptom_entries],
            'meds': [{'name': m.drug_name, 'dose': m.dose_mg, 'note': m.note} for m in visit.medication_entries],
            'se': [{'name': s.side_effect_name, 'score': s.score, 'note': s.note} for s in visit.side_effect_entries],
            'mse': [{'cat': m.category, 'name': m.finding_name, 'score': m.score, 'note': m.note} for m in visit.mse_entries],
            'scales': [{'name': sa.scale_name, 'score': sa.total_score, 'label': sa.severity_label} for sa in getattr(visit, 'scale_assessments', [])],
            'stressors': [{'type': st.stressor_type, 'duration': st.duration, 'note': st.note} for st in getattr(visit, 'stressor_entries', [])],
            'events': [{'type': me.event_type, 'duration': me.duration, 'note': me.note} for me in getattr(visit, 'major_events', [])],
            'notes': getattr(visit, 'notes', '')
        }

    return {
        'symptom_datasets': symptom_datasets, 'symptom_unified': symptom_unified,
        'medication_datasets': medication_datasets, 'med_unified': med_unified,
        'side_effect_datasets': side_effect_datasets, 'se_unified': se_unified,
        'mse_datasets': mse_datasets, 'mse_unified': mse_unified,
        'scale_datasets': scale_datasets, 'scale_unified': scale_unified,
        'scale_names': list(scale_data.keys()),
        'symptom_names': list(symptom_data.keys()),
        'med_names': list(med_data.keys()),
        'se_names': list(se_data.keys()),
        'mse_categories': list(mse_data.keys()),
        'visit_details': visit_details_map,
        'stressors': stressors_data,
        'events': events_data,
        'substances': substances_data
    }

@app.route('/life_chart_preview')
def life_chart_preview():
    patient = (
    db.session.query(Patient)
    .join(Visit)
    .join(SymptomEntry)
    .order_by(Visit.date.desc())
    .first()
    )
    
    if not patient:
        return ""

    chart_data = prepare_chart_data(patient.id)

    return render_template(
        'life_chart_mini.html',
        symptom_datasets=chart_data['symptom_datasets'],
        symptom_unified=chart_data['symptom_unified'],
        visit_details=chart_data['visit_details']
    )

@app.route('/mse_chart_preview')
def mse_chart_preview():
    patient = Patient.query.join(Visit).order_by(Visit.date.desc()).first()
    if not patient:
        return ""

    chart_data = prepare_chart_data(patient.id)

    # If no MSE data exists, still render empty chart shell
    return render_template(
        'mse_chart_mini.html',
        mse_datasets=chart_data.get('mse_datasets', []),
        mse_unified=chart_data.get('mse_unified')
    )



# --- CHART LOGIC 4-PANEL ---
@app.route('/life_chart/<int:patient_id>')
@login_required
def life_chart(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    visits = Visit.query.filter_by(patient_id=patient.id).order_by(Visit.date).all()
    
    # Check if a specific visit_id was passed in the URL (e.g., ?visit_id=5)
    target_visit_id = request.args.get('visit_id', type=int)
    target_visit = None
    
    if target_visit_id:
        # Fetch the specific visit to populate the form
        target_visit = Visit.query.get(target_visit_id)
        # Security: Ensure this visit actually belongs to this patient
        if target_visit and target_visit.patient_id != patient.id:
            target_visit = None
    
    # 1. Helpers
    def get_days(dur_str):
        if not dur_str: return 0
        d = parse_duration(dur_str)
        return d.days if d else 0

    def build_clinical_points(entry, v_date, type_lbl, skip_onset_progression=False):
        pts = []
        dur_text = getattr(entry, 'duration_text', None) or getattr(entry, 'duration', None) or ''
        days = get_days(dur_text)
        # If onset/progression scores exist but duration is missing, use default so all three points are shown
        has_onset_or_prog = (entry.score_onset is not None) or (entry.score_progression is not None)
        if days <= 0 and has_onset_or_prog:
            days = 14  # default duration in days so onset/progression get a date range
        if not skip_onset_progression and days > 0:
            start = v_date - timedelta(days=days)  # Onset = visit date - duration (e.g. 12 days ago)
            if entry.score_onset is not None:
                pts.append({'x': start.strftime('%Y-%m-%d'), 'y': entry.score_onset, 'detail': f"{type_lbl} Onset", 'phase': 'Onset'})
            if entry.score_progression is not None:
                mid = start + timedelta(days=days // 2)  # Progression = onset + half duration (e.g. 6 days ago)
                pts.append({'x': mid.strftime('%Y-%m-%d'), 'y': entry.score_progression, 'detail': f"{type_lbl} Progression", 'phase': 'Progression'})
        if entry.score_current is not None:
            pts.append({'x': v_date.strftime('%Y-%m-%d'), 'y': entry.score_current, 'detail': f"{type_lbl} Current", 'phase': 'Current'})
        return pts

    def build_med_points(entry, v_date):
        pts = []

        # --- Tapering: RTP/RTI for chart Y; actual dose for tooltips only ---
        if entry.is_tapering and entry.taper_plan:
            try:
                plan = json.loads(entry.taper_plan)
                current_date = v_date
                for step in plan:
                    days = get_days(step.get('duration_text', ''))
                    y_val, actual_dose = compute_med_chart_value(entry.drug_name, step.get('dose_mg', ''), step.get('frequency', ''), 'rtp')
                    duration = max(1, days)
                    for i in range(duration):
                        d = current_date + timedelta(days=i)
                        pts.append({
                            'x': d.strftime('%Y-%m-%d'),
                            'y': y_val,
                            'actualDose': actual_dose,
                            'detail': f"Freq: {step.get('frequency', '')} (Tapering)",
                            'actualEntry': (i == 0)
                        })
                    current_date += timedelta(days=duration)
                return pts
            except Exception:
                pass

        # --- Standard: RTP/RTI for line chart; tooltips show actual dose only ---
        days = get_days(getattr(entry, 'duration_text', ''))
        y_val, actual_dose = compute_med_chart_value(entry.drug_name, entry.dose_mg, entry.frequency or '', 'rtp')
        duration = max(1, days)
        for i in range(duration):
            d = v_date + timedelta(days=i)
            pts.append({
                'x': d.strftime('%Y-%m-%d'),
                'y': y_val,
                'actualDose': actual_dose,
                'detail': f"Freq: {entry.frequency}",
                'actualEntry': (i == 0)
            })
        return pts

    # 2. Gather Data (Separated by Chart)
    symptoms = {}
    meds = {}
    se = {}
    mse = {}
    scales = {}
    previous_symptom_names_lc = set()  # symptom names from earlier visits (for skipping onset/progression if same symptom)

    # Visit Details for Modal
    visit_details = {}
    stressors_data = []
    events_data = []
    substances_data = []

    for v in visits:
        v_date_str = v.date.strftime('%Y-%m-%d')
        
        for st in getattr(v, 'stressor_entries', []):
            stressors_data.append({
                'type': st.stressor_type, 'duration': st.duration or '', 'note': st.note or '',
                'date': calc_event_date(v.date, st.duration)
            })
        for me in getattr(v, 'major_events', []):
            events_data.append({
                'type': me.event_type, 'duration': me.duration or '', 'note': me.note or '',
                'date': calc_event_date(v.date, me.duration)
            })
        for su in getattr(v, 'substance_use_entries', []):
            # Life chart strip: compute start/end from Age at First Use + Current Status (see Life Chart Substance Strip Logic)
            patient_age = getattr(patient, 'age', None)
            age_first = getattr(su, 'age_at_first_use', None)
            current_status = (getattr(su, 'current_status', None) or '').strip()
            abstinent_since = getattr(su, 'abstinent_since', None)

            start_str = None
            end_str = None

            if age_first is not None and patient_age is not None and age_first < patient_age:
                years_before_visit = patient_age - age_first
                try:
                    start_date = v.date.replace(year=v.date.year - years_before_visit)
                    start_str = start_date.strftime('%Y-%m-%d')
                except ValueError:
                    pass
            if not start_str and su.start_date:
                start_str = su.start_date.strftime('%Y-%m-%d')
            if not start_str:
                dur = parse_duration(su.note or '')
                if dur:
                    start_str = (v.date - dur).strftime('%Y-%m-%d')
            if not start_str:
                start_str = v_date_str

            if current_status == 'Currently Abstinent' and abstinent_since:
                end_str = abstinent_since.strftime('%Y-%m-%d')
            if not end_str and su.end_date:
                end_str = su.end_date.strftime('%Y-%m-%d')
            if not end_str:
                end_str = v_date_str

            substances_data.append({
                'substance': su.substance_name,
                'pattern': su.pattern or 'Occasional',
                'start_date': start_str,
                'end_date': end_str,
                'note': su.note or ''
            })

        # Build Modal Data
        visit_details[v_date_str] = {
            'date': v_date_str,
            'clinical_state': getattr(v, 'clinical_state', ''),
            'medication_adherence': getattr(v, 'medication_adherence', ''),
            'symptoms': [{'name': s.symptom_name, 'score': s.score_current, 'note': s.note} for s in v.symptom_entries],
            'meds': [{'name': m.drug_name, 'dose': m.dose_mg, 'freq': m.frequency, 'is_tapering': m.is_tapering, 'taper_plan': m.taper_plan} for m in v.medication_entries],
            'se': [{'name': s.side_effect_name, 'score': s.score_current} for s in v.side_effect_entries],
            'mse': [{'cat': m.category, 'name': m.finding_name, 'score': m.score_current} for m in v.mse_entries],
            'scales': [{'name': sa.scale_name, 'score': sa.total_score, 'label': sa.severity_label} for sa in getattr(v, 'scale_assessments', [])],
            'stressors': [{'type': st.stressor_type, 'duration': st.duration, 'note': st.note} for st in getattr(v, 'stressor_entries', [])],
            'events': [{'type': me.event_type, 'duration': me.duration, 'note': me.note} for me in getattr(v, 'major_events', [])]
        }

        # Symptom: skip onset/progression if this symptom already existed in a previous visit (case-insensitive, partial match > 85%)
        for s in v.symptom_entries:
            if s.symptom_name not in symptoms: symptoms[s.symptom_name] = []
            seen_in_previous = any(_symptom_name_matches(s.symptom_name, prev) for prev in previous_symptom_names_lc)
            symptoms[s.symptom_name].extend(build_clinical_points(s, v.date, 'Symptom', skip_onset_progression=seen_in_previous))
        for s in v.symptom_entries:
            previous_symptom_names_lc.add(s.symptom_name)

        for m in v.medication_entries:
            if m.drug_name not in meds: meds[m.drug_name] = []
            meds[m.drug_name].extend(build_med_points(m, v.date))
            
        for s in v.side_effect_entries:
            if s.side_effect_name not in se: se[s.side_effect_name] = []
            se[s.side_effect_name].extend(build_clinical_points(s, v.date, 'Side Effect'))
            
        for m in v.mse_entries:
            # Use Finding Name as key for individual lines
            label = m.finding_name if m.finding_name else m.category
            if label not in mse: mse[label] = []
            mse[label].extend(build_clinical_points(m, v.date, f"MSE ({m.category})"))

        for sa in getattr(v, 'scale_assessments', []):
            if sa.scale_name not in scales:
                scales[sa.scale_name] = []
            scales[sa.scale_name].append({
                'x': v_date_str,
                'y': sa.total_score,
                'detail': sa.severity_label,
                'phase': 'Current'
            })

    # 3. Format Function (Calculates Phase for Unified Lines)
    def calculate_unified(data_map, label, color):
        daily_sums = {}
        daily_counts = {}
        
        # Determine all points contributing to unified
        for item_points in data_map.values():
            for p in item_points:
                date_key = p['x']
                daily_sums[date_key] = daily_sums.get(date_key, 0) + p['y']
                daily_counts[date_key] = daily_counts.get(date_key, 0) + 1
        
        if not daily_sums: return None
        
        unified_points = []
        for k, v in daily_sums.items():
            avg = v / daily_counts[k]
            # Create breakdown for tooltip
            breakdown = []
            is_current = False
            actual_entry = False
            for name, points in data_map.items():
                for pt in points:
                    if pt['x'] == k:
                        breakdown.append({'name': name, 'score': pt['y'], 'actualDose': pt.get('actualDose')})
                        if pt.get('phase') == 'Current':
                            is_current = True
                        if pt.get('actualEntry'):
                            actual_entry = True
            unified_points.append({
                'x': k,
                'y': avg,
                'detail': 'Average',
                'breakdown': breakdown,
                'phase': 'Current' if is_current else 'History',
                'actualEntry': actual_entry
            })
            
        unified_points.sort(key=lambda p: p['x'])

        return {
            "label": label,
            "data": unified_points,
            "borderColor": color,
            "backgroundColor": "white",
            "pointBorderColor": color,
            "borderWidth": 4,
            "fill": False,
            "pointRadius": 2,
            "pointHoverRadius": 4,
            "pointHitRadius": 6,
            "tension": 0.4,
            "isUnified": True
        }

    def build_dataset(data_map, prefix):
        datasets = []
        colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#e6194b', '#3cb44b', '#ffe119', '#4363d8']
        for i, (label, points) in enumerate(data_map.items()):
            datasets.append({
                'label': label,
                'data': sorted(points, key=lambda x: x['x']),
                'borderColor': colors[i % len(colors)],
                'backgroundColor': colors[i % len(colors)],
                'fill': False,
                'tension': 0.2,
                'hidden': True
            })
        return datasets

    # 4. Clinical State and Adherence Ranges (for annotation bands) — stored per patient
    clinical_states = []
    adherences = []
    pid = patient.id if patient else None
    if pid:
        for s in ClinicalStateRange.query.filter_by(patient_id=pid).all():
            clinical_states.append({
                'state': s.state,
                'start': s.start_date.strftime('%Y-%m-%d') if s.start_date else None,
                'end': s.end_date.strftime('%Y-%m-%d') if s.end_date else None
            })
        for a in AdherenceRange.query.filter_by(patient_id=pid).all():
            adherences.append({
                'status': a.status,
                'start': a.start_date.strftime('%Y-%m-%d') if a.start_date else None,
                'end': a.end_date.strftime('%Y-%m-%d') if a.end_date else None
            })

    # 5. Render
    return render_template(
        'life_chart.html',
        patient=patient,
        visit=target_visit,  # Pass the target visit for context-aware form
        today=date.today(),
        guest=session.get('role') == 'guest',
        
        # Data for Charts
        symptom_datasets=build_dataset(symptoms, "symptom"),
        medication_datasets=build_dataset(meds, "med"),
        side_effect_datasets=build_dataset(se, "se"),
        mse_datasets=build_dataset(mse, "mse"),
        scale_datasets=build_dataset(scales, "scale"),

        # Unified Lines
        symptom_unified=calculate_unified(symptoms, "Unified Symptoms (Avg)", "black"),
        med_unified=calculate_unified(meds, "Unified Meds (Avg)", "black"),
        se_unified=calculate_unified(se, "Unified SE (Avg)", "black"),
        mse_unified=calculate_unified(mse, "Unified MSE (Avg)", "black"),
        scale_unified=calculate_unified(scales, "Unified Scales (Avg)", "black"),

        # Lists for Sidebar Checklists
        symptom_names=list(symptoms.keys()),
        med_names=list(meds.keys()),
        se_names=list(se.keys()),
        mse_categories=list(mse.keys()),
        scale_names=list(scales.keys()),
        
        visit_details=visit_details,
        clinical_states=clinical_states,
        adherences=adherences,
        stressors=stressors_data,
        events=events_data,
        substances=substances_data
    )


@app.route('/life_chart/export/<int:patient_id>')
@login_required
def preview_lifechart(patient_id):
    """Preview/Export Life Chart with date range and visible datasets filter."""
    patient = Patient.query.get_or_404(patient_id)
    
    start_str = request.args.get('start')
    end_str = request.args.get('end')
    # Use unquote to handle special characters in drug names
    visible_labels_str = unquote(request.args.get('visible', ''))
    
    try:
        start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
    except:
        start_date = date.today() - timedelta(days=365)
        end_date = date.today()

    # Fetch Data (Filter visits by date range for efficiency)
    visits = Visit.query.filter(
        Visit.patient_id == patient.id,
        Visit.date >= start_date,
        Visit.date <= end_date
    ).order_by(Visit.date).all()

    # Helper functions (same as life_chart route)
    def get_days(dur_str):
        if not dur_str: return 0
        d = parse_duration(dur_str)
        return d.days if d else 0

    def build_clinical_points(entry, v_date, type_lbl):
        pts = []
        dur_text = getattr(entry, 'duration_text', None) or getattr(entry, 'duration', None) or ''
        days = get_days(dur_text)
        has_onset_or_prog = (hasattr(entry, 'score_onset') and entry.score_onset is not None) or (hasattr(entry, 'score_progression') and entry.score_progression is not None)
        if days <= 0 and has_onset_or_prog:
            days = 14
        if days > 0:
            start = v_date - timedelta(days=days)
            if hasattr(entry, 'score_onset') and entry.score_onset is not None:
                pts.append({'x': start.strftime('%Y-%m-%d'), 'y': float(entry.score_onset), 'phase': 'Onset'})
            if hasattr(entry, 'score_progression') and entry.score_progression is not None:
                mid = start + timedelta(days=days // 2)
                pts.append({'x': mid.strftime('%Y-%m-%d'), 'y': float(entry.score_progression), 'phase': 'Progression'})
        if hasattr(entry, 'score_current') and entry.score_current is not None:
            pts.append({'x': v_date.strftime('%Y-%m-%d'), 'y': float(entry.score_current), 'phase': 'Current'})
        elif hasattr(entry, 'score') and entry.score is not None:
            pts.append({'x': v_date.strftime('%Y-%m-%d'), 'y': float(entry.score), 'phase': 'Current'})
        return pts

    def build_med_points(entry, v_date):
        pts = []
        drug_name = getattr(entry, 'drug_name', '')

        if getattr(entry, 'is_tapering', False) and getattr(entry, 'taper_plan', None):
            try:
                plan = json.loads(entry.taper_plan)
                current_date = v_date
                for step in plan:
                    days = get_days(step.get('duration_text', ''))
                    y_val, actual_dose = compute_med_chart_value(drug_name, step.get('dose_mg', ''), step.get('frequency', ''), 'rtp')
                    duration = max(1, days)
                    for i in range(duration):
                        d = current_date + timedelta(days=i)
                        pts.append({
                            'x': d.strftime('%Y-%m-%d'),
                            'y': y_val,
                            'actualDose': actual_dose,
                            'detail': f"Freq: {step.get('frequency', '')} (Tapering)",
                            'actualEntry': (i == 0)
                        })
                    current_date += timedelta(days=duration)
                return pts
            except Exception:
                pass

        days = get_days(getattr(entry, 'duration_text', ''))
        y_val, actual_dose = compute_med_chart_value(drug_name, getattr(entry, 'dose_mg', ''), getattr(entry, 'frequency', '') or '', 'rtp')
        duration = max(1, days)
        for i in range(duration):
            d = v_date + timedelta(days=i)
            pts.append({
                'x': d.strftime('%Y-%m-%d'),
                'y': y_val,
                'actualDose': actual_dose,
                'detail': f"Freq: {getattr(entry, 'frequency', '')}",
                'actualEntry': (i == 0)
            })
        return pts

    # Build data maps from visits
    symptoms = {}
    meds = {}
    se = {}
    mse = {}
    scales = {}

    for visit in visits:
        for s in visit.symptom_entries:
            if s.symptom_name not in symptoms:
                symptoms[s.symptom_name] = []
            symptoms[s.symptom_name].extend(build_clinical_points(s, visit.date, 'Symptom'))
            
        for m in visit.medication_entries:
            if m.drug_name not in meds:
                meds[m.drug_name] = []
            meds[m.drug_name].extend(build_med_points(m, visit.date))
            
        for s in visit.side_effect_entries:
            if s.side_effect_name not in se:
                se[s.side_effect_name] = []
            se[s.side_effect_name].extend(build_clinical_points(s, visit.date, 'Side Effect'))
            
        for m in visit.mse_entries:
            label = m.finding_name if m.finding_name else m.category
            if label not in mse:
                mse[label] = []
            mse[label].extend(build_clinical_points(m, visit.date, f"MSE ({m.category})"))

        for sa in getattr(visit, 'scale_assessments', []):
            if sa.scale_name not in scales:
                scales[sa.scale_name] = []
            scales[sa.scale_name].append({
                'x': visit.date.strftime('%Y-%m-%d'),
                'y': float(sa.total_score),
                'phase': 'Current'
            })

    # Initialize Grouping Dictionary (Order determines Chart Order)
    grouped_data = {
        'Symptoms': [],
        'Medications': [],
        'Side Effects': [],
        'MSE Findings': [],
        'Scale Assessments': []
    }

    # Helper to Populate Groups
    # CRITICAL FIX: keys must match what build_dataset expects ("symptom", "mse", "se", "med")
    def build_dataset(data_map, prefix):
        datasets = []
        colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#e6194b', '#3cb44b', '#ffe119', '#4363d8']
        for i, (label, points) in enumerate(data_map.items()):
            datasets.append({
                'label': label,
                'data': sorted(points, key=lambda x: x['x']),
                'borderColor': colors[i % len(colors)],
                'backgroundColor': colors[i % len(colors)],
                'fill': False,
                'tension': 0.2,
                'hidden': False
            })
        return datasets

    def add_to_group(data, type_key, category):
        datasets = build_dataset(data, type_key)
        for ds in datasets:
            ds['category'] = category
            grouped_data[category].append(ds)

    # Execute Mapping (Recommended Order: Symptoms -> Meds -> Side Effects -> MSE -> Scales)
    add_to_group(symptoms, "symptom", "Symptoms")
    add_to_group(meds, "med", "Medications")      # Moved Meds up
    add_to_group(se, "se", "Side Effects")
    add_to_group(mse, "mse", "MSE Findings")
    add_to_group(scales, "scale", "Scale Assessments")

    # Filter by Label
    if visible_labels_str:
        visible_labels = set(x.strip() for x in visible_labels_str.split(','))
        
        for cat in grouped_data:
            # Only keep datasets where the label matches a checked item
            grouped_data[cat] = [
                d for d in grouped_data[cat] 
                if d['label'] in visible_labels
            ]

    doc = getattr(patient, 'doctor', None)
    doctor_display = (doc.full_name or getattr(doc, 'username', '')) if doc else ''
    return render_template(
        'preview_lifechart.html',
        patient=patient,
        doctor_display=doctor_display,
        grouped_datasets=grouped_data,
        start_date=start_date,
        end_date=end_date
    )


@app.route('/guest/preview_lifechart')
def guest_preview_lifechart():
    token = request.args.get('token')
    if not token:
        abort(404)
    entry = GuestShare.query.filter_by(token=token).first()
    if not entry or entry.is_expired():
        abort(404)

    data = json.loads(entry.data_json)
    start_str = request.args.get('start')
    end_str = request.args.get('end')
    try:
        start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        start_date = date.today() - timedelta(days=365)
        end_date = date.today()

    guest_patient = {
        "name": data.get('patient', {}).get('name', 'Guest Patient'),
        "age": data.get('patient', {}).get('age', ''),
        "sex": data.get('patient', {}).get('sex', '')
    }
    guest_doctor = data.get('doctor', {"name": "Doctor"})

    # Build grouped_datasets from stored JSON (same shape as preview_lifechart)
    def to_map(items, name_key='name'):
        m = {}
        for item in items:
            label = item.get(name_key) or item.get('cat', '')
            if not label:
                continue
            if label not in m:
                m[label] = []
            pt = {'x': item.get('date', ''), 'y': item.get('score', 0), 'phase': item.get('phase', 'Current')}
            if pt['x']:
                m[label].append(pt)
        return m

    symptoms = to_map(data.get('symptoms', []))
    mse = to_map(data.get('mse', []), 'cat')
    se = to_map(data.get('se', []))
    meds_raw = data.get('meds', [])
    meds = {}
    for item in meds_raw:
        label = item.get('name', '')
        if not label:
            continue
        if label not in meds:
            meds[label] = []
        d = item.get('date', '')
        try:
            y = float(item.get('dose', '0').split()[0]) if item.get('dose') else 0
        except Exception:
            y = 0
        if d:
            meds[label].append({'x': d[:10], 'y': y, 'phase': 'Current'})

    colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#e6194b', '#3cb44b', '#ffe119', '#4363d8']

    def build_dataset_list(data_map):
        out = []
        for i, (label, points) in enumerate(data_map.items()):
            out.append({
                'label': label,
                'data': sorted([p for p in points if p.get('x')], key=lambda x: x['x']),
                'borderColor': colors[i % len(colors)],
                'backgroundColor': colors[i % len(colors)],
                'fill': False,
                'tension': 0.2,
                'hidden': False
            })
        return out

    grouped_data = {
        'Symptoms': build_dataset_list(symptoms),
        'Medications': build_dataset_list(meds),
        'Side Effects': build_dataset_list(se),
        'MSE Findings': build_dataset_list(mse),
        'Scale Assessments': []
    }
    visible_labels_str = unquote(request.args.get('visible', ''))
    if visible_labels_str:
        visible_labels = set(x.strip() for x in visible_labels_str.split(','))
        for cat in grouped_data:
            grouped_data[cat] = [d for d in grouped_data[cat] if d['label'] in visible_labels]

    doctor_display = (guest_doctor.get('name', '') if guest_doctor else '') or ''
    return render_template(
        'preview_lifechart.html',
        patient=guest_patient,
        doctor=guest_doctor,
        guest=True,
        guest_token=token,
        doctor_display=doctor_display,
        grouped_datasets=grouped_data,
        start_date=start_date,
        end_date=end_date
    )


@app.route('/preview_prescription/<int:visit_id>')
@login_required
def preview_prescription(visit_id):
    """Preview prescription before printing."""
    visit = Visit.query.get_or_404(visit_id)
    patient = visit.patient
    include_qr = request.args.get('include_qr') == 'true'

    # Chief complaints: chronological (longest duration first); follow-up: carried-over duration from previous visit
    previous_visit = Visit.query.filter(
        Visit.patient_id == visit.patient_id,
        Visit.date < visit.date
    ).order_by(Visit.date.desc()).first()
    previous_symptom_names = {s.symptom_name.strip().lower() for s in previous_visit.symptom_entries} if previous_visit else set()

    chief_complaints_sorted = []
    for s in visit.symptom_entries:
        name = s.symptom_name
        if previous_visit and name.strip().lower() in previous_symptom_names:
            delta = visit.date - previous_visit.date
            display_duration = format_timedelta_as_duration(delta)
            sort_days = delta.days
        else:
            display_duration = s.duration_text or ''
            sort_days = duration_to_days(s.duration_text or '')
        chief_complaints_sorted.append({'name': name, 'duration_display': display_duration, 'sort_days': sort_days})
    chief_complaints_sorted.sort(key=lambda x: x['sort_days'], reverse=True)
    
    lifchart_url = None
    qr_image_b64 = None
    if include_qr:
        base_url = request.url_root.rstrip('/')
        lifchart_url = f"{base_url}/life_chart/{patient.id}"
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(lifchart_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        qr_image_b64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
    
    return render_template('preview_prescription.html', 
                         patient=patient, 
                         visit=visit, 
                         chief_complaints_sorted=chief_complaints_sorted,
                         lifchart_url=lifchart_url,
                         qr_image_b64=qr_image_b64)


def generate_prescription_pdf(visit_id, include_qr=False):
    """Generate PDF prescription."""
    visit = Visit.query.get_or_404(visit_id)
    patient = visit.patient
    doctor = patient.doctor  # Get doctor details
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, 
                           rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=18)
    
    story = []
    styles = getSampleStyleSheet()
    
    # Header - Use Doctor's Clinic Name
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#000000'),
        alignment=TA_CENTER,
        spaceAfter=12
    )
    header_text = doctor.clinic_name if doctor and doctor.clinic_name else ""
    sub_text = doctor.address_text if doctor and doctor.address_text else ""
    story.append(Paragraph(header_text, header_style))
    story.append(Paragraph(sub_text, styles['Normal']))
    story.append(Spacer(1, 12))
    
    # Patient Info
    patient_data = [
        ['Name:', patient.name],
        ['Age:', str(patient.age)],
        ['Sex:', patient.sex],
        ['Date:', visit.date.strftime('%d-%b-%Y')]
    ]
    patient_table = Table(patient_data, colWidths=[2*inch, 4*inch])
    patient_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(patient_table)
    story.append(Spacer(1, 20))
    
    # Medications
    story.append(Paragraph("Rx", styles['Heading2']))
    med_data = [['Sl.No', 'Generic/Brand Name', 'Dose', 'Frequency', 'Duration']]
    for idx, med in enumerate(visit.medication_entries, 1):
        drug_display = med.drug_name
        if med.drug_type:
            if med.drug_type == 'Generic':
                drug_display = f"{med.drug_name} (Gen)"
            else:
                drug_display = med.drug_name
        med_data.append([
            str(idx),
            drug_display,
            med.dose_mg or '-',
            format_frequency(med.frequency) or med.note or '-',
            med.duration_text or '-'
        ])
    
    med_table = Table(med_data, colWidths=[0.5*inch, 2.5*inch, 1*inch, 1.5*inch, 1.5*inch])
    med_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(med_table)
    story.append(Spacer(1, 20))
    
    # QR Code if requested
    if include_qr:
        base_url = request.url_root.rstrip('/')
        lifchart_url = f"{base_url}/life_chart/{patient.id}"
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(lifchart_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        qr_image = Image(img_buffer, width=2*inch, height=2*inch)
        story.append(Spacer(1, 20))
        story.append(Paragraph("Scan to view Life Chart", styles['Normal']))
        story.append(qr_image)
    
    doc.build(story)
    buffer.seek(0)
    return buffer

@app.route('/guest/start')
def start_guest():
    session.clear()
    session.pop('guest_token', None)
    session['guest'] = True
    session['role'] = 'guest'
    session['guest_first_visit'] = True
    flash('Guest mode enabled. Data will not be saved.', 'info')
    return redirect(url_for('first_visit'))
    
@app.route('/guest/first_visit')
def guest_first_visit():
    if not session.get('guest'):
        abort(403)
    return render_template('guest_first_visit.html')
    
@app.route('/guest/prescription', methods=['POST'])
def guest_prescription():
    if not session.get('guest'):
        abort(403)

    # 1. Capture Doctor Details (same modal fields as guest_both)
    guest_doctor = {
        "name": request.form.get("doc_name", "Doctor"),
        "qualification": request.form.get("doc_qual", ""),
        "registration": request.form.get("doc_reg", ""),
        "clinic": request.form.get("doc_clinic", ""),
        "address": request.form.get("doc_address", ""),
        "phone": request.form.get("doc_phone", ""),
        "email": request.form.get("doc_email", ""),
        "social": request.form.get("doc_social", "")
    }

    signature_b64 = session.get('guest_signature_b64', '')
    sig_file = request.files.get('doc_signature')
    if sig_file and sig_file.filename != '':
        signature_b64 = base64.b64encode(sig_file.read()).decode('utf-8')
        session['guest_signature_b64'] = signature_b64

    # 2. Capture Patient Details
    guest_patient = {
        "name": request.form.get("patient_name", "Guest Patient"),
        "age": request.form.get("patient_age") or request.form.get("age", ""),
        "sex": request.form.get("patient_sex") or request.form.get("sex", ""),
        "address": request.form.get("patient_address") or request.form.get("address", "")
    }

    # Safely convert follow-up string to Date object
    fu_date_str = request.form.get('follow_up_date')
    fu_date = None
    if fu_date_str:
        try:
            fu_date = datetime.strptime(fu_date_str, '%Y-%m-%d').date()
        except Exception:
            pass

    # 3. Build Temp Visit (native date objects + keys matching preview_prescription.html)
    visit = {
        "id": "Guest",
        "date": get_ist_now().date(),
        "chief_complaints": request.form.get('chief_complaints', ''),
        "provisional_diagnosis": request.form.get('provisional_diagnosis', ''),
        "differential_diagnosis": request.form.get('differential_diagnosis', ''),
        "next_visit_date": fu_date,
        "type_of_next_follow_up": request.form.get('type_of_next_follow_up', ''),
        "safety_profile": None,
        "note": request.form.get('visit_note') or request.form.get('note', ''),
        "symptom_entries": [],
        "side_effect_entries": [],
        "mse_entries": [],
        "medication_entries": []
    }

    drug_names = request.form.getlist('drug_name[]')
    dose_mgs = request.form.getlist('dose_full[]') or request.form.getlist('dose_mg[]')
    d_freqs = request.form.getlist('frequency[]')
    durations = request.form.getlist('med_duration_text[]') or request.form.getlist('med_duration[]')
    med_notes = request.form.getlist('med_note[]')
    d_forms = request.form.getlist('med_form[]')

    for i, name in enumerate(drug_names):
        name_s = (name or '').strip()
        dose_s = (dose_mgs[i] if i < len(dose_mgs) else '').strip()
        dur_s = (durations[i] if i < len(durations) else '').strip()
        if not name_s and not dose_s and not dur_s:
            continue
        if name_s:
            visit["medication_entries"].append({
                'drug_name': name_s,
                'drug_type': 'Generic',
                'dose_mg': dose_mgs[i] if i < len(dose_mgs) else '',
                'frequency': d_freqs[i] if i < len(d_freqs) else '',
                'duration_text': durations[i] if i < len(durations) else '',
                'note': med_notes[i] if i < len(med_notes) else '',
                'form_type': d_forms[i] if i < len(d_forms) else 'Tablet',
                'is_tapering': False,
                'taper_plan': None
            })

    session.pop('guest_first_visit', None)

    return render_template(
        "preview_prescription.html",
        guest=True,
        patient=None,
        guest_patient=guest_patient,
        visit=visit,
        guest_doctor=guest_doctor,
        guest_signature_b64=signature_b64
    )

@app.route('/guest/both', methods=['POST'])
def guest_both():
    if not session.get('guest'):
        abort(403)

    token = session.get('guest_token')
    if request.form.get('is_chart_update') == 'true' and token:
        return update_guest_share(token, redirect_to_prescription=True)

    # 1. Cleanup Old Links
    try:
        GuestShare.query.filter(GuestShare.expires_at < get_ist_now()).delete()
        db.session.commit()
    except Exception:
        db.session.rollback()

    # 2. Capture Basic Info
    guest_doctor = {
        "name": request.form.get("doc_name", "Doctor"),
        "qualification": request.form.get("doc_qual", ""),
        "registration": request.form.get("doc_reg", ""),
        "clinic": request.form.get("doc_clinic", ""),
        "address": request.form.get("doc_address", ""),
        "phone": request.form.get("doc_phone", ""),
        "email": request.form.get("doc_email", ""),
        "social": request.form.get("doc_social", "")
    }

    signature_b64 = session.get('guest_signature_b64', '')
    sig_file = request.files.get('doc_signature')
    if sig_file and sig_file.filename != '':
        signature_b64 = base64.b64encode(sig_file.read()).decode('utf-8')
        session['guest_signature_b64'] = signature_b64

    guest_patient = {
        "name": request.form.get("patient_name", "Guest Patient"),
        "age": request.form.get("patient_age") or request.form.get("age", ""),
        "sex": request.form.get("patient_sex") or request.form.get("sex", ""),
        "address": request.form.get("patient_address") or request.form.get("address", "")
    }

    # --- 3. ROBUST DATA CAPTURE (With DATES & NOTES) ---
    now_ist = get_ist_now()
    today = now_ist.date()
    today_iso = now_ist.isoformat()

    # A. Symptoms (Now with Duration Calc)
    symptoms = []
    names = request.form.getlist('symptom_name[]')
    onsets = request.form.getlist('symptom_onset[]')
    progressions = request.form.getlist('symptom_progression[]')
    currents = request.form.getlist('symptom_current[]')
    sym_notes = request.form.getlist('symptom_note[]')
    durations = request.form.getlist('duration_text[]') or request.form.getlist('symptom_duration[]')

    for i, name in enumerate(names):
        dur_text = durations[i] if i < len(durations) else ""
        if not (name or "").strip() and not (dur_text or "").strip():
            continue
        
        # 1. Scores
        def safe_int(val_list, idx, default=5):
            try: return int(val_list[idx]) if idx < len(val_list) else default
            except (ValueError, TypeError): return default

        onset = safe_int(onsets, i)
        prog = safe_int(progressions, i)
        curr = safe_int(currents, i)
        note = sym_notes[i] if i < len(sym_notes) else ""
        
        # 2. Date Calculation (Crucial for Unified Charts)
        # Use existing utility or default to 14 days
        try:
            delta = parse_duration(dur_text) if dur_text else timedelta(days=14)
        except:
            delta = timedelta(days=14)
            
        d_onset = today - delta
        # Calculate midpoint date for progression
        total_days = (today - d_onset).days
        d_prog = d_onset + timedelta(days=total_days // 2)
        
        # 3. Save with Explicit Dates
        symptoms.append({
            "name": name, "score": onset, "phase": "Onset", 
            "note": note, "date": d_onset.isoformat()
        })
        symptoms.append({
            "name": name, "score": prog, "phase": "Progression", 
            "note": note, "date": d_prog.isoformat()
        })
        symptoms.append({
            "name": name, "score": curr, "phase": "Current",
            "note": note, "date": today_iso, "duration": dur_text
        })

    def safe_float(val_list, idx, default=None):
        try:
            v = val_list[idx] if idx < len(val_list) else None
            return float(v) if v not in (None, '') else default
        except (ValueError, TypeError):
            return default

    # B. MSE Findings (Onset & Progression)
    mse = []
    mse_cats = request.form.getlist('mse_category[]')
    mse_findings = request.form.getlist('mse_finding_name[]')
    mse_onsets = request.form.getlist('mse_onset[]')
    mse_progs = request.form.getlist('mse_progression[]')
    mse_currs = request.form.getlist('mse_current[]') or request.form.getlist('mse_score[]')
    mse_notes = request.form.getlist('mse_note[]')
    mse_durs = request.form.getlist('mse_duration[]')

    for i, cat in enumerate(mse_cats):
        finding_name = (mse_findings[i] if i < len(mse_findings) else "").strip()
        if not cat or not finding_name:
            continue
        onset = safe_float(mse_onsets, i)
        prog = safe_float(mse_progs, i)
        curr = safe_float(mse_currs, i, 0.0)
        note = mse_notes[i] if i < len(mse_notes) else ""
        dur_text = mse_durs[i] if i < len(mse_durs) else ""
        try:
            delta = parse_duration(dur_text) if dur_text else timedelta(days=14)
        except Exception:
            delta = timedelta(days=14)
        d_onset = now_ist - delta
        d_prog = d_onset + timedelta(days=(now_ist - d_onset).days // 2)
        if onset is not None:
            mse.append({"cat": cat, "name": finding_name, "score": onset, "phase": "Onset", "note": note, "date": d_onset.isoformat()})
        if prog is not None:
            mse.append({"cat": cat, "name": finding_name, "score": prog, "phase": "Progression", "note": note, "date": d_prog.isoformat()})
        mse.append({"cat": cat, "name": finding_name, "score": curr, "phase": "Current", "note": note, "date": today_iso})

    # C. Medications (Upgraded for Tapering & Duration support)
    meds_chart = []
    drug_names = request.form.getlist('drug_name[]')
    dose_mgs = request.form.getlist('dose_full[]') or request.form.getlist('dose_mg[]')
    d_freqs = request.form.getlist('frequency[]')
    d_durs = request.form.getlist('med_duration[]') or request.form.getlist('med_duration_text[]')
    med_notes = request.form.getlist('med_note[]')
    d_forms = request.form.getlist('med_form[]')

    last_med = None
    for i, name in enumerate(drug_names):
        dose_str = dose_mgs[i] if i < len(dose_mgs) else ""
        dur = d_durs[i] if i < len(d_durs) else ""
        if not (name or "").strip() and not (dose_str or "").strip() and not (dur or "").strip():
            continue
        dose_str = dose_str or ""
        dur = dur or ""
        freq = d_freqs[i] if i < len(d_freqs) else ""
        note = med_notes[i] if i < len(med_notes) else ""
        score_val = 0.0
        if dose_str:
            nums = re.findall(r"[-+]?\d*\.\d+|\d+", dose_str)
            if nums:
                score_val = float(nums[0])
        if last_med and last_med["name"].strip().lower() == (name or "").strip().lower():
            if (dose_str.strip() or dur.strip()):
                last_med["is_tapering"] = True
                if not last_med.get("taper_plan"):
                    last_med["taper_plan"] = [{
                        "dose_mg": last_med["dose"],
                        "frequency": last_med.get("frequency", ""),
                        "duration_text": last_med.get("duration", ""),
                        "note": last_med.get("note", "")
                    }]
                last_med["taper_plan"].append({
                    "dose_mg": dose_str,
                    "frequency": freq,
                    "duration_text": dur,
                    "note": note
                })
        elif (name or "").strip():
            new_med = {
                "name": (name or "").strip(),
                "score": score_val,
                "phase": "Current",
                "dose": dose_str,
                "frequency": freq,
                "duration": dur,
                "note": note,
                "date": today_iso,
                "is_tapering": False,
                "taper_plan": None,
                "form_type": d_forms[i] if i < len(d_forms) else 'Tablet'
            }
            meds_chart.append(new_med)
            last_med = new_med

    # D. Side Effects (Onset & Progression)
    se_chart = []
    se_names = request.form.getlist('side_effect_name[]')
    se_onsets = request.form.getlist('side_effect_onset[]')
    se_progs = request.form.getlist('side_effect_progression[]')
    se_currs = request.form.getlist('side_effect_current[]') or request.form.getlist('side_effect_score[]')
    se_notes = request.form.getlist('side_effect_note[]')
    se_durs = request.form.getlist('side_effect_duration[]')

    for i, name in enumerate(se_names):
        dur_text = se_durs[i] if i < len(se_durs) else ""
        if not (name or "").strip() and not (dur_text or "").strip():
            continue
        name = (name or "").strip()
        if name:
            onset = safe_float(se_onsets, i)
            prog = safe_float(se_progs, i)
            curr = safe_float(se_currs, i, 0.0)
            note = se_notes[i] if i < len(se_notes) else ""
            dur_text = se_durs[i] if i < len(se_durs) else ""
            try:
                delta = parse_duration(dur_text) if dur_text else timedelta(days=14)
            except Exception:
                delta = timedelta(days=14)
            d_onset = now_ist - delta
            d_prog = d_onset + timedelta(days=(now_ist - d_onset).days // 2)
            if onset is not None:
                se_chart.append({"name": name, "score": onset, "phase": "Onset", "note": note, "date": d_onset.isoformat()})
            if prog is not None:
                se_chart.append({"name": name, "score": prog, "phase": "Progression", "note": note, "date": d_prog.isoformat()})
            se_chart.append({"name": name, "score": curr, "phase": "Current", "note": note, "date": today_iso, "duration": dur_text})

    # 4. Save to DB (session-aware token reuse)
    patient_details = {
        "name": request.form.get('patient_name', 'Guest Patient'),
        "age": request.form.get('age', '') or request.form.get('patient_age', ''),
        "sex": request.form.get('sex', '') or request.form.get('patient_sex', ''),
        "address": request.form.get('address', '') or request.form.get('patient_address', ''),
        "date": today_iso
    }
    doctor_details = {
        "name": request.form.get('doc_name', 'Doctor'),
        "qualification": request.form.get('doc_qual', ''),
        "registration": request.form.get('doc_reg', ''),
        "clinic": request.form.get('doc_clinic', ''),
        "address": request.form.get('doc_address', ''),
        "phone": request.form.get('doc_phone', ''),
        "email": request.form.get('doc_email', ''),
        "social": request.form.get('doc_social', '')
    }
    sig_b64 = session.get('guest_signature_b64', '')
    sig_file = request.files.get('doc_signature')
    if sig_file and sig_file.filename != '':
        sig_b64 = base64.b64encode(sig_file.read()).decode('utf-8')
        session['guest_signature_b64'] = sig_b64

    chart_data = {
        "patient": patient_details,
        "doctor": doctor_details,
        "signature_b64": sig_b64,
        "chief_complaints": request.form.get('chief_complaints', ''),
        "stressors": request.form.get('stressors_data', ''),
        "personality": request.form.get('personality_data', ''),
        "major_events": request.form.get('major_events_data', ''),
        "scales": request.form.get('scales_data', ''),
        "substance_use": request.form.get('substance_use_data', ''),
        "adherence": request.form.get('adherence_data', ''),
        "provisional_diagnosis": request.form.get('provisional_diagnosis', ''),
        "differential_diagnosis": request.form.get('differential_diagnosis', ''),
        "follow_up_date": request.form.get('follow_up_date', ''),
        "note": request.form.get('visit_note') or request.form.get('note', ''),
        "symptoms": symptoms,
        "mse": mse,
        "meds": meds_chart,
        "se": se_chart
    }

    token = session.get('guest_token')
    share_entry = None

    if token:
        share_entry = GuestShare.query.filter_by(token=token).first()
        if share_entry and share_entry.is_expired():
            share_entry = None

    expiry = get_ist_now() + timedelta(minutes=30)

    if share_entry:
        share_entry.data_json = json.dumps(chart_data)
        share_entry.expires_at = expiry
    else:
        token = str(uuid.uuid4())
        session['guest_token'] = token
        share_entry = GuestShare(
            token=token,
            data_json=json.dumps(chart_data),
            expires_at=expiry,
            created_at=get_ist_now()
        )
        db.session.add(share_entry)

    db.session.commit()

    lifchart_url = f"{request.url_root.rstrip('/')}/guest/share/{token}"

    # 5. Build Visit for Prescription PDF
    current_symps = [{"symptom_name": s.get("name", ""), "duration_text": s.get("duration", "")} for s in symptoms if s.get("phase") == "Current"]
    current_ses = [{"side_effect_name": s.get("name", ""), "duration_text": s.get("duration", "")} for s in se_chart if s.get("phase") == "Current"]
    current_mses = [{"category": m.get("cat", ""), "finding_name": m.get("name", "")} for m in mse if m.get("phase") == "Current"]

    fu_date_str = request.form.get('follow_up_date')
    fu_date = None
    if fu_date_str:
        try:
            fu_date = datetime.strptime(fu_date_str, '%Y-%m-%d').date()
        except Exception:
            pass

    visit_obj = {
        "id": "Guest",
        "date": get_ist_now().date(),
        "provisional_diagnosis": request.form.get('provisional_diagnosis', ''),
        "differential_diagnosis": request.form.get('differential_diagnosis', ''),
        "next_visit_date": fu_date,
        "type_of_next_follow_up": request.form.get('type_of_next_follow_up', ''),
        "safety_profile": None,
        "note": request.form.get('visit_note') or request.form.get('note', ''),
        "symptom_entries": current_symps,
        "side_effect_entries": current_ses,
        "mse_entries": current_mses,
        "medication_entries": []
    }

    for med in meds_chart:
        visit_obj['medication_entries'].append({
            'drug_name': med.get('name', ''),
            'drug_type': 'Generic',
            'dose_mg': med.get('dose', ''),
            'frequency': med.get('frequency', ''),
            'duration_text': med.get('duration', ''),
            'note': med.get('note', ''),
            'form_type': med.get('form_type', 'Tablet'),
            'is_tapering': med.get('is_tapering', False),
            'taper_plan': json.dumps(med.get('taper_plan', [])) if med.get('taper_plan') else None
        })

    chief_complaints_sorted = []
    for s in current_symps:
        name = s.get("symptom_name", "")
        dur = s.get("duration_text", "")
        chief_complaints_sorted.append({"name": name, "duration_display": dur, "sort_days": duration_to_days(dur)})
    chief_complaints_sorted.sort(key=lambda x: x["sort_days"], reverse=True)
    chief_complaints_sorted = [{"name": x["name"], "duration_display": x["duration_display"]} for x in chief_complaints_sorted]

    session.pop('guest_first_visit', None)

    return render_template(
        "preview_prescription.html",
        visit=visit_obj,
        patient=None,
        guest=True,
        guest_patient=guest_patient,
        lifchart_url=lifchart_url,
        guest_doctor=guest_doctor,
        guest_signature_b64=signature_b64,
        chief_complaints_sorted=chief_complaints_sorted
    )


@app.route('/guest/share/<token>')
def guest_share_view(token):
    # 1. Validation
    entry = GuestShare.query.filter_by(token=token).first()
    if not entry: return "Link invalid", 404
    if entry.is_expired():
        db.session.delete(entry)
        db.session.commit()
        return "This link has expired (30 minute limit).", 410

    # 2. Unpack Data
    data = json.loads(entry.data_json)
    symptoms = data.get('symptoms', [])
    meds = data.get('meds', [])
    se = data.get('se', [])
    mse = data.get('mse', [])
    
    # 3. Sidebar Filters
    symptom_names = sorted(list(set(s['name'] for s in symptoms if 'name' in s)))
    med_names = sorted(list(set(m['name'] for m in meds if 'name' in m)))
    se_names = sorted(list(set(s['name'] for s in se if 'name' in s)))
    mse_categories = sorted(list(set(m['cat'] for m in mse if 'cat' in m)))

    # 4. Visit Details & Modal Logic
    visit_date_obj = get_ist_now().date()
    visit_date_str = visit_date_obj.isoformat()
    visit_id_str = "999"

    current_symptoms = [s for s in symptoms if s.get('phase') == 'Current']

    # JS expects string dates and dicts
    dummy_visit_js = {
        "id": "guest",
        "date": visit_date_str,
        "type": "First Visit (Guest)",
        "symptoms": current_symptoms,
        "mse": mse,
        "medication_entries": [],
        "meds": meds,
        "se": se,
        "chief_complaints": data.get('chief_complaints', ''),
        "provisional_diagnosis": data.get('provisional_diagnosis', ''),
        "differential_diagnosis": data.get('differential_diagnosis', ''),
        "follow_up_date": data.get('follow_up_date', ''),
        "notes": data.get('note', '')
    }

    # Jinja form expects Python date objects and 'medication_entries' mapping
    fu_date_str = data.get('follow_up_date')
    fu_date = None
    if fu_date_str:
        try:
            fu_date = datetime.strptime(fu_date_str, '%Y-%m-%d').date()
        except Exception:
            pass

    medication_entries = []
    for m in meds:
        taper_plan_json = None
        if m.get('is_tapering') and m.get('taper_plan'):
            taper_plan_json = json.dumps(m['taper_plan'])
        medication_entries.append({
            'drug_name': m.get('name', ''),
            'drug_type': m.get('drug_type', 'Generic'),
            'dose_mg': m.get('dose', ''),
            'frequency': m.get('frequency', ''),
            'duration_text': m.get('duration', ''),
            'note': m.get('note', ''),
            'form_type': m.get('form_type', 'Tablet'),
            'is_tapering': m.get('is_tapering', False),
            'taper_plan': taper_plan_json
        })

    form_visit = {
        "id": "guest",
        "date": visit_date_obj,
        "provisional_diagnosis": data.get('provisional_diagnosis', ''),
        "differential_diagnosis": data.get('differential_diagnosis', ''),
        "next_visit_date": fu_date,
        "note": data.get('note', ''),
        "medication_entries": medication_entries
    }

    # 5. Helper: Build Datasets (Using Explicit Dates)
    def build_dataset(items, label_prefix):
        datasets = {}
        offset_days = {"Onset": -14, "Progression": -7, "Current": 0}

        for item in items:
            label = item.get("name") or item.get("cat")
            phase = item.get("phase", "Current")

            if "date" in item:
                point_date = item["date"][:10]
            else:
                dt = datetime.strptime(visit_date_str, "%Y-%m-%d") + timedelta(days=offset_days.get(phase, 0))
                point_date = dt.strftime("%Y-%m-%d")

            if label not in datasets:
                datasets[label] = { "label": label, "data": [], "fill": False, "tension": 0.3 }

            datasets[label]["data"].append({
                "x": point_date,
                "y": item["score"],
                "phase": phase,
                "symptom_name": label,
                "visit_id": visit_id_str,
                "detail": item.get("note", ""),
                "reported_on": visit_date_str
            })

        return list(datasets.values())

    # 6. Helper: Calculate Unified Lines (GROUP BY DATE)
    def calculate_unified(items, label, color):
        if not items: return None

        offset_days = {"Onset": -14, "Progression": -7, "Current": 0}
        date_groups = {}

        for item in items:
            if "date" in item:
                d_key = item["date"][:10]
            else:
                phase = item.get("phase", "Current")
                dt = datetime.strptime(visit_date_str, "%Y-%m-%d") + timedelta(days=offset_days.get(phase, 0))
                d_key = dt.strftime("%Y-%m-%d")

            if d_key not in date_groups: date_groups[d_key] = []
            date_groups[d_key].append(item)

        unified_points = []
        for d_key, group_items in date_groups.items():
            avg = sum(i["score"] for i in group_items) / len(group_items)
            breakdown = [{"name": i.get("name") or i.get("cat"), "score": i["score"]} for i in group_items]
            phases = list(set(i.get("phase", "Current") for i in group_items))
            phase_label = phases[0] if len(phases) == 1 else "Mixed"

            unified_points.append({
                "x": d_key,
                "y": round(avg, 2),
                "phase": phase_label,
                "symptom_name": label,
                "visit_id": visit_id_str,
                "reported_on": visit_date_str,
                "breakdown": breakdown
            })

        unified_points.sort(key=lambda p: p['x'])

        return {
            "label": label,
            "data": unified_points,
            "borderColor": color,
            "backgroundColor": "white",
            "pointBorderColor": color,
            "borderWidth": 4,
            "fill": False,
            "pointRadius": 2,
            "pointHoverRadius": 4,
            "pointHitRadius": 6,
            "tension": 0.4,
            "isUnified": True
        }

    # 5b. Helper: Build Medication Lines (Day-by-Day Expansion)
    def build_med_dataset(meds_list):
        datasets = {}
        for item in meds_list:
            label = item.get("name")
            if not label:
                continue
            if label not in datasets:
                datasets[label] = {"label": label, "data": [], "fill": False, "tension": 0.1, "hidden": True}
            base_date = item.get("date", visit_date_str)
            v_date = datetime.strptime(base_date[:10], "%Y-%m-%d")
            if item.get("is_tapering") and item.get("taper_plan"):
                current_date = v_date
                for step in item["taper_plan"]:
                    dur_text = step.get("duration_text", "")
                    try:
                        days = parse_duration(dur_text).days if parse_duration(dur_text) else 0
                    except Exception:
                        days = 0
                    duration = max(1, days)
                    y_val, actual_dose = compute_med_chart_value(label, step.get("dose_mg", ""), step.get("frequency", ""), "rtp")
                    for j in range(duration):
                        d = current_date + timedelta(days=j)
                        datasets[label]["data"].append({
                            "x": d.strftime("%Y-%m-%d"),
                            "y": y_val,
                            "actualDose": actual_dose,
                            "detail": f"Freq: {step.get('frequency', '')} (Tapering)",
                            "phase": "Current"
                        })
                    current_date += timedelta(days=duration)
            else:
                dur_text = item.get("duration", "")
                try:
                    days = parse_duration(dur_text).days if parse_duration(dur_text) else 0
                except Exception:
                    days = 0
                duration = max(1, days)
                y_val, actual_dose = compute_med_chart_value(label, item.get("dose", ""), item.get("frequency", ""), "rtp")
                for j in range(duration):
                    d = v_date + timedelta(days=j)
                    datasets[label]["data"].append({
                        "x": d.strftime("%Y-%m-%d"),
                        "y": y_val,
                        "actualDose": actual_dose,
                        "detail": f"Freq: {item.get('frequency', '')}",
                        "phase": "Current"
                    })
        return list(datasets.values())

    # 6b. Helper: Calculate Unified Meds from the Expanded Lines
    def calculate_unified_meds(meds_datasets, label, color):
        if not meds_datasets:
            return None
        daily_sums = {}
        daily_counts = {}
        for ds in meds_datasets:
            for p in ds["data"]:
                dk = p["x"]
                daily_sums[dk] = daily_sums.get(dk, 0) + p["y"]
                daily_counts[dk] = daily_counts.get(dk, 0) + 1
        unified_points = []
        for k, v in daily_sums.items():
            unified_points.append({
                "x": k, "y": round(v / daily_counts[k], 2),
                "phase": "Current", "detail": "Average", "breakdown": []
            })
        unified_points.sort(key=lambda p: p['x'])
        return {
            "label": label, "data": unified_points, "borderColor": color,
            "backgroundColor": "white", "pointBorderColor": color,
            "borderWidth": 4, "fill": False, "pointRadius": 2, "isUnified": True
        }

    med_datasets_ready = build_med_dataset(meds)

    # 7. Render – pass stored patient so template can show name, age, sex, address
    saved_patient_data = data.get('patient', {})
    class DummyPatient:
        def __init__(self, d):
            self.name = d.get('name', 'Guest Patient')
            self.age = d.get('age', '')
            self.sex = d.get('sex', '')
            self.address = d.get('address', '')
    dummy_patient = DummyPatient(saved_patient_data)

    return render_template(
        'life_chart.html',
        guest=True,
        guest_token=token,
        patient=dummy_patient,
        visit=form_visit,
        guest_doctor=data.get('doctor', {}),
        guest_signature_b64=data.get('signature_b64', ''),
        adherence_ranges=AdherenceRange.query.all(),
        clinical_state_ranges=ClinicalStateRange.query.all(),

        symptom_datasets=build_dataset(symptoms, "symptom"),
        medication_datasets=med_datasets_ready,
        side_effect_datasets=build_dataset(se, "se"),
        mse_datasets=build_dataset(mse, "mse"),

        symptom_unified=calculate_unified(symptoms, "Unified Symptoms (Avg)", "rgba(0, 0, 0, 1)"),
        med_unified=calculate_unified_meds(med_datasets_ready, "Unified Meds (Avg)", "rgba(0, 0, 0, 1)"),
        se_unified=calculate_unified(se, "Unified SE (Avg)", "rgba(0, 0, 0, 1)"),
        mse_unified=calculate_unified(mse, "Unified MSE (Avg)", "rgba(0, 0, 0, 1)"),

        symptom_names=symptom_names,
        med_names=med_names,
        se_names=se_names,
        mse_categories=mse_categories,

        visit_details={visit_id_str: dummy_visit_js}
    )


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
