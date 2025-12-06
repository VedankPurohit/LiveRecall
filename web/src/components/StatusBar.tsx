'use client';

import type { SystemStatus } from '@/types';

interface StatusBarProps {
  status: SystemStatus | null;
}

export function StatusBar({ status }: StatusBarProps) {
  if (!status) {
    return (
      <footer className="px-8 py-3 border-t border-[#1c1c1e]">
        <div className="flex items-center gap-2 text-sm text-[#636366]">
          <div className="w-2 h-2 rounded-full bg-[#48484a] animate-pulse" />
          <span>Connecting...</span>
        </div>
      </footer>
    );
  }

  return (
    <footer className="px-8 py-3 border-t border-[#1c1c1e]">
      <div className="flex items-center justify-between text-[13px]">
        {/* Left - Recording & Stats */}
        <div className="flex items-center gap-5">
          {/* Recording indicator */}
          <div className="flex items-center gap-2">
            <div
              className={`w-2 h-2 rounded-full ${
                status.recording.is_recording
                  ? 'bg-red-500 status-pulse'
                  : 'bg-[#48484a]'
              }`}
            />
            <span className={status.recording.is_recording ? 'text-white' : 'text-[#636366]'}>
              {status.recording.is_recording ? 'Recording' : 'Paused'}
            </span>
            {status.recording.is_recording && (
              <span className="text-[#48484a]">
                {status.recording.mode}
              </span>
            )}
          </div>

          {/* Divider */}
          <div className="w-px h-3 bg-[#38383a]" />

          {/* Screenshots count */}
          <span className="text-[#86868b]">
            {status.database.total_screenshots.toLocaleString()} captures
          </span>

          {/* Unsynced warning */}
          {status.database.unsynced > 0 && (
            <>
              <div className="w-px h-3 bg-[#38383a]" />
              <span className="text-[#ff9f0a]">
                {status.database.unsynced} pending sync
              </span>
            </>
          )}
        </div>

        {/* Right - Model & Health */}
        <div className="flex items-center gap-5">
          {/* Model */}
          <span className={status.model.loaded ? 'text-[#30d158]' : 'text-[#636366]'}>
            {status.model.loaded ? `Model active (${status.model.device})` : 'Model idle'}
          </span>

          {/* Divider */}
          <div className="w-px h-3 bg-[#38383a]" />

          {/* System health */}
          <div className="flex items-center gap-1.5">
            <div
              className={`w-1.5 h-1.5 rounded-full ${
                status.healthy ? 'bg-[#30d158]' : 'bg-[#ff453a]'
              }`}
            />
            <span className={status.healthy ? 'text-[#30d158]' : 'text-[#ff453a]'}>
              {status.healthy ? 'System OK' : 'Error'}
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
}
