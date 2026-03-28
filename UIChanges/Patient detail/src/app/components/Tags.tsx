import { useState, useRef, useEffect } from 'react';

interface TagsProps {
  tags: string[];
  onAddTag: (tag: string) => void;
  onRemoveTag: (tag: string) => void;
}

const predefinedTags = [
  'High Risk',
  'Non-compliant',
  'VIP',
  'Research Participant',
  'Needs Follow-up',
  'Treatment Resistant',
  'Good Prognosis',
  'Requires Interpreter',
  'Medico-legal'
];

export function Tags({ tags, onAddTag, onRemoveTag }: TagsProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [customTag, setCustomTag] = useState('');
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false);
        setSearchQuery('');
        setCustomTag('');
      }
    };

    if (showDropdown) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showDropdown]);

  const handleAddTag = (tag: string) => {
    const formattedTag = tag.replace(/\s+/g, '');
    onAddTag(formattedTag);
    setShowDropdown(false);
    setSearchQuery('');
    setCustomTag('');
  };

  const filteredTags = predefinedTags.filter(tag => 
    tag.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="px-4 py-3 border-b border-[#e4ecec]">
      <div className="flex items-center justify-between mb-2">
        <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: '13px', color: '#3f4948', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          TAGS
        </div>
        <button 
          onClick={() => setIsEditing(!isEditing)}
          className="hover:opacity-70 transition-opacity cursor-pointer"
          style={{ fontSize: '14px' }}
        >
          ✏️
        </button>
      </div>

      {tags.length === 0 ? (
        <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 400, fontSize: '12px', color: '#9aacae', fontStyle: 'italic' }}>
          No tags added
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          {tags.map((tag, index) => (
            <span 
              key={index}
              className="inline-flex items-center gap-1.5 bg-[#e4ecec] px-3 py-1 rounded-full"
              style={{ fontFamily: 'Inter, sans-serif', fontWeight: 500, fontSize: '13px', color: '#006672' }}
            >
              <span>#{tag}</span>
              {isEditing && (
                <button 
                  onClick={() => onRemoveTag(tag)}
                  className="hover:opacity-70 transition-opacity ml-1"
                  style={{ fontSize: '12px', lineHeight: 1 }}
                >
                  ×
                </button>
              )}
            </span>
          ))}
          {isEditing && (
            <div className="relative" ref={dropdownRef}>
              <button 
                onClick={() => setShowDropdown(!showDropdown)}
                className="flex items-center justify-center bg-[#006672] text-white rounded-full hover:bg-[#005560] transition-colors"
                style={{ width: '20px', height: '20px', fontSize: '12px' }}
              >
                +
              </button>
              {showDropdown && (
                <div 
                  className="absolute z-20 bg-white border border-[#e4ecec] rounded-lg shadow-lg"
                  style={{ 
                    top: '100%',
                    left: '0',
                    marginTop: '4px',
                    minWidth: '240px',
                    maxHeight: '300px',
                    overflowY: 'auto'
                  }}
                >
                  <div className="p-2 border-b border-[#e4ecec]">
                    <input 
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Search tags..."
                      className="w-full px-3 py-1.5 border border-[#d2dcdc] rounded"
                      style={{ fontFamily: 'Inter, sans-serif', fontSize: '13px' }}
                      autoFocus
                    />
                  </div>
                  <div className="py-1">
                    {filteredTags.map((tag, index) => (
                      <button 
                        key={index}
                        onClick={() => handleAddTag(tag)}
                        className="w-full text-left px-3 py-2 hover:bg-[#f8fafa] transition-colors"
                        style={{ fontFamily: 'Inter, sans-serif', fontSize: '13px', color: '#181c1d' }}
                      >
                        {tag}
                      </button>
                    ))}
                    <div className="border-t border-[#e4ecec] mt-1 pt-1 px-3 py-2">
                      <div style={{ fontFamily: 'Inter, sans-serif', fontSize: '12px', color: '#9aacae', marginBottom: '4px' }}>
                        Custom tag:
                      </div>
                      <div className="flex gap-2">
                        <input 
                          type="text"
                          value={customTag}
                          onChange={(e) => setCustomTag(e.target.value)}
                          placeholder="Enter custom tag"
                          className="flex-1 px-2 py-1 border border-[#d2dcdc] rounded"
                          style={{ fontFamily: 'Inter, sans-serif', fontSize: '12px' }}
                          onKeyPress={(e) => {
                            if (e.key === 'Enter' && customTag.trim()) {
                              handleAddTag(customTag);
                            }
                          }}
                        />
                        <button 
                          onClick={() => customTag.trim() && handleAddTag(customTag)}
                          className="px-2 py-1 bg-[#006672] text-white rounded hover:bg-[#005560] transition-colors"
                          style={{ fontFamily: 'Inter, sans-serif', fontSize: '12px' }}
                        >
                          Add
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
