'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

interface SetupStatus {
  current_version: string;
  last_seen_version: string;
  needs_setup: boolean;
}

type SetupStep = 'welcome' | 'resetting' | 'granting' | 'complete';

export default function SetupPage() {
  const [status, setStatus] = useState<SetupStatus | null>(null);
  const [step, setStep] = useState<SetupStep>('welcome');
  const [error, setError] = useState<string | null>(null);
  const [autoResetTriggered, setAutoResetTriggered] = useState(false);

  useEffect(() => {
    fetchStatus();
  }, []);

  // Auto-trigger reset when page loads and setup is needed
  useEffect(() => {
    if (status?.needs_setup && !autoResetTriggered && step === 'welcome') {
      setAutoResetTriggered(true);
      handleResetPermissions();
    }
  }, [status, autoResetTriggered, step]);

  const fetchStatus = async () => {
    try {
      const response = await fetch('/api/v1/setup/status');
      const data = await response.json();
      setStatus(data);

      // If setup not needed, go straight to complete
      if (!data.needs_setup) {
        setStep('complete');
      }
    } catch (err) {
      console.error('Failed to fetch setup status:', err);
    }
  };

  const handleResetPermissions = async () => {
    setStep('resetting');
    setError(null);

    try {
      const response = await fetch('/api/v1/setup/reset-permissions', {
        method: 'POST',
      });
      const data = await response.json();

      if (data.success) {
        setStep('granting');
      } else {
        setError(data.message || 'Failed to reset permissions');
        setStep('welcome');
      }
    } catch (err) {
      setError('Failed to connect to backend');
      setStep('welcome');
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

  return (
    <div className="min-h-screen bg-black flex flex-col items-center justify-center p-4">
      <div className="max-w-md w-full">
        {/* Logo/Title */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-medium text-[#f5f5f5] mb-2">LiveRecall</h1>
          <p className="text-sm text-[#8a8a8a]">
            {isFirstRun
              ? "Welcome! Let's set up screen capture."
              : isUpdate
                ? `Updated to v${status?.current_version}`
                : 'Setup'}
          </p>
        </div>

        {/* Step Content */}
        <div className="bg-[#0f0f0f] rounded-lg border border-[#1e1e1e] p-6">
          {step === 'welcome' && (
            <>
              <h2 className="text-lg font-medium text-[#f5f5f5] mb-4">
                Screen Capture Permission
              </h2>
              <p className="text-sm text-[#8a8a8a] mb-4">
                LiveRecall needs screen capture permission to record your screen.
                {isUpdate && ' After an update, macOS requires re-granting this permission.'}
              </p>
              <p className="text-sm text-[#8a8a8a] mb-6">
                Click the button below to reset permissions. You&apos;ll be prompted for your
                admin password, then macOS will ask you to grant screen capture access.
              </p>

              {error && (
                <div className="mb-4 p-3 bg-[#ef4444]/10 border border-[#ef4444]/20 rounded text-sm text-[#ef4444]">
                  {error}
                </div>
              )}

              <button
                onClick={handleResetPermissions}
                className="w-full py-3 px-4 bg-[#86efac] text-black rounded font-medium hover:bg-[#86efac]/90 transition-colors"
              >
                Reset Permissions
              </button>
            </>
          )}

          {step === 'resetting' && (
            <div className="text-center py-8">
              <div className="w-8 h-8 border-2 border-[#86efac]/30 border-t-[#86efac] rounded-full animate-spin mx-auto mb-4" />
              <p className="text-sm text-[#8a8a8a]">Resetting permissions...</p>
              <p className="text-xs text-[#555] mt-2">
                Enter your admin password when prompted
              </p>
            </div>
          )}

          {step === 'granting' && (
            <>
              <h2 className="text-lg font-medium text-[#f5f5f5] mb-4">
                Grant Permission
              </h2>
              <div className="space-y-4 text-sm text-[#8a8a8a] mb-6">
                <p>Now grant screen capture permission:</p>
                <ol className="list-decimal list-inside space-y-2 text-[#f5f5f5]">
                  <li>A dialog will appear asking for Screen Recording permission</li>
                  <li>
                    Click &quot;Open System Settings&quot; or go to System Settings → Privacy &
                    Security → Screen Recording
                  </li>
                  <li>Find &quot;LiveRecall&quot; and toggle it ON</li>
                  <li>You may need to restart LiveRecall</li>
                </ol>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setStep('welcome');
                    setAutoResetTriggered(false);
                  }}
                  className="flex-1 py-3 px-4 border border-[#333] text-[#8a8a8a] rounded font-medium hover:bg-[#1e1e1e] transition-colors"
                >
                  Back
                </button>
                <button
                  onClick={handleCompleteSetup}
                  className="flex-1 py-3 px-4 bg-[#86efac] text-black rounded font-medium hover:bg-[#86efac]/90 transition-colors"
                >
                  Done
                </button>
              </div>
            </>
          )}

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

        {/* Skip option */}
        {(step === 'welcome' || step === 'granting') && (
          <div className="text-center mt-4">
            <button
              onClick={handleCompleteSetup}
              className="text-xs text-[#555] hover:text-[#8a8a8a] transition-colors"
            >
              Skip setup
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
