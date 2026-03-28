interface BackgroundItem {
  label: string;
  findings: string[];
}

interface BackgroundBadgesProps {
  items: BackgroundItem[];
}

export function BackgroundBadges({ items }: BackgroundBadgesProps) {
  if (items.length === 0) return null;

  return (
    <div className="px-4 py-3 border-b border-[#e4ecec]">
      <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: '11px', color: '#9aacae', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '8px' }}>
        BACKGROUND
      </div>
      <div className="flex flex-wrap gap-2">
        {items.map((item, index) => (
          <div 
            key={index} 
            className="bg-white border border-[#e4ecec] rounded-xl p-3"
          >
            <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: '13px', color: '#3f4948', marginBottom: '8px' }}>
              {item.label}
            </div>
            <div className="flex flex-wrap gap-1.5">
              {item.findings.map((finding, fIndex) => (
                <span 
                  key={fIndex}
                  className="inline-block bg-[#e4ecec] px-2.5 py-1 rounded-full"
                  style={{ fontFamily: 'Inter, sans-serif', fontWeight: 500, fontSize: '12px', color: '#006672' }}
                >
                  {finding}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
