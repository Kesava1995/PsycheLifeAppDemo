import json

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone, timedelta

db = SQLAlchemy()


def parse_doctor_social_handle_json(raw):
    """
    Parse doctors.social_handle: JSON object {linkedin, website, instagram}
    or legacy plain text (treated as Instagram).
    """
    empty = {"linkedin": "", "website": "", "instagram": ""}
    if raw is None:
        return dict(empty)
    if not isinstance(raw, str):
        return dict(empty)
    s = raw.strip()
    if not s:
        return dict(empty)
    try:
        data = json.loads(s)
        if isinstance(data, dict):
            return {
                "linkedin": str(data.get("linkedin") or "")[:800],
                "website": str(data.get("website") or "")[:800],
                "instagram": str(data.get("instagram") or "")[:300],
            }
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return {**empty, "instagram": s[:300]}


def serialize_doctor_social_handle_json(linkedin="", website="", instagram=""):
    """Build JSON string for doctors.social_handle."""
    d = {
        "linkedin": (linkedin or "").strip()[:800],
        "website": (website or "").strip()[:800],
        "instagram": (instagram or "").strip()[:300],
    }
    return json.dumps(d, ensure_ascii=False)


def parse_doctor_clinics_list(clinics_json_raw, legacy_name, legacy_address):
    """
    List of {"name", "address"} from doctors.clinics_json, or legacy clinic_name + address_text.
    """
    if clinics_json_raw and isinstance(clinics_json_raw, str) and clinics_json_raw.strip():
        try:
            data = json.loads(clinics_json_raw)
            if isinstance(data, list):
                out = []
                for item in data:
                    if isinstance(item, dict):
                        n = (item.get("name") or "").strip()[:300]
                        a = (item.get("address") or "").strip()[:4000]
                        if n or a:
                            out.append({"name": n, "address": a})
                return out
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    ln = (legacy_name or "").strip()
    la = (legacy_address or "").strip()
    if ln or la:
        return [{"name": ln[:300], "address": la[:4000]}]
    return []


def serialize_doctor_clinics_list(clinics_list):
    """JSON array for doctors.clinics_json."""
    clean = []
    for c in clinics_list or []:
        if not isinstance(c, dict):
            continue
        n = (c.get("name") or "").strip()[:300]
        a = (c.get("address") or "").strip()[:4000]
        if n or a:
            clean.append({"name": n, "address": a})
    return json.dumps(clean, ensure_ascii=False) if clean else None


def doctor_rx_clinic_header(doctor, clinic_index=None):
    """(name, address) for prescription header; clinic_index selects row when multiple."""
    if not doctor:
        return "", ""
    lst = doctor.clinics_list
    if not lst:
        return (doctor.clinic_name or "").strip(), (doctor.address_text or "").strip()
    try:
        idx = int(clinic_index) if clinic_index is not None else 0
    except (TypeError, ValueError):
        idx = 0
    idx = max(0, min(idx, len(lst) - 1))
    c = lst[idx]
    return (c.get("name") or "").strip(), (c.get("address") or "").strip()


