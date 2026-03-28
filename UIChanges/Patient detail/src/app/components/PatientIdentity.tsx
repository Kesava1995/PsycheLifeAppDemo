import { useState, useEffect } from 'react';

interface PatientIdentityProps {
  name: string;
  age: number;
  sex: string;
  uniqueId: string;
  quickRecallCue: string;
  phone: string;
  email: string;
}

export function PatientIdentity({ name, age, sex, uniqueId, quickRecallCue, phone, email }: PatientIdentityProps) {
  const [isScrolled, setIsScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = (e: Event) => {
      const target = e.target as HTMLElement;
      setIsScrolled(target.scrollTop > 50);
    };

    const leftPanel = document.getElementById('left-panel');
    if (leftPanel) {
      leftPanel.addEventListener('scroll', handleScroll);
      return () => leftPanel.removeEventListener('scroll', handleScroll);
    }
  }, []);

  const initials = name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();

  if (isScrolled) {
    return (
      <div className="bg-white border-b border-[#e4ecec] px-4 py-2 flex items-center gap-3" style={{ height: '48px' }}>
        <div className="flex items-center justify-center rounded-full bg-[#006672] text-white" style={{ width: '32px', height: '32px', fontFamily: 'Manrope, sans-serif', fontWeight: 700, fontSize: '13px' }}>
          {initials}
        </div>
        <div>
          <div style={{ fontFamily: 'Manrope, sans-serif', fontWeight: 700, fontSize: '14px', color: '#181c1d' }}>
            {name}
          </div>
          <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 500, fontSize: '11px', color: '#3d5050' }}>
            {uniqueId}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="px-4 py-5 bg-white border-b border-[#e4ecec]">
      <div className="flex items-start gap-3 mb-3">
        <div className="flex items-center justify-center bg-[#006672] text-white" style={{ width: '64px', height: '64px', borderRadius: '10px', fontFamily: 'Manrope, sans-serif', fontWeight: 700, fontSize: '24px' }}>
          {initials}
        </div>
        <div className="flex-1">
          <div style={{ fontFamily: 'Manrope, sans-serif', fontWeight: 700, fontSize: '18px', color: '#181c1d', marginBottom: '2px' }}>
            {name}
          </div>
          <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 500, fontSize: '13px', color: '#3d5050', marginBottom: '2px' }}>
            {age}Y • {sex}
          </div>
          <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 500, fontSize: '12px', color: '#3d5050' }}>
            {uniqueId}
          </div>
        </div>
      </div>

      <div className="mb-3 p-3 bg-[#fef9ec] border-l-4 border-[#f59e0b] rounded-lg" style={{ borderLeftWidth: '3px' }}>
        <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 500, fontSize: '13px', color: '#92620a', fontStyle: 'italic' }}>
          {quickRecallCue}
        </div>
      </div>

      <div className="space-y-1">
        <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 400, fontSize: '13px', color: '#3d5050' }}>
          📞 {phone}
        </div>
        <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 400, fontSize: '13px', color: '#3d5050' }}>
          ✉️ {email}
        </div>
      </div>
    </div>
  );
}
