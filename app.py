"""
PsycheLife - Medical web app for psychiatric patient management.
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, make_response, session, abort
from functools import wraps
from datetime import datetime, date, timedelta, timezone
from models import db, Doctor, Patient, Visit, SymptomEntry, MedicationEntry, SideEffectEntry, MSEEntry, GuestShare, StressorEntry, PersonalityEntry, SafetyMedicalProfile, MajorEvent, AdherenceRange, ClinicalStateRange, DefaultTemplate, CustomTemplate, SubstanceUseEntry, ScaleAssessment
from medical_utils import get_unified_dose, calculate_start_date, parse_duration, calculate_midpoint_date, format_frequency, process_scale_submission
import io
import os
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import qrcode
from urllib.parse import urljoin, unquote
from werkzeug.utils import secure_filename
import base64
import uuid
import json
from sqlalchemy import text

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
basedir = os.path.abspath(os.path.dirname(__file__))

# Use absolute path for DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'psychelife.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Use absolute path for Uploads
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'static', 'signatures')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

os.makedirs(os.path.join(basedir, 'instance'), exist_ok=True)
db.init_app(app)

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

# --- Register Helper for Templates ---
@app.context_processor
def utility_processor():
    """Register utility functions for use in templates."""
    return dict(format_frequency=format_frequency)


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

@app.route('/guest/lifechart', methods=['GET', 'POST'])
@app.route('/guest/lifechart', methods=['GET', 'POST'])
def guest_lifechart():
    """
    Generate Life Chart for Guest Mode.
    Now uses the DB + Shared View (same as QR code) for a consis@app.route('/guest/lifechart', methods=['GET', 'POST'])