class Doctor(db.Model):
    __tablename__ = 'doctors'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    # Shareable public profile URL slug: /public_profile/<slug> (lowercase, unique)
    public_profile_slug = db.Column(db.String(64), unique=True, nullable=True)
    
    # New Fields for Prescription Personalization
    full_name = db.Column(db.String(100)) # e.g. "Dr. John Doe"
    clinic_name = db.Column(db.String(200))
    kmc_code = db.Column(db.String(50))
    address_text = db.Column(db.Text)
    # JSON array [{"name","address"}, ...]; legacy clinic_name/address_text kept in sync with first entry
    clinics_json = db.Column(db.Text, nullable=True)
    # JSON: {"linkedin","website","instagram"} — see parse_doctor_social_handle_json
    social_handle = db.Column(db.Text, nullable=True)
    signature_filename = db.Column(db.String(200)) # Path to uploaded image
    profile_photo = db.Column(db.LargeBinary, nullable=True)
    profile_photo_mimetype = db.Column(db.String(80), nullable=True)
    designation = db.Column(db.String(255), nullable=True)

    # Phase 1: New Contact Details
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))

    # SMTP: App Password for the doctor's email provider (Zoho, Gmail, etc.). Stored encrypted (decrypted when sending).
    smtp_app_password = db.Column(db.String(255), nullable=True)

    # Comma-separated days before appointment to send reminders (e.g. "7,3,1"). Default 7, 3, 1.
    appointment_reminder_days = db.Column(db.String(50), default="7,3,1")

    # Active schedule template for appointment slot calculation
    active_template_id = db.Column(db.Integer, db.ForeignKey('schedule_templates.id'), nullable=True)

    # Clinic hours for dashboard: JSON text e.g. {"morning": {"start": "09:00", "end": "17:00"}, "evening": {"start": "17:00", "end": "22:00"}}
    clinic_hours = db.Column(db.Text, nullable=True)

    # Saved custom quick-registration templates: JSON {"templates": [{"id", "name", "sections": {key: bool}}]}
    registration_templates_json = db.Column(db.Text, nullable=True)
    
    patients = db.relationship('Patient', backref='doctor', lazy=True)

    @property
    def social_handles(self):
        return parse_doctor_social_handle_json(self.social_handle)

    @property
    def clinics_list(self):
        return parse_doctor_clinics_list(self.clinics_json, self.clinic_name, self.address_text)


class DoctorExternalProfile(db.Model):
    """Optional public / external-facing copy (left panel on profile_ext). Name is stored on Doctor.full_name."""
    __tablename__ = 'doctor_external_profiles'

    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), unique=True, nullable=False)
    headline = db.Column(db.String(200), nullable=True)
    public_bio = db.Column(db.Text, nullable=True)
    # JSON arrays for public profile_ext left panel (see migrate_doctor_external_profiles_schema)
    conditions_treated_json = db.Column(db.Text, nullable=True)  # list[str]
    accolades_json = db.Column(db.Text, nullable=True)  # list[str]
    care_model_json = db.Column(db.Text, nullable=True)  # list[{"title","body"}]
    hero_pills_json = db.Column(db.Text, nullable=True)  # extra hero pills (Reg: always from Doctor.kmc_code)
    # JSON list[str] — Google Maps share URLs per clinic, same order as Doctor.clinics_list
    clinic_map_links_json = db.Column(db.Text, nullable=True)

    doctor = db.relationship('Doctor', backref=db.backref('external_profile', uselist=False))


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
    email = db.Column(db.String(120), nullable=True)  # For appointment and medication reminders
    attender_name = db.Column(db.String(100))
    attender_relation = db.Column(db.String(50))
    attender_reliability = db.Column(db.String(10))  # 'Yes' or 'No'
    personal_notes = db.Column(db.Text)  # Patient recall cue (private, doctor-only)

    # Patient-specific reminder days override (e.g. "7,3,1"). If empty, doctor's appointment_reminder_days is used.
    appointment_reminder_days = db.Column(db.String(50), nullable=True)
    
    visits = db.relationship('Visit', backref='patient', lazy=True, cascade='all, delete-orphan')
    adherence_ranges = db.relationship('AdherenceRange', backref='patient', lazy=True, foreign_keys='AdherenceRange.patient_id')
    clinical_state_ranges = db.relationship('ClinicalStateRange', backref='patient', lazy=True, foreign_keys='ClinicalStateRange.patient_id')


