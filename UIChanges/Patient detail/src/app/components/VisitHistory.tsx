import { useState } from 'react';

interface Visit {
  id: string;
  date: string;
  type: string;
  provisionalDiagnosis: string;
  clinicalState: string;
  chiefComplaints: string;
  medications: string[];
  mse: string;
  nextFollowUp: string;
}

interface VisitHistoryProps {
  visits: Visit[];
  onEdit: (id: string) => void;
  onDelete: (id: string) => void;
}

export function VisitHistory({ visits, onEdit, onDelete }: VisitHistoryProps) {
  const [selectedVisit, setSelectedVisit] = useState<Visit | null>(null);

  if (visits.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div style={{ fontSize: '48px', marginBottom: '16px' }}>📋</div>
        <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 400, fontSize: '14px', color: '#9aacae', marginBottom: '16px' }}>
          No visits recorded yet
        </div>
        <button 
          className="px-5 py-2 bg-[#006672] text-white rounded-lg hover:bg-[#005560] transition-colors"
          style={{ fontFamily: 'Inter, sans-serif', fontWeight: 500, fontSize: '14px' }}
        >
          Add First Visit
        </button>
      </div>
    );
  }

  return (
    <>
      <div className="flex items-end justify-between mb-5">
        <div style={{ fontFamily: 'Manrope, sans-serif', fontWeight: 700, fontSize: '20px', color: '#181c1d' }}>
          Visit History
        </div>
        <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 400, fontSize: '13px', color: '#3d5050' }}>
          {visits.length} visits total
        </div>
      </div>

      <div className="space-y-2">
        {visits.map((visit) => (
          <div 
            key={visit.id}
            className="bg-white border border-[#e4ecec] rounded-xl p-4 cursor-pointer hover:bg-[#f8fafa] hover:border-[#bdc8cb] transition-all duration-150"
            onClick={(e) => {
              if (!(e.target as HTMLElement).closest('.action-button')) {
                setSelectedVisit(visit);
              }
            }}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: '14px', color: '#006672', marginBottom: '4px' }}>
                  {new Date(visit.date).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })}
                </div>
                <span 
                  className="inline-block bg-[#e4ecec] px-3 py-1 rounded-full mb-2"
                  style={{ fontFamily: 'Inter, sans-serif', fontWeight: 500, fontSize: '12px', color: '#3f4948' }}
                >
                  {visit.type}
                </span>
                <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 400, fontSize: '13px', color: '#3d5050' }}>
                  {visit.provisionalDiagnosis}
                </div>
              </div>
              <div className="flex items-center gap-3 action-button">
                <button 
                  onClick={() => onEdit(visit.id)}
                  className="hover:opacity-70 transition-opacity"
                  style={{ fontSize: '14px', color: '#9aacae' }}
                >
                  ✏️
                </button>
                <button 
                  onClick={() => onDelete(visit.id)}
                  className="hover:opacity-70 transition-opacity"
                  style={{ fontSize: '14px', color: '#9aacae' }}
                >
                  🗑️
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {selectedVisit && (
        <>
          <div 
            className="fixed inset-0 bg-black/50 z-40"
            onClick={() => setSelectedVisit(null)}
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={() => setSelectedVisit(null)}>
            <div 
              className="bg-white rounded-2xl shadow-xl p-8" 
              style={{ width: '600px', maxWidth: '90vw', maxHeight: '80vh', overflowY: 'auto', scrollbarWidth: 'none', msOverflowStyle: 'none' }}
              onClick={(e) => e.stopPropagation()}
            >
              <style>{`
                .bg-white::-webkit-scrollbar {
                  display: none;
                }
              `}</style>
              
              <h3 style={{ fontFamily: 'Manrope, sans-serif', fontWeight: 600, fontSize: '18px', color: '#181c1d', marginBottom: '20px' }}>
                {new Date(selectedVisit.date).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })} • {selectedVisit.type}
              </h3>
              
              <div className="space-y-4 mb-6">
                <div>
                  <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: '12px', color: '#9aacae', textTransform: 'uppercase', marginBottom: '4px' }}>
                    PROVISIONAL DIAGNOSIS
                  </div>
                  <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 400, fontSize: '14px', color: '#181c1d' }}>
                    {selectedVisit.provisionalDiagnosis}
                  </div>
                </div>

                <div>
                  <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: '12px', color: '#9aacae', textTransform: 'uppercase', marginBottom: '4px' }}>
                    CLINICAL STATE
                  </div>
                  <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 400, fontSize: '14px', color: '#181c1d' }}>
                    {selectedVisit.clinicalState}
                  </div>
                </div>

                <div>
                  <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: '12px', color: '#9aacae', textTransform: 'uppercase', marginBottom: '4px' }}>
                    CHIEF COMPLAINTS
                  </div>
                  <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 400, fontSize: '14px', color: '#181c1d' }}>
                    {selectedVisit.chiefComplaints}
                  </div>
                </div>

                <div>
                  <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: '12px', color: '#9aacae', textTransform: 'uppercase', marginBottom: '4px' }}>
                    MEDICATIONS PRESCRIBED
                  </div>
                  <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 400, fontSize: '14px', color: '#181c1d' }}>
                    {selectedVisit.medications.join(', ')}
                  </div>
                </div>

                <div>
                  <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: '12px', color: '#9aacae', textTransform: 'uppercase', marginBottom: '4px' }}>
                    MSE SUMMARY
                  </div>
                  <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 400, fontSize: '14px', color: '#181c1d' }}>
                    {selectedVisit.mse}
                  </div>
                </div>

                <div>
                  <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: '12px', color: '#9aacae', textTransform: 'uppercase', marginBottom: '4px' }}>
                    NEXT FOLLOW-UP
                  </div>
                  <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 400, fontSize: '14px', color: '#181c1d' }}>
                    {selectedVisit.nextFollowUp}
                  </div>
                </div>
              </div>

              <div className="flex gap-3 justify-end pt-4 border-t border-[#e4ecec]">
                <button 
                  className="px-5 py-2 bg-[#006672] text-white rounded-lg hover:bg-[#005560] transition-colors"
                  style={{ fontFamily: 'Inter, sans-serif', fontWeight: 500, fontSize: '14px' }}
                >
                  View Full Performa
                </button>
                <button 
                  onClick={() => setSelectedVisit(null)}
                  className="px-5 py-2 hover:bg-[#f4f5f5] rounded-lg transition-colors"
                  style={{ fontFamily: 'Inter, sans-serif', fontWeight: 500, fontSize: '14px', color: '#3d5050' }}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
}