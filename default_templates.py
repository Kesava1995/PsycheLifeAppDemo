from app import app, db, DefaultTemplate
import json

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

with app.app_context():
    for name, syms in defaults.items():
        # Check if already exists to avoid duplicates
        if not DefaultTemplate.query.filter_by(name=name).first():
            db.session.add(DefaultTemplate(name=name, symptoms=json.dumps(syms)))
    db.session.commit()
    print("Default templates filled successfully.")