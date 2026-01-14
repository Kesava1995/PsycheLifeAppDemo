"""
PsycheLife - Medical web app for psychiatric patient management.
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, make_response, session, abort
from functools import wraps
from datetime import datetime, date, timedelta
from models import db, Doctor, Patient, Visit, SymptomEntry, MedicationEntry, SideEffectEntry, MSEEntry
from medical_utils import get_unified_dose, calculate_start_date, parse_duration, calculate_midpoint_date
import io
import os
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import qrcode
from urllib.parse import urljoin
from werkzeug.utils import secure_filename
import base64

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
basedir = os.path.abspath(os.path.dirname(__file__))

# Use absolute path for DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'psychelife.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Use absolute path for Uploads
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'static', 'signatures')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)


# Hardcoded credentials (for demo - replace with database lookup in production)
VALID_CREDENTIALS = {
    'admin': 'doctor'
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
                password_hash=generate_password_hash('doctor')
            )
            db.session.add(default_doctor)
            db.session.commit()


@app.route('/')
def landing():
    """Landing page - Facebook-style login/signup."""
    if 'logged_in' in session and session.get('logged_in'):
        return redirect(url_for('dashboard'))
    if 'guest' in session:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login handler - processes login from landing page."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Check hardcoded credentials first (for backward compatibility)
        if username in VALID_CREDENTIALS and VALID_CREDENTIALS[username] == password:
            session['logged_in'] = True
            session['username'] = username
            session['role'] = 'doctor'
            
            # --- UPDATED: Fetch ID so profile retrieval works for admin ---
            doc = Doctor.query.filter_by(username=username).first()
            if doc:
                session['doctor_id'] = doc.id
            # -------------------------------------------------------------
            
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        
        # Check database for doctor
        doctor = Doctor.query.filter_by(username=username).first()
        if doctor:
            from werkzeug.security import check_password_hash
            if check_password_hash(doctor.password_hash, password):
                session['logged_in'] = True
                session['username'] = username
                session['doctor_id'] = doctor.id
                session['role'] = 'doctor'
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
        
        flash('Invalid credentials. Please try again.', 'error')
        return redirect(url_for('landing'))
    
    # GET request - redirect to landing
    return redirect(url_for('landing'))

@app.route('/guest/lifechart', methods=['GET', 'POST'])
def guest_lifechart():
    """
    Session-only lifechart for Guest Mode.
    """
    # 1. Initialize empty lists to prevent UnboundLocalError
    symptoms = []
    mse = []
    meds = []
    se = []

    # 2. Handle POST (Form Submission from Dashboard)
    if request.method == 'POST':
        # --- Process Symptoms ---
        names = request.form.getlist('symptom_name[]')
        onsets = request.form.getlist('symptom_onset[]')
        progressions = request.form.getlist('symptom_progression[]')
        currents = request.form.getlist('symptom_current[]')

        for i, name in enumerate(names):
            if not name.strip(): continue
            if i < len(onsets) and onsets[i].isdigit():
                symptoms.append({"name": name, "score": int(onsets[i]), "phase": "Onset"})
            if i < len(progressions) and progressions[i].isdigit():
                symptoms.append({"name": name, "score": int(progressions[i]), "phase": "Progression"})
            if i < len(currents) and currents[i].isdigit():
                symptoms.append({"name": name, "score": int(currents[i]), "phase": "Current"})

        # --- Process MSE ---
        mse_cats = request.form.getlist('mse_category[]')
        mse_scores = request.form.getlist('mse_score[]')
        for cat, score in zip(mse_cats, mse_scores):
            if score.isdigit():
                mse.append({"cat": cat, "score": int(score)})

        # --- Process Medications ---
        drug_names = request.form.getlist('drug_name[]')
        dose_mgs = request.form.getlist('dose_mg[]')
        for i, name in enumerate(drug_names):
            if name.strip() and i < len(dose_mgs) and dose_mgs[i]:
                try:
                    score_val = float(dose_mgs[i])
                except ValueError:
                    score_val = 0.0
                meds.append({
                    "name": name,
                    "score": score_val,      # For Chart (Y-axis)
                    "dose": dose_mgs[i],     # For Modal Display
                    "phase": "Current"
                })

        # --- Process Side Effects ---
        se_names = request.form.getlist('side_effect_name[]')
        se_scores = request.form.getlist('side_effect_score[]')
        for i, name in enumerate(se_names):
            if name.strip() and i < len(se_scores) and se_scores[i].isdigit():
                se.append({
                    "name": name,
                    "score": int(se_scores[i]),
                    "phase": "Current"
                })

        # Update Cache
        session['guest_chart_cache'] = {
            'symptoms': symptoms,
            'mse': mse,
            'meds': meds,
            'se': se
        }

    # 3. Handle GET (Load from Cache)
    else:
        cached = session.get('guest_chart_cache')
        if cached:
            symptoms = cached.get('symptoms', [])
            mse = cached.get('mse', [])
            meds = cached.get('meds', [])
            se = cached.get('se', [])
        else:
            flash('Life chart session expired or empty.', 'info')

    visit_date = datetime.utcnow().strftime('%Y-%m-%d')

    # ---- Build ONE synthetic visit for the Modal ----
    # FIX: Pass the populated 'meds' and 'se' lists here
    visit = {
        "date": visit_date,
        "type": "First Visit (Guest)",
        "symptoms": symptoms,
        "mse": mse,
        "meds": meds,  # <--- Was empty [], now passing data
        "se": se,      # <--- Was empty [], now passing data
        "notes": ""
    }

    # ---- Convert to chart-ready datasets ----
    def build_dataset(items, label_prefix):
        datasets = {}
        offset_days = {"Onset": -14, "Progression": -7, "Current": 0}

        for item in items:
            # Determine label (Name for symptoms/meds, Category for MSE)
            label = item.get("name") or item.get("cat")
            phase = item.get("phase", "Current")

            point_date = (
                datetime.strptime(visit_date, "%Y-%m-%d")
                + timedelta(days=offset_days.get(phase, 0))
            ).strftime("%Y-%m-%d")

            if label not in datasets:
                datasets[label] = {
                    "label": label,
                    "data": [],
                    "fill": False,
                    "tension": 0.3
                }

            datasets[label]["data"].append({
                "x": point_date,
                "y": item["score"],
                "phase": phase,
                "symptom_name": item.get("name")
            })

        for ds in datasets.values():
            ds["data"].sort(key=lambda p: p["x"])

        return list(datasets.values())

    symptom_datasets = build_dataset(symptoms, "symptom")
    mse_datasets = build_dataset(mse, "mse")
    medication_datasets = build_dataset(meds, "med")
    side_effect_datasets = build_dataset(se, "se")

    # Unified averages
    def unified(items):
        if not items: return None
        avg = sum(i["score"] for i in items) / len(items)
        return {
            "label": "Unified (Avg)",
            "isUnified": True,
            "data": [{"x": visit_date, "y": avg}],
            "borderColor": "#000",
            "borderWidth": 3
        }

    session.pop('guest_first_visit', None)

    return render_template(
        'life_chart.html',
        guest=True,
        patient=None,

        symptom_datasets=symptom_datasets,
        symptom_unified=unified(symptoms),

        medication_datasets=medication_datasets,
        med_unified=unified(meds),

        side_effect_datasets=side_effect_datasets,
        se_unified=unified(se),

        mse_datasets=mse_datasets,
        mse_unified=unified(mse),

        symptom_names=sorted({s["name"] for s in symptoms if s.get("name")}),
        med_names=sorted({m["name"] for m in meds}),
        se_names=sorted({s["name"] for s in se}),
        mse_categories=sorted(list(set([m["cat"] for m in mse]))),

        visit_details={0: visit}
    )

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Doctor registration."""
    if request.method == 'POST':
        firstname = request.form.get('firstname', '').strip()
        lastname = request.form.get('lastname', '').strip()
        mobile = request.form.get('mobile', '').strip()
        specialty = request.form.get('specialty', '').strip()
        password = request.form.get('password', '')
        
        if not all([firstname, lastname, mobile, password]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('landing'))
        
        # Create username from firstname + lastname
        username = f"{firstname.lower()}{lastname.lower()}"
        
        # Check if username already exists
        if Doctor.query.filter_by(username=username).first():
            flash('An account with this name already exists. Please use a different name or log in.', 'error')
            return redirect(url_for('landing'))
        
        # Create new doctor
        from werkzeug.security import generate_password_hash
        doctor = Doctor(
            username=username,
            password_hash=generate_password_hash(password)
        )
        db.session.add(doctor)
        db.session.commit()
        
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('landing'))
    
    # GET request - redirect to landing
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
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        doctor.full_name = request.form.get('full_name', '').strip()
        doctor.clinic_name = request.form.get('clinic_name', '').strip()
        doctor.kmc_code = request.form.get('kmc_code', '').strip()
        doctor.address_text = request.form.get('address_text', '').strip()
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
        return redirect(url_for('dashboard'))
        
    return render_template('profile.html', doctor=doctor)


