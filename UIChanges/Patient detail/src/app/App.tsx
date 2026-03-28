import { useState } from 'react';
import { Navbar } from './components/Navbar';
import { PatientIdentity } from './components/PatientIdentity';
import { ActionButtons } from './components/ActionButtons';
import { AlertsCard } from './components/AlertsCard';
import { ClinicalSummary } from './components/ClinicalSummary';
import { CurrentMedications } from './components/CurrentMedications';
import { BackgroundBadges } from './components/BackgroundBadges';
import { Tags } from './components/Tags';
import { SendCustomMessage } from './components/SendCustomMessage';
import { Notes } from './components/Notes';
import { VisitHistory } from './components/VisitHistory';

// Mock data
const initialNotes = [
  {
    date: '2026-03-20',
    text: 'Patient showing good response to current medication regimen. Family reports improved sleep patterns.',
    checked: false
  },
  {
    date: '2026-03-15',
    text: 'Follow-up scheduled in 2 weeks. Continue current treatment plan.',
    checked: true
  }
];

const visits = [
  {
    id: '1',
    date: '2026-03-12',
    type: 'Follow-up',
    provisionalDiagnosis: 'Schizophrenia, Paranoid Type',
    clinicalState: 'Stable',
    chiefComplaints: 'Patient reports reduced auditory hallucinations. Sleep quality has improved. Still experiencing some mild paranoid ideation.',
    medications: ['Olanzapine 10mg', 'Clonazepam 0.5mg'],
    mse: 'Cooperative, well-groomed. Speech coherent. Mood euthymic. No active psychotic symptoms observed during interview. Insight partial.',
    nextFollowUp: '26 March 2026'
  },
  {
    id: '2',
    date: '2026-02-28',
    type: 'Initial Assessment',
    provisionalDiagnosis: 'Schizophrenia, Paranoid Type',
    clinicalState: 'Acute',
    chiefComplaints: 'Persistent auditory hallucinations for past 3 months. Command hallucinations. Sleep disturbance. Social withdrawal.',
    medications: ['Olanzapine 10mg'],
    mse: 'Guarded, poor eye contact. Tangential speech. Mood anxious. Active auditory hallucinations. Poor insight.',
    nextFollowUp: '12 March 2026'
  },
  {
    id: '3',
    date: '2026-02-15',
    type: 'Consultation',
    provisionalDiagnosis: 'Rule out Psychotic Disorder',
    clinicalState: 'Evaluation',
    chiefComplaints: 'Family brought patient due to bizarre behavior, talking to self, suspiciousness of family members.',
    medications: [],
    mse: 'Disheveled appearance, guarded. Disorganized speech. Mood labile. Appears to be responding to internal stimuli.',
    nextFollowUp: '28 February 2026'
  }
];

const backgroundItems = [
  {
    label: 'Premorbid Personality',
    findings: ['Anxious', 'Introverted', 'Perfectionistic']
  },
  {
    label: 'Adverse Childhood Experiences',
    findings: ['Witnessed domestic violence', 'Parental separation']
  },
  {
    label: 'Family Psychiatric History',
    findings: ['Maternal uncle - bipolar', 'Maternal grandmother - nervous breakdown']
  },
  {
    label: 'Drug Allergies',
    findings: ['Penicillin - rash']
  }
];

export default function App() {
  const [notes, setNotes] = useState(initialNotes);
  const [tags, setTags] = useState(['HighRisk', 'NonCompliant', 'VIP']);

  const handleAddNote = (note: { date: string; text: string }) => {
    setNotes([{ ...note, checked: false }, ...notes]);
  };

  const handleToggleNote = (index: number) => {
    const newNotes = [...notes];
    newNotes[index].checked = !newNotes[index].checked;
    setNotes(newNotes);
  };

  const handleAddTag = (tag: string) => {
    if (!tags.includes(tag)) {
      setTags([...tags, tag]);
    }
  };

  const handleRemoveTag = (tag: string) => {
    setTags(tags.filter(t => t !== tag));
  };

  const handleEditVisit = (id: string) => {
    console.log('Edit visit:', id);
  };

  const handleDeleteVisit = (id: string) => {
    console.log('Delete visit:', id);
  };

  return (
    <div className="min-h-screen bg-[#f4f5f5]">
      <Navbar />
      
      <div className="flex" style={{ height: 'calc(100vh - 65px)' }}>
        {/* Left Panel - 50% width */}
        <div 
          id="left-panel"
          className="bg-white border-r border-[#e4ecec]"
          style={{ 
            width: '50%', 
            height: '100%',
            overflowY: 'auto',
            scrollBehavior: 'smooth',
            scrollbarWidth: 'none',
            msOverflowStyle: 'none',
            WebkitOverflowScrolling: 'touch'
          }}
        >
          <style>{`
            #left-panel::-webkit-scrollbar {
              display: none;
            }
          `}</style>
          
          <PatientIdentity 
            name="Rajesh Kumar"
            age={28}
            sex="Male"
            uniqueId="PT-2024-0847"
            quickRecallCue="Young IT professional. First episode psychosis. Lives with parents."
            phone="+91 98765 43210"
            email="rajesh.k@email.com"
          />
          
          <ActionButtons />
          
          <AlertsCard flags={['Suicidality', 'Active Substance Use']} />
          
          <ClinicalSummary 
            provisionalDiagnosis="Schizophrenia, Paranoid Type"
            differentials={[
              'Brief Psychotic Disorder',
              'Substance-Induced Psychotic Disorder'
            ]}
            clinicalState="Stable"
          />
          
          <CurrentMedications 
            medications={[
              { name: 'Olanzapine', dose: '10mg', frequency: 'Once daily at bedtime' },
              { name: 'Clonazepam', dose: '0.5mg', frequency: 'Twice daily' }
            ]}
          />
          
          <BackgroundBadges items={backgroundItems} />
          
          <Tags tags={tags} onAddTag={handleAddTag} onRemoveTag={handleRemoveTag} />
          
          <SendCustomMessage 
            patientContact="+91 98765 43210"
            patientEmail="rajesh.k@email.com"
          />
          
          <Notes notes={notes} onAddNote={handleAddNote} onToggleNote={handleToggleNote} />
        </div>

        {/* Right Panel - 50% width */}
        <div 
          className="flex-1 px-8 py-7"
          style={{ 
            width: '50%',
            height: '100%',
            overflowY: 'auto',
            scrollBehavior: 'smooth',
            scrollbarWidth: 'none',
            msOverflowStyle: 'none',
            WebkitOverflowScrolling: 'touch',
            backgroundColor: '#f4f5f5'
          }}
        >
          <style>{`
            .flex-1::-webkit-scrollbar {
              display: none;
            }
          `}</style>
          
          <VisitHistory 
            visits={visits}
            onEdit={handleEditVisit}
            onDelete={handleDeleteVisit}
          />
        </div>
      </div>
    </div>
  );
}