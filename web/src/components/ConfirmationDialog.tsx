'use client';

import { useEffect, useRef } from 'react';
import { AlertTriangle, Trash2, EyeOff, X } from 'lucide-react';

interface ConfirmationDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmText: string;
  confirmVariant: 'danger' | 'warning';
  isLoading?: boolean;
}

export function ConfirmationDialog({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText,
  confirmVariant,
  isLoading = false,
}: ConfirmationDialogProps) {
  const dialogRef = useRef<HTMLDivElement>(null);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen && !isLoading) {
        onClose();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, isLoading, onClose]);

  // Focus trap
  useEffect(() => {
    if (isOpen && dialogRef.current) {
      dialogRef.current.focus();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const isDanger = confirmVariant === 'danger';
  const Icon = isDanger ? Trash2 : EyeOff;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={isLoading ? undefined : onClose}
      />

      {/* Dialog */}
      <div
        ref={dialogRef}
        tabIndex={-1}
        className="relative bg-[#1c1c1c] border border-[#333] rounded-xl shadow-2xl w-full max-w-md mx-4 animate-in zoom-in-95 duration-200"
      >
        {/* Close button */}
        <button
          onClick={onClose}
          disabled={isLoading}
          className="absolute top-4 right-4 p-1 text-[#8a8a8a] hover:text-[#f5f5f5] hover:bg-[#333] rounded transition-colors disabled:opacity-50"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="p-6">
          {/* Icon and title */}
          <div className="flex items-start gap-4 mb-4">
            <div
              className={`p-3 rounded-full ${
                isDanger ? 'bg-[#ef4444]/10' : 'bg-[#fbbf24]/10'
              }`}
            >
              <Icon
                className={`w-6 h-6 ${
                  isDanger ? 'text-[#ef4444]' : 'text-[#fbbf24]'
                }`}
              />
            </div>
            <div className="flex-1 pt-1">
              <h2 className="text-lg font-semibold text-[#f5f5f5] mb-1">
                {title}
              </h2>
              <p className="text-sm text-[#8a8a8a] leading-relaxed">{message}</p>
            </div>
          </div>

          {/* Warning note for delete */}
          {isDanger && (
            <div className="flex items-start gap-2 p-3 bg-[#ef4444]/5 border border-[#ef4444]/20 rounded-lg mb-6">
              <AlertTriangle className="w-4 h-4 text-[#ef4444] flex-shrink-0 mt-0.5" />
              <p className="text-xs text-[#ef4444]/80">
                This action cannot be undone. The files will be permanently
                removed from your system.
              </p>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 mt-6">
            <button
              onClick={onClose}
              disabled={isLoading}
              className="px-4 py-2 text-sm text-[#8a8a8a] hover:text-[#f5f5f5] hover:bg-[#333] rounded-lg transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={onConfirm}
              disabled={isLoading}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2 ${
                isDanger
                  ? 'bg-[#ef4444] hover:bg-[#dc2626] text-white'
                  : 'bg-[#fbbf24] hover:bg-[#f59e0b] text-black'
              }`}
            >
              {isLoading ? (
                <>
                  <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Icon className="w-4 h-4" />
                  {confirmText}
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
