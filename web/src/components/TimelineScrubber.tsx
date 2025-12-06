'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import type { DensityBucket } from '@/types';

interface TimelineScrubberProps {
  buckets: DensityBucket[];
  currentIndex: number;
  totalScreenshots: number;
  currentTimestamp: string | null;
  onPositionChange: (index: number) => void;
  onPrevious: () => void;
  onNext: () => void;
}

function formatTimestamp(ts: string | null): string {
  if (!ts || ts.length !== 12) return '';
  const year = 2000 + parseInt(ts.slice(0, 2));
  const month = parseInt(ts.slice(2, 4));
  const day = parseInt(ts.slice(4, 6));
  const hour = parseInt(ts.slice(6, 8));
  const minute = parseInt(ts.slice(8, 10));

  const date = new Date(year, month - 1, day, hour, minute);
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

export default function TimelineScrubber({
  buckets,
  currentIndex,
  totalScreenshots,
  currentTimestamp,
  onPositionChange,
  onPrevious,
  onNext,
}: TimelineScrubberProps) {
  const trackRef = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [hoveredBucket, setHoveredBucket] = useState<number | null>(null);

  // Calculate max count for normalization
  const maxCount = Math.max(...buckets.map(b => b.count), 1);

  // Calculate thumb position as percentage
  const thumbPosition = totalScreenshots > 0 ? (currentIndex / totalScreenshots) * 100 : 0;

  const handleTrackClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!trackRef.current) return;
    const rect = trackRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const percentage = Math.max(0, Math.min(1, x / rect.width));
    const newIndex = Math.round(percentage * (totalScreenshots - 1));
    onPositionChange(newIndex);
  }, [totalScreenshots, onPositionChange]);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!trackRef.current) return;
      const rect = trackRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const percentage = Math.max(0, Math.min(1, x / rect.width));
      const newIndex = Math.round(percentage * (totalScreenshots - 1));
      onPositionChange(newIndex);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, totalScreenshots, onPositionChange]);

  return (
    <div className="bg-neutral-950 border border-neutral-800 rounded-xl p-4">
      {/* Timestamp Display */}
      <div className="flex items-center justify-between mb-3">
        <button
          onClick={onPrevious}
          disabled={currentIndex <= 0}
          className="w-8 h-8 flex items-center justify-center text-neutral-400 hover:text-white hover:bg-neutral-800 rounded-lg disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
        </button>

        <div className="text-center">
          <p className="text-white font-medium">{formatTimestamp(currentTimestamp)}</p>
          <p className="text-xs text-neutral-500">
            {currentIndex + 1} of {totalScreenshots.toLocaleString()}
          </p>
        </div>

        <button
          onClick={onNext}
          disabled={currentIndex >= totalScreenshots - 1}
          className="w-8 h-8 flex items-center justify-center text-neutral-400 hover:text-white hover:bg-neutral-800 rounded-lg disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </div>

      {/* Density Timeline */}
      <div
        ref={trackRef}
        onClick={handleTrackClick}
        className="relative h-12 bg-neutral-900 rounded-lg cursor-pointer overflow-hidden"
      >
        {/* Density Bars */}
        <div className="absolute inset-0 flex items-end gap-px px-1 py-1">
          {buckets.map((bucket, i) => {
            const height = bucket.count > 0 ? Math.max(4, (bucket.count / maxCount) * 100) : 0;
            const isHovered = hoveredBucket === i;

            return (
              <div
                key={i}
                className="flex-1 flex items-end"
                onMouseEnter={() => setHoveredBucket(i)}
                onMouseLeave={() => setHoveredBucket(null)}
              >
                <div
                  className={`w-full rounded-sm transition-all duration-75 ${
                    bucket.count > 0
                      ? isHovered
                        ? 'bg-blue-400'
                        : 'bg-blue-500/60'
                      : 'bg-neutral-800'
                  }`}
                  style={{ height: `${height}%` }}
                />
              </div>
            );
          })}
        </div>

        {/* Thumb/Position Indicator */}
        <div
          className="absolute top-0 bottom-0 w-0.5 bg-white shadow-lg pointer-events-none"
          style={{ left: `${thumbPosition}%` }}
        >
          {/* Thumb handle */}
          <div
            onMouseDown={handleMouseDown}
            className={`absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-4 h-4 bg-white rounded-full shadow-lg cursor-grab pointer-events-auto ${
              isDragging ? 'cursor-grabbing scale-110' : ''
            }`}
          />
        </div>

        {/* Hover tooltip */}
        {hoveredBucket !== null && buckets[hoveredBucket] && (
          <div
            className="absolute bottom-full mb-2 px-2 py-1 bg-neutral-800 rounded text-xs text-white whitespace-nowrap pointer-events-none z-10"
            style={{
              left: `${(hoveredBucket / buckets.length) * 100}%`,
              transform: 'translateX(-50%)',
            }}
          >
            {buckets[hoveredBucket].count} screenshots
          </div>
        )}
      </div>

      {/* Time Labels */}
      {buckets.length > 0 && (
        <div className="flex justify-between mt-2 text-xs text-neutral-500">
          <span>{formatTimestamp(buckets[0]?.start)}</span>
          <span>{formatTimestamp(buckets[buckets.length - 1]?.end)}</span>
        </div>
      )}
    </div>
  );
}
