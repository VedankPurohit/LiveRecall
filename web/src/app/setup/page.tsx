'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';

// =============================================================================
// Types
// =============================================================================

interface SetupStatus {
  current_version: string;
  last_seen_version: string;
  needs_setup: boolean;
  needs_permission: boolean;
  platform: string;
}

interface EnhancedSetupStatus extends SetupStatus {
  models_ready: boolean;
  clip_status: 'not_downloaded' | 'downloading' | 'ready';
  text_embedding_status: 'not_downloaded' | 'downloading' | 'ready';
  ocr_status: 'ready' | 'not_available';
  migration_status: MigrationStatus | null;
}

interface MigrationStatus {
  needs_migration: boolean;
  total_screenshots: number;
  screenshots_with_ocr: number;
  screenshots_without_ocr: number;
  progress_percent: number;
  estimated_time_minutes: number | null;
}

interface SyncProgress {
  is_syncing: boolean;
  total: number;
  processed: number;
  current_phase: string;
  embeddings_done: number;
  ocr_done: number;
  text_embeddings_done: number;
}

interface EventStatus {
  clip: { loaded: boolean; downloading: boolean; downloaded: boolean };
  text_embedding: { loaded: boolean; downloading: boolean; downloaded: boolean };
  ocr: { available: boolean };
  sync: SyncProgress;
  ocr_stats: { pending: number; completed: number };
}

type SetupStep = 'loading' | 'models' | 'permission' | 'migration' | 'complete';

// =============================================================================
// Component
// =============================================================================

