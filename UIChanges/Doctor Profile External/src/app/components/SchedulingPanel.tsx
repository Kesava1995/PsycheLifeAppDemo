import { ChevronLeft, ChevronRight, Video, MapPin, Lock } from 'lucide-react';

interface SchedulingPanelProps {
  selectedDate: Date;
  setSelectedDate: (date: Date) => void;
  selectedTimeSlot: string | null;
  setSelectedTimeSlot: (slot: string | null) => void;
  visitType: 'in-person' | 'online';
  setVisitType: (type: 'in-person' | 'online') => void;
}

export function SchedulingPanel({
  selectedDate,
  setSelectedDate,
  selectedTimeSlot,
  setSelectedTimeSlot,
  visitType,
  setVisitType,
}: SchedulingPanelProps) {
  const today = new Date();
  const currentMonth = selectedDate.getMonth();
  const currentYear = selectedDate.getFullYear();

  const monthNames = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];

  const weekdays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  const getDaysInMonth = (month: number, year: number) => {
    return new Date(year, month + 1, 0).getDate();
  };

  const getFirstDayOfMonth = (month: number, year: number) => {
    return new Date(year, month, 1).getDay();
  };

  const generateCalendarDays = () => {
    const daysInMonth = getDaysInMonth(currentMonth, currentYear);
    const firstDay = getFirstDayOfMonth(currentMonth, currentYear);
    const days = [];

    // Previous month padding
    for (let i = 0; i < firstDay; i++) {
      days.push(null);
    }

    // Current month days
    for (let i = 1; i <= daysInMonth; i++) {
      days.push(i);
    }

    return days;
  };

  const isToday = (day: number | null) => {
    if (!day) return false;
    const date = new Date(currentYear, currentMonth, day);
    return (
      date.getDate() === today.getDate() &&
      date.getMonth() === today.getMonth() &&
      date.getFullYear() === today.getFullYear()
    );
  };

  const isSelected = (day: number | null) => {
    if (!day) return false;
    return (
      day === selectedDate.getDate() &&
      currentMonth === selectedDate.getMonth() &&
      currentYear === selectedDate.getFullYear()
    );
  };

  const isPastDate = (day: number | null) => {
    if (!day) return false;
    const date = new Date(currentYear, currentMonth, day);
    const todayStart = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    return date < todayStart;
  };

  const hasAvailability = (day: number | null) => {
    if (!day || isPastDate(day)) return false;
    // Mock: All future dates have availability
    return true;
  };

  const handleDateClick = (day: number | null) => {
    if (!day || isPastDate(day)) return;
    const newDate = new Date(currentYear, currentMonth, day);
    setSelectedDate(newDate);
    setSelectedTimeSlot(null); // Reset time slot when date changes
  };

  const previousMonth = () => {
    const newDate = new Date(currentYear, currentMonth - 1, 1);
    setSelectedDate(newDate);
  };

  const nextMonth = () => {
    const newDate = new Date(currentYear, currentMonth + 1, 1);
    setSelectedDate(newDate);
  };

  const morningSlots = ['8:00 AM', '9:00 AM', '10:00 AM', '11:00 AM'];
  const afternoonSlots = ['12:00 PM', '1:00 PM', '2:00 PM', '3:00 PM', '4:00 PM'];
  const eveningSlots = ['5:00 PM', '6:00 PM', '7:00 PM'];

  const unavailableSlots = ['9:00 AM', '2:00 PM', '6:00 PM']; // Mock unavailable slots

  const calendarDays = generateCalendarDays();

  return (
    <div className="sticky top-6">
      <div className="bg-white dark:bg-[#1a2224] rounded-[16px] p-6 border border-[#e8f0f0] dark:border-[#2a3234]">
        {/* Header */}
        <div className="mb-6">
          <h2 className="text-[22px] font-[700] text-[#1a2224] dark:text-white mb-1" style={{ fontFamily: 'Manrope, sans-serif' }}>
            Schedule Your Visit
          </h2>
          <p className="text-[#8aacae] dark:text-[#4a6668] text-sm" style={{ fontFamily: 'Inter, sans-serif' }}>
            Choose your preferred date and time
          </p>
        </div>

        {/* Visit Type */}
        <div className="mb-6">
          <label className="block text-[#1a2224] dark:text-white mb-3 font-[600]" style={{ fontFamily: 'Inter, sans-serif' }}>
            Visit Type
          </label>
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={() => setVisitType('in-person')}
              className={`p-4 rounded-[8px] border-2 transition-all ${
                visitType === 'in-person'
                  ? 'border-[#008896] bg-[#008896]/5 dark:bg-[#008896]/10'
                  : 'border-[#e8f0f0] dark:border-[#2a3234] hover:border-[#008896]/30'
              }`}
            >
              <MapPin className={`w-5 h-5 mx-auto mb-2 ${visitType === 'in-person' ? 'text-[#008896]' : 'text-[#8aacae] dark:text-[#4a6668]'}`} />
              <span className={`text-sm font-[500] ${visitType === 'in-person' ? 'text-[#008896]' : 'text-[#4a6668] dark:text-[#8aacae]'}`} style={{ fontFamily: 'Inter, sans-serif' }}>
                In-person
              </span>
            </button>
            <button
              onClick={() => setVisitType('online')}
              className={`p-4 rounded-[8px] border-2 transition-all ${
                visitType === 'online'
                  ? 'border-[#008896] bg-[#008896]/5 dark:bg-[#008896]/10'
                  : 'border-[#e8f0f0] dark:border-[#2a3234] hover:border-[#008896]/30'
              }`}
            >
              <Video className={`w-5 h-5 mx-auto mb-2 ${visitType === 'online' ? 'text-[#008896]' : 'text-[#8aacae] dark:text-[#4a6668]'}`} />
              <span className={`text-sm font-[500] ${visitType === 'online' ? 'text-[#008896]' : 'text-[#4a6668] dark:text-[#8aacae]'}`} style={{ fontFamily: 'Inter, sans-serif' }}>
                Online
              </span>
            </button>
          </div>
        </div>

        {/* Calendar */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <span className="text-[#1a2224] dark:text-white font-[600]" style={{ fontFamily: 'Inter, sans-serif' }}>
              {monthNames[currentMonth]} {currentYear}
            </span>
            <div className="flex gap-2">
              <button
                onClick={previousMonth}
                className="w-8 h-8 rounded-full hover:bg-[#e8f0f0] dark:hover:bg-[#2a3234] flex items-center justify-center transition-colors"
              >
                <ChevronLeft className="w-4 h-4 text-[#4a6668] dark:text-[#8aacae]" />
              </button>
              <button
                onClick={nextMonth}
                className="w-8 h-8 rounded-full hover:bg-[#e8f0f0] dark:hover:bg-[#2a3234] flex items-center justify-center transition-colors"
              >
                <ChevronRight className="w-4 h-4 text-[#4a6668] dark:text-[#8aacae]" />
              </button>
            </div>
          </div>

          {/* Weekday headers */}
          <div className="grid grid-cols-7 gap-1 mb-2">
            {weekdays.map((day) => (
              <div key={day} className="text-center text-xs text-[#8aacae] dark:text-[#4a6668] font-[500] py-1" style={{ fontFamily: 'Inter, sans-serif' }}>
                {day}
              </div>
            ))}
          </div>

          {/* Calendar grid */}
          <div className="grid grid-cols-7 gap-1">
            {calendarDays.map((day, index) => (
              <button
                key={index}
                onClick={() => handleDateClick(day)}
                disabled={!day || isPastDate(day)}
                className={`
                  aspect-square flex items-center justify-center rounded-[8px] text-sm relative transition-all
                  ${!day ? 'invisible' : ''}
                  ${isPastDate(day) ? 'text-[#e8f0f0] dark:text-[#2a3234] cursor-not-allowed' : ''}
                  ${isSelected(day) ? 'bg-[#008896] text-white' : ''}
                  ${isToday(day) && !isSelected(day) ? 'border-2 border-[#008896] text-[#008896]' : ''}
                  ${!isSelected(day) && !isToday(day) && !isPastDate(day) ? 'hover:bg-[#e8f0f0] dark:hover:bg-[#2a3234] text-[#1a2224] dark:text-white' : ''}
                `}
                style={{ fontFamily: 'Inter, sans-serif', fontWeight: 500 }}
              >
                {day}
                {hasAvailability(day) && !isSelected(day) && !isToday(day) && (
                  <div className="absolute bottom-1 left-1/2 transform -translate-x-1/2 w-1 h-1 bg-[#008896] rounded-full" />
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Time Slots */}
        <div className="mb-6">
          <label className="block text-[#1a2224] dark:text-white mb-3 font-[600]" style={{ fontFamily: 'Inter, sans-serif' }}>
            Available Time Slots
          </label>

          {/* Morning */}
          <div className="mb-4">
            <p className="text-xs text-[#8aacae] dark:text-[#4a6668] mb-2 font-[500]" style={{ fontFamily: 'Inter, sans-serif' }}>
              Morning (8 AM - 12 PM)
            </p>
            <div className="flex flex-wrap gap-2">
              {morningSlots.map((slot) => {
                const isUnavailable = unavailableSlots.includes(slot);
                const isSlotSelected = selectedTimeSlot === slot;
                return (
                  <button
                    key={slot}
                    onClick={() => !isUnavailable && setSelectedTimeSlot(slot)}
                    disabled={isUnavailable}
                    className={`px-4 py-2 rounded-[999px] text-sm transition-all ${
                      isSlotSelected
                        ? 'bg-[#008896] text-white'
                        : isUnavailable
                        ? 'bg-[#f5f5f5] dark:bg-[#0d1315] text-[#e8f0f0] dark:text-[#2a3234] cursor-not-allowed'
                        : 'bg-white dark:bg-[#0d1315] border border-[#e8f0f0] dark:border-[#2a3234] text-[#4a6668] dark:text-[#8aacae] hover:border-[#008896]'
                    }`}
                    style={{ fontFamily: 'Inter, sans-serif', fontWeight: 500 }}
                  >
                    {slot}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Afternoon */}
          <div className="mb-4">
            <p className="text-xs text-[#8aacae] dark:text-[#4a6668] mb-2 font-[500]" style={{ fontFamily: 'Inter, sans-serif' }}>
              Afternoon (12 PM - 5 PM)
            </p>
            <div className="flex flex-wrap gap-2">
              {afternoonSlots.map((slot) => {
                const isUnavailable = unavailableSlots.includes(slot);
                const isSlotSelected = selectedTimeSlot === slot;
                return (
                  <button
                    key={slot}
                    onClick={() => !isUnavailable && setSelectedTimeSlot(slot)}
                    disabled={isUnavailable}
                    className={`px-4 py-2 rounded-[999px] text-sm transition-all ${
                      isSlotSelected
                        ? 'bg-[#008896] text-white'
                        : isUnavailable
                        ? 'bg-[#f5f5f5] dark:bg-[#0d1315] text-[#e8f0f0] dark:text-[#2a3234] cursor-not-allowed'
                        : 'bg-white dark:bg-[#0d1315] border border-[#e8f0f0] dark:border-[#2a3234] text-[#4a6668] dark:text-[#8aacae] hover:border-[#008896]'
                    }`}
                    style={{ fontFamily: 'Inter, sans-serif', fontWeight: 500 }}
                  >
                    {slot}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Evening */}
          <div>
            <p className="text-xs text-[#8aacae] dark:text-[#4a6668] mb-2 font-[500]" style={{ fontFamily: 'Inter, sans-serif' }}>
              Evening (5 PM - 8 PM)
            </p>
            <div className="flex flex-wrap gap-2">
              {eveningSlots.map((slot) => {
                const isUnavailable = unavailableSlots.includes(slot);
                const isSlotSelected = selectedTimeSlot === slot;
                return (
                  <button
                    key={slot}
                    onClick={() => !isUnavailable && setSelectedTimeSlot(slot)}
                    disabled={isUnavailable}
                    className={`px-4 py-2 rounded-[999px] text-sm transition-all ${
                      isSlotSelected
                        ? 'bg-[#008896] text-white'
                        : isUnavailable
                        ? 'bg-[#f5f5f5] dark:bg-[#0d1315] text-[#e8f0f0] dark:text-[#2a3234] cursor-not-allowed'
                        : 'bg-white dark:bg-[#0d1315] border border-[#e8f0f0] dark:border-[#2a3234] text-[#4a6668] dark:text-[#8aacae] hover:border-[#008896]'
                    }`}
                    style={{ fontFamily: 'Inter, sans-serif', fontWeight: 500 }}
                  >
                    {slot}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* CTA Button */}
        <button
          disabled={!selectedTimeSlot}
          className={`w-full py-3 rounded-[8px] font-[600] transition-all ${
            selectedTimeSlot
              ? 'bg-[#008896] text-white hover:bg-[#006672]'
              : 'bg-[#e8f0f0] dark:bg-[#2a3234] text-[#8aacae] dark:text-[#4a6668] cursor-not-allowed'
          }`}
          style={{ fontFamily: 'Inter, sans-serif' }}
        >
          Proceed to Book
        </button>

        {/* Footer Notes */}
        <div className="mt-4 space-y-2">
          <p className="text-xs text-[#8aacae] dark:text-[#4a6668] text-center" style={{ fontFamily: 'Inter, sans-serif' }}>
            Free cancellation up to 24 hours before appointment
          </p>
          <div className="flex items-center justify-center gap-2">
            <Lock className="w-3 h-3 text-[#8aacae] dark:text-[#4a6668]" />
            <p className="text-xs text-[#8aacae] dark:text-[#4a6668]" style={{ fontFamily: 'Inter, sans-serif' }}>
              Your information is safe and secure
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
