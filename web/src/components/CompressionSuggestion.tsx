'use client';

import { useState, useEffect } from 'react';
import { getCompressionStats, updateConfig, startCompression } from '@/lib/api';
import type { CompressionStats } from '@/types';

const DISMISSED_KEY = 'liverecall_compression_dismissed';

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(i > 1 ? 1 : 0)} ${units[i]}`;
}

export function CompressionSuggestion() {
  const [stats, setStats] = useState<CompressionStats | null>(null);
  const [visible, setVisible] = useState(false);
  const [exiting, setExiting] = useState(false);
  const [enabling, setEnabling] = useState(false);

  useEffect(() => {
    if (localStorage.getItem(DISMISSED_KEY)) return;

    const fetchStats = async () => {
      try {
        const data = await getCompressionStats();
        if (data.compressible_count > 0) {
          setStats(data);
          requestAnimationFrame(() => setVisible(true));
        }
      } catch {
        // Silently fail
      }
    };

    fetchStats();
  }, []);

  const dismiss = () => {
    localStorage.setItem(DISMISSED_KEY, Date.now().toString());
    setExiting(true);
    setTimeout(() => setVisible(false), 300);
  };

  const handleEnable = async () => {
    setEnabling(true);
    try {
      await updateConfig({ compression_enabled: true });
      try {
        await startCompression();
      } catch {
        // Config enabled but immediate start failed — will run on next trigger
      }
      dismiss();
    } catch (err) {
      console.error('Failed to enable compression:', err);
      setEnabling(false);
    }
  };

  if (!stats || !visible) return null;

  // ~295KB avg screenshot at quality 95, ~55% savings compressing to 75
  const estimatedSavings = stats.compressible_count * 295_000 * 0.55;

  return (
    <div
      className={`fixed bottom-6 left-1/2 -translate-x-1/2 z-50 transition-all duration-300 ease-out ${
        exiting
          ? 'opacity-0 translate-y-4'
          : 'opacity-100 translate-y-0 animate-slide-up'
      }`}
    >
      <div className="relative bg-[#0a0a0a] border border-[#1e1e1e] rounded-xl px-6 py-5 shadow-2xl shadow-black/60 w-[480px]">
        {/* Subtle green glow at top */}
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-[#86efac]/40 to-transparent rounded-t-xl" />

        <div className="flex items-start gap-4">
          {/* Icon */}
          <div className="flex-shrink-0 mt-0.5">
            <div className="w-10 h-10 rounded-lg bg-[#86efac]/10 flex items-center justify-center">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#86efac" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <p className="text-sm text-[#f5f5f5] font-medium">
              Free up {formatBytes(estimatedSavings)} of storage
            </p>
            <p className="text-xs text-[#666] mt-1.5 leading-relaxed">
              You have <span className="text-[#86efac] font-medium">{stats.compressible_count.toLocaleString()}</span> screenshots older than 2 months that can be compressed. Search and embeddings stay untouched.
            </p>

            {/* Buttons */}
            <div className="flex items-center gap-2.5 mt-3.5">
              <button
                onClick={handleEnable}
                disabled={enabling}
                className="px-3.5 py-2 rounded-lg text-xs font-medium bg-[#86efac]/15 text-[#86efac] hover:bg-[#86efac]/25 disabled:opacity-50 transition-colors"
              >
                {enabling ? (
                  <span className="flex items-center gap-1.5">
                    <span className="w-3 h-3 border border-[#86efac]/30 border-t-[#86efac] rounded-full animate-spin" />
                    Enabling...
                  </span>
                ) : (
                  'Enable Auto-Compression'
                )}
              </button>
              <button
                onClick={dismiss}
                className="px-3.5 py-2 rounded-lg text-xs text-[#555] hover:text-[#8a8a8a] hover:bg-[#1a1a1a] transition-colors"
              >
                Maybe later
              </button>
            </div>
          </div>

          {/* Close button */}
          <button
            onClick={dismiss}
            className="flex-shrink-0 -mt-1 -mr-2 p-1.5 rounded text-[#333] hover:text-[#666] transition-colors"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