# Root route is now handled by landing()


@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    """Dashboard - New Patient & First Visit creation."""
    if request.method == 'POST':
        # Check if guest mode - prevent saving
        if session.get('role') == 'guest':
            workflow = request.form.get('workflow')

            if workflow == 'prescription':
                return redirect(url_for('guest_prescription'), code=307)

            elif workflow == 'lifechart':
                # Cache form data for guest life chart
                symptoms = []
                names = request.form.getlist('symptom_name[]')
                onsets = request.form.getlist('symptom_onset[]')
                progressions = request.form.getlist('symptom_progression[]')
                currents = request.form.getlist('symptom_current[]')

                for i, name in enumerate(names):
                    if not name.strip():
                        continue
                    if onsets[i].isdigit():
                        symptoms.append({"name": name, "score": int(onsets[i]), "phase": "Onset"})
                    if progressions[i].isdigit():
                        symptoms.append({"name": name, "score": int(progressions[i]), "phase": "Progression"})
                    if currents[i].isdigit():
                        symptoms.append({"name": name, "score": int(currents[i]), "phase": "Current"})

                mse = []
                cats = request.form.getlist('mse_category[]')
                scores = request.form.getlist('mse_score[]')
                for c, s in zip(cats, scores):
                    if s.isdigit():
                        mse.append({"cat": c, "score": int(s)})

                session['guest_chart_cache'] = {
                    "symptoms": symptoms,
                    "mse": mse
                }

                return redirect(url_for('guest_lifechart_proxy'), code=307)

            elif workflow == 'both':
                return redirect(url_for('guest_both'), code=307)

            return redirect(url_for('dashboard'))
        
        # Get patient info
        patient_name = request.form.get('patient_name')
        age = request.form.get('age')
        sex = request.form.get('sex')
        address = request.form.get('address')
        visit_date_str = request.form.get('visit_date')
        
        if not all([patient_name, age, sex, visit_date_str]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('dashboard'))
        
        try:
            visit_date = datetime.strptime(visit_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format.', 'error')
            return redirect(url_for('dashboard'))
        
        # Get or create doctor
        doctor = Doctor.query.filter_by(username=session.get('username', 'admin')).first()
        if not doctor:
            from werkzeug.security import generate_password_hash
            doctor = Doctor(username=session.get('username', 'admin'), password_hash=generate_password_hash('doctor'))
            db.session.add(doctor)
            db.session.commit()
        
        # Create patient
        patient = Patient(
            name=patient_name,
            age=int(age),
            sex=sex,
            address=address,
            doctor_id=doctor.id
        )
        db.session.add(patient)
        db.session.flush()
        
        # Create visit
        visit = Visit(
            patient_id=patient.id,
            date=visit_date,
            visit_type='First',
            provisional_diagnosis=request.form.get('provisional_diagnosis', ''),
            differential_diagnosis=request.form.get('differential_diagnosis', '')
        )
        db.session.add(visit)
        db.session.flush()
        
        # Process form data
        process_visit_form_data(visit, request.form)
        
        db.session.commit()
        
        # Handle workflow
        workflow = request.form.get('workflow')
        if workflow == 'prescription':
            return redirect(url_for('preview_prescription', visit_id=visit.id))
        elif workflow == 'lifechart':
            return redirect(url_for('life_chart', patient_id=patient.id))
        elif workflow == 'both':
            return redirect(url_for('preview_prescription', visit_id=visit.id, include_qr='true'))
        else:
            return redirect(url_for('patient_detail', patient_id=patient.id))
    
    # GET request - show dashboard
    is_guest = session.get('role') == 'guest'
    doctor = None
    patients = []
    
    if not is_guest:
        doctor = Doctor.query.filter_by(username=session.get('username', 'admin')).first()
        if doctor:
            patients = Patient.query.filter_by(doctor_id=doctor.id).all()
    
    today = date.today()
    
    return render_template('dashboard.html', patients=patients, today=today, is_guest=is_guest)


@app.route('/guest/lifechart_proxy', methods=['POST'])
def guest_lifechart_proxy():
    if not session.get('guest'):
        abort(403)
    return guest_lifechart()



def process_visit_form_data(visit, form_data):
    """Helper function to process and save visit form data."""
    # Process symptoms
    symptom_names = form_data.getlist('symptom_name[]')
    symptom_onsets = form_data.getlist('symptom_onset[]')
    symptom_progressions = form_data.getlist('symptom_progression[]')
    symptom_currents = form_data.getlist('symptom_current[]')
    duration_texts = form_data.getlist('duration_text[]')
    symptom_notes = form_data.getlist('symptom_note[]')
    
    for i, name in enumerate(symptom_names):
        if name.strip():
            entry = SymptomEntry(
                visit_id=visit.id,
                symptom_name=name,
                score_onset=float(symptom_onsets[i]) if i < len(symptom_onsets) and symptom_onsets[i] else None,
                score_progression=float(symptom_progressions[i]) if i < len(symptom_progressions) and symptom_progressions[i] else None,
                score_current=float(symptom_currents[i]) if i < len(symptom_currents) and symptom_currents[i] else 0,
                duration_text=duration_texts[i] if i < len(duration_texts) else '',
                note=symptom_notes[i] if i < len(symptom_notes) else ''
            )
            db.session.add(entry)
    
    # Process medications
    drug_names = form_data.getlist('drug_name[]')
    drug_types = form_data.getlist('drug_type[]')
    dose_mgs = form_data.getlist('dose_mg[]')
    med_duration_texts = form_data.getlist('med_duration_text[]')
    med_notes = form_data.getlist('med_note[]')
    
    for i, name in enumerate(drug_names):
        if name.strip():
            entry = MedicationEntry(
                visit_id=visit.id,
                drug_name=name,
                drug_type=drug_types[i] if i < len(drug_types) else None,
                dose_mg=dose_mgs[i] if i < len(dose_mgs) else '',
                duration_text=med_duration_texts[i] if i < len(med_duration_texts) else '',
                note=med_notes[i] if i < len(med_notes) else ''
            )
            db.session.add(entry)
    
    # Process side effects
    se_names = form_data.getlist('side_effect_name[]')
    se_scores = form_data.getlist('side_effect_score[]')
    se_notes = form_data.getlist('side_effect_note[]')
    
    for i, name in enumerate(se_names):
        if name.strip():
            entry = SideEffectEntry(
                visit_id=visit.id,
                side_effect_name=name,
                score=float(se_scores[i]) if i < len(se_scores) and se_scores[i] else 0,
                note=se_notes[i] if i < len(se_notes) else ''
            )
            db.session.add(entry)
    
    # Process MSE entries
    mse_categories = form_data.getlist('mse_category[]')
    mse_finding_names = form_data.getlist('mse_finding_name[]')
    mse_scores = form_data.getlist('mse_score[]')
    mse_durations = form_data.getlist('mse_duration[]')
    mse_notes = form_data.getlist('mse_note[]')
    
    for i, cat in enumerate(mse_categories):
        if cat:
            entry = MSEEntry(
                visit_id=visit.id,
                category=cat,
                finding_name=mse_finding_names[i] if i < len(mse_finding_names) else '',
                score=float(mse_scores[i]) if i < len(mse_scores) and mse_scores[i] else 0,
                duration=mse_durations[i] if i < len(mse_durations) else '',
                note=mse_notes[i] if i < len(mse_notes) else ''
            )
            db.session.add(entry)
    
    # Process visit note
    visit_note = form_data.get('visit_note', '')
    if visit_note:
        visit.note = visit_note


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
        visit_date_str = request.form.get('date')
        if not visit_date_str:
            flash('Please select a date.', 'error')
            return redirect(url_for('add_visit', patient_id=patient_id))
        
        try:
            visit_date = datetime.strptime(visit_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format.', 'error')
            return redirect(url_for('add_visit', patient_id=patient_id))
        
        # Create visit
        visit = Visit(
            patient_id=patient.id,
            date=visit_date,
            visit_type='Follow-up',
            provisional_diagnosis=request.form.get('provisional_diagnosis', ''),
            differential_diagnosis=request.form.get('differential_diagnosis', '')
        )
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
            return redirect(url_for('life_chart', patient_id=patient.id))
        elif submit_action == 'both':
            return redirect(url_for('preview_prescription', visit_id=visit.id, include_qr='true'))
        else:
            return redirect(url_for('patient_detail', patient_id=patient.id))
        
    # GET Request - Auto-fill logic
    today = date.today()
    
    # Fetch the most recent visit to copy data from
    last_visit = Visit.query.filter_by(patient_id=patient.id).order_by(Visit.date.desc()).first()
    
    return render_template('add_visit.html', patient=patient, today=today, last_visit=last_visit)


@app.route('/visit/<int:visit_id>/edit', methods=['GET', 'POST'])
@doctor_required
def edit_visit(visit_id):
    """Edit an existing visit."""
    visit = Visit.query.get_or_404(visit_id)
    patient = visit.patient
    
    if request.method == 'POST':
        # Update visit date
        visit_date_str = request.form.get('date')
        if visit_date_str:
            try:
                visit.date = datetime.strptime(visit_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format.', 'error')
        
        # Update diagnosis
        visit.provisional_diagnosis = request.form.get('provisional_diagnosis', '')
        visit.differential_diagnosis = request.form.get('differential_diagnosis', '')
        
        # Delete existing entries
        SymptomEntry.query.filter_by(visit_id=visit.id).delete()
        MedicationEntry.query.filter_by(visit_id=visit.id).delete()
        SideEffectEntry.query.filter_by(visit_id=visit.id).delete()
        MSEEntry.query.filter_by(visit_id=visit.id).delete()
        
        # Process new form data
        process_visit_form_data(visit, request.form)
        
        db.session.commit()
        
        # Handle submit_action
        submit_action = request.form.get('submit_action')
        if submit_action == 'prescription':
            return redirect(url_for('preview_prescription', visit_id=visit.id))
        elif submit_action == 'lifechart':
            return redirect(url_for('life_chart', patient_id=patient.id))
        elif submit_action == 'both':
            return redirect(url_for('preview_prescription', visit_id=visit.id, include_qr='true'))
        else:
            return redirect(url_for('patient_detail', patient_id=patient.id))
    
    # GET request
    return render_template('edit_visit.html', visit=visit, patient=patient)


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
            'symptom_names': [], 'med_names': [], 'se_names': [], 'mse_categories': [],
            'visit_details': {}
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
        v_date = datetime.combine(visit.date, datetime.min.time()).isoformat()
        for entry in visit.medication_entries:
            name = entry.drug_name
            val = get_unified_dose(name, entry.dose_mg)
            if name not in med_data: med_data[name] = []
            med_data[name].append({'x': v_date, 'y': val, 'visit_id': visit.id})
            
    medication_datasets = [] # RENAMED to match template
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
            'notes': getattr(visit, 'notes', '')
        }

    return {
        'symptom_datasets': symptom_datasets, 'symptom_unified': symptom_unified,
        'medication_datasets': medication_datasets, 'med_unified': med_unified,
        'side_effect_datasets': side_effect_datasets, 'se_unified': se_unified,
        'mse_datasets': mse_datasets, 'mse_unified': mse_unified,
        'symptom_names': list(symptom_data.keys()),
        'med_names': list(med_data.keys()),
        'se_names': list(se_data.keys()),
        'mse_categories': list(mse_data.keys()),
        'visit_details': visit_details_map
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



@app.route('/life_chart/<int:patient_id>')
@login_required
def life_chart(patient_id):
    """Life chart visualization page."""
    patient = Patient.query.get_or_404(patient_id)
    chart_data = prepare_chart_data(patient_id)
    
    return render_template(
        'life_chart.html',
        patient=patient,
        symptom_datasets=chart_data['symptom_datasets'],
        symptom_unified=chart_data.get('symptom_unified'),
        medication_datasets=chart_data['medication_datasets'], # Explicitly named
        med_unified=chart_data.get('med_unified'),
        side_effect_datasets=chart_data['side_effect_datasets'], # Explicitly named
        se_unified=chart_data.get('se_unified'),
        mse_datasets=chart_data['mse_datasets'],
        mse_unified=chart_data.get('mse_unified'),
        symptom_names=chart_data.get('symptom_names', []),
        med_names=chart_data.get('med_names', []),
        se_names=chart_data.get('se_names', []),
        mse_categories=chart_data.get('mse_categories', []),
        visit_details=chart_data.get('visit_details', {})
    )


@app.route('/preview_prescription/<int:visit_id>')
@login_required
def preview_prescription(visit_id):
    """Preview prescription before printing."""
    visit = Visit.query.get_or_404(visit_id)
    patient = visit.patient
    include_qr = request.args.get('include_qr') == 'true'
    
    lifchart_url = None
    if include_qr:
        base_url = request.url_root.rstrip('/')
        lifchart_url = f"{base_url}/life_chart/{patient.id}"
    
    return render_template('preview_prescription.html', 
                         patient=patient, 
                         visit=visit, 
                         lifchart_url=lifchart_url)


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
            med.note or '-',  # Frequency mapped to note
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
    return redirect(url_for('dashboard'))
    
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

    for i, name in enumerate(drug_names):
        if name.strip():
            # Append simple dictionary instead of complex object
            visit["medication_entries"].append({
                'drug_name': name,
                'dose_mg': dose_mgs[i] if i < len(dose_mgs) else '',
                'duration_text': durations[i] if i < len(durations) else '',
                'note': notes[i] if i < len(notes) else '',
                'drug_type': None
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
    
    guest_patient = {
        "name": request.form.get("patient_name", "Guest Patient"),
        "age": request.form.get("age", ""),
        "sex": request.form.get("sex", ""),
        "address": request.form.get("address", "")
    }

    session.pop('guest_first_visit', None)
    base_url = request.url_root.rstrip('/')
    lifchart_url = f"{base_url}/guest/lifechart"
    
    # --- FIX START: Use Dictionary instead of Class ---
    visit = {
        "date": date.today(),
        "provisional_diagnosis": request.form.get('provisional_diagnosis', ''),
        "medication_entries": []
    }

    drug_names = request.form.getlist('drug_name[]')
    dose_mgs = request.form.getlist('dose_mg[]')
    durations = request.form.getlist('med_duration_text[]')
    notes = request.form.getlist('med_note[]')

    for i, name in enumerate(drug_names):
        if name.strip():
            visit['medication_entries'].append({
                'drug_name': name,
                'dose_mg': dose_mgs[i] if i < len(dose_mgs) else '',
                'duration_text': durations[i] if i < len(durations) else '',
                'note': notes[i] if i < len(notes) else '',
                'drug_type': None
            })
    # --- FIX END ---
            
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


if __name__ == '__main__':
    init_db()
    app.run(debug=True)