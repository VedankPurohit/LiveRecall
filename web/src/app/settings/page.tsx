'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  getConfig,
  updateConfig,
  getStatus,
  startRecording,
  stopRecording,
  startSync,
  getSyncStatus,
  startCompression,
  getCompressionStatus,
  getCompressionStats,
} from '@/lib/api';
import type { AppConfig, SystemStatus, SyncStatus, CompressionStatus, CompressionStats } from '@/types';

const MODES = ['normal', 'games', 'fast', 'presentation', 'video', 'coding'];
const SAFE_MODE_LEVELS = [
  { value: 'low', label: 'Low' },
  { value: 'lowmid', label: 'Low-Mid' },
  { value: 'mid', label: 'Medium' },
  { value: 'midhigh', label: 'Mid-High' },
  { value: 'high', label: 'High' },
  { value: 'veryhigh', label: 'Very High' },
  { value: 'extreme', label: 'Extreme' },
];

export default function SettingsPage() {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
  const [compressionStatus, setCompressionStatus] = useState<CompressionStatus | null>(null);
  const [compressionStats, setCompressionStats] = useState<CompressionStats | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [configData, statusData, compStats] = await Promise.all([
          getConfig(),
          getStatus(),
          getCompressionStats(),
        ]);
        setConfig(configData);
        setStatus(statusData);
        setCompressionStats(compStats);
      } catch (err) {
        console.error('Failed to fetch settings:', err);
      }
    };
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const pollStatus = async () => {
      try {
        const [sync, compression] = await Promise.all([
          getSyncStatus(),
          getCompressionStatus(),
        ]);
        setSyncStatus(sync);
        setCompressionStatus(compression);
      } catch (err) {
        console.error('Failed to fetch status:', err);
      }
    };
    pollStatus();
    const interval = setInterval(pollStatus, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleUpdate = async (updates: Parameters<typeof updateConfig>[0]) => {
    try {
      await updateConfig(updates);
      const newConfig = await getConfig();
      setConfig(newConfig);
    } catch (err) {
      console.error('Failed to update:', err);
    }
  };

  const handleRecordingToggle = async () => {
    try {
      if (status?.recording.is_recording) {
        await stopRecording();
      } else {
        await startRecording();
      }
      const newStatus = await getStatus();
      setStatus(newStatus);
    } catch (err) {
      console.error('Failed to toggle recording:', err);
    }
  };

  if (!config || !status) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="w-4 h-4 border border-[#333] border-t-[#86efac] rounded-full animate-spin" />
      </div>
    );
  }

  const isRecording = status.recording.is_recording;
  const isSyncing = syncStatus?.is_syncing ?? false;
  const unsynced = status.database.unsynced;
  const modelLoaded = status.model?.loaded ?? false;

  return (
    <div className="min-h-screen bg-black flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-black border-b border-[#1e1e1e]">
        <div className="flex items-center justify-between h-12 px-4">
          <div className="flex items-center gap-6">
            <Link href="/" className="text-base font-medium text-[#f5f5f5] tracking-tight hover:text-[#86efac] transition-colors">
              LiveRecall
            </Link>
            <nav className="flex items-center">
              <Link href="/" className="px-3 py-1.5 text-sm text-[#8a8a8a] hover:text-[#f5f5f5] transition-colors">
                Timeline
              </Link>
              <Link href="/" className="px-3 py-1.5 text-sm text-[#8a8a8a] hover:text-[#f5f5f5] transition-colors">
                Search
              </Link>
              <span className="px-3 py-1.5 text-sm text-[#86efac]">Settings</span>
            </nav>
          </div>
          <div className="flex items-center gap-2">
            {unsynced > 0 && !isSyncing && (
              <button
                onClick={() => startSync()}
                className="flex items-center gap-1.5 px-2 py-1 rounded text-xs text-[#fbbf24] hover:bg-[#1c1c1c] transition-colors"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-[#fbbf24]" />
                {unsynced} unsynced
              </button>
            )}
            {isSyncing && (
              <div className="flex items-center gap-1.5 px-2 py-1 text-xs text-[#86efac]">
                <div className="w-3 h-3 border border-[#86efac]/30 border-t-[#86efac] rounded-full animate-spin" />
                Syncing...
              </div>
            )}
            <button
              onClick={handleRecordingToggle}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                isRecording ? 'text-[#ef4444]' : 'text-[#8a8a8a] hover:text-[#86efac]'
              }`}
            >
              <span className={`w-2 h-2 rounded-full ${isRecording ? 'bg-[#ef4444] animate-pulse' : 'bg-[#555]'}`} />
              {isRecording ? 'Stop' : 'Record'}
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-lg mx-auto px-4 py-6">
          <h1 className="text-lg font-medium text-[#f5f5f5] mb-6">Settings</h1>

          {/* Recording */}
          <Section title="Recording">
            <Row label="Status" value={isRecording ? 'Recording' : 'Paused'}>
              <button
                onClick={handleRecordingToggle}
                className={`px-2.5 py-1 rounded text-xs transition-colors ${
                  isRecording
                    ? 'text-[#ef4444] hover:bg-[#ef4444]/10'
                    : 'text-[#86efac] hover:bg-[#86efac]/10'
                }`}
              >
                {isRecording ? 'Stop' : 'Start'}
              </button>
            </Row>
            <Row label="Mode">
              <select
                value={config.capture.mode}
                onChange={(e) => handleUpdate({ capture_mode: e.target.value })}
                className="bg-[#0f0f0f] text-[#f5f5f5] px-2 py-1 rounded border border-[#1e1e1e] text-xs focus:border-[#86efac]/50 focus:outline-none"
              >
                {MODES.map((mode) => (
                  <option key={mode} value={mode}>{mode}</option>
                ))}
              </select>
            </Row>
            <Row label="Interval" value={`${config.capture.interval}s`}>
              <input
                type="range"
                min={1}
                max={10}
                step={0.5}
                value={config.capture.interval}
                onChange={(e) => handleUpdate({ capture_interval: Number(e.target.value) })}
                className="w-20 accent-[#86efac]"
              />
            </Row>
            <Row label="Quality" value={`${config.capture.quality}%`}>
              <input
                type="range"
                min={50}
                max={100}
                step={5}
                value={config.capture.quality}
                onChange={(e) => handleUpdate({ capture_quality: Number(e.target.value) })}
                className="w-20 accent-[#86efac]"
              />
            </Row>
          </Section>

          {/* Sync */}
          <Section title="Search">
            <Row
              label="Sync"
              value={isSyncing ? `${syncStatus?.processed}/${syncStatus?.total}` : `${unsynced} pending`}
            >
              <button
                onClick={() => startSync()}
                disabled={isSyncing || unsynced === 0}
                className="px-2.5 py-1 rounded text-xs text-[#86efac] hover:bg-[#86efac]/10 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                {isSyncing ? 'Syncing...' : 'Sync'}
              </button>
            </Row>
            <Row label="Safe Mode" value={config.safe_mode_enabled ? 'On' : 'Off'}>
              <Toggle
                enabled={config.safe_mode_enabled}
                onChange={() => handleUpdate({ safe_mode_enabled: !config.safe_mode_enabled })}
              />
            </Row>
            {config.safe_mode_enabled && (
              <Row label="Filter Level">
                <select
                  value={config.safe_mode_level}
                  onChange={(e) => handleUpdate({ safe_mode_level: e.target.value as any })}
                  className="bg-[#0f0f0f] text-[#f5f5f5] px-2 py-1 rounded border border-[#1e1e1e] text-xs focus:border-[#86efac]/50 focus:outline-none"
                >
                  {SAFE_MODE_LEVELS.map((level) => (
                    <option key={level.value} value={level.value}>{level.label}</option>
                  ))}
                </select>
              </Row>
            )}
          </Section>

          {/* Storage */}
          <Section title="Storage">
            <Row label="Auto-compress" value={config.compression.enabled ? 'On' : 'Off'}>
              <Toggle
                enabled={config.compression.enabled}
                onChange={() => handleUpdate({ compression_enabled: !config.compression.enabled })}
              />
            </Row>
            {config.compression.enabled && (
              <Row label="After" value={`${config.compression.after_days} days`}>
                <input
                  type="range"
                  min={7}
                  max={180}
                  step={7}
                  value={config.compression.after_days}
                  onChange={(e) => handleUpdate({ compression_after_days: Number(e.target.value) })}
                  className="w-20 accent-[#86efac]"
                />
              </Row>
            )}
            <Row
              label="Compress now"
              value={
                compressionStatus?.is_compressing
                  ? `${compressionStatus.processed}/${compressionStatus.total}`
                  : `${compressionStats?.compressible_count || 0} eligible`
              }
            >
              <button
                onClick={() => startCompression()}
                disabled={compressionStatus?.is_compressing || !compressionStats?.compressible_count}
                className="px-2.5 py-1 rounded text-xs text-[#fbbf24] hover:bg-[#fbbf24]/10 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                {compressionStatus?.is_compressing ? 'Running...' : 'Compress'}
              </button>
            </Row>
          </Section>

          {/* Stats */}
          <Section title="Statistics">
            <div className="space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-[#555]">Total snapshots</span>
                <span className="text-[#8a8a8a]">{status.database.total_screenshots.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#555]">Synced</span>
                <span className="text-[#8a8a8a]">{status.database.synced.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#555]">Compressed</span>
                <span className="text-[#8a8a8a]">{status.database.compressed.toLocaleString()}</span>
              </div>
            </div>
          </Section>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-[#080808] border-t border-[#1e1e1e] py-2 px-4">
        <div className="flex items-center justify-between text-[10px] text-[#555]">
          <span className={modelLoaded ? 'text-[#86efac]' : ''}>
            Model {modelLoaded ? 'loaded' : 'unloaded'}
          </span>
          <span>{status.database.total_screenshots} snapshots</span>
        </div>
      </footer>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-6">
      <h2 className="text-[10px] font-medium text-[#555] uppercase tracking-wider mb-3">{title}</h2>
      <div className="space-y-1">{children}</div>
    </div>
  );
}

function Row({
  label,
  value,
  children,
}: {
  label: string;
  value?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between py-2 px-3 rounded hover:bg-[#0f0f0f] transition-colors">
      <div className="flex items-center gap-3">
        <span className="text-xs text-[#f5f5f5]">{label}</span>
        {value && <span className="text-xs text-[#555]">{value}</span>}
      </div>
      {children}
    </div>
  );
}

function Toggle({ enabled, onChange }: { enabled: boolean; onChange: () => void }) {
  return (
    <button
      onClick={onChange}
      className={`w-8 h-5 rounded-full transition-colors relative ${
        enabled ? 'bg-[#86efac]' : 'bg-[#333]'
      }`}
    >
      <div
        className={`absolute top-0.5 w-4 h-4 rounded-full bg-black shadow transition-transform ${
          enabled ? 'left-3.5' : 'left-0.5'
        }`}
      />
    </button>
  );
}
