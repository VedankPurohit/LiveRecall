'use client';

import { Trash2, EyeOff, Eye, X, CheckSquare, ArrowLeftRight } from 'lucide-react';

interface SelectionToolbarProps {
  selectedCount: number;
  onDelete: () => void;
  onHide: () => void;
  onUnhide: () => void;
  onClear: () => void;
  onSelectAll: () => void;
  showUnhide: boolean;
  showToggle?: boolean;  // Show toggle button instead of hide/unhide when in 'all' view
  onToggleVisibility?: () => void;  // Toggle visibility of selected items
  isLoading?: boolean;
}

export function SelectionToolbar({
  selectedCount,
  onDelete,
  onHide,
  onUnhide,
  onClear,
  onSelectAll,
  showUnhide,
  showToggle = false,
  onToggleVisibility,
  isLoading = false,
}: SelectionToolbarProps) {
  if (selectedCount === 0) return null;

  return (
    <div className="fixed bottom-20 left-1/2 -translate-x-1/2 z-50 bg-[#1c1c1c] border border-[#333] rounded-lg px-4 py-2.5 flex items-center gap-4 shadow-xl animate-in slide-in-from-bottom-4 duration-200">
      {/* Selection count */}
      <div className="flex items-center gap-2">
        <CheckSquare className="w-4 h-4 text-[#86efac]" />
        <span className="text-sm text-[#f5f5f5] font-medium">
          {selectedCount} selected
        </span>
      </div>

      {/* Divider */}
      <div className="w-px h-6 bg-[#333]" />

      {/* Selection actions */}
      <div className="flex items-center gap-1">
        <button
          onClick={onSelectAll}
          disabled={isLoading}
          className="px-3 py-1.5 text-xs text-[#86efac] hover:bg-[#86efac]/10 rounded transition-colors disabled:opacity-50"
        >
          Select All
        </button>
        <button
          onClick={onClear}
          disabled={isLoading}
          className="px-3 py-1.5 text-xs text-[#8a8a8a] hover:text-[#f5f5f5] hover:bg-[#333] rounded transition-colors disabled:opacity-50"
        >
          Clear
        </button>
      </div>

      {/* Divider */}
      <div className="w-px h-6 bg-[#333]" />

      {/* Bulk actions */}
      <div className="flex items-center gap-1">
        {showToggle && onToggleVisibility ? (
          <button
            onClick={onToggleVisibility}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-[#a78bfa] hover:bg-[#a78bfa]/10 rounded transition-colors disabled:opacity-50"
          >
            <ArrowLeftRight className="w-3.5 h-3.5" />
            Toggle Visibility
          </button>
        ) : showUnhide ? (
          <button
            onClick={onUnhide}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-[#86efac] hover:bg-[#86efac]/10 rounded transition-colors disabled:opacity-50"
          >
            <Eye className="w-3.5 h-3.5" />
            Unhide
          </button>
        ) : (
          <button
            onClick={onHide}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-[#fbbf24] hover:bg-[#fbbf24]/10 rounded transition-colors disabled:opacity-50"
          >
            <EyeOff className="w-3.5 h-3.5" />
            Hide
          </button>
        )}
        <button
          onClick={onDelete}
          disabled={isLoading}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-[#ef4444] hover:bg-[#ef4444]/10 rounded transition-colors disabled:opacity-50"
        >
          <Trash2 className="w-3.5 h-3.5" />
          Delete
        </button>
      </div>

      {/* Close button */}
      <button
        onClick={onClear}
        disabled={isLoading}
        className="ml-2 p-1 text-[#8a8a8a] hover:text-[#f5f5f5] hover:bg-[#333] rounded transition-colors disabled:opacity-50"
        title="Clear selection"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}