class Visit(db.Model):
    __tablename__ = 'visits'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    visit_type = db.Column(db.String(20), nullable=False)  # 'First' or 'Follow-up'
    quick_mode = db.Column(db.Boolean, nullable=False, default=False)
    provisional_diagnosis = db.Column(db.Text)
    differential_diagnosis = db.Column(db.Text)
    next_visit_date = db.Column(db.Date)
    type_of_next_follow_up = db.Column(db.String(80), nullable=True)
    note = db.Column(db.Text)
    
    clinical_state = db.Column(db.Text, nullable=True)  # JSON array of snapshot labels or legacy plain string
    medication_adherence = db.Column(db.String(50), nullable=True)
    ace_data = db.Column(db.Text, nullable=True)  # Adverse childhood experiences (JSON)
    family_history_psychiatric = db.Column(db.Text, nullable=True)  # JSON: {"present": bool, "items": ["Depression", "OTHERS: ..."]}
    developmental_milestone_delay = db.Column(db.Text, nullable=True)  # JSON: {"status": "No delay reported"|"Delay reported"|"Unknown", "types": [...], "notes": ""}
    functional_impairment = db.Column(db.Text, nullable=True)  # JSON: {"work": 0, "social": 0, "relationships": 0, "personal_care": 0, "leisure": 0}
    psychiatric_history_previously_treated = db.Column(db.String(10), nullable=True)  # Yes/No
    psychiatric_history_currently_on_treatment = db.Column(db.String(10), nullable=True)  # Yes/No
    psychiatric_history_previous_diagnosis = db.Column(db.Text, nullable=True)  # JSON list
    psychiatric_history_medication_history = db.Column(db.Text, nullable=True)  # JSON list
    psychiatric_history_duration_of_illness = db.Column(db.String(100), nullable=True)

    symptom_entries = db.relationship('SymptomEntry', backref='visit', lazy=True, cascade='all, delete-orphan')
    medication_entries = db.relationship('MedicationEntry', backref='visit', lazy=True, cascade='all, delete-orphan')
    side_effect_entries = db.relationship('SideEffectEntry', backref='visit', lazy=True, cascade='all, delete-orphan')
    mse_entries = db.relationship('MSEEntry', backref='visit', lazy=True, cascade='all, delete-orphan')
    
    # Phase 2: New Relationships
    stressor_entries = db.relationship('StressorEntry', backref='visit', lazy=True, cascade='all, delete-orphan')
    personality_entries = db.relationship('PersonalityEntry', backref='visit', lazy=True, cascade='all, delete-orphan')
    safety_profile = db.relationship('SafetyMedicalProfile', backref='visit', uselist=False, cascade='all, delete-orphan')
    major_events = db.relationship('MajorEvent', backref='visit', lazy=True, cascade='all, delete-orphan')
    adherence_ranges = db.relationship('AdherenceRange', backref='visit', lazy=True, foreign_keys='AdherenceRange.visit_id')
    clinical_state_ranges = db.relationship('ClinicalStateRange', backref='visit', lazy=True, foreign_keys='ClinicalStateRange.visit_id')
    substance_use_entries = db.relationship('SubstanceUseEntry', backref='visit', lazy=True, cascade='all, delete-orphan')
    scale_assessments = db.relationship('ScaleAssessment', backref='visit', lazy=True, cascade='all, delete-orphan')
    negative_history_entries = db.relationship('NegativeHistoryEntry', backref='visit', lazy=True, cascade='all, delete-orphan')


class NegativeHistoryEntry(db.Model):
    __tablename__ = 'negative_history_entries'

    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id'), nullable=False, index=True)
    item_id = db.Column(db.String(100), nullable=False)
    item_label = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Unknown')  # Yes / No / Unknown
    severity = db.Column(db.Integer, nullable=True)
    duration = db.Column(db.String(120), nullable=True)
    sequelae = db.Column(db.String(255), nullable=True)


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


