import { useState } from 'react';

interface SendCustomMessageProps {
  patientContact: string;
  patientEmail: string;
}

const templates = {
  'Appointment reminder': 'Hello, this is a reminder about your upcoming appointment with Dr. [Name] on [Date] at [Time]. Please confirm your attendance.',
  'Follow-up reminder': 'Hello, you are due for a follow-up visit. Please contact us to schedule an appointment at your earliest convenience.',
  'Lab report ready': 'Your lab reports are ready. Please visit the clinic to collect them or schedule an appointment to discuss the results.'
};

export function SendCustomMessage({ patientContact, patientEmail }: SendCustomMessageProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [selectedChannel, setSelectedChannel] = useState<'whatsapp' | 'gmail' | null>(null);
  const [subject, setSubject] = useState('');
  const [message, setMessage] = useState('');

  const handleTemplateClick = (templateName: string) => {
    if (templateName === 'Custom') {
      setMessage('');
    } else {
      setMessage(templates[templateName as keyof typeof templates] || '');
    }
  };

  const handleSend = () => {
    console.log('Sending message:', { channel: selectedChannel, subject, message });
    // Reset form
    setIsExpanded(false);
    setSelectedChannel(null);
    setSubject('');
    setMessage('');
  };

  const handleCancel = () => {
    setIsExpanded(false);
    setSelectedChannel(null);
    setSubject('');
    setMessage('');
  };

  return (
    <div className="px-4 py-3 border-b border-[#e4ecec]">
      <button 
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-center gap-2 bg-[#f8fafa] border rounded-lg hover:bg-[#f0f0f0] transition-colors"
        style={{ 
          padding: '12px 16px', 
          fontFamily: 'Inter, sans-serif', 
          fontWeight: 600, 
          fontSize: '13px', 
          color: '#181c1d',
          borderWidth: '1.5px',
          borderColor: '#e4ecec',
          borderRadius: '10px'
        }}
      >
        <span>✉️</span>
        <span>Send Custom Message</span>
      </button>

      <div 
        style={{ 
          maxHeight: isExpanded ? '1000px' : '0',
          overflow: 'hidden',
          transition: 'max-height 200ms ease-in-out'
        }}
      >
        <div className="mt-3 space-y-3">
          {/* Channel Selection */}
          <div className="flex gap-2">
            <button 
              onClick={() => setSelectedChannel('whatsapp')}
              className="flex-1 flex flex-col items-center justify-center gap-1.5 rounded-lg transition-all"
              style={{ 
                padding: '12px',
                fontFamily: 'Inter, sans-serif',
                fontWeight: 600,
                fontSize: '13px',
                backgroundColor: selectedChannel === 'whatsapp' ? '#dcfce7' : '#f0fdf4',
                borderWidth: selectedChannel === 'whatsapp' ? '2px' : '1.5px',
                borderColor: '#86efac',
                color: '#166534',
                borderRadius: '10px'
              }}
            >
              <span style={{ fontSize: '18px' }}>💬</span>
              <span>WhatsApp</span>
            </button>
            <button 
              onClick={() => setSelectedChannel('gmail')}
              className="flex-1 flex flex-col items-center justify-center gap-1.5 rounded-lg transition-all"
              style={{ 
                padding: '12px',
                fontFamily: 'Inter, sans-serif',
                fontWeight: 600,
                fontSize: '13px',
                backgroundColor: selectedChannel === 'gmail' ? '#fecaca' : '#fef2f2',
                borderWidth: selectedChannel === 'gmail' ? '2px' : '1.5px',
                borderColor: '#fca5a5',
                color: '#991b1b',
                borderRadius: '10px'
              }}
            >
              <span style={{ fontSize: '18px' }}>📧</span>
              <span>Gmail</span>
            </button>
          </div>

          {/* Compose Area */}
          {selectedChannel && (
            <div 
              className="space-y-3"
              style={{ 
                maxHeight: selectedChannel ? '1000px' : '0',
                overflow: 'hidden',
                transition: 'max-height 200ms ease-in-out'
              }}
            >
              {/* To field */}
              <div>
                <label style={{ fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: '12px', color: '#3d5050', display: 'block', marginBottom: '4px' }}>
                  To:
                </label>
                <div 
                  className="w-full px-3 py-2 bg-[#f8fafa] border border-[#e4ecec] rounded-lg"
                  style={{ fontFamily: 'Inter, sans-serif', fontSize: '13px', color: '#3d5050' }}
                >
                  {selectedChannel === 'whatsapp' ? patientContact : patientEmail}
                </div>
              </div>

              {/* Subject (Gmail only) */}
              {selectedChannel === 'gmail' && (
                <div>
                  <label style={{ fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: '12px', color: '#3d5050', display: 'block', marginBottom: '4px' }}>
                    Subject:
                  </label>
                  <input 
                    type="text"
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                    className="w-full px-3 py-2 border border-[#e4ecec] rounded-lg"
                    style={{ fontFamily: 'Inter, sans-serif', fontSize: '13px' }}
                    placeholder="Enter subject"
                  />
                </div>
              )}

              {/* Message */}
              <div>
                <label style={{ fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: '12px', color: '#3d5050', display: 'block', marginBottom: '4px' }}>
                  Message:
                </label>
                <textarea 
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  className="w-full px-3 py-2 border border-[#e4ecec] rounded-lg resize-none"
                  style={{ fontFamily: 'Inter, sans-serif', fontSize: '14px', minHeight: '100px' }}
                  placeholder="Type your message here..."
                />
              </div>

              {/* Quick Templates */}
              <div>
                <div style={{ fontFamily: 'Inter, sans-serif', fontSize: '11px', color: '#9aacae', marginBottom: '6px' }}>
                  Quick templates:
                </div>
                <div className="flex flex-wrap gap-2">
                  {['Appointment reminder', 'Follow-up reminder', 'Lab report ready', 'Custom'].map((template) => (
                    <button 
                      key={template}
                      onClick={() => handleTemplateClick(template)}
                      className="px-2.5 py-1 bg-[#e4ecec] hover:bg-[#d2dcdc] rounded-full transition-colors"
                      style={{ fontFamily: 'Inter, sans-serif', fontSize: '11px', color: '#3d5050' }}
                    >
                      {template}
                    </button>
                  ))}
                </div>
              </div>

              {/* Send Button */}
              <button 
                onClick={handleSend}
                className="w-full bg-[#006672] text-white rounded-lg hover:bg-[#005560] transition-colors"
                style={{ 
                  padding: '10px', 
                  fontFamily: 'Inter, sans-serif', 
                  fontWeight: 600, 
                  fontSize: '13px',
                  borderRadius: '8px'
                }}
              >
                Send
              </button>

              {/* Cancel Link */}
              <div className="text-center">
                <button 
                  onClick={handleCancel}
                  className="hover:opacity-70 transition-opacity"
                  style={{ fontFamily: 'Inter, sans-serif', fontWeight: 400, fontSize: '13px', color: '#3d5050' }}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