tent experience.
    """
    if not session.get('guest'):
        abort(403)

    # 1. Handle POST (Form Submission from Dashboard)
    if request.method == 'POST':
        # --- A. CLEANUP (Keep DB healthy) ---
        try:
            GuestShare.query.filter(GuestShare.expires_at < datetime.now(timezone.utc)).delete()
            db.session.commit()
        except Exception:
            db.session.rollback()

        # --- B. CAPTURE DATA (Exact logic from guest_both) ---
        today = date.today()
        
        # 1. Symptoms
        symptoms = []
        names = request.form.getlist('symptom_name[]')
        onsets = request.form.getlist('symptom_onset[]')
        progressions = request.form.getlist('symptom_progression[]')
        currents = request.form.getlist('symptom_current[]')
        sym_notes = request.form.getlist('symptom_note[]')
        durations = request.form.getlist('duration_text[]')

        for i, name in enumerate(names):
            if not name.strip(): continue
            
            # Helper for safe integers
            def safe_int(val_list, idx, default=5):
                try: return int(val_list[idx]) if idx < len(val_list) else default
                except (ValueError, TypeError): return default

            onset = safe_int(onsets, i)
            prog = safe_int(progressions, i)
            curr = safe_int(currents, i)
            note = sym_notes[i] if i < len(sym_notes) else ""
            
            # Date Calculation
            dur_text = durations[i] if i < len(durations) else ""
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
            symptoms.append({"name": name, "score": curr, "phase": "Current", "note": note, "date": today.isoformat()})

        # 2. MSE Findings
        mse = []
        mse_cats = request.form.getlist('mse_category[]')
        mse_scores = request.form.getlist('mse_score[]')
        mse_notes = request.form.getlist('mse_note[]')
        for i, (cat, score) in enumerate(zip(mse_cats, mse_scores)):
            try: val = int(score)
            except: val = 0
            note = mse_notes[i] if i < len(mse_notes) else ""
            mse.append({"cat": cat, "score": val, "note": note, "date": today.isoformat()})

        # 3. Medications
        meds_chart = []
        drug_names = request.form.getlist('drug_name[]')
        dose_mgs = request.form.getlist('dose_full[]') or request.form.getlist('dose_mg[]')
        med_notes = request.form.getlist('med_note[]')
        for i, name in enumerate(drug_names):
            if name.strip():
                score_val = 0.0
                dose_str = dose_mgs[i] if i < len(dose_mgs) else ""
                if dose_str:
                    import re
                    nums = re.findall(r"[-+]?\d*\.\d+|\d+", dose_str)
                    if nums: score_val = float(nums[0])
                note = med_notes[i] if i < len(med_notes) else ""
                meds_chart.append({"name": name, "score": score_val, "phase": "Current", "dose": dose_str, "note": note, "date": today.isoformat()})

        # 4. Side Effects
        se_chart = []
        se_names = request.form.getlist('side_effect_name[]')
        se_scores = request.form.getlist('side_effect_score[]')
        se_notes = request.form.getlist('side_effect_note[]')
        for i, name in enumerate(se_names):
            if name.strip():
                try: val = int(se_scores[i]) if i < len(se_scores) else 0
                except: val = 0
                note = se_notes[i] if i < len(se_notes) else ""
                se_chart.append({"name": name, "score": val, "phase": "Current", "note": note, "date": today.isoformat()})

        # --- C. SAVE TO DB ---
        chart_data = {
            'symptoms': symptoms, 'mse': mse, 'meds': meds_chart, 'se': se_chart
        }
        
        token = str(uuid.uuid4())
        expiry = datetime.now(timezone.utc) + timedelta(minutes=30)
        
        share_entry = GuestShare(
            token=token,
            data_json=json.dumps(chart_data),
            expires_at=expiry
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


@app.route('/profile', methods=['GET', 'POST'])
@doctor_required
def profile():
    """Doctor profile settings."""
    doctor = Doctor.query.get(session.get('doctor_id'))
    if not doctor:
        flash('Doctor not found.', 'error')
        return redirect(url_for('first_visit'))
    
    if request.method == 'POST':
        doctor.full_name = request.form.get('full_name', '').strip()
        doctor.clinic_name = request.form.get('clinic_name', '').strip()
        doctor.kmc_code = request.form.get('kmc_code', '').strip()
        doctor.address_text = request.form.get('address_text', '').strip()
        
        # --- PHASE 1 UPDATES: Phone & Email ---
        doctor.phone = request.form.get('phone', '').strip()
        doctor.email = request.form.get('email', '').strip()
        
        doctor.social_handle = request.form.get('social_handle', '').strip()
        
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
        return redirect(url_for('first_visit'))
        
    return render_template('profile.html', doctor=doctor)


# Root route is now handled by landing()


@app.route('/dashboard')
@login_required
def dashboard():
    """Renders the main dashboard view."""
    return render_template('dashboard.html')


@app.route('/first_visit', methods=['GET', 'POST'])
@login_required
def first_visit():
    """First Visit - New Patient & First Visit creation."""
    # No fallback to admin: if there's no doctor_id, the user shouldn't be here.
    doc_id = session.get('doctor_id')
    doctor = Doctor.query.get(doc_id) if doc_id is not None else None

    if not doctor:
        session.clear()
        flash('Session expired. Please log in.', 'error')
        return redirect(url_for('landing'))

    if request.method == 'POST':
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
        
        # --- CRITICAL FIX: Don't re-fetch "admin". Use the doctor we found above. ---
        if not doctor:
             flash('Error: No doctor account identified. Please log in.', 'error')
             return redirect(url_for('logout'))
        # --------------------------------------------------------------------------

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
            provisional_diagnosis=request.form.get('provisional_diagnosis', ''),
            differential_diagnosis=request.form.get('differential_diagnosis', ''),
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
    is_guest = session.get('role') == 'guest'
    patients = []
    if not is_guest and doctor:
        patients = Patient.query.filter_by(doctor_id=doctor.id).all()
    
    today = date.today()
    
    return render_template('first_visit.html', patients=patients, today=today, is_guest=is_guest, doctor=doctor)


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


@app.route('/guest/lifechart_proxy', methods=['POST'])
def guest_lifechart_proxy():
    if not session.get('guest'):
        abort(403)
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
    
    visit.note = form_data.get('visit_note', '')
    
    # Helper for Duration (Single Field Now)
    def get_duration(index, prefix):
        # Reads 'symptom_duration[]' list directly
        dur_list = form_data.getlist(f'{prefix}_duration[]')
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

    # 1c. Adherence Ranges (from modal JSON)
    adherence_json = form_data.get('adherence_data', '')
    if adherence_json:
        try:
            for ar in AdherenceRange.query.filter_by(visit_id=visit.id).all():
                db.session.delete(ar)
            for item in json.loads(adherence_json):
                if isinstance(item, dict) and item.get('status'):
                    start_d = parse_date(item.get('start')) if item.get('start') else None
                    end_d = parse_date(item.get('end')) if item.get('end') else None
                    db.session.add(AdherenceRange(
                        visit_id=visit.id,
                        status=item['status'],
                        start_date=start_d,
                        end_date=end_d
                    ))
        except (json.JSONDecodeError, TypeError):
            pass

    # 1d. Clinical State Ranges (from modal JSON)
    clinical_state_json = form_data.get('clinical_state_data', '')
    if clinical_state_json:
        try:
            for csr in ClinicalStateRange.query.filter_by(visit_id=visit.id).all():
                db.session.delete(csr)
            for item in json.loads(clinical_state_json):
                if isinstance(item, dict) and item.get('state'):
                    start_d = parse_date(item.get('start')) if item.get('start') else None
                    end_d = parse_date(item.get('end')) if item.get('end') else None
                    db.session.add(ClinicalStateRange(
                        visit_id=visit.id,
                        state=item['state'],
                        start_date=start_d,
                        end_date=end_d
                    ))
        except (json.JSONDecodeError, TypeError):
            pass

    # 1e. Scales (Phase 2) - from modal JSON
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

    # 3. SYMPTOMS
    s_names = form_data.getlist('symptom_name[]')
    s_onsets = form_data.getlist('symptom_onset[]')
    s_progs = form_data.getlist('symptom_progression[]')
    s_currs = form_data.getlist('symptom_current[]')
    s_notes = form_data.getlist('symptom_note[]')
    
    for i, name in enumerate(s_names):
        if name.strip():
            entry = SymptomEntry(
                visit_id=visit.id,
                symptom_name=name,
                score_onset=float(s_onsets[i]) if i < len(s_onsets) and s_onsets[i] else None,
                score_progression=float(s_progs[i]) if i < len(s_progs) and s_progs[i] else None,
                score_current=float(s_currs[i]) if i < len(s_currs) and s_currs[i] else 0,
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
        if not name.strip():
            continue
        dose = d_full_doses[i] if i < len(d_full_doses) else ''
        freq = d_freqs[i] if i < len(d_freqs) else ''
        dur = d_durs[i] if i < len(d_durs) else ''
        note = d_notes[i] if i < len(d_notes) else ''

        if last_med and last_med.drug_name.strip().lower() == name.strip().lower():
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
        else:
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
        if name.strip():
            # Handle float/int conversion safely
            curr_val = float(se_currs[i]) if i < len(se_currs) and se_currs[i] else 0
            
            entry = SideEffectEntry(
                visit_id=visit.id,
                side_effect_name=name,
                score_onset=float(se_onsets[i]) if i < len(se_onsets) and se_onsets[i] else None,
                score_progression=float(se_progs[i]) if i < len(se_progs) and se_progs[i] else None,
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
    
    # Fallback for old field name (backward compatibility)
    if not mse_currs or all(not x for x in mse_currs):
        mse_scores_old = form_data.getlist('mse_score[]')
        mse_currs = mse_scores_old
    
    for i, cat in enumerate(mse_cats):
        if cat and i < len(mse_findings) and mse_findings[i].strip():
            curr_val = float(mse_currs[i]) if i < len(mse_currs) and mse_currs[i] else 0
            
            entry = MSEEntry(
                visit_id=visit.id,
                category=cat,
                finding_name=mse_findings[i],
                score_onset=float(mse_onsets[i]) if i < len(mse_onsets) and mse_onsets[i] else None,
                score_progression=float(mse_progs[i]) if i < len(mse_progs) and mse_progs[i] else None,
                score_current=curr_val,
                duration=get_duration(i, 'mse'),  # Helper (Maps to mse_duration_val[])
                note=mse_notes[i] if i < len(mse_notes) else '',
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

    # 8. Substance Use History
    sub_names = form_data.getlist('substance_name[]')
    sub_patterns = form_data.getlist('substance_pattern[]')
    sub_starts = form_data.getlist('substance_start[]')
    sub_ends = form_data.getlist('substance_end[]')
    sub_notes = form_data.getlist('substance_note[]')
    SubstanceUseEntry.query.filter_by(visit_id=visit.id).delete()
    for i, name in enumerate(sub_names):
        if name.strip():
            start_d = parse_date(sub_starts[i]) if i < len(sub_starts) and sub_starts[i] else None
            end_d = parse_date(sub_ends[i]) if i < len(sub_ends) and sub_ends[i] else None
            db.session.add(SubstanceUseEntry(
                visit_id=visit.id,
                substance_name=name,
                pattern=sub_patterns[i] if i < len(sub_patterns) else 'Occasional',
                start_date=start_d,
                end_date=end_d,
                note=sub_notes[i] if i < len(sub_notes) else ''
            ))


@app.route('/patient/<int:patient_id>')
@login_required
def patient_detail(patient_id):
    """Patient detail page showing all visits."""
    patient = Patient.query.get_or_404(patient_id)
    visits = Visit.query.filter_by(patient_id=patient_id).order_by(Visit.date.desc()).all()
    return render_template('patient_detail.html', patient=patient, visits=visits)


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
        if request.form.get('provisional_diagnosis'): visit.provisional_diagnosis = request.form.get('provisional_diagnosis')
        if request.form.get('differential_diagnosis'): visit.differential_diagnosis = request.form.get('differential_diagnosis')
        
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
    return render_template('add_visit.html', patient=patient, today=today, last_visit=last_visit, doctor=doctor)


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
        
        visit.provisional_diagnosis = request.form.get('provisional_diagnosis', '')
        visit.differential_diagnosis = request.form.get('differential_diagnosis', '')
        
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
    adherence_data = json.dumps([{'status': a.status, 'start': a.start_date.strftime('%Y-%m-%d') if a.start_date else None, 'end': a.end_date.strftime('%Y-%m-%d') if a.end_date else None} for a in visit.adherence_ranges])
    clinical_state_data = json.dumps([{'state': c.state, 'start': c.start_date.strftime('%Y-%m-%d') if c.start_date else None, 'end': c.end_date.strftime('%Y-%m-%d') if c.end_date else None} for c in visit.clinical_state_ranges])
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
    return render_template('edit_visit.html', visit=visit, patient=patient, previous_visit=previous_visit, doctor=doctor, major_events_data=major_events_data, stressors_data=stressors_data, adherence_data=adherence_data, clinical_state_data=clinical_state_data, substances_data=substances_data, scales_data=scales_data)


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
    visit.provisional_diagnosis = request.form.get('provisional_diagnosis', '')
    visit.differential_diagnosis = request.form.get('differential_diagnosis', '')
    visit.clinical_state = request.form.get('clinical_state', '')
    visit.medication_adherence = request.form.get('medication_adherence', '')
    
    next_date = request.form.get('next_visit_date')
    if next_date:
        visit.next_visit_date = parse_date(next_date)

    # --- RANGES UPDATES (Clinical State & Adherence with dates, same as edit_visit modal) ---
    adherence_json = request.form.get('adherence_data', '')
    if adherence_json:
        try:
            for ar in AdherenceRange.query.filter_by(visit_id=visit.id).all():
                db.session.delete(ar)
            for item in json.loads(adherence_json):
                if isinstance(item, dict) and item.get('status'):
                    start_d = parse_date(item.get('start')) if item.get('start') else None
                    end_d = parse_date(item.get('end')) if item.get('end') else None
                    db.session.add(AdherenceRange(
                        visit_id=visit.id, status=item['status'], start_date=start_d, end_date=end_d
                    ))
        except (json.JSONDecodeError, TypeError):
            pass

    clinical_state_json = request.form.get('clinical_state_data', '')
    if clinical_state_json:
        try:
            for csr in ClinicalStateRange.query.filter_by(visit_id=visit.id).all():
                db.session.delete(csr)
            for item in json.loads(clinical_state_json):
                if isinstance(item, dict) and item.get('state'):
                    start_d = parse_date(item.get('start')) if item.get('start') else None
                    end_d = parse_date(item.get('end')) if item.get('end') else None
                    db.session.add(ClinicalStateRange(
                        visit_id=visit.id, state=item['state'], start_date=start_d, end_date=end_d
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
        if not name.strip():
            continue
        dose = d_full_doses[i] if i < len(d_full_doses) else ''
        freq = d_freqs[i] if i < len(d_freqs) else ''
        dur = d_durs[i] if i < len(d_durs) else ''
        note = d_notes[i] if i < len(d_notes) else ''

        if last_med and last_med.drug_name.strip().lower() == name.strip().lower():
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
        else:
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
    for visit in visits:
        visit_date = datetime.combine(visit.date, datetime.min.time())
        visit_date_str = visit_date.isoformat() # Store original visit date string
        
        for entry in visit.symptom_entries:
            name = entry.symptom_name
            if name not in symptom_data: symptom_data[name] = []
            
            points = []
            if visit.visit_type == 'First':
                duration = parse_duration(entry.duration_text or '') or timedelta(0)
                onset = visit_date - duration
                mid = calculate_midpoint_date(onset, visit_date)
                
                # Add metadata: phase, specific symptom name, and the original visit date
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
                
            for p in points:
                if p['y'] is not None:
                    p['visit_id'] = visit.id
                    p['detail'] = entry.note or ''
                    symptom_data[name].append(p)
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

            # --- NEW: Tapering Check ---
            if entry.is_tapering and entry.taper_plan:
                try:
                    plan = json.loads(entry.taper_plan)
                    current_date = v_date
                    for step in plan:
                        dose = get_unified_dose(name, step.get('dose_mg', ''))
                        med_data[name].append({
                            'x': current_date.isoformat(),
                            'y': dose,
                            'visit_id': visit.id
                        })
                        # Advance the date by the duration for the next step's starting point
                        dur_delta = parse_duration(step.get('duration_text', ''))
                        if dur_delta:
                            current_date += dur_delta
                    continue  # Skip standard logic below
                except Exception:
                    pass

            # --- Standard Logic ---
            val = get_unified_dose(name, entry.dose_mg)
            med_data[name].append({'x': v_date.isoformat(), 'y': val, 'visit_id': visit.id})

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
            substances_data.append({
                'substance': su.substance_name,
                'pattern': su.pattern or 'Occasional',
                'start_date': su.start_date.strftime('%Y-%m-%d') if su.start_date else str_date,
                'end_date': su.end_date.strftime('%Y-%m-%d') if su.end_date else str_date,
                'note': su.note or ''
            })

    # --- 5. Visit Details for Modal ---
    visit_details_map = {}
    for visit in visits:
        visit_details_map[visit.id] = {
            'date': visit.date.strftime('%Y-%m-%d'),
            'type': visit.visit_type,
            'diagnosis': visit.provisional_diagnosis,
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

    def build_clinical_points(entry, v_date, type_lbl):
        pts = []
        days = get_days(getattr(entry, 'duration_text', '')) or get_days(getattr(entry, 'duration', ''))
        start = v_date - timedelta(days=days) if days else v_date
        
        # Onset (at Start Date)
        if entry.score_onset is not None:
            pts.append({'x': start.strftime('%Y-%m-%d'), 'y': entry.score_onset, 'detail': f"{type_lbl} Onset", 'phase': 'Onset'})
        # Progression (at Midpoint)
        if entry.score_progression is not None and days > 0:
            mid = start + timedelta(days=days/2)
            pts.append({'x': mid.strftime('%Y-%m-%d'), 'y': entry.score_progression, 'detail': f"{type_lbl} Progression", 'phase': 'Progression'})
        # Current (at Visit Date)
        if entry.score_current is not None:
            pts.append({'x': v_date.strftime('%Y-%m-%d'), 'y': entry.score_current, 'detail': f"{type_lbl} Current", 'phase': 'Current'})
        return pts

    def build_med_points(entry, v_date):
        pts = []

        # --- NEW: Check for Tapering Plan ---
        if entry.is_tapering and entry.taper_plan:
            try:
                plan = json.loads(entry.taper_plan)
                current_date = v_date
                for step in plan:
                    days = get_days(step.get('duration_text', ''))
                    dose = get_unified_dose(entry.drug_name, step.get('dose_mg', ''))
                    duration = max(1, days)
                    # Fill daily points for this taper step
                    for i in range(duration):
                        d = current_date + timedelta(days=i)
                        pts.append({
                            'x': d.strftime('%Y-%m-%d'),
                            'y': dose,
                            'detail': f"Freq: {step.get('frequency', '')} (Tapering)"
                        })
                    current_date += timedelta(days=duration)
                return pts
            except Exception:
                pass  # Fallback to standard logic if JSON parsing fails

        # --- STANDARD (Non-Tapering) LOGIC ---
        days = get_days(getattr(entry, 'duration_text', ''))
        dose = get_unified_dose(entry.drug_name, entry.dose_mg)
        # Daily points from visit date onwards
        duration = max(1, days)
        for i in range(duration):
            d = v_date + timedelta(days=i)
            pts.append({
                'x': d.strftime('%Y-%m-%d'),
                'y': dose,
                'detail': f"Freq: {entry.frequency}"
            })
        return pts

    # 2. Gather Data (Separated by Chart)
    symptoms = {}
    meds = {}
    se = {}
    mse = {}
    scales = {}

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
            substances_data.append({
                'substance': su.substance_name,
                'pattern': su.pattern or 'Occasional',
                'start_date': su.start_date.strftime('%Y-%m-%d') if su.start_date else v_date_str,
                'end_date': su.end_date.strftime('%Y-%m-%d') if su.end_date else v_date_str,
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

        for s in v.symptom_entries:
            if s.symptom_name not in symptoms: symptoms[s.symptom_name] = []
            symptoms[s.symptom_name].extend(build_clinical_points(s, v.date, 'Symptom'))
            
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
            for name, points in data_map.items():
                for pt in points:
                    if pt['x'] == k:
                        breakdown.append({'name': name, 'score': pt['y']})
                        # Determine phase for unified point
                        if pt.get('phase') == 'Current':
                            is_current = True
            
            unified_points.append({
                'x': k, 
                'y': avg, 
                'detail': 'Average',
                'breakdown': breakdown,
                'phase': 'Current' if is_current else 'History' 
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

    # 4. Clinical State and Adherence Ranges (for annotation bands)
    clinical_states = []
    adherences = []
    for v in visits:
        for s in ClinicalStateRange.query.filter_by(visit_id=v.id).all():
            clinical_states.append({
                'state': s.state,
                'start': s.start_date.strftime('%Y-%m-%d') if s.start_date else None,
                'end': s.end_date.strftime('%Y-%m-%d') if s.end_date else None
            })
        for a in AdherenceRange.query.filter_by(visit_id=v.id).all():
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
        days = get_days(getattr(entry, 'duration_text', '')) or get_days(getattr(entry, 'duration', ''))
        start = v_date - timedelta(days=days) if days else v_date
        
        # Onset
        if hasattr(entry, 'score_onset') and entry.score_onset is not None:
            pts.append({'x': start.strftime('%Y-%m-%d'), 'y': float(entry.score_onset), 'phase': 'Onset'})
        # Progression
        if hasattr(entry, 'score_progression') and entry.score_progression is not None and days > 0:
            mid = start + timedelta(days=days/2)
            pts.append({'x': mid.strftime('%Y-%m-%d'), 'y': float(entry.score_progression), 'phase': 'Progression'})
        # Current
        if hasattr(entry, 'score_current') and entry.score_current is not None:
            pts.append({'x': v_date.strftime('%Y-%m-%d'), 'y': float(entry.score_current), 'phase': 'Current'})
        elif hasattr(entry, 'score') and entry.score is not None:
            pts.append({'x': v_date.strftime('%Y-%m-%d'), 'y': float(entry.score), 'phase': 'Current'})
        
        return pts

    def build_med_points(entry, v_date):
        pts = []

        # --- NEW: Check for Tapering Plan ---
        if getattr(entry, 'is_tapering', False) and getattr(entry, 'taper_plan', None):
            try:
                plan = json.loads(entry.taper_plan)
                current_date = v_date
                for step in plan:
                    days = get_days(step.get('duration_text', ''))
                    try:
                        dose_str = step.get('dose_mg', '0')
                        dose_val = float(dose_str.split()[0]) if dose_str.split() else 0
                    except Exception:
                        dose_val = 0
                    duration = max(1, days)

                    for i in range(duration):
                        d = current_date + timedelta(days=i)
                        pts.append({
                            'x': d.strftime('%Y-%m-%d'),
                            'y': dose_val,
                            'detail': f"Freq: {step.get('frequency', '')} (Tapering)"
                        })
                    current_date += timedelta(days=duration)
                return pts
            except Exception:
                pass  # Fallback

        # --- STANDARD (Non-Tapering) LOGIC ---
        days = get_days(getattr(entry, 'duration_text', ''))
        try:
            dose_str = entry.dose_mg or '0'
            dose_val = float(dose_str.split()[0]) if dose_str.split() else 0
        except Exception:
            dose_val = 0

        duration = max(1, days)
        for i in range(duration):
            d = v_date + timedelta(days=i)
            pts.append({
                'x': d.strftime('%Y-%m-%d'),
                'y': dose_val,
                'detail': f"Freq: {entry.frequency}"
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

    return render_template(
        'preview_lifechart.html',
        patient=patient,
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
    header_text = doctor.clinic_name if doctor and doctor.clinic_name else "ElevenEleven Health"
    sub_text = doctor.address_text if doctor and doctor.address_text else "Psychiatry & Wellness Center"
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
    
    # 1. Capture Doctor Details
    guest_doctor = {
        "name": request.form.get("doctor_name", "Doctor"),
        "clinic": request.form.get("clinic_name", ""),
        "qualification": request.form.get("doctor_qualification", ""), 
        "registration": request.form.get("doctor_registration", ""),
        "address": request.form.get("clinic_address", ""),
        "social": request.form.get("social_handle", "")
    }

    # Handle Ephemeral Signature (Base64)
    signature_b64 = None
    if 'signature_upload' in request.files:
        file = request.files['signature_upload']
        if file and file.filename:
            img_data = file.read()
            signature_b64 = base64.b64encode(img_data).decode('utf-8')

    # 2. Capture Patient Details
    guest_patient = {
        "name": request.form.get("patient_name", "Guest Patient"),
        "age": request.form.get("age", ""),
        "sex": request.form.get("sex", ""),
        "address": request.form.get("address", "")
    }

    # 3. Build Temp Visit (Using a simple Dictionary structure)
    # This prevents the issue where class attributes were being used incorrectly
    visit = {
        "date": date.today(),
        "provisional_diagnosis": request.form.get('provisional_diagnosis', ''),
        "medication_entries": [] # Initialize empty list directly on the object
    }

    drug_names = request.form.getlist('drug_name[]')
    dose_mgs = request.form.getlist('dose_mg[]')
    durations = request.form.getlist('med_duration_text[]')
    notes = request.form.getlist('med_note[]')
    d_forms = request.form.getlist('med_form[]')

    for i, name in enumerate(drug_names):
        if name.strip():
            visit["medication_entries"].append({
                'drug_name': name,
                'dose_mg': dose_mgs[i] if i < len(dose_mgs) else '',
                'duration_text': durations[i] if i < len(durations) else '',
                'note': notes[i] if i < len(notes) else '',
                'drug_type': None,
                'form_type': d_forms[i] if i < len(d_forms) else 'Tablet'
            })

    session.pop('guest_first_visit', None)
    
    return render_template(
        "preview_prescription.html",
        guest=True,
        patient=None,
        guest_patient=guest_patient,
        visit=visit, # Passing the dictionary
        guest_doctor=guest_doctor,
        guest_signature_b64=signature_b64 
    )

@app.route('/guest/both', methods=['POST'])
def guest_both():
    if not session.get('guest'):
        abort(403)
        
    # 1. Cleanup Old Links
    try:
        GuestShare.query.filter(GuestShare.expires_at < datetime.now(timezone.utc)).delete()
        db.session.commit()
    except Exception:
        db.session.rollback()

    # 2. Capture Basic Info
    guest_doctor = {
        "name": request.form.get("doctor_name", "Doctor"),
        "clinic": request.form.get("clinic_name", ""),
        "qualification": request.form.get("doctor_qualification", ""), 
        "registration": request.form.get("doctor_registration", ""),
        "address": request.form.get("clinic_address", ""),
        "social": request.form.get("social_handle", "")
    }
    
    signature_b64 = None
    if 'signature_upload' in request.files:
        file = request.files['signature_upload']
        if file and file.filename:
            img_data = file.read()
            signature_b64 = base64.b64encode(img_data).decode('utf-8')
            
    guest_patient = {
        "name": request.form.get("patient_name", "Guest Patient"),
        "age": request.form.get("age", ""),
        "sex": request.form.get("sex", ""),
        "address": request.form.get("address", "")
    }

    # --- 3. ROBUST DATA CAPTURE (With DATES & NOTES) ---
    today = date.today() # Base anchor date
    
    # A. Symptoms (Now with Duration Calc)
    symptoms = []
    names = request.form.getlist('symptom_name[]')
    onsets = request.form.getlist('symptom_onset[]')
    progressions = request.form.getlist('symptom_progression[]')
    currents = request.form.getlist('symptom_current[]')
    sym_notes = request.form.getlist('symptom_note[]')
    durations = request.form.getlist('duration_text[]') # <--- NEW Capture

    for i, name in enumerate(names):
        if not name.strip(): continue
        
        # 1. Scores
        def safe_int(val_list, idx, default=5):
            try: return int(val_list[idx]) if idx < len(val_list) else default
            except (ValueError, TypeError): return default

        onset = safe_int(onsets, i)
        prog = safe_int(progressions, i)
        curr = safe_int(currents, i)
        note = sym_notes[i] if i < len(sym_notes) else ""
        
        # 2. Date Calculation (Crucial for Unified Charts)
        dur_text = durations[i] if i < len(durations) else ""
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
            "note": note, "date": today.isoformat()
        })

    # B. MSE Findings
    mse = []
    mse_cats = request.form.getlist('mse_category[]')
    mse_scores = request.form.getlist('mse_score[]')
    mse_notes = request.form.getlist('mse_note[]')
    
    for i, (cat, score) in enumerate(zip(mse_cats, mse_scores)):
        try: val = int(score)
        except: val = 0
        note = mse_notes[i] if i < len(mse_notes) else ""
        mse.append({"cat": cat, "score": val, "note": note, "date": today.isoformat()})

    # C. Medications
    meds_chart = []
    drug_names = request.form.getlist('drug_name[]')
    dose_mgs = request.form.getlist('dose_full[]') or request.form.getlist('dose_mg[]')
    med_notes = request.form.getlist('med_note[]')
    d_forms = request.form.getlist('med_form[]')

    for i, name in enumerate(drug_names):
        if name.strip():
            score_val = 0.0
            dose_str = dose_mgs[i] if i < len(dose_mgs) else ""
            if dose_str:
                import re
                nums = re.findall(r"[-+]?\d*\.\d+|\d+", dose_str)
                if nums: score_val = float(nums[0])
            
            note = med_notes[i] if i < len(med_notes) else ""
            meds_chart.append({
                "name": name, "score": score_val, "phase": "Current", 
                "dose": dose_str, "note": note, "date": today.isoformat()
            })

    # D. Side Effects
    se_chart = []
    se_names = request.form.getlist('side_effect_name[]')
    se_scores = request.form.getlist('side_effect_score[]')
    se_notes = request.form.getlist('side_effect_note[]')
    
    for i, name in enumerate(se_names):
        if name.strip():
            try: val = int(se_scores[i]) if i < len(se_scores) else 0
            except: val = 0
            note = se_notes[i] if i < len(se_notes) else ""
            se_chart.append({
                "name": name, "score": val, "phase": "Current", 
                "note": note, "date": today.isoformat()
            })

    # 4. Save to DB
    chart_data = {
        'symptoms': symptoms, 'mse': mse, 'meds': meds_chart, 'se': se_chart
    }
    
    token = str(uuid.uuid4())
    expiry = datetime.now(timezone.utc) + timedelta(minutes=30)
    
    share_entry = GuestShare(
        token=token,
        data_json=json.dumps(chart_data),
        expires_at=expiry
    )
    db.session.add(share_entry)
    db.session.commit()

    lifchart_url = f"{request.url_root.rstrip('/')}/guest/share/{token}"

    # 5. Build Visit for Prescription PDF
    visit = {
        "date": date.today(),
        "provisional_diagnosis": request.form.get('provisional_diagnosis', ''),
        "medication_entries": []
    }
    durations = request.form.getlist('med_duration[]') or request.form.getlist('med_duration_text[]')

    for i, name in enumerate(drug_names):
        if name.strip():
            visit['medication_entries'].append({
                'drug_name': name,
                'dose_mg': dose_mgs[i] if i < len(dose_mgs) else '',
                'duration_text': durations[i] if i < len(durations) else '',
                'note': med_notes[i] if i < len(med_notes) else '',
                'drug_type': None,
                'form_type': d_forms[i] if i < len(d_forms) else 'Tablet'
            })

    session.pop('guest_first_visit', None)
            
    return render_template(
        "preview_prescription.html",
        visit=visit,
        patient=None,
        guest=True,
        guest_patient=guest_patient,
        lifchart_url=lifchart_url,
        guest_doctor=guest_doctor,
        guest_signature_b64=signature_b64
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
    visit_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    visit_id_str = "999"

    current_symptoms = [s for s in symptoms if s.get('phase') == 'Current']
    
    dummy_visit = {
        "date": visit_date,
        "type": "Shared View",
        "diagnosis": "Guest Mode",
        "symptoms": current_symptoms,
        "meds": meds,
        "se": se,
        "mse": mse,
        "notes": "Shared via temporary link"
    }

    # 5. Helper: Build Datasets (Using Explicit Dates)
    def build_dataset(items, label_prefix):
        datasets = {}
        # Fallback if 'date' is missing (old data)
        offset_days = {"Onset": -14, "Progression": -7, "Current": 0}

        for item in items:
            label = item.get("name") or item.get("cat")
            phase = item.get("phase", "Current")
            
            # USE SAVED DATE IF AVAILABLE
            if "date" in item:
                point_date = item["date"]
            else:
                dt = datetime.strptime(visit_date, "%Y-%m-%d") + timedelta(days=offset_days.get(phase, 0))
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
                "reported_on": visit_date
            })
            
        return list(datasets.values())

    # 6. Helper: Calculate Unified Lines (GROUP BY DATE)
    def calculate_unified(items, label, color):
        if not items: return None
        
        offset_days = {"Onset": -14, "Progression": -7, "Current": 0}
        
        # GROUP BY EXACT DATE (Not Phase!)
        date_groups = {} 

        for item in items:
            # Determine Date
            if "date" in item:
                d_key = item["date"]
            else:
                phase = item.get("phase", "Current")
                dt = datetime.strptime(visit_date, "%Y-%m-%d") + timedelta(days=offset_days.get(phase, 0))
                d_key = dt.strftime("%Y-%m-%d")
                
            if d_key not in date_groups: date_groups[d_key] = []
            date_groups[d_key].append(item)
            
        unified_points = []
        for d_key, group_items in date_groups.items():
            avg = sum(i["score"] for i in group_items) / len(group_items)
            
            breakdown = [{"name": i.get("name") or i.get("cat"), "score": i["score"]} for i in group_items]
            
            # Determine phase for tooltip (Mix if multiple phases on same day)
            phases = list(set(i.get("phase", "Current") for i in group_items))
            phase_label = phases[0] if len(phases) == 1 else "Mixed"

            unified_points.append({
                "x": d_key,
                "y": round(avg, 2),
                "phase": phase_label,
                "symptom_name": label,
                "visit_id": visit_id_str,
                "reported_on": visit_date,
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

    # 7. Render
    return render_template(
        'life_chart.html',
        guest=True,
        patient=None,
        
        symptom_datasets=build_dataset(symptoms, "symptom"),
        medication_datasets=build_dataset(meds, "med"),
        side_effect_datasets=build_dataset(se, "se"),
        mse_datasets=build_dataset(mse, "mse"),
        
        # Unified Lines
        symptom_unified=calculate_unified(symptoms, "Unified Symptoms (Avg)", "rgba(0, 0, 0, 1)"),
        med_unified=calculate_unified(meds, "Unified Meds (Avg)", "rgba(0, 0, 0, 1)"),
        se_unified=calculate_unified(se, "Unified SE (Avg)", "rgba(0, 0, 0, 1)"),
        mse_unified=calculate_unified(mse, "Unified MSE (Avg)", "rgba(0, 0, 0, 1)"),
        
        symptom_names=symptom_names,
        med_names=med_names,
        se_names=se_names,
        mse_categories=mse_categories,
        
        visit_details={visit_id_str: dummy_visit}
    )


if __name__ == '__main__':
    init_db()
    app.run(debug=True)