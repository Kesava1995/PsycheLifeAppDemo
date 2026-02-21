from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()


class Doctor(db.Model):
    __tablename__ = 'doctors'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    
    # New Fields for Prescription Personalization
    full_name = db.Column(db.String(100)) # e.g. "Dr. John Doe"
    clinic_name = db.Column(db.String(200))
    kmc_code = db.Column(db.String(50))
    address_text = db.Column(db.Text)
    social_handle = db.Column(db.String(100)) # e.g. "@drjohnpsych"
    signature_filename = db.Column(db.String(200)) # Path to uploaded image
    
    # Phase 1: New Contact Details
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    
    patients = db.relationship('Patient', backref='doctor', lazy=True)


class Patient(db.Model):
    __tablename__ = 'patients'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    sex = db.Column(db.String(10), nullable=False)
    address = db.Column(db.Text)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    
    # Phase 1: Extended Details
    phone = db.Column(db.String(20))  # Optional Phone
    attender_name = db.Column(db.String(100))
    attender_relation = db.Column(db.String(50))
    attender_reliability = db.Column(db.String(10))  # 'Yes' or 'No'
    personal_notes = db.Column(db.Text)  # Doctor's personal ID notes
    
    visits = db.relationship('Visit', backref='patient', lazy=True, cascade='all, delete-orphan')


class Visit(db.Model):
    __tablename__ = 'visits'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    visit_type = db.Column(db.String(20), nullable=False)  # 'First' or 'Follow-up'
    provisional_diagnosis = db.Column(db.Text)
    differential_diagnosis = db.Column(db.Text)
    
    next_visit_date = db.Column(db.Date)
    
    note = db.Column(db.Text)
    
    clinical_state = db.Column(db.String(50), nullable=True)
    medication_adherence = db.Column(db.String(50), nullable=True)
    
    symptom_entries = db.relationship('SymptomEntry', backref='visit', lazy=True, cascade='all, delete-orphan')
    medication_entries = db.relationship('MedicationEntry', backref='visit', lazy=True, cascade='all, delete-orphan')
    side_effect_entries = db.relationship('SideEffectEntry', backref='visit', lazy=True, cascade='all, delete-orphan')
    mse_entries = db.relationship('MSEEntry', backref='visit', lazy=True, cascade='all, delete-orphan')
    
    # Phase 2: New Relationships
    stressor_entries = db.relationship('StressorEntry', backref='visit', lazy=True, cascade='all, delete-orphan')
    personality_entries = db.relationship('PersonalityEntry', backref='visit', lazy=True, cascade='all, delete-orphan')
    safety_profile = db.relationship('SafetyMedicalProfile', backref='visit', uselist=False, cascade='all, delete-orphan')
    major_events = db.relationship('MajorEvent', backref='visit', lazy=True, cascade='all, delete-orphan')
    adherence_ranges = db.relationship('AdherenceRange', backref='visit', lazy=True, cascade='all, delete-orphan')
    clinical_state_ranges = db.relationship('ClinicalStateRange', backref='visit', lazy=True, cascade='all, delete-orphan')


class SymptomEntry(db.Model):
    __tablename__ = 'symptom_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id'), nullable=False)
    symptom_name = db.Column(db.String(200), nullable=False)
    score_onset = db.Column(db.Float)
    score_progression = db.Column(db.Float)
    score_current = db.Column(db.Float, nullable=False)
    duration_text = db.Column(db.String(100))
    note = db.Column(db.Text)


class MedicationEntry(db.Model):
    __tablename__ = 'medication_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id'), nullable=False)
    drug_name = db.Column(db.String(200), nullable=False)
    drug_type = db.Column(db.String(50))  # 'Brand' or 'Generic'
    form_type = db.Column(db.String(50))  # 'Tablet', 'Capsule', or 'Injection'
    dose_mg = db.Column(db.String(50))
    
    # Phase 1: Frequency Dropdown (0-0-1 etc)
    frequency = db.Column(db.String(20))
    
    duration_text = db.Column(db.String(100))
    note = db.Column(db.Text)  # Instructions (Before/After food)
    
    is_tapering = db.Column(db.Boolean, default=False)
    taper_plan = db.Column(db.Text, nullable=True)  # JSON array of steps


