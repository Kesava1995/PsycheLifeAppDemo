export function ActionButtons() {
  return (
    <div className="px-4 py-3 space-y-2">
      <button 
        className="w-full flex items-center justify-center gap-2 bg-[#006672] text-white rounded-lg transition-opacity hover:opacity-90"
        style={{ padding: '14px', fontFamily: 'Manrope, sans-serif', fontWeight: 600, fontSize: '14px', borderRadius: '10px' }}
      >
        <span>📊</span>
        <span>View Life Chart</span>
      </button>
      
      <button 
        className="w-full flex items-center justify-center gap-2 bg-[#181c1d] text-white rounded-lg transition-opacity hover:opacity-90"
        style={{ padding: '14px', fontFamily: 'Manrope, sans-serif', fontWeight: 600, fontSize: '14px', borderRadius: '10px' }}
      >
        <span>➕</span>
        <span>Add Follow-up</span>
      </button>
    </div>
  );
}