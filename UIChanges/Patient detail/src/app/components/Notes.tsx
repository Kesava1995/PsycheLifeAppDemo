import { useState } from 'react';

interface Note {
  date: string;
  text: string;
  checked: boolean;
}

interface NotesProps {
  notes: Note[];
  onAddNote: (note: { date: string; text: string }) => void;
  onToggleNote: (index: number) => void;
}

export function Notes({ notes, onAddNote, onToggleNote }: NotesProps) {
  const [showModal, setShowModal] = useState(false);
  const [noteDate, setNoteDate] = useState(new Date().toISOString().split('T')[0]);
  const [noteText, setNoteText] = useState('');

  const handleSave = () => {
    if (noteText.trim()) {
      onAddNote({ date: noteDate, text: noteText });
      setNoteText('');
      setNoteDate(new Date().toISOString().split('T')[0]);
      setShowModal(false);
    }
  };

  return (
    <div className="px-4 py-3">
      <div className="flex items-center justify-between mb-3">
        <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: '11px', color: '#9aacae', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          NOTES
        </div>
        <button 
          onClick={() => setShowModal(true)}
          className="flex items-center justify-center bg-[#006672] text-white rounded-full hover:bg-[#005560] transition-colors"
          style={{ width: '24px', height: '24px', fontSize: '14px' }}
        >
          +
        </button>
      </div>

      {notes.length === 0 ? (
        <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 400, fontSize: '13px', color: '#9aacae', fontStyle: 'italic' }}>
          No notes for this patient.
        </div>
      ) : (
        <div className="space-y-2">
          {notes.map((note, index) => (
            <div key={index} className="bg-[#f8fafa] rounded-lg p-3 flex items-start gap-2.5" style={{ transition: 'all 150ms' }}>
              <button 
                onClick={() => onToggleNote(index)}
                className="flex items-center justify-center cursor-pointer"
                style={{ 
                  width: '16px',
                  height: '16px',
                  minWidth: '16px',
                  borderRadius: '4px',
                  borderWidth: '1.5px',
                  borderColor: note.checked ? '#006672' : '#bdc8cb',
                  backgroundColor: note.checked ? '#006672' : 'white',
                  marginTop: '2px',
                  transition: 'all 150ms'
                }}
              >
                {note.checked && (
                  <span style={{ color: 'white', fontSize: '10px', lineHeight: 1 }}>✓</span>
                )}
              </button>
              <div className="flex-1">
                <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: '12px', color: '#006672', marginBottom: '4px' }}>
                  {new Date(note.date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}
                </div>
                <div 
                  style={{ 
                    fontFamily: 'Inter, sans-serif', 
                    fontWeight: 400, 
                    fontSize: '13px', 
                    color: note.checked ? '#9aacae' : '#181c1d',
                    textDecoration: note.checked ? 'line-through' : 'none',
                    transition: 'all 150ms'
                  }}
                >
                  {note.text}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <>
          <div 
            className="fixed inset-0 bg-black/50 z-40"
            onClick={() => setShowModal(false)}
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl shadow-xl p-8" style={{ width: '500px', maxWidth: '90vw' }}>
              <h3 style={{ fontFamily: 'Manrope, sans-serif', fontWeight: 600, fontSize: '18px', color: '#181c1d', marginBottom: '20px' }}>
                Add Note
              </h3>
              
              <div className="mb-4">
                <label style={{ fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: '13px', color: '#3d5050', display: 'block', marginBottom: '6px' }}>
                  Date
                </label>
                <input 
                  type="date"
                  value={noteDate}
                  onChange={(e) => setNoteDate(e.target.value)}
                  className="w-full px-3 py-2 border border-[#d2dcdc] rounded-lg"
                  style={{ fontFamily: 'Inter, sans-serif', fontSize: '14px' }}
                />
              </div>

              <div className="mb-6">
                <label style={{ fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: '13px', color: '#3d5050', display: 'block', marginBottom: '6px' }}>
                  Note / Reminder
                </label>
                <textarea 
                  value={noteText}
                  onChange={(e) => setNoteText(e.target.value)}
                  className="w-full px-3 py-2 border border-[#d2dcdc] rounded-lg resize-none"
                  style={{ fontFamily: 'Inter, sans-serif', fontSize: '14px', minHeight: '120px' }}
                  placeholder="Enter your note here..."
                />
              </div>

              <div className="flex gap-3 justify-end">
                <button 
                  onClick={() => setShowModal(false)}
                  className="px-5 py-2 rounded-lg hover:bg-[#f4f5f5] transition-colors"
                  style={{ fontFamily: 'Inter, sans-serif', fontWeight: 500, fontSize: '14px', color: '#3d5050' }}
                >
                  Cancel
                </button>
                <button 
                  onClick={handleSave}
                  className="px-5 py-2 bg-[#006672] text-white rounded-lg hover:bg-[#005560] transition-colors"
                  style={{ fontFamily: 'Inter, sans-serif', fontWeight: 500, fontSize: '14px' }}
                >
                  Save
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