export default function SetupPage() {
  const [status, setStatus] = useState<EnhancedSetupStatus | null>(null);
  const [eventStatus, setEventStatus] = useState<EventStatus | null>(null);
  const [step, setStep] = useState<SetupStep>('loading');
  const [error, setError] = useState<string | null>(null);
  const [syncTriggered, setSyncTriggered] = useState(false);
  const [downloadTriggered, setDownloadTriggered] = useState(false);

  // Fetch enhanced setup status
  const fetchStatus = useCallback(async () => {
    try {
      const response = await fetch('/api/v1/setup/enhanced-status');
      const data: EnhancedSetupStatus = await response.json();
      setStatus(data);
      return data;
    } catch (err) {
      console.error('Failed to fetch setup status:', err);
      return null;
    }
  }, []);

  // Fetch real-time status from events endpoint
  const fetchEventStatus = useCallback(async () => {
    try {
      const response = await fetch('/api/v1/events/status');
      const data: EventStatus = await response.json();
      setEventStatus(data);
      return data;
    } catch (err) {
      console.error('Failed to fetch event status:', err);
      return null;
    }
  }, []);

  // Determine which step we should be on
  const determineStep = useCallback((status: EnhancedSetupStatus, eventStatus: EventStatus | null): SetupStep => {
    // Check if models are ready (either from enhanced-status or events-status)
    // The eventStatus.downloaded field provides a more reliable check when models are downloaded but not loaded
    const clipReady = status.clip_status === 'ready' || eventStatus?.clip?.downloaded;
    const textReady = status.text_embedding_status === 'ready' || eventStatus?.text_embedding?.downloaded;

    // Check if models are downloading or not ready
    if (!clipReady || !textReady ||
        eventStatus?.clip?.downloading ||
        eventStatus?.text_embedding?.downloading) {
      return 'models';
    }

    // Check if permission is needed (macOS only, on update)
    if (status.needs_permission && status.needs_setup && status.platform === 'macos') {
      return 'permission';
    }

    // Check if OCR migration is needed
    if (status.migration_status?.needs_migration ||
        (eventStatus?.ocr_stats?.pending && eventStatus.ocr_stats.pending > 0)) {
      return 'migration';
    }

    return 'complete';
  }, []);

  // Initial load
  useEffect(() => {
    const init = async () => {
      try {
        const setupStatus = await fetchStatus();
        const evtStatus = await fetchEventStatus();

        if (setupStatus) {
          const nextStep = determineStep(setupStatus, evtStatus);
          setStep(nextStep);
        } else {
          // API returned null - show error
          setError('Could not connect to backend. Is it running?');
          setStep('models'); // Show something rather than stuck loading
        }
      } catch (err) {
        console.error('Setup init error:', err);
        setError('Failed to load setup status. Check if backend is running.');
        setStep('models'); // Show something rather than stuck loading
      }
    };
    init();
  }, [fetchStatus, fetchEventStatus, determineStep]);

  // Poll for updates during active steps
  useEffect(() => {
    if (step === 'loading' || step === 'complete') return;

    const interval = setInterval(async () => {
      const setupStatus = await fetchStatus();
      const evtStatus = await fetchEventStatus();

      if (setupStatus) {
        const nextStep = determineStep(setupStatus, evtStatus);

        // Auto-advance steps when done
        if (step === 'models' && nextStep !== 'models') {
          setStep(nextStep);
        } else if (step === 'migration' && nextStep === 'complete') {
          setStep('complete');
        }
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [step, fetchStatus, fetchEventStatus, determineStep]);

  // Auto-trigger model download when on models step
  useEffect(() => {
    if (step === 'models' && !downloadTriggered && status) {
      // Check if any model needs downloading
      const needsClip = status.clip_status !== 'ready';
      const needsBge = status.text_embedding_status !== 'ready';

      if (needsClip || needsBge) {
        setDownloadTriggered(true);
        // Trigger download endpoint - this will download models
        fetch('/api/v1/setup/download-models', { method: 'POST' })
          .then(async (response) => {
            // The endpoint returns an SSE stream, but we don't need to read it
            // The polling will pick up the status changes
            console.log('Model download triggered');
          })
          .catch(console.error);
      }
    }
  }, [step, downloadTriggered, status]);

  // Trigger sync when on migration step
  useEffect(() => {
    if (step === 'migration' && !syncTriggered && !eventStatus?.sync?.is_syncing) {
      setSyncTriggered(true);
      // Trigger sync to process OCR for existing screenshots
      fetch('/api/v1/sync/start', { method: 'POST' }).catch(console.error);
    }
  }, [step, syncTriggered, eventStatus?.sync?.is_syncing]);

  const handleResetPermissions = async () => {
    setError(null);
    try {
      const response = await fetch('/api/v1/setup/reset-permissions', {
        method: 'POST',
      });
      const data = await response.json();
      if (!data.success) {
        setError(data.message || 'Failed to reset permissions');
      }
    } catch (err) {
      setError('Failed to connect to backend');
    }
  };

  const handleCompleteSetup = async () => {
    try {
      await fetch('/api/v1/setup/complete', { method: 'POST' });
      setStep('complete');
    } catch (err) {
      console.error('Failed to complete setup:', err);
    }
  };

  const isFirstRun = status && !status.last_seen_version;
  const isUpdate = status && status.last_seen_version && status.last_seen_version !== status.current_version;

  // Calculate migration progress (guard against division by zero)
  const migrationProgress = eventStatus?.ocr_stats
    ? (eventStatus.ocr_stats.completed + eventStatus.ocr_stats.pending > 0
        ? (eventStatus.ocr_stats.completed / (eventStatus.ocr_stats.completed + eventStatus.ocr_stats.pending)) * 100
        : 100)
    : status?.migration_status?.progress_percent ?? 0;

  return (
    <div className="min-h-screen bg-black flex flex-col items-center justify-center p-4">
      <div className="max-w-md w-full">
        {/* Logo/Title */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-medium text-[#f5f5f5] mb-2">LiveRecall</h1>
          <p className="text-sm text-[#8a8a8a]">
            {isFirstRun
              ? "Welcome! Let's get you set up."
              : isUpdate
                ? `Updated to v${status?.current_version}`
                : 'Setup'}
          </p>
        </div>

        {/* Step Content */}
        <div className="bg-[#0f0f0f] rounded-lg border border-[#1e1e1e] p-6">

          {/* Loading State */}
          {step === 'loading' && (
            <div className="text-center py-8">
              <div className="w-8 h-8 border-2 border-[#86efac]/30 border-t-[#86efac] rounded-full animate-spin mx-auto mb-4" />
              <p className="text-sm text-[#8a8a8a]">Checking setup status...</p>
            </div>
          )}

          {/* Models Step - Download Progress */}
          {step === 'models' && (
            <>
              <h2 className="text-lg font-medium text-[#f5f5f5] mb-4">
                Downloading Models
              </h2>
              <p className="text-sm text-[#8a8a8a] mb-6">
                LiveRecall uses AI models for image and text search.
                This is a one-time download.
              </p>

              {/* CLIP Model */}
              <div className="mb-4">
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-[#f5f5f5]">CLIP Vision Model</span>
                  <span className="text-[#8a8a8a]">
                    {(status?.clip_status === 'ready' || eventStatus?.clip?.downloaded) ? 'Ready' :
                     eventStatus?.clip?.downloading ? 'Downloading...' :
                     status?.clip_status === 'downloading' ? 'Downloading...' : 'Pending'}
                  </span>
                </div>
                <div className="h-2 bg-[#1e1e1e] rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all duration-300 ${
                      (status?.clip_status === 'ready' || eventStatus?.clip?.downloaded)
                        ? 'bg-[#86efac] w-full'
                        : 'bg-[#86efac]/50 w-1/3 animate-pulse'
                    }`}
                  />
                </div>
                <p className="text-xs text-[#555] mt-1">~1.7 GB - Required for image search</p>
              </div>

              {/* Text Embedding Model */}
              <div className="mb-4">
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-[#f5f5f5]">Text Embedding Model</span>
                  <span className="text-[#8a8a8a]">
                    {(status?.text_embedding_status === 'ready' || eventStatus?.text_embedding?.downloaded) ? 'Ready' :
                     eventStatus?.text_embedding?.downloading ? 'Downloading...' :
                     status?.text_embedding_status === 'downloading' ? 'Downloading...' : 'Pending'}
                  </span>
                </div>
                <div className="h-2 bg-[#1e1e1e] rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all duration-300 ${
                      (status?.text_embedding_status === 'ready' || eventStatus?.text_embedding?.downloaded)
                        ? 'bg-[#86efac] w-full'
                        : 'bg-[#86efac]/50 w-1/4 animate-pulse'
                    }`}
                  />
                </div>
                <p className="text-xs text-[#555] mt-1">~130 MB - For text search</p>
              </div>

              {/* OCR Status */}
              <div className="mb-6">
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-[#f5f5f5]">OCR Engine</span>
                  <span className="text-[#8a8a8a]">
                    {(status?.ocr_status === 'ready' || eventStatus?.ocr?.available) ? 'Ready' : 'Not Available'}
                  </span>
                </div>
                <div className="h-2 bg-[#1e1e1e] rounded-full overflow-hidden">
                  <div
                    className={`h-full ${
                      (status?.ocr_status === 'ready' || eventStatus?.ocr?.available) ? 'bg-[#86efac] w-full' : 'bg-[#555] w-full'
                    }`}
                  />
                </div>
                <p className="text-xs text-[#555] mt-1">
                  {status?.platform === 'macos' ? 'Apple Vision (built-in)' : 'Tesseract'}
                </p>
              </div>

              <div className="text-center">
                {!(status?.clip_status === 'ready' || eventStatus?.clip?.downloaded) && (
                  <>
                    <div className="w-6 h-6 border-2 border-[#86efac]/30 border-t-[#86efac] rounded-full animate-spin mx-auto mb-2" />
                    <p className="text-xs text-[#555]">
                      Downloading models automatically...
                    </p>
                  </>
                )}
              </div>
            </>
          )}

          {/* Permission Step */}
          {step === 'permission' && (
            <>
              <h2 className="text-lg font-medium text-[#f5f5f5] mb-4">
                Screen Capture Permission
              </h2>
              <p className="text-sm text-[#8a8a8a] mb-4">
                LiveRecall needs screen capture permission to record your screen.
                {isUpdate && ' After an update, macOS requires re-granting this permission.'}
              </p>
              <div className="space-y-4 text-sm text-[#8a8a8a] mb-6">
                <ol className="list-decimal list-inside space-y-2 text-[#f5f5f5]">
                  <li>Click &quot;Reset Permissions&quot; below</li>
                  <li>Enter your admin password when prompted</li>
                  <li>Go to System Settings → Privacy & Security → Screen Recording</li>
                  <li>Find &quot;LiveRecall&quot; and toggle it ON</li>
                </ol>
              </div>

              {error && (
                <div className="mb-4 p-3 bg-[#ef4444]/10 border border-[#ef4444]/20 rounded text-sm text-[#ef4444]">
                  {error}
                </div>
              )}

              <div className="flex gap-3">
                <button
                  onClick={handleResetPermissions}
                  className="flex-1 py-3 px-4 bg-[#86efac] text-black rounded font-medium hover:bg-[#86efac]/90 transition-colors"
                >
                  Reset Permissions
                </button>
                <button
                  onClick={() => {
                    // Check if we should go to migration or complete
                    if (status?.migration_status?.needs_migration) {
                      setStep('migration');
                    } else {
                      handleCompleteSetup();
                    }
                  }}
                  className="flex-1 py-3 px-4 border border-[#333] text-[#8a8a8a] rounded font-medium hover:bg-[#1e1e1e] transition-colors"
                >
                  Continue
                </button>
              </div>
            </>
          )}

          {/* Migration Step - OCR Processing */}
          {step === 'migration' && (
            <>
              <h2 className="text-lg font-medium text-[#f5f5f5] mb-4">
                Processing Existing Screenshots
              </h2>
              <p className="text-sm text-[#8a8a8a] mb-6">
                LiveRecall is extracting text from your existing screenshots to enable text search.
                This runs in the background.
              </p>

              {/* Progress Bar */}
              <div className="mb-4">
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-[#f5f5f5]">OCR Processing</span>
                  <span className="text-[#8a8a8a]">
                    {Math.round(migrationProgress || 0)}%
                  </span>
                </div>
                <div className="h-2 bg-[#1e1e1e] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[#86efac] transition-all duration-500"
                    style={{ width: `${migrationProgress || 0}%` }}
                  />
                </div>
              </div>

              {/* Stats */}
              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="bg-[#1e1e1e] rounded p-3 text-center">
                  <div className="text-lg font-medium text-[#f5f5f5]">
                    {eventStatus?.ocr_stats?.completed ?? status?.migration_status?.screenshots_with_ocr ?? 0}
                  </div>
                  <div className="text-xs text-[#8a8a8a]">Processed</div>
                </div>
                <div className="bg-[#1e1e1e] rounded p-3 text-center">
                  <div className="text-lg font-medium text-[#f5f5f5]">
                    {eventStatus?.ocr_stats?.pending ?? status?.migration_status?.screenshots_without_ocr ?? 0}
                  </div>
                  <div className="text-xs text-[#8a8a8a]">Remaining</div>
                </div>
              </div>

              {/* Current Phase */}
              {eventStatus?.sync?.is_syncing && (
                <div className="flex items-center justify-center gap-2 mb-4">
                  <div className="w-4 h-4 border-2 border-[#86efac]/30 border-t-[#86efac] rounded-full animate-spin" />
                  <span className="text-sm text-[#8a8a8a]">
                    {eventStatus.sync.current_phase === 'embedding' && 'Generating image embeddings...'}
                    {eventStatus.sync.current_phase === 'ocr' && 'Extracting text (OCR)...'}
                    {eventStatus.sync.current_phase === 'text_embedding' && 'Generating text embeddings...'}
                    {!eventStatus.sync.current_phase && 'Processing...'}
                  </span>
                </div>
              )}

              {status?.migration_status?.estimated_time_minutes && migrationProgress < 100 && (
                <p className="text-xs text-[#555] text-center mb-4">
                  Estimated time remaining: ~{Math.round(status.migration_status.estimated_time_minutes * (100 - migrationProgress) / 100)} minutes
                </p>
              )}

              <button
                onClick={handleCompleteSetup}
                className="w-full py-3 px-4 bg-[#86efac] text-black rounded font-medium hover:bg-[#86efac]/90 transition-colors"
              >
                {migrationProgress >= 100 ? 'Continue' : 'Continue in Background'}
              </button>
              <p className="text-xs text-[#555] text-center mt-2">
                Processing will continue in the background
              </p>
            </>
          )}

          {/* Complete Step */}
          {step === 'complete' && (
            <div className="text-center py-4">
              <div className="w-12 h-12 rounded-full bg-[#86efac]/10 flex items-center justify-center mx-auto mb-4">
                <svg
                  className="w-6 h-6 text-[#86efac]"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              </div>
              <h2 className="text-lg font-medium text-[#f5f5f5] mb-2">Setup Complete!</h2>
              <p className="text-sm text-[#8a8a8a] mb-6">LiveRecall is ready to use.</p>
              <Link
                href="/"
                className="inline-block py-3 px-8 bg-[#86efac] text-black rounded font-medium hover:bg-[#86efac]/90 transition-colors"
              >
                Open LiveRecall
              </Link>
            </div>
          )}
        </div>

        {/* Step indicators */}
        {step !== 'loading' && step !== 'complete' && (
          <div className="flex justify-center gap-2 mt-6">
            <div className={`w-2 h-2 rounded-full ${step === 'models' ? 'bg-[#86efac]' : 'bg-[#333]'}`} />
            <div className={`w-2 h-2 rounded-full ${step === 'permission' ? 'bg-[#86efac]' : 'bg-[#333]'}`} />
            <div className={`w-2 h-2 rounded-full ${step === 'migration' ? 'bg-[#86efac]' : 'bg-[#333]'}`} />
          </div>
        )}
      </div>
    </div>
  );
}