class DoctorSymptomUsage(db.Model):
    __tablename__ = 'doctor_symptom_usage'

    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False, index=True)
    symptom_name = db.Column(db.String(200), nullable=False)
    symptom_key = db.Column(db.String(200), nullable=False)

    # JSON array of YYYY-MM-DD strings (one entry per day-of-use event)
    usage_dates_json = db.Column(db.Text, nullable=False, default='[]')
    last_used_at = db.Column(db.DateTime, nullable=True)

    # Cached score refreshed once per day
    score_cached = db.Column(db.Float, nullable=False, default=0.0)
    score_updated_on = db.Column(db.Date, nullable=True)

    __table_args__ = (db.UniqueConstraint('doctor_id', 'symptom_key', name='_doctor_symptom_key_uc'),)


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
    category = db.Column(db.String(50), nullable=False)  # 'Thought', 'Perception', 'Mood', 'Structured'
    finding_name = db.Column(db.String(200))
    
    # Phase 1: 3 Sliders Support
    score_onset = db.Column(db.Float)
    score_progression = db.Column(db.Float)
    score_current = db.Column(db.Float, nullable=False)  # Renamed from 'score'
    
    duration = db.Column(db.String(100))
    note = db.Column(db.Text)

    # New: Insight + Additional MSE findings
    insight_status = db.Column(db.String(20))  # 'Present', 'Partial', 'Absent'
    insight_grade = db.Column(db.Integer)      # 1–6, if graded
    addl_mse_f_note = db.Column(db.Text)       # Additional MSE findings (free text)

    # Structured MSE fields — only populated when category == 'Structured'
    consciousness = db.Column(db.String(50))
    appearance = db.Column(db.String(50))
    cooperation = db.Column(db.String(50))
    rapport = db.Column(db.String(50))
    eye_contact = db.Column(db.Text)  # JSON list
    psychomotor = db.Column(db.String(50))
    involuntary_movements = db.Column(db.Text)  # JSON list
    speech_reaction_time = db.Column(db.String(50))
    speech_relevance = db.Column(db.String(50))
    speech_coherence = db.Column(db.String(50))
    speech_intensity = db.Column(db.String(50))
    speech_pitch = db.Column(db.String(50))
    speech_ease = db.Column(db.String(50))
    affect_items = db.Column(db.Text)  # JSON list
    affect_reactivity = db.Column(db.String(20))
    affect_range = db.Column(db.String(30))
    affect_congruence = db.Column(db.String(20))
    affect_appropriateness = db.Column(db.String(20))
    
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
        """Compare expiry to current IST (naive) so 30-minute links match Indian time."""
        ist_now = datetime.utcnow() + timedelta(hours=5, minutes=30)
        return self.expires_at < ist_now


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
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id'), nullable=True)  # optional: which visit last updated
    status = db.Column(db.String(50), nullable=False)  # 'Complete', 'Partial', 'No Adherence'
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)


class ClinicalStateRange(db.Model):
    __tablename__ = 'clinical_state_ranges'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id'), nullable=True)  # optional: which visit last updated
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


class SubstanceUseEntry(db.Model):
    __tablename__ = 'substance_use_entries'

    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id'), nullable=False)
    substance_name = db.Column(db.String(200), nullable=False)
    pattern = db.Column(db.String(100))
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    note = db.Column(db.Text)

    # Extended structured fields for new UI
    age_at_first_use = db.Column(db.Integer, nullable=True)
    current_status = db.Column(db.String(50), nullable=True)  # 'Ongoing Use', 'Currently Abstinent', 'Past Use'
    has_abstinence_history = db.Column(db.Boolean, nullable=True)
    longest_abstinence_months = db.Column(db.Integer, nullable=True)  # legacy / graphing; optional
    abstinent_since = db.Column(db.Date, nullable=True)  # interpreted from Month + Year
    # Ongoing use: dropdown capture (e.g. "3 Months", "1 Year")
    last_use_ago = db.Column(db.String(80), nullable=True)
    abstinence_duration = db.Column(db.String(80), nullable=True)


class ScaleAssessment(db.Model):
    __tablename__ = 'scale_assessment'

    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey('visits.id'), nullable=False)
    scale_id = db.Column(db.String(50), nullable=False)   # e.g. 'CIWA-Ar' or 'Y-BOCS'
    scale_name = db.Column(db.String(100), nullable=False)
    total_score = db.Column(db.Integer, nullable=False)
    severity_label = db.Column(db.String(100), nullable=False)
    raw_responses = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Appointment(db.Model):
    __tablename__ = 'appointments'

    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer)
    sex = db.Column(db.String(10))
    start_time = db.Column(db.String(20))  # e.g. "09:00"
    slot_duration = db.Column(db.Integer)  # 15 or 30
    type = db.Column(db.String(50))  # 'New Case' or 'Follow-up'
    status = db.Column(db.String(50), default='Confirmed')  # 'Confirmed', 'Pending', 'Postponed'
    view_details = db.Column(db.Text)
    email = db.Column(db.String(120), nullable=True)  # Patient email for appointment reminders
    # Visit format: In-person | Online (DB column name "format" — Python attr appt_format)
    appt_format = db.Column("format", db.String(20), nullable=True, default="In-person")


class DashboardNote(db.Model):
    __tablename__ = 'dashboard_notes'

    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=True)
    message = db.Column(db.String(255), nullable=False)
    trigger_time = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)


