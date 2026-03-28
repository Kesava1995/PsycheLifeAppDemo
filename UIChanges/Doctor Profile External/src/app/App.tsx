import { useState } from 'react';
import { Navbar } from './components/Navbar';
import { DoctorDetails } from './components/DoctorDetails';
import { SchedulingPanel } from './components/SchedulingPanel';

export default function App() {
  const [selectedDate, setSelectedDate] = useState<Date>(new Date());
  const [selectedTimeSlot, setSelectedTimeSlot] = useState<string | null>(null);
  const [visitType, setVisitType] = useState<'in-person' | 'online'>('in-person');

  return (
    <div className="min-h-screen bg-[#fafafa] dark:bg-[#0d1315]">
      <Navbar />
      
      <div className="max-w-[1200px] mx-auto px-8 pt-6 pb-8">
        <div className="flex gap-8 h-[calc(100vh-56px-48px)]">
          {/* Left Panel - Doctor Details */}
          <div className="w-2/3 overflow-y-auto pr-2">
            <DoctorDetails />
          </div>
          
          {/* Right Panel - Scheduling */}
          <div className="w-1/3 overflow-y-auto pl-2">
            <SchedulingPanel
              selectedDate={selectedDate}
              setSelectedDate={setSelectedDate}
              selectedTimeSlot={selectedTimeSlot}
              setSelectedTimeSlot={setSelectedTimeSlot}
              visitType={visitType}
              setVisitType={setVisitType}
            />
          </div>
        </div>
      </div>
    </div>
  );
}