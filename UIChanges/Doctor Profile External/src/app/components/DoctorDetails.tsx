import { useState } from 'react';
import { Phone, Mail, Globe, Instagram, Linkedin, MapPin, Clock, ChevronDown, ChevronUp, Star, Trophy } from 'lucide-react';

type TabType = 'contact' | 'clinics' | 'reviews' | 'care-model' | 'faqs';

export function DoctorDetails() {
  const [activeTab, setActiveTab] = useState<TabType>('contact');
  const [bioExpanded, setBioExpanded] = useState(false);
  const [expandedFaq, setExpandedFaq] = useState<number | null>(null);

  const tabs: { id: TabType; label: string }[] = [
    { id: 'contact', label: 'Contact' },
    { id: 'clinics', label: 'Clinics' },
    { id: 'reviews', label: 'Reviews' },
    { id: 'care-model', label: 'Care Model' },
    { id: 'faqs', label: 'FAQs' },
  ];

  const situations = [
    'Depression', 'Anxiety', 'Bipolar Disorder', 'Schizophrenia', 'OCD',
    'PTSD', 'Substance Use', 'Sleep Disorders', 'Relationship Issues',
    'Work Stress', 'Grief & Loss', 'Personality Disorders', 'ADHD', 'Dementia'
  ];

  const accolades = [
    'Best Psychiatrist Award 2022',
    'Fellow of Indian Psychiatric Society',
    '12+ Research Publications',
    'Gold Medalist - MD Psychiatry'
  ];

  const clinics = [
    {
      name: 'Mind Wellness Clinic',
      address: '123 Residency Road, Bangalore - 560025',
      phone: '+91 98765 43210',
      timings: 'Mon-Sat: 9 AM - 6 PM',
    },
    {
      name: 'Serenity Mental Health Center',
      address: '45 MG Road, Indiranagar, Bangalore - 560038',
      phone: '+91 98765 43211',
      timings: 'Mon-Fri: 2 PM - 8 PM',
    },
  ];

  const reviews = [
    {
      name: 'Priya Sharma',
      date: 'March 15, 2026',
      rating: 5,
      text: 'Dr. Mehta is incredibly empathetic and professional. The treatment plan was thorough and I felt heard throughout the process. Highly recommended!'
    },
    {
      name: 'Rahul Kumar',
      date: 'March 10, 2026',
      rating: 5,
      text: 'Excellent doctor with great listening skills. Took time to understand my concerns and provided practical solutions. Very satisfied with the care.'
    },
    {
      name: 'Anjali Desai',
      date: 'March 5, 2026',
      rating: 4,
      text: 'Very knowledgeable and approachable. The clinic environment is comfortable and the staff is supportive. Would definitely recommend.'
    },
    {
      name: 'Vikram Singh',
      date: 'February 28, 2026',
      rating: 5,
      text: 'One of the best psychiatrists I have consulted. Dr. Mehta combines expertise with genuine care. The follow-up support is excellent.'
    },
  ];

  const careModel = [
    {
      phase: 'Assessment',
      description: 'Comprehensive evaluation of mental health through detailed consultation and psychological assessments'
    },
    {
      phase: 'Diagnosis',
      description: 'Evidence-based diagnosis using DSM-5 criteria and clinical expertise to understand your condition'
    },
    {
      phase: 'Treatment',
      description: 'Personalized treatment plan combining therapy, medication management, and lifestyle modifications'
    },
    {
      phase: 'Maintenance',
      description: 'Regular follow-ups and adjustments to ensure sustained progress and prevent relapse'
    },
  ];

  const faqs = [
    {
      question: 'What should I bring to my first appointment?',
      answer: 'Please bring any previous medical records, list of current medications, insurance information, and a brief note about your concerns. This helps us provide better care from the first session.'
    },
    {
      question: 'How long does a typical consultation last?',
      answer: 'Initial consultations usually last 45-60 minutes. Follow-up sessions are typically 30 minutes, though this can vary based on your needs.'
    },
    {
      question: 'Do you accept insurance?',
      answer: 'Yes, we accept most major insurance plans. Please contact our clinic with your insurance details to verify coverage before your appointment.'
    },
    {
      question: 'Is medication always necessary?',
      answer: 'Not always. Treatment plans are personalized based on your specific condition. We explore all options including therapy, lifestyle changes, and when appropriate, medication.'
    },
    {
      question: 'How soon can I expect to see improvement?',
      answer: 'This varies by individual and condition. Some patients notice improvements within 2-4 weeks, while others may take longer. We monitor progress closely and adjust treatment as needed.'
    },
  ];

  return (
    <div className="space-y-6">
      {/* Hero Section */}
      <div className="bg-white dark:bg-[#1a2224] rounded-[12px] p-6 border border-[#e8f0f0] dark:border-[#2a3234]">
        <div className="flex gap-6">
          {/* Doctor Photo */}
          <div className="w-[120px] h-[120px] bg-[#008896] rounded-[16px] flex items-center justify-center flex-shrink-0">
            <span className="text-white text-[40px]" style={{ fontFamily: 'Manrope, sans-serif', fontWeight: 700 }}>
              AM
            </span>
          </div>

          {/* Doctor Info */}
          <div className="flex-1">
            <h1 className="text-[26px] font-[700] text-[#1a2224] dark:text-white mb-1" style={{ fontFamily: 'Manrope, sans-serif' }}>
              Dr. Aditya Mehta
            </h1>
            <p className="text-[#008896] mb-3" style={{ fontFamily: 'Inter, sans-serif', fontWeight: 500 }}>
              Consultant Psychiatrist
            </p>

            {/* Pills */}
            <div className="flex flex-wrap gap-2 mb-3">
              <span className="px-4 py-1.5 bg-[#e8f0f0] dark:bg-[#2a3234] text-[#4a6668] dark:text-[#b0c4c6] rounded-[999px] text-sm">
                15+ Years Experience
              </span>
              <span className="px-4 py-1.5 bg-[#e8f0f0] dark:bg-[#2a3234] text-[#4a6668] dark:text-[#b0c4c6] rounded-[999px] text-sm">
                Reg No: MCI-123456
              </span>
              <span className="px-4 py-1.5 bg-[#e8f0f0] dark:bg-[#2a3234] text-[#4a6668] dark:text-[#b0c4c6] rounded-[999px] text-sm">
                English, Hindi, Kannada
              </span>
            </div>

            {/* Bio */}
            <div>
              <p className="text-[#4a6668] dark:text-[#8aacae] leading-relaxed" style={{ fontFamily: 'Inter, sans-serif' }}>
                {bioExpanded 
                  ? 'Dr. Aditya Mehta is a highly experienced psychiatrist specializing in mood disorders, anxiety, and psychotic disorders. With over 15 years of clinical experience, he combines evidence-based treatment with compassionate care. Dr. Mehta believes in a holistic approach to mental health, integrating therapy, medication management, and lifestyle modifications to help patients achieve lasting wellness.'
                  : 'Dr. Aditya Mehta is a highly experienced psychiatrist specializing in mood disorders, anxiety, and psychotic disorders. With over 15 years of clinical experience, he combines evidence-based treatment with compassionate care...'}
              </p>
              <button 
                onClick={() => setBioExpanded(!bioExpanded)}
                className="text-[#008896] mt-1 hover:underline"
                style={{ fontFamily: 'Inter, sans-serif', fontWeight: 500 }}
              >
                {bioExpanded ? 'Read less' : 'Read more'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Accolades */}
      <div className="bg-white dark:bg-[#1a2224] rounded-[12px] p-6 border border-[#e8f0f0] dark:border-[#2a3234]">
        <h2 className="text-[20px] font-[700] text-[#1a2224] dark:text-white mb-4" style={{ fontFamily: 'Manrope, sans-serif' }}>
          Accolades & Recognition
        </h2>
        <div className="grid grid-cols-2 gap-3">
          {accolades.map((accolade, index) => (
            <div key={index} className="flex items-center gap-3 p-3 bg-[#fafafa] dark:bg-[#0d1315] rounded-[8px] border border-[#e8f0f0] dark:border-[#2a3234]">
              <Trophy className="w-5 h-5 text-[#008896] flex-shrink-0" />
              <span className="text-[#1a2224] dark:text-white text-sm" style={{ fontFamily: 'Inter, sans-serif' }}>
                {accolade}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Situations */}
      <div className="bg-white dark:bg-[#1a2224] rounded-[12px] p-6 border border-[#e8f0f0] dark:border-[#2a3234]">
        <h2 className="text-[20px] font-[700] text-[#1a2224] dark:text-white mb-4" style={{ fontFamily: 'Manrope, sans-serif' }}>
          Conditions Treated
        </h2>
        <div className="flex flex-wrap gap-2">
          {situations.map((situation, index) => (
            <span
              key={index}
              className="px-4 py-1.5 bg-[#006672] dark:bg-[#005561] text-white rounded-[999px] text-sm"
              style={{ fontFamily: 'Inter, sans-serif' }}
            >
              {situation}
            </span>
          ))}
        </div>
      </div>

      {/* Tabs */}
      <div className="sticky top-0 bg-[#fafafa] dark:bg-[#0d1315] py-3 z-10">
        <div className="flex gap-2 overflow-x-auto pb-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-5 py-2 rounded-[999px] whitespace-nowrap transition-colors ${
                activeTab === tab.id
                  ? 'bg-[#008896] text-white'
                  : 'bg-white dark:bg-[#1a2224] text-[#4a6668] dark:text-[#8aacae] border border-[#e8f0f0] dark:border-[#2a3234] hover:border-[#008896]'
              }`}
              style={{ fontFamily: 'Inter, sans-serif', fontWeight: 500 }}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <div className="pb-8">
        {activeTab === 'contact' && (
          <div className="bg-white dark:bg-[#1a2224] rounded-[12px] p-6 border border-[#e8f0f0] dark:border-[#2a3234]">
            <h2 className="text-[20px] font-[700] text-[#1a2224] dark:text-white mb-4" style={{ fontFamily: 'Manrope, sans-serif' }}>
              Contact Information
            </h2>
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <Phone className="w-5 h-5 text-[#008896]" />
                <span className="text-[#1a2224] dark:text-white" style={{ fontFamily: 'Inter, sans-serif' }}>
                  +91 98765 43210
                </span>
              </div>
              <div className="flex items-center gap-3">
                <Mail className="w-5 h-5 text-[#008896]" />
                <span className="text-[#1a2224] dark:text-white" style={{ fontFamily: 'Inter, sans-serif' }}>
                  dr.aditya.mehta@email.com
                </span>
              </div>
              <div className="flex items-center gap-3">
                <Globe className="w-5 h-5 text-[#008896]" />
                <a href="#" className="text-[#008896] hover:underline" style={{ fontFamily: 'Inter, sans-serif' }}>
                  www.dradityamehta.com
                </a>
              </div>
              <div className="flex items-center gap-3">
                <Instagram className="w-5 h-5 text-[#008896]" />
                <a href="#" className="text-[#008896] hover:underline" style={{ fontFamily: 'Inter, sans-serif' }}>
                  @dradityamehta
                </a>
              </div>
              <div className="flex items-center gap-3">
                <Linkedin className="w-5 h-5 text-[#008896]" />
                <a href="#" className="text-[#008896] hover:underline" style={{ fontFamily: 'Inter, sans-serif' }}>
                  Dr. Aditya Mehta
                </a>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'clinics' && (
          <div className="space-y-4">
            {clinics.map((clinic, index) => (
              <div key={index} className="bg-white dark:bg-[#1a2224] rounded-[12px] p-6 border border-[#e8f0f0] dark:border-[#2a3234]">
                <h3 className="text-[18px] font-[700] text-[#1a2224] dark:text-white mb-4" style={{ fontFamily: 'Manrope, sans-serif' }}>
                  {clinic.name}
                </h3>
                <div className="space-y-3 mb-4">
                  <div className="flex items-start gap-3">
                    <MapPin className="w-5 h-5 text-[#008896] flex-shrink-0 mt-0.5" />
                    <span className="text-[#4a6668] dark:text-[#8aacae]" style={{ fontFamily: 'Inter, sans-serif' }}>
                      {clinic.address}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <Phone className="w-5 h-5 text-[#008896]" />
                    <span className="text-[#4a6668] dark:text-[#8aacae]" style={{ fontFamily: 'Inter, sans-serif' }}>
                      {clinic.phone}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <Clock className="w-5 h-5 text-[#008896]" />
                    <span className="px-3 py-1 bg-[#e8f0f0] dark:bg-[#2a3234] text-[#006672] dark:text-[#00a8bb] rounded-[999px] text-sm">
                      {clinic.timings}
                    </span>
                  </div>
                </div>
                {/* Map Placeholder */}
                <div className="w-full h-40 bg-[#e8f0f0] dark:bg-[#2a3234] rounded-[8px] flex items-center justify-center">
                  <span className="text-[#8aacae] dark:text-[#4a6668]" style={{ fontFamily: 'Inter, sans-serif' }}>
                    Map View
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'reviews' && (
          <div className="bg-white dark:bg-[#1a2224] rounded-[12px] p-6 border border-[#e8f0f0] dark:border-[#2a3234]">
            <div className="mb-6">
              <div className="flex items-center gap-3 mb-2">
                <span className="text-[32px] font-[700] text-[#1a2224] dark:text-white" style={{ fontFamily: 'Manrope, sans-serif' }}>
                  4.8
                </span>
                <div>
                  <div className="flex gap-1 mb-1">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <Star key={star} className="w-5 h-5 fill-[#008896] text-[#008896]" />
                    ))}
                  </div>
                  <span className="text-[#8aacae] dark:text-[#4a6668] text-sm" style={{ fontFamily: 'Inter, sans-serif' }}>
                    Based on 124 reviews
                  </span>
                </div>
              </div>
            </div>
            <div className="space-y-4">
              {reviews.map((review, index) => (
                <div key={index} className="p-4 bg-[#fafafa] dark:bg-[#0d1315] rounded-[8px] border border-[#e8f0f0] dark:border-[#2a3234]">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <p className="font-[600] text-[#1a2224] dark:text-white" style={{ fontFamily: 'Inter, sans-serif' }}>
                        {review.name}
                      </p>
                      <p className="text-sm text-[#8aacae] dark:text-[#4a6668]" style={{ fontFamily: 'Inter, sans-serif' }}>
                        {review.date}
                      </p>
                    </div>
                    <div className="flex gap-0.5">
                      {[1, 2, 3, 4, 5].map((star) => (
                        <Star 
                          key={star} 
                          className={`w-4 h-4 ${star <= review.rating ? 'fill-[#008896] text-[#008896]' : 'text-[#e8f0f0] dark:text-[#2a3234]'}`} 
                        />
                      ))}
                    </div>
                  </div>
                  <p className="text-[#4a6668] dark:text-[#8aacae]" style={{ fontFamily: 'Inter, sans-serif' }}>
                    {review.text}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'care-model' && (
          <div className="bg-white dark:bg-[#1a2224] rounded-[12px] p-6 border border-[#e8f0f0] dark:border-[#2a3234]">
            <h2 className="text-[20px] font-[700] text-[#1a2224] dark:text-white mb-6" style={{ fontFamily: 'Manrope, sans-serif' }}>
              Our Care Model
            </h2>
            <div className="grid grid-cols-2 gap-4">
              {careModel.map((phase, index) => (
                <div key={index} className="p-5 bg-[#fafafa] dark:bg-[#0d1315] rounded-[12px] border border-[#e8f0f0] dark:border-[#2a3234]">
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-8 h-8 bg-[#008896] rounded-full flex items-center justify-center">
                      <span className="text-white font-[700]" style={{ fontFamily: 'Manrope, sans-serif' }}>
                        {index + 1}
                      </span>
                    </div>
                    <h3 className="text-[18px] font-[700] text-[#1a2224] dark:text-white" style={{ fontFamily: 'Manrope, sans-serif' }}>
                      {phase.phase}
                    </h3>
                  </div>
                  <p className="text-[#4a6668] dark:text-[#8aacae] text-sm" style={{ fontFamily: 'Inter, sans-serif' }}>
                    {phase.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'faqs' && (
          <div className="bg-white dark:bg-[#1a2224] rounded-[12px] p-6 border border-[#e8f0f0] dark:border-[#2a3234]">
            <h2 className="text-[20px] font-[700] text-[#1a2224] dark:text-white mb-4" style={{ fontFamily: 'Manrope, sans-serif' }}>
              Frequently Asked Questions
            </h2>
            <div className="space-y-3">
              {faqs.map((faq, index) => (
                <div key={index} className="border border-[#e8f0f0] dark:border-[#2a3234] rounded-[8px] overflow-hidden">
                  <button
                    onClick={() => setExpandedFaq(expandedFaq === index ? null : index)}
                    className="w-full flex items-center justify-between p-4 text-left hover:bg-[#fafafa] dark:hover:bg-[#0d1315] transition-colors"
                  >
                    <span className="font-[600] text-[#1a2224] dark:text-white" style={{ fontFamily: 'Inter, sans-serif' }}>
                      {faq.question}
                    </span>
                    {expandedFaq === index ? (
                      <ChevronUp className="w-5 h-5 text-[#008896] flex-shrink-0" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-[#8aacae] dark:text-[#4a6668] flex-shrink-0" />
                    )}
                  </button>
                  <div 
                    className={`transition-all duration-300 ease-in-out ${
                      expandedFaq === index ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'
                    } overflow-hidden`}
                  >
                    <p className="px-4 pb-4 text-[#4a6668] dark:text-[#8aacae]" style={{ fontFamily: 'Inter, sans-serif' }}>
                      {faq.answer}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