class SideEffectEntry(db.Model):
    __tablename__ = 'side_effect_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id'), nullable=False)
    side_effect_name = db.Column(db.String(200), nullable=False)
    
    # Phase 1: 3 Sliders Support
    score_onset = db.Column(db.Float)
    score_progression = db.Column(db.Float)
    score_current = db.Column(db.Float, nullable=False)  # Renamed from 'score' conceptually
    
    # NEW: Duration Support
    duration_text = db.Column(db.String(100))
    
    note = db.Column(db.Text)
    
    # --- FIX FOR CRASH: Explicitly map the legacy 'score' column ---
    score = db.Column(db.Integer, default=0)
    
    # Backward compatibility property if needed
    @property
    def score_prop(self):
        return self.score_current


class MSEEntry(db.Model):
    __tablename__ = 'mse_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id'), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # 'Thought', 'Perception', 'Affect'
    finding_name = db.Column(db.String(200))
    
    # Phase 1: 3 Sliders Support
    score_onset = db.Column(db.Float)
    score_progression = db.Column(db.Float)
    score_current = db.Column(db.Float, nullable=False)  # Renamed from 'score'
    
    duration = db.Column(db.String(100))
    note = db.Column(db.Text)
    
    # --- FIX FOR CRASH: Explicitly map the legacy 'score' column ---
    score = db.Column(db.Integer, default=0)
    
    # Backward compatibility property if needed
    @property
    def score_prop(self):
        return self.score_current


class GuestShare(db.Model):
    __tablename__ = 'guest_shares'
    
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(36), unique=True, nullable=False)
    data_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)

    def is_expired(self):
        # 1. Get current UTC time
        now = datetime.now(timezone.utc)
        
        # 2. Check if the DB time has timezone info
        if self.expires_at.tzinfo is None:
            # If DB is Naive (SQLite default), make 'now' Naive too
            now = now.replace(tzinfo=None)
            
        return now > self.expires_at


# --- Phase 2: New Models ---

class StressorEntry(db.Model):
    __tablename__ = 'stressor_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id'), nullable=False)
    stressor_type = db.Column(db.String(200))  # e.g., Financial, Loss
    duration = db.Column(db.String(50), nullable=True)
    note = db.Column(db.Text)


class MajorEvent(db.Model):
    __tablename__ = 'major_events'
    
    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id'), nullable=False)
    event_type = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.String(50), nullable=True)
    note = db.Column(db.Text)


class AdherenceRange(db.Model):
    __tablename__ = 'adherence_ranges'
    
    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False)  # 'Complete', 'Partial', 'No Adherence'
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)


class ClinicalStateRange(db.Model):
    __tablename__ = 'clinical_state_ranges'
    
    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id'), nullable=False)
    state = db.Column(db.String(50), nullable=False)  # 'Recovery', 'Remission', etc.
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)


class PersonalityEntry(db.Model):
    __tablename__ = 'personality_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id'), nullable=False)
    trait = db.Column(db.String(200))  # e.g., Paranoid, Borderline
    note = db.Column(db.Text)


class SafetyMedicalProfile(db.Model):
    __tablename__ = 'safety_medical_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id'), nullable=False)
    
    drug_allergies = db.Column(db.Text)
    medical_comorbidities = db.Column(db.Text)
    non_psychiatric_meds = db.Column(db.Text)


class DefaultTemplate(db.Model):
    __tablename__ = 'default_templates'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    symptoms = db.Column(db.Text, nullable=False)  # Stored as JSON string


class CustomTemplate(db.Model):
    __tablename__ = 'custom_templates'
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    symptoms = db.Column(db.Text, nullable=False)  # Stored as JSON string

    __table_args__ = (db.UniqueConstraint('doctor_id', 'name', name='_doctor_template_uc'),)
