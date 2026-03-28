interface AlertsCardProps {
  flags: string[];
}

export function AlertsCard({ flags }: AlertsCardProps) {
  if (flags.length === 0) return null;

  return (
    <div className="mx-4 my-3 p-4 bg-[#fff0f0] border-l-4 border-[#ba1a1a] rounded-lg">
      <div className="flex items-center gap-1 mb-2" style={{ fontFamily: 'Inter, sans-serif', fontWeight: 700, fontSize: '13px', color: '#ba1a1a' }}>
        <span>⚠️</span>
        <span>Alerts</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {flags.map((flag, index) => (
          <span 
            key={index}
            className="bg-[#fee2e2] text-[#991b1b] px-3 py-1 rounded-full"
            style={{ fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: '12px' }}
          >
            {flag}
          </span>
        ))}
      </div>
    </div>
  );
}
