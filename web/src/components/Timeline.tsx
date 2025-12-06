'use client';

import { useMemo, useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight, X } from 'lucide-react';
import type { Screenshot } from '@/types';

interface TimelineProps {
  screenshots: Screenshot[];
  getImageUrl: (path: string) => string;
}

interface DayGroup {
  date: string;
  displayDate: string;
  screenshots: Screenshot[];
}

function parseTimestamp(timestamp: string): Date {
  if (timestamp.length !== 12) return new Date();

  const year = 2000 + parseInt(timestamp.slice(0, 2));
  const month = parseInt(timestamp.slice(2, 4)) - 1;
  const day = parseInt(timestamp.slice(4, 6));
  const hour = parseInt(timestamp.slice(6, 8));
  const minute = parseInt(timestamp.slice(8, 10));
  const second = parseInt(timestamp.slice(10, 12));

  return new Date(year, month, day, hour, minute, second);
}

function formatTime(timestamp: string): string {
  const date = parseTimestamp(timestamp);
  return date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}

export function Timeline({ screenshots, getImageUrl }: TimelineProps) {
  const [selectedImage, setSelectedImage] = useState<Screenshot | null>(null);

  // Keyboard navigation for lightbox
  useEffect(() => {
    if (!selectedImage) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      const currentIndex = screenshots.findIndex((s) => s.id === selectedImage.id);

      if (e.key === 'ArrowLeft' && currentIndex > 0) {
        setSelectedImage(screenshots[currentIndex - 1]);
      } else if (e.key === 'ArrowRight' && currentIndex < screenshots.length - 1) {
        setSelectedImage(screenshots[currentIndex + 1]);
      } else if (e.key === 'Escape') {
        setSelectedImage(null);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedImage, screenshots]);

  // Group screenshots by day
  const dayGroups = useMemo(() => {
    const groups: Map<string, DayGroup> = new Map();

    screenshots.forEach((screenshot) => {
      const date = parseTimestamp(screenshot.timestamp);
      const dateKey = date.toISOString().split('T')[0];

      if (!groups.has(dateKey)) {
        groups.set(dateKey, {
          date: dateKey,
          displayDate: date.toLocaleDateString('en-US', {
            weekday: 'long',
            month: 'long',
            day: 'numeric',
          }),
          screenshots: [],
        });
      }

      groups.get(dateKey)!.screenshots.push(screenshot);
    });

    return Array.from(groups.values()).sort(
      (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()
    );
  }, [screenshots]);

  if (screenshots.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-[#86868b]">
        <div className="w-16 h-16 rounded-2xl bg-[#1c1c1e] flex items-center justify-center mb-5">
          <svg className="w-8 h-8 text-[#48484a]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" />
          </svg>
        </div>
        <p className="text-lg font-medium text-white mb-1">No timeline yet</p>
        <p className="text-sm">Screenshots will appear here once captured</p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-8 py-6">
      {dayGroups.map((group) => (
        <div key={group.date} className="mb-10">
          {/* Day Header - minimal */}
          <div className="sticky top-0 z-10 vibrancy py-4 -mx-8 px-8 mb-5">
            <h2 className="text-xl font-semibold tracking-tight">{group.displayDate}</h2>
            <p className="text-sm text-[#86868b] mt-0.5">
              {group.screenshots.length} capture{group.screenshots.length !== 1 ? 's' : ''}
            </p>
          </div>

          {/* Horizontal scroll strip */}
          <div className="flex gap-3 overflow-x-auto pb-2 -mx-8 px-8 scrollbar-hide">
            {group.screenshots.map((screenshot) => (
              <div
                key={screenshot.id}
                onClick={() => setSelectedImage(screenshot)}
                className="flex-shrink-0 cursor-pointer group"
              >
                <div className="relative rounded-xl overflow-hidden bg-[#1c1c1e] transition-transform hover:scale-[1.02]">
                  <img
                    src={getImageUrl(screenshot.image_path)}
                    alt=""
                    className="h-36 w-auto object-cover"
                    loading="lazy"
                  />
                  {/* Time overlay */}
                  <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/60 to-transparent p-2">
                    <span className="text-xs text-white/90 font-medium">
                      {formatTime(screenshot.timestamp)}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      {/* Lightbox */}
      {selectedImage && (
        <div
          className="fixed inset-0 z-50 bg-black/95 flex items-center justify-center"
          onClick={() => setSelectedImage(null)}
        >
          {/* Close */}
          <button
            onClick={() => setSelectedImage(null)}
            className="absolute top-5 right-5 z-10 w-10 h-10 flex items-center justify-center text-white/60 hover:text-white bg-white/10 hover:bg-white/20 rounded-full transition-all"
          >
            <X className="w-5 h-5" />
          </button>

          {/* Navigation */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              const currentIndex = screenshots.findIndex((s) => s.id === selectedImage.id);
              if (currentIndex > 0) {
                setSelectedImage(screenshots[currentIndex - 1]);
              }
            }}
            className="absolute left-5 top-1/2 -translate-y-1/2 w-12 h-12 flex items-center justify-center text-white/60 hover:text-white bg-white/10 hover:bg-white/20 rounded-full transition-all"
          >
            <ChevronLeft className="w-6 h-6" />
          </button>

          <button
            onClick={(e) => {
              e.stopPropagation();
              const currentIndex = screenshots.findIndex((s) => s.id === selectedImage.id);
              if (currentIndex < screenshots.length - 1) {
                setSelectedImage(screenshots[currentIndex + 1]);
              }
            }}
            className="absolute right-5 top-1/2 -translate-y-1/2 w-12 h-12 flex items-center justify-center text-white/60 hover:text-white bg-white/10 hover:bg-white/20 rounded-full transition-all"
          >
            <ChevronRight className="w-6 h-6" />
          </button>

          {/* Image */}
          <div onClick={(e) => e.stopPropagation()}>
            <img
              src={getImageUrl(selectedImage.image_path)}
              alt=""
              className="max-w-[90vw] max-h-[85vh] object-contain rounded-lg shadow-2xl"
            />
          </div>

          {/* Bottom bar */}
          <div className="absolute bottom-0 inset-x-0 glass py-4 px-6">
            <div className="max-w-3xl mx-auto text-center">
              <p className="text-white font-medium">{formatTime(selectedImage.timestamp)}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
