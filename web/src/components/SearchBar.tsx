'use client';

import { useCallback, useEffect, useRef } from 'react';
import { Search, Loader2 } from 'lucide-react';

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  onSearch: (query: string) => void;
  isSearching: boolean;
}

export function SearchBar({ value, onChange, onSearch, isSearching }: SearchBarProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<NodeJS.Timeout>();

  // Debounced search
  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    debounceRef.current = setTimeout(() => {
      onSearch(value);
    }, 300);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [value, onSearch]);

  // Focus on Cmd+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
      }
      // Escape to clear
      if (e.key === 'Escape' && document.activeElement === inputRef.current) {
        onChange('');
        inputRef.current?.blur();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onChange]);

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      onSearch(value);
    },
    [value, onSearch]
  );

  return (
    <form onSubmit={handleSubmit} className="relative">
      <div className="relative group">
        {/* Search Icon */}
        <div className="absolute inset-y-0 left-0 pl-5 flex items-center pointer-events-none">
          {isSearching ? (
            <Loader2 className="w-5 h-5 text-[#86868b] animate-spin" />
          ) : (
            <Search className="w-5 h-5 text-[#86868b] group-focus-within:text-[#0a84ff] transition-colors" />
          )}
        </div>

        {/* Input */}
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Search your visual memory..."
          className="search-input w-full pl-14 pr-24 py-4 bg-[#1c1c1e] border border-[#38383a] rounded-2xl text-white placeholder-[#636366] focus:outline-none focus:border-[#0a84ff] text-[17px]"
        />

        {/* Keyboard Shortcut */}
        <div className="absolute inset-y-0 right-0 pr-4 flex items-center pointer-events-none">
          <div className="hidden sm:flex items-center gap-1 px-2 py-1.5 text-xs text-[#636366] bg-[#2c2c2e] rounded-lg border border-[#38383a]">
            <span className="text-[10px]">⌘</span>
            <span>K</span>
          </div>
        </div>
      </div>
    </form>
  );
}