class ScheduleTemplate(db.Model):
    __tablename__ = 'schedule_templates'

    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    is_default = db.Column(db.Boolean, default=False)

    # Stored as JSON list of dicts: [{"start": "09:00", "end": "17:00"}, {"start": "17:00", "end": "22:00"}]
    working_hours = db.Column(db.JSON, nullable=False)

    # Stored as JSON dict: {"New Registration": 45, "Extended Follow-up": 30, "Follow-up": 15, ...}
    slot_durations = db.Column(db.JSON, nullable=False)


class Feedback(db.Model):
    __tablename__ = 'feedback'

    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    issue_type = db.Column(db.String(100), nullable=False)
    other_issue_type = db.Column(db.String(255), nullable=True)
    priority = db.Column(db.String(20), nullable=False, default='Minor')
    description = db.Column(db.Text, nullable=False)
    screenshot = db.Column(db.LargeBinary, nullable=True)
    screenshot_name = db.Column(db.String(255), nullable=True)
    screenshot_mimetype = db.Column(db.String(80), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    doctor = db.relationship('Doctor', backref=db.backref('feedbacks', lazy=True))


def migrate_doctor_external_profiles_schema(cursor, column_exists_fn, table_exists_fn):
    """
    SQLite: ensure doctor_external_profiles exists and has headline + public_bio.
    Used by migrate_db.py (create_all does not add columns to existing tables).

    Args:
        cursor: sqlite3 cursor from db.engine.raw_connection()
        column_exists_fn: (cursor, table_name, column_name) -> bool
        table_exists_fn: (cursor, table_name) -> bool
    """
    print("\n[Doctor External Profiles]")
    if not table_exists_fn(cursor, 'doctor_external_profiles'):
        cursor.execute(
            """
            CREATE TABLE doctor_external_profiles (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                doctor_id INTEGER NOT NULL UNIQUE,
                headline VARCHAR(200),
                public_bio TEXT,
                conditions_treated_json TEXT,
                accolades_json TEXT,
                care_model_json TEXT,
                hero_pills_json TEXT,
                clinic_map_links_json TEXT,
                FOREIGN KEY (doctor_id) REFERENCES doctors (id)
            )
            """
        )
        print("  + Created doctor_external_profiles table")
        return
    print("  - doctor_external_profiles table exists")
    for col, spec in (
        ('headline', 'VARCHAR(200)'),
        ('public_bio', 'TEXT'),
        ('conditions_treated_json', 'TEXT'),
        ('accolades_json', 'TEXT'),
        ('care_model_json', 'TEXT'),
        ('hero_pills_json', 'TEXT'),
        ('clinic_map_links_json', 'TEXT'),
    ):
        if not column_exists_fn(cursor, 'doctor_external_profiles', col):
            cursor.execute(f'ALTER TABLE doctor_external_profiles ADD COLUMN {col} {spec}')
            print(f"  + Added {col}")
        else:
            print(f"  - {col} exists")


def migrate_doctor_social_handle_normalize(session):
    """
    One-time style: rewrite each doctor.social_handle to canonical JSON.
    Legacy plain text becomes instagram-only JSON.
    """
    changed = 0
    for d in Doctor.query.all():
        raw = d.social_handle
        if raw is None:
            continue
        if isinstance(raw, str) and not raw.strip():
            continue
        parsed = parse_doctor_social_handle_json(raw)
        new_s = serialize_doctor_social_handle_json(
            parsed["linkedin"], parsed["website"], parsed["instagram"]
        )
        if new_s != raw:
            d.social_handle = new_s
            changed += 1
    if changed:
        session.commit()
    return changed


def migrate_doctor_clinics_normalize(session):
    """
    Backfill doctors.clinics_json from legacy clinic_name + address_text when JSON is empty.
    """
    changed = 0
    for d in Doctor.query.all():
        raw = d.clinics_json
        if raw and str(raw).strip():
            continue
        ln = (d.clinic_name or "").strip()
        la = (d.address_text or "").strip()
        if not ln and not la:
            continue
        d.clinics_json = json.dumps(
            [{"name": ln[:300], "address": la[:4000]}], ensure_ascii=False
        )
        changed += 1
    if changed:
        session.commit()
    return changed
