import { useState } from 'react';

interface Medication {
  name: string;
  dose: string;
  frequency: string;
}

interface CurrentMedicationsProps {
  medications: Medication[];
}

export function CurrentMedications({ medications }: CurrentMedicationsProps) {
  const [hoveredMed, setHoveredMed] = useState<number | null>(null);

  return (
    <div className="px-4 py-3 border-b border-[#e4ecec]">
      <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: '11px', color: '#9aacae', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '8px' }}>
        MEDICATIONS
      </div>
      <div className="flex flex-wrap gap-2">
        {medications.map((med, index) => (
          <div key={index} className="relative">
            <span 
              className="inline-block bg-[#006672] text-white px-3 py-1 rounded-full cursor-pointer hover:bg-[#005560] transition-colors"
              style={{ fontFamily: 'Inter, sans-serif', fontWeight: 500, fontSize: '12px' }}
              onMouseEnter={() => setHoveredMed(index)}
              onMouseLeave={() => setHoveredMed(null)}
            >
              {med.name} {med.dose}
            </span>
            {hoveredMed === index && (
              <div 
                className="absolute z-10 bg-[#181c1d] text-white px-3 py-2 rounded-lg shadow-lg"
                style={{ 
                  fontFamily: 'Inter, sans-serif', 
                  fontWeight: 400, 
                  fontSize: '12px',
                  top: '100%',
                  left: '50%',
                  transform: 'translateX(-50%)',
                  marginTop: '4px',
                  whiteSpace: 'nowrap'
                }}
              >
                {med.frequency}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
