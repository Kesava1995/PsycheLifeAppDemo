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
    
    patients = db.relationship('Patient', backref='doctor', lazy=True)


class Patient(db.Model):
    __tablename__ = 'patients'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    sex = db.Column(db.String(10), nullable=False)
    address = db.Column(db.Text)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    visits = db.relationship('Visit', backref='patient', lazy=True, cascade='all, delete-orphan')


class Visit(db.Model):
    __tablename__ = 'visits'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    visit_type = db.Column(db.String(20), nullable=False)  # 'First' or 'Follow-up'
    provisional_diagnosis = db.Column(db.Text)
    differential_diagnosis = db.Column(db.Text)
    note = db.Column(db.Text)
    
    symptom_entries = db.relationship('SymptomEntry', backref='visit', lazy=True, cascade='all, delete-orphan')
    medication_entries = db.relationship('MedicationEntry', backref='visit', lazy=True, cascade='all, delete-orphan')
    side_effect_entries = db.relationship('SideEffectEntry', backref='visit', lazy=True, cascade='all, delete-orphan')
    mse_entries = db.relationship('MSEEntry', backref='visit', lazy=True, cascade='all, delete-orphan')


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
    dose_mg = db.Column(db.String(50))
    duration_text = db.Column(db.String(100))
    note = db.Column(db.Text)  # Used for frequency/instructions


class SideEffectEntry(db.Model):
    __tablename__ = 'side_effect_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id'), nullable=False)
    side_effect_name = db.Column(db.String(200), nullable=False)
    score = db.Column(db.Float, nullable=False)
    note = db.Column(db.Text)


class MSEEntry(db.Model):
    __tablename__ = 'mse_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id'), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # 'Thought', 'Perception', 'Affect'
    finding_name = db.Column(db.String(200))
    score = db.Column(db.Float, nullable=False)
    duration = db.Column(db.String(100))
    note = db.Column(db.Text)


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

