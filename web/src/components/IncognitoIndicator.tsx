'use client';

import { useState, useEffect, useRef } from 'react';
import { EyeOff, ChevronDown, X, Clock } from 'lucide-react';
import { IncognitoStatus } from '@/types';

interface IncognitoIndicatorProps {
  status: IncognitoStatus;
  onSetDuration: (minutes: number) => void;
  onStop: () => void;
  isLoading?: boolean;
}

const DURATION_OPTIONS = [
  { minutes: 5, label: '5 minutes' },
  { minutes: 15, label: '15 minutes' },
  { minutes: 30, label: '30 minutes' },
  { minutes: 60, label: '1 hour' },
];

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export function IncognitoIndicator({
  status,
  onSetDuration,
  onStop,
  isLoading = false,
}: IncognitoIndicatorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [remainingSeconds, setRemainingSeconds] = useState(status.remaining_seconds);
  const menuRef = useRef<HTMLDivElement>(null);

  // Update countdown timer
  useEffect(() => {
    setRemainingSeconds(status.remaining_seconds);

    if (!status.active) return;

    const interval = setInterval(() => {
      setRemainingSeconds((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [status.active, status.remaining_seconds]);

  // Close menu on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Close menu on Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsOpen(false);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  if (status.active) {
    return (
      <div ref={menuRef} className="relative">
        <button
          onClick={() => setIsOpen(!isOpen)}
          disabled={isLoading}
          className="flex items-center gap-2 px-3 py-1.5 bg-[#7c3aed]/20 border border-[#7c3aed]/40 text-[#a78bfa] rounded-lg hover:bg-[#7c3aed]/30 transition-colors disabled:opacity-50"
        >
          <EyeOff className="w-4 h-4" />
          <span className="text-sm font-medium">
            Incognito {formatTime(remainingSeconds)}
          </span>
          <ChevronDown
            className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          />
        </button>

        {isOpen && (
          <div className="absolute top-full right-0 mt-2 w-48 bg-[#1c1c1c] border border-[#333] rounded-lg shadow-xl overflow-hidden animate-in fade-in slide-in-from-top-2 duration-150 z-50">
            <div className="p-3 border-b border-[#333]">
              <div className="flex items-center gap-2 text-[#a78bfa]">
                <Clock className="w-4 h-4" />
                <span className="text-sm font-medium">
                  {formatTime(remainingSeconds)} remaining
                </span>
              </div>
            </div>

            <div className="p-1">
              <p className="px-2 py-1.5 text-xs text-[#666]">Extend duration</p>
              {DURATION_OPTIONS.map((option) => (
                <button
                  key={option.minutes}
                  onClick={() => {
                    onSetDuration(option.minutes);
                    setIsOpen(false);
                  }}
                  disabled={isLoading}
                  className="w-full px-3 py-2 text-sm text-left text-[#f5f5f5] hover:bg-[#333] rounded transition-colors disabled:opacity-50"
                >
                  {option.label}
                </button>
              ))}
            </div>

            <div className="border-t border-[#333] p-1">
              <button
                onClick={() => {
                  onStop();
                  setIsOpen(false);
                }}
                disabled={isLoading}
                className="w-full px-3 py-2 text-sm text-left text-[#ef4444] hover:bg-[#ef4444]/10 rounded transition-colors flex items-center gap-2 disabled:opacity-50"
              >
                <X className="w-4 h-4" />
                Stop Incognito
              </button>
            </div>
          </div>
        )}
      </div>
    );
  }

  // Inactive state - show button to enable
  return (
    <div ref={menuRef} className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isLoading}
        className="flex items-center gap-2 px-3 py-1.5 bg-[#333] text-[#8a8a8a] rounded-lg hover:bg-[#444] hover:text-[#f5f5f5] transition-colors disabled:opacity-50"
        title="Enable Incognito Mode"
      >
        <EyeOff className="w-4 h-4" />
        <ChevronDown
          className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`}
        />
      </button>

      {isOpen && (
        <div className="absolute top-full right-0 mt-2 w-48 bg-[#1c1c1c] border border-[#333] rounded-lg shadow-xl overflow-hidden animate-in fade-in slide-in-from-top-2 duration-150 z-50">
          <div className="p-3 border-b border-[#333]">
            <p className="text-sm font-medium text-[#f5f5f5]">Incognito Mode</p>
            <p className="text-xs text-[#666] mt-1">
              New captures will be hidden
            </p>
          </div>

          <div className="p-1">
            {DURATION_OPTIONS.map((option) => (
              <button
                key={option.minutes}
                onClick={() => {
                  onSetDuration(option.minutes);
                  setIsOpen(false);
                }}
                disabled={isLoading}
                className="w-full px-3 py-2 text-sm text-left text-[#f5f5f5] hover:bg-[#7c3aed]/20 hover:text-[#a78bfa] rounded transition-colors disabled:opacity-50"
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
