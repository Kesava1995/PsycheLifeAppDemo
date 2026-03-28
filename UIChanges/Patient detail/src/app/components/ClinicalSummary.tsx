interface ClinicalSummaryProps {
  provisionalDiagnosis: string;
  differentials: string[];
  clinicalState: string;
}

export function ClinicalSummary({ provisionalDiagnosis, differentials, clinicalState }: ClinicalSummaryProps) {
  return (
    <div className="border-b border-[#e4ecec]">
      <div className="px-4 py-3">
        <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: '11px', color: '#9aacae', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '8px' }}>
          CURRENT DIAGNOSIS
        </div>
        <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: '14px', color: '#181c1d', marginBottom: '6px' }}>
          {provisionalDiagnosis}
        </div>
        {differentials.map((diff, index) => (
          <div key={index} style={{ fontFamily: 'Inter, sans-serif', fontWeight: 400, fontSize: '13px', color: '#3d5050', marginBottom: '3px' }}>
            · {diff}
          </div>
        ))}
      </div>

      <div className="px-4 py-3 border-t border-[#e4ecec]">
        <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: '11px', color: '#9aacae', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '8px' }}>
          CLINICAL STATE
        </div>
        <span 
          className="inline-block bg-[#e4ecec] px-3 py-1 rounded-full"
          style={{ fontFamily: 'Inter, sans-serif', fontWeight: 500, fontSize: '13px', color: '#181c1d' }}
        >
          {clinicalState}
        </span>
      </div>
    </div>
  );
}
