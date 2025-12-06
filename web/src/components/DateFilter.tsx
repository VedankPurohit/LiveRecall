'use client';

import { useState } from 'react';

interface DateFilterProps {
  onFilterChange: (startDate: string | undefined, endDate: string | undefined) => void;
}

type Preset = '1h' | '24h' | '7d' | '30d' | 'all' | 'custom';

// Convert Date to YYMMDDHHMMSS format
function dateToTimestamp(date: Date): string {
  const year = (date.getFullYear() % 100).toString().padStart(2, '0');
  const month = (date.getMonth() + 1).toString().padStart(2, '0');
  const day = date.getDate().toString().padStart(2, '0');
  const hour = date.getHours().toString().padStart(2, '0');
  const minute = date.getMinutes().toString().padStart(2, '0');
  const second = date.getSeconds().toString().padStart(2, '0');
  return `${year}${month}${day}${hour}${minute}${second}`;
}

// Convert YYYY-MM-DDTHH:MM input to YYMMDDHHMMSS
function inputToTimestamp(input: string): string {
  if (!input) return '';
  const date = new Date(input);
  return dateToTimestamp(date);
}

// Get start timestamp for preset
function getPresetStartDate(preset: Preset): string | undefined {
  if (preset === 'all') return undefined;

  const now = new Date();
  switch (preset) {
    case '1h':
      return dateToTimestamp(new Date(now.getTime() - 60 * 60 * 1000));
    case '24h':
      return dateToTimestamp(new Date(now.getTime() - 24 * 60 * 60 * 1000));
    case '7d':
      return dateToTimestamp(new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000));
    case '30d':
      return dateToTimestamp(new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000));
    default:
      return undefined;
  }
}

export default function DateFilter({ onFilterChange }: DateFilterProps) {
  const [activePreset, setActivePreset] = useState<Preset>('all');
  const [showCustom, setShowCustom] = useState(false);
  const [customStart, setCustomStart] = useState('');
  const [customEnd, setCustomEnd] = useState('');

  const handlePresetClick = (preset: Preset) => {
    if (preset === 'custom') {
      setShowCustom(true);
      setActivePreset('custom');
      return;
    }

    setActivePreset(preset);
    setShowCustom(false);
    const startDate = getPresetStartDate(preset);
    onFilterChange(startDate, undefined);
  };

  const handleCustomApply = () => {
    const startTs = customStart ? inputToTimestamp(customStart) : undefined;
    const endTs = customEnd ? inputToTimestamp(customEnd) : undefined;
    onFilterChange(startTs, endTs);
  };

  const presets: { key: Preset; label: string }[] = [
    { key: '1h', label: '1h' },
    { key: '24h', label: '24h' },
    { key: '7d', label: '7d' },
    { key: '30d', label: '30d' },
    { key: 'all', label: 'All' },
  ];

  return (
    <div className="space-y-3">
      {/* Preset Buttons */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-neutral-500 mr-1">Time:</span>
        {presets.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => handlePresetClick(key)}
            className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
              activePreset === key && !showCustom
                ? 'bg-blue-500 text-white'
                : 'bg-neutral-800 text-neutral-400 hover:text-white hover:bg-neutral-700'
            }`}
          >
            {label}
          </button>
        ))}
        <button
          onClick={() => handlePresetClick('custom')}
          className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
            showCustom
              ? 'bg-blue-500 text-white'
              : 'bg-neutral-800 text-neutral-400 hover:text-white hover:bg-neutral-700'
          }`}
        >
          Custom
        </button>
      </div>

      {/* Custom Date Range */}
      {showCustom && (
        <div className="flex items-center gap-3 bg-neutral-900 rounded-lg p-3">
          <div className="flex items-center gap-2">
            <label className="text-xs text-neutral-500">From:</label>
            <input
              type="datetime-local"
              value={customStart}
              onChange={(e) => setCustomStart(e.target.value)}
              className="bg-neutral-800 text-white text-sm px-2 py-1 rounded border border-neutral-700 focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div className="flex items-center gap-2">
            <label className="text-xs text-neutral-500">To:</label>
            <input
              type="datetime-local"
              value={customEnd}
              onChange={(e) => setCustomEnd(e.target.value)}
              className="bg-neutral-800 text-white text-sm px-2 py-1 rounded border border-neutral-700 focus:border-blue-500 focus:outline-none"
            />
          </div>
          <button
            onClick={handleCustomApply}
            className="px-3 py-1 bg-blue-500 text-white text-sm font-medium rounded-md hover:bg-blue-600 transition-colors"
          >
            Apply
          </button>
        </div>
      )}
    </div>
  );
}
