export function Navbar() {
  return (
    <nav className="w-full bg-white border-b border-[#e4ecec]">
      <div className="max-w-[1200px] mx-auto px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <h1 style={{ fontFamily: 'Manrope, sans-serif', fontWeight: 700, fontSize: '18px', color: '#006672' }}>
            Clinical Curator
          </h1>
          <div className="flex items-center gap-6">
            <a href="#" style={{ fontFamily: 'Inter, sans-serif', fontWeight: 500, fontSize: '14px', color: '#3d5050' }}>
              Patients
            </a>
            <a href="#" style={{ fontFamily: 'Inter, sans-serif', fontWeight: 500, fontSize: '14px', color: '#3d5050' }}>
              Dashboard
            </a>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <button style={{ fontFamily: 'Inter, sans-serif', fontWeight: 500, fontSize: '14px', color: '#3d5050' }}>
            Dr. Profile
          </button>
        </div>
      </div>
    </nav>
  );
}
