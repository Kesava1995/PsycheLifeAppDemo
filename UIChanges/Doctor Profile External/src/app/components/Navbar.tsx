import { Activity } from 'lucide-react';
import React from 'react';

export function Navbar() {
  return (
    <nav className="sticky top-0 z-50 bg-white dark:bg-[#1a2224] h-14 border-b border-[#e8f0f0] dark:border-[#2a3234]">
      <div className="max-w-[1200px] mx-auto px-8 h-full flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-[#008896] animate-pulse" strokeWidth={2.5} />
          <span className="text-[20px] font-[700] text-[#008896]" style={{ fontFamily: 'Manrope, sans-serif' }}>
            Continuum
          </span>
        </div>
        
        {/* Clinic Name - Centered */}
        <div className="absolute left-1/2 transform -translate-x-1/2">
          <span className="text-[16px] font-[600] text-[#1a2224] dark:text-white" style={{ fontFamily: 'Manrope, sans-serif' }}>
            Mind Wellness Clinic
          </span>
        </div>
        
        {/* Dark Mode Toggle - Right */}
        <DarkModeToggle />
      </div>
    </nav>
  );
}

function DarkModeToggle() {
  const [isDark, setIsDark] = React.useState(false);

  const toggleDarkMode = () => {
    setIsDark(!isDark);
    document.documentElement.classList.toggle('dark');
  };

  return (
    <button
      onClick={toggleDarkMode}
      className="w-9 h-9 rounded-full border border-[#e8f0f0] hover:bg-[#fafafa] dark:hover:bg-[#2a3234] flex items-center justify-center transition-colors"
      aria-label="Toggle dark mode"
    >
      {isDark ? (
        <svg className="w-5 h-5 text-[#008896]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
        </svg>
      ) : (
        <svg className="w-5 h-5 text-[#4a6668]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
        </svg>
      )}
    </button>
  );
}