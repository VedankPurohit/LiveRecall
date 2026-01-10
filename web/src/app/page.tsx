'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import Link from 'next/link';
import {
  getStatus,
  getSyncStatus,
  startRecording,
  stopRecording,
  startSync,
  getScreenshots,
  getScreenshotOffset,
  getDensity,
  getImageUrl,
  search,
  getIncognitoStatus,
  setIncognitoMode,
  stopIncognitoMode,
  bulkDeleteScreenshots,
  bulkHideScreenshots,
  bulkUnhideScreenshots,
} from '@/lib/api';
import type { Screenshot, SystemStatus, SyncStatus, DensityBucket, IncognitoStatus, VisibilityFilter } from '@/types';
import { useSelection } from '@/hooks/useSelection';
import { SelectionToolbar } from '@/components/SelectionToolbar';
import { ConfirmationDialog } from '@/components/ConfirmationDialog';
import { IncognitoIndicator } from '@/components/IncognitoIndicator';

// localStorage keys
const STORAGE_KEYS = {
  SAFE_MODE: 'liverecall_safe_mode',
  SAFE_MODE_LEVEL: 'liverecall_safe_mode_level',
  DATE_PRESET: 'liverecall_date_preset',
  VISIBILITY_FILTER: 'liverecall_visibility_filter',
};

const SAFE_MODE_LEVELS = [
  { value: 'low', label: 'Low' },
  { value: 'lowmid', label: 'Low-Mid' },
  { value: 'mid', label: 'Medium' },
  { value: 'midhigh', label: 'Mid-High' },
  { value: 'high', label: 'High' },
  { value: 'veryhigh', label: 'Very High' },
  { value: 'extreme', label: 'Extreme' },
];

export default function Home() {
  const [activeView, setActiveView] = useState<'timeline' | 'search'>('timeline');
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
  const [snapshots, setSnapshots] = useState<Screenshot[]>([]);
  const [densityBuckets, setDensityBuckets] = useState<DensityBucket[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [totalSnapshots, setTotalSnapshots] = useState(0);
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Screenshot[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchTime, setSearchTime] = useState<number | null>(null);
  const [searchStartDate, setSearchStartDate] = useState<string | undefined>();
  const [searchEndDate, setSearchEndDate] = useState<string | undefined>();
  const [selectedImage, setSelectedImage] = useState<Screenshot | null>(null);
  const [datePreset, setDatePreset] = useState<string>('all');
  const [safeMode, setSafeMode] = useState(true);
  const [safeModeLevel, setSafeModeLevel] = useState<string>('mid');
  const [hasTriggeredSync, setHasTriggeredSync] = useState(false);

  // Incognito state
  const [incognitoStatus, setIncognitoStatus] = useState<IncognitoStatus>({
    active: false,
    remaining_seconds: 0,
    until_timestamp: null,
  });
  const [isIncognitoLoading, setIsIncognitoLoading] = useState(false);

  // Visibility filter
  const [visibilityFilter, setVisibilityFilter] = useState<VisibilityFilter>('visible_only');

  // Selection state
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showHideConfirm, setShowHideConfirm] = useState(false);
  const [isBulkOperationLoading, setIsBulkOperationLoading] = useState(false);

  // Gallery state (all snapshots for search view when query is empty)
  const [gallerySnapshots, setGallerySnapshots] = useState<Screenshot[]>([]);
  const [galleryTotal, setGalleryTotal] = useState(0);

  // Infinite scroll state for gallery (bidirectional)
  const [galleryOffset, setGalleryOffset] = useState(0);
  const [hasMoreGallery, setHasMoreGallery] = useState(true);
  const [hasMoreGalleryBefore, setHasMoreGalleryBefore] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [isLoadingMoreBefore, setIsLoadingMoreBefore] = useState(false);
  const GALLERY_PAGE_SIZE = 50;
  const loadMoreRef = useRef<HTMLDivElement>(null);
  const loadMoreBeforeRef = useRef<HTMLDivElement>(null);
  const gridContainerRef = useRef<HTMLDivElement>(null);

  const mainImageRef = useRef<HTMLImageElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const [highlightedId, setHighlightedId] = useState<number | null>(null);
  const skipGalleryFetchRef = useRef(false); // Skip auto-fetch when navigating to specific position
  const skipLoadBeforeRef = useRef(false); // Skip "load before" after navigation to prevent immediate trigger

  // Selection hook - works with current view's items
  const currentViewItems = activeView === 'search'
    ? (query.trim() ? searchResults : gallerySnapshots)
    : snapshots;
  const selection = useSelection(currentViewItems);

  // Load preferences from localStorage
  useEffect(() => {
    const savedSafeMode = localStorage.getItem(STORAGE_KEYS.SAFE_MODE);
    if (savedSafeMode !== null) {
      setSafeMode(savedSafeMode === 'true');
    }
    const savedSafeModeLevel = localStorage.getItem(STORAGE_KEYS.SAFE_MODE_LEVEL);
    if (savedSafeModeLevel) {
      setSafeModeLevel(savedSafeModeLevel);
    }
    const savedDatePreset = localStorage.getItem(STORAGE_KEYS.DATE_PRESET);
    if (savedDatePreset) {
      setDatePreset(savedDatePreset);
      handleDatePreset(savedDatePreset, false);
    }
    const savedVisibilityFilter = localStorage.getItem(STORAGE_KEYS.VISIBILITY_FILTER);
    if (savedVisibilityFilter) {
      setVisibilityFilter(savedVisibilityFilter as VisibilityFilter);
    }
  }, []);

  // Fetch incognito status
  useEffect(() => {
    const fetchIncognitoStatus = async () => {
      try {
        const status = await getIncognitoStatus();
        setIncognitoStatus(status);
      } catch (err) {
        console.error('Failed to fetch incognito status:', err);
      }
    };
    fetchIncognitoStatus();
    const interval = setInterval(fetchIncognitoStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  // Save safe mode preferences
  const handleSafeModeToggle = () => {
    const newValue = !safeMode;
    setSafeMode(newValue);
    localStorage.setItem(STORAGE_KEYS.SAFE_MODE, String(newValue));
  };

  const handleSafeModeLevelChange = (level: string) => {
    setSafeModeLevel(level);
    localStorage.setItem(STORAGE_KEYS.SAFE_MODE_LEVEL, level);
  };

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const [statusData, syncData] = await Promise.all([getStatus(), getSyncStatus()]);
        setStatus(statusData);
        setSyncStatus(syncData);
      } catch (err) {
        console.error('Failed to fetch status:', err);
      }
    };
    fetchStatus();
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  const [isLoading, setIsLoading] = useState(true);

  // Refetch data when visibility filter changes
  const fetchData = useCallback(async () => {
    try {
      const [snapshotsData, densityData] = await Promise.all([
        getScreenshots(500, 0, undefined, undefined, visibilityFilter),
        getDensity(100, visibilityFilter),
      ]);
      if (snapshotsData?.screenshots) {
        setSnapshots(snapshotsData.screenshots);
        setTotalSnapshots(snapshotsData.total);
      }
      if (densityData?.buckets) {
        setDensityBuckets(densityData.buckets);
      }
      if (snapshotsData?.screenshots?.length > 0) {
        setCurrentIndex(0);
      }
    } catch (err) {
      console.error('Failed to fetch data:', err);
    } finally {
      setIsLoading(false);
    }
  }, [visibilityFilter]);

  useEffect(() => {
    setIsLoading(true);
    fetchData();
  }, [fetchData]);

  // Fetch gallery snapshots for search view when query is empty
  useEffect(() => {
    if (activeView === 'search' && !query.trim()) {
      // Skip if we're navigating to a specific position (e.g., from View in Grid)
      if (skipGalleryFetchRef.current) {
        skipGalleryFetchRef.current = false;
        return;
      }
      const fetchGallery = async () => {
        try {
          // Reset pagination state for both directions
          setGalleryOffset(0);
          setHasMoreGallery(true);
          setHasMoreGalleryBefore(false); // Starting from offset 0, nothing before
          const data = await getScreenshots(GALLERY_PAGE_SIZE, 0, undefined, undefined, visibilityFilter);
          if (data?.screenshots) {
            setGallerySnapshots(data.screenshots);
            setGalleryTotal(data.total);
            setHasMoreGallery(data.screenshots.length === GALLERY_PAGE_SIZE && data.screenshots.length < data.total);
          }
        } catch (err) {
          console.error('Failed to fetch gallery:', err);
        }
      };
      fetchGallery();
    }
  }, [activeView, query, visibilityFilter]);

  // Load more gallery images for infinite scroll
  const loadMoreGallery = useCallback(async () => {
    if (isLoadingMore || !hasMoreGallery || query.trim()) return;

    setIsLoadingMore(true);
    try {
      const newOffset = galleryOffset + GALLERY_PAGE_SIZE;
      const data = await getScreenshots(GALLERY_PAGE_SIZE, newOffset, undefined, undefined, visibilityFilter);

      if (data?.screenshots?.length) {
        setGallerySnapshots(prev => [...prev, ...data.screenshots]);
        setGalleryOffset(newOffset);
        setHasMoreGallery(data.screenshots.length === GALLERY_PAGE_SIZE && gallerySnapshots.length + data.screenshots.length < data.total);
      } else {
        setHasMoreGallery(false);
      }
    } catch (err) {
      console.error('Failed to load more gallery:', err);
    } finally {
      setIsLoadingMore(false);
    }
  }, [isLoadingMore, hasMoreGallery, galleryOffset, visibilityFilter, query, gallerySnapshots.length]);

  // Load more gallery images before current position (for bidirectional scroll)
  const loadMoreGalleryBefore = useCallback(async () => {
    // Skip if flag is set (navigation in progress, flag cleared after scroll completes)
    if (skipLoadBeforeRef.current) return;

    if (isLoadingMoreBefore || !hasMoreGalleryBefore || galleryOffset <= 0 || query.trim()) return;

    setIsLoadingMoreBefore(true);
    try {
      const loadCount = Math.min(GALLERY_PAGE_SIZE, galleryOffset);
      const newOffset = galleryOffset - loadCount;

      // Capture scroll position before prepending
      const container = gridContainerRef.current;
      const scrollHeightBefore = container?.scrollHeight || 0;

      const data = await getScreenshots(loadCount, newOffset, undefined, undefined, visibilityFilter);

      if (data?.screenshots?.length) {
        // Prepend to existing screenshots
        setGallerySnapshots(prev => [...data.screenshots, ...prev]);
        setGalleryOffset(newOffset);
        setHasMoreGalleryBefore(newOffset > 0);

        // Restore scroll position after prepending (compensate for new content)
        if (container) {
          requestAnimationFrame(() => {
            const scrollHeightAfter = container.scrollHeight;
            const heightDiff = scrollHeightAfter - scrollHeightBefore;
            container.scrollTop += heightDiff;
          });
        }
      } else {
        setHasMoreGalleryBefore(false);
      }
    } catch (err) {
      console.error('Failed to load more gallery (before):', err);
    } finally {
      setIsLoadingMoreBefore(false);
    }
  }, [isLoadingMoreBefore, hasMoreGalleryBefore, galleryOffset, visibilityFilter, query]);

  // Intersection observer for infinite scroll (load more at bottom)
  useEffect(() => {
    if (activeView !== 'search' || query.trim()) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMoreGallery && !isLoadingMore) {
          loadMoreGallery();
        }
      },
      { threshold: 0.1, rootMargin: '100px' }
    );

    if (loadMoreRef.current) {
      observer.observe(loadMoreRef.current);
    }

    return () => observer.disconnect();
  }, [activeView, query, hasMoreGallery, isLoadingMore, loadMoreGallery]);

  // Intersection observer for bidirectional scroll (load more at top)
  useEffect(() => {
    if (activeView !== 'search' || query.trim() || !hasMoreGalleryBefore) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMoreGalleryBefore && !isLoadingMoreBefore) {
          loadMoreGalleryBefore();
        }
      },
      { threshold: 0.1, rootMargin: '100px' }
    );

    if (loadMoreBeforeRef.current) {
      observer.observe(loadMoreBeforeRef.current);
    }

    return () => observer.disconnect();
  }, [activeView, query, hasMoreGalleryBefore, isLoadingMoreBefore, loadMoreGalleryBefore]);

  // Auto-sync when user starts searching (to load model)
  useEffect(() => {
    if (query.trim() && !hasTriggeredSync && status?.database.unsynced && status.database.unsynced > 0) {
      setHasTriggeredSync(true);
      startSync().catch(console.error);
    }
  }, [query, hasTriggeredSync, status?.database.unsynced]);

  useEffect(() => {
    if (!query.trim()) {
      setSearchResults([]);
      setSearchTime(null);
      return;
    }

    const timer = setTimeout(async () => {
      setIsSearching(true);
      try {
        const startTime = performance.now();
        const data = await search(query, 50, safeMode, safeModeLevel, searchStartDate, searchEndDate, visibilityFilter);
        setSearchResults(data.results);
        setSearchTime(performance.now() - startTime);
      } catch (err) {
        console.error('Search failed:', err);
        setSearchResults([]);
      } finally {
        setIsSearching(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [query, searchStartDate, searchEndDate, safeMode, safeModeLevel, visibilityFilter]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (selectedImage) setSelectedImage(null);
        else if (selection.selectedIds.size > 0) selection.clearSelection();
        else if (query) setQuery('');
        return;
      }
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        searchInputRef.current?.focus();
        return;
      }
      if (e.key === '/' && document.activeElement?.tagName !== 'INPUT') {
        e.preventDefault();
        searchInputRef.current?.focus();
        return;
      }
      // Cmd/Ctrl+A: Select all visible items
      if ((e.metaKey || e.ctrlKey) && e.key === 'a' && document.activeElement?.tagName !== 'INPUT') {
        e.preventDefault();
        selection.selectAll();
        return;
      }
      // Cmd/Ctrl+Shift+I: Toggle incognito (15 min default)
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'i') {
        e.preventDefault();
        handleIncognitoToggle(incognitoStatus.active ? 0 : 15);
        return;
      }
      // Delete/Backspace: Delete selected (with confirmation)
      if ((e.key === 'Delete' || e.key === 'Backspace') && selection.selectedIds.size > 0 && document.activeElement?.tagName !== 'INPUT') {
        e.preventDefault();
        setShowDeleteConfirm(true);
        return;
      }
      // H: Hide selected (with confirmation)
      if (e.key === 'h' && selection.selectedIds.size > 0 && document.activeElement?.tagName !== 'INPUT') {
        e.preventDefault();
        setShowHideConfirm(true);
        return;
      }
      if (activeView === 'timeline' && !selectedImage && document.activeElement?.tagName !== 'INPUT') {
        // Timeline: left = older (higher index), right = newer (lower index)
        // Shift = 10 steps, Shift+Cmd = max(10, 2% of total)
        const fastJump = Math.max(10, Math.floor(totalSnapshots * 0.02));
        const step = (e.metaKey || e.ctrlKey) && e.shiftKey ? fastJump : e.shiftKey ? 10 : 1;
        if (e.key === 'ArrowLeft') {
          e.preventDefault();
          setCurrentIndex(i => Math.min(totalSnapshots - 1, i + step));
        } else if (e.key === 'ArrowRight') {
          e.preventDefault();
          setCurrentIndex(i => Math.max(0, i - step));
        } else if (e.key === 'Home') {
          e.preventDefault();
          setCurrentIndex(totalSnapshots - 1);
        } else if (e.key === 'End') {
          e.preventDefault();
          setCurrentIndex(0);
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [activeView, selectedImage, query, totalSnapshots, selection, incognitoStatus.active]);

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

  // Incognito handlers
  const handleIncognitoToggle = async (durationMinutes: number) => {
    setIsIncognitoLoading(true);
    try {
      if (durationMinutes === 0) {
        await stopIncognitoMode();
      } else {
        await setIncognitoMode(durationMinutes);
      }
      const status = await getIncognitoStatus();
      setIncognitoStatus(status);
    } catch (err) {
      console.error('Failed to toggle incognito:', err);
    } finally {
      setIsIncognitoLoading(false);
    }
  };

  // Bulk operation handlers
  const handleBulkDelete = async () => {
    setIsBulkOperationLoading(true);
    try {
      const ids = Array.from(selection.selectedIds);
      console.log('Deleting screenshots:', ids);
      const result = await bulkDeleteScreenshots(ids);
      console.log('Delete result:', result);

      // Remove deleted items from current view immediately
      const idSet = new Set(ids);
      if (activeView === 'search') {
        if (query.trim()) {
          setSearchResults(prev => prev.filter(s => !idSet.has(s.id)));
        } else {
          setGallerySnapshots(prev => prev.filter(s => !idSet.has(s.id)));
          setGalleryTotal(prev => Math.max(0, prev - ids.length));
        }
      } else if (activeView === 'timeline') {
        setSnapshots(prev => prev.filter(s => !idSet.has(s.id)));
      }

      selection.clearSelection();
      // Refresh background data (for totals, stats etc.)
      fetchData();
    } catch (err) {
      console.error('Failed to delete screenshots:', err);
      // Show error to user - handle both Error objects and plain objects
      let errorMessage = 'Unknown error';
      if (err instanceof Error) {
        errorMessage = err.message;
      } else if (typeof err === 'object' && err !== null) {
        // Handle cases where error is a plain object (e.g., { detail: "message" })
        const errObj = err as Record<string, unknown>;
        errorMessage = (errObj.detail as string) || (errObj.message as string) || JSON.stringify(err);
      } else if (typeof err === 'string') {
        errorMessage = err;
      }
      alert(`Failed to delete: ${errorMessage}. Make sure the server is running.`);
    } finally {
      setIsBulkOperationLoading(false);
      setShowDeleteConfirm(false);
    }
  };

  const handleBulkHide = async () => {
    setIsBulkOperationLoading(true);
    try {
      const ids = Array.from(selection.selectedIds);
      await bulkHideScreenshots(ids);

      // Immediately remove hidden items from view (if visibility filter excludes them)
      if (visibilityFilter === 'visible_only') {
        const idSet = new Set(ids);
        if (activeView === 'search') {
          if (query.trim()) {
            setSearchResults(prev => prev.filter(s => !idSet.has(s.id)));
          } else {
            setGallerySnapshots(prev => prev.filter(s => !idSet.has(s.id)));
            setGalleryTotal(prev => Math.max(0, prev - ids.length));
          }
        } else if (activeView === 'timeline') {
          setSnapshots(prev => prev.filter(s => !idSet.has(s.id)));
        }
      }

      selection.clearSelection();
      // Refresh background data (for totals, stats etc.)
      fetchData();
    } catch (err) {
      console.error('Failed to hide screenshots:', err);
    } finally {
      setIsBulkOperationLoading(false);
      setShowHideConfirm(false);
    }
  };

  const handleBulkUnhide = async () => {
    setIsBulkOperationLoading(true);
    try {
      const ids = Array.from(selection.selectedIds);
      await bulkUnhideScreenshots(ids);

      // Immediately remove unhidden items from view (if viewing hidden_only)
      if (visibilityFilter === 'hidden_only') {
        const idSet = new Set(ids);
        if (activeView === 'search') {
          if (query.trim()) {
            setSearchResults(prev => prev.filter(s => !idSet.has(s.id)));
          } else {
            setGallerySnapshots(prev => prev.filter(s => !idSet.has(s.id)));
            setGalleryTotal(prev => Math.max(0, prev - ids.length));
          }
        } else if (activeView === 'timeline') {
          setSnapshots(prev => prev.filter(s => !idSet.has(s.id)));
        }
      }

      selection.clearSelection();
      // Refresh background data (for totals, stats etc.)
      fetchData();
    } catch (err) {
      console.error('Failed to unhide screenshots:', err);
    } finally {
      setIsBulkOperationLoading(false);
    }
  };

  // Toggle visibility handler for 'all' view - inverts visibility of each selected item
  const handleToggleVisibility = async () => {
    setIsBulkOperationLoading(true);
    try {
      const ids = Array.from(selection.selectedIds);
      const selectedItems = currentViewItems.filter(s => ids.includes(s.id));

      // Separate into hidden and visible
      const hiddenIds = selectedItems.filter(s => s.is_hidden).map(s => s.id);
      const visibleIds = selectedItems.filter(s => !s.is_hidden).map(s => s.id);

      // Unhide the hidden ones, hide the visible ones
      const promises = [];
      if (hiddenIds.length > 0) promises.push(bulkUnhideScreenshots(hiddenIds));
      if (visibleIds.length > 0) promises.push(bulkHideScreenshots(visibleIds));
      await Promise.all(promises);

      selection.clearSelection();
      // Refresh data
      await fetchData();
      if (activeView === 'search') {
        if (query.trim()) {
          const data = await search(query, 50, safeMode, safeModeLevel, searchStartDate, searchEndDate, visibilityFilter);
          setSearchResults(data?.results || []);
        } else {
          const data = await getScreenshots(100, 0, undefined, undefined, visibilityFilter);
          if (data?.screenshots) {
            setGallerySnapshots(data.screenshots);
            setGalleryTotal(data.total);
          }
        }
      }
    } catch (err) {
      console.error('Failed to toggle visibility:', err);
    } finally {
      setIsBulkOperationLoading(false);
    }
  };

  const handleDatePreset = useCallback((preset: string, save = true) => {
    setDatePreset(preset);
    if (save) {
      localStorage.setItem(STORAGE_KEYS.DATE_PRESET, preset);
    }

    // Always clear end date for all presets - prevents stale endDate causing issues
    setSearchEndDate(undefined);

    const now = new Date();
    const format = (d: Date) => {
      const y = (d.getFullYear() % 100).toString().padStart(2, '0');
      const m = (d.getMonth() + 1).toString().padStart(2, '0');
      const day = d.getDate().toString().padStart(2, '0');
      const h = d.getHours().toString().padStart(2, '0');
      const min = d.getMinutes().toString().padStart(2, '0');
      const s = d.getSeconds().toString().padStart(2, '0');
      return `${y}${m}${day}${h}${min}${s}`;
    };

    if (preset === 'all') {
      setSearchStartDate(undefined);
    } else if (preset === '1h') {
      setSearchStartDate(format(new Date(now.getTime() - 60 * 60 * 1000)));
    } else if (preset === '24h') {
      setSearchStartDate(format(new Date(now.getTime() - 24 * 60 * 60 * 1000)));
    } else if (preset === '7d') {
      setSearchStartDate(format(new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)));
    } else if (preset === '30d') {
      setSearchStartDate(format(new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)));
    }
  }, []);

  const handleSearchFocus = () => {
    if (activeView !== 'search') {
      setActiveView('search');
    }
  };

  // Navigate to a specific screenshot in the grid view
  const navigateToGrid = useCallback(async (screenshot: Screenshot) => {
    // Set flag to skip the auto-fetch useEffect that would reset to offset 0
    skipGalleryFetchRef.current = true;

    // Switch to search view (grid mode)
    setActiveView('search');
    setQuery(''); // Clear search query to show gallery
    setSelectedImage(null);

    try {
      // Get the target screenshot's position in the sorted list
      const { offset: targetOffset } = await getScreenshotOffset(screenshot.id, visibilityFilter);

      // Calculate a starting offset that centers the target image
      // Load GALLERY_PAGE_SIZE images before and after the target
      const startOffset = Math.max(0, targetOffset - Math.floor(GALLERY_PAGE_SIZE / 2));

      // Load screenshots around the target position
      const data = await getScreenshots(GALLERY_PAGE_SIZE * 2, startOffset, undefined, undefined, visibilityFilter);

      if (data?.screenshots) {
        // Verify target is in loaded data
        const targetInData = data.screenshots.some(s => s.id === screenshot.id);
        if (!targetInData) {
          console.warn(`Target screenshot ${screenshot.id} not found in loaded data. Offset: ${targetOffset}, StartOffset: ${startOffset}, Loaded: ${data.screenshots.length}`);
        }

        setGallerySnapshots(data.screenshots);
        setGalleryTotal(data.total);
        setGalleryOffset(startOffset);
        // Allow loading more in both directions
        setHasMoreGallery(startOffset + data.screenshots.length < data.total);
        setHasMoreGalleryBefore(startOffset > 0);

        // Skip the first "load before" trigger since we're navigating to a specific position
        // The scroll-to-element will position the view correctly
        if (startOffset > 0) {
          skipLoadBeforeRef.current = true;
        }
      }

      // Highlight and scroll to target
      setHighlightedId(screenshot.id);

      // Use requestAnimationFrame to ensure React has rendered, then scroll
      requestAnimationFrame(() => {
        setTimeout(() => {
          const element = document.getElementById(`grid-item-${screenshot.id}`);
          if (element) {
            element.scrollIntoView({ behavior: 'smooth', block: 'center' });
          } else {
            console.warn(`Could not find element grid-item-${screenshot.id} to scroll to`);
          }

          // Clear the skip flag after scroll completes (give time for scroll animation)
          // This ensures scrolling up to load older images works after navigation
          setTimeout(() => {
            skipLoadBeforeRef.current = false;
            setHighlightedId(null);
          }, 500);
        }, 100);
      });

    } catch (err) {
      console.error('Failed to navigate to grid:', err);
      // Fallback to loading from start
      try {
        const data = await getScreenshots(GALLERY_PAGE_SIZE, 0, undefined, undefined, visibilityFilter);
        if (data?.screenshots) {
          setGallerySnapshots(data.screenshots);
          setGalleryTotal(data.total);
          setGalleryOffset(0);
          setHasMoreGallery(data.screenshots.length === GALLERY_PAGE_SIZE);
          setHasMoreGalleryBefore(false);
        }
      } catch (fallbackErr) {
        console.error('Fallback gallery load failed:', fallbackErr);
      }
    }
  }, [visibilityFilter]);

  // Navigate to a specific screenshot in the timeline
  const navigateToTimeline = useCallback(async (screenshot: Screenshot) => {
    // First, try to find the screenshot in the current snapshots by ID
    const existingIndex = snapshots.findIndex(s => s.id === screenshot.id);

    if (existingIndex !== -1) {
      // Found in current data - just navigate
      setCurrentIndex(existingIndex);
      setHighlightedId(screenshot.id);
      setActiveView('timeline');
      setSelectedImage(null);
      // Clear highlight after 2 seconds
      setTimeout(() => setHighlightedId(null), 2000);
      return;
    }

    // Not in current data - we need to load screenshots around that timestamp
    // The timeline is sorted newest first, so we need to find the offset
    try {
      // Fetch screenshots starting from around the target timestamp
      // We'll get a batch that includes the target
      const response = await getScreenshots(500, 0);
      if (response?.screenshots) {
        setSnapshots(response.screenshots);
        setTotalSnapshots(response.total);

        // Find the index again in the new data
        const newIndex = response.screenshots.findIndex((s: Screenshot) => s.id === screenshot.id);
        if (newIndex !== -1) {
          setCurrentIndex(newIndex);
          setHighlightedId(screenshot.id);
          setActiveView('timeline');
          setSelectedImage(null);
          setTimeout(() => setHighlightedId(null), 2000);
        } else {
          // Still not found - maybe it's older than our limit
          // Just switch to timeline at the start
          setCurrentIndex(0);
          setActiveView('timeline');
          setSelectedImage(null);
        }
      }
    } catch (err) {
      console.error('Failed to load screenshots for timeline navigation:', err);
      // Fallback - just switch to timeline
      setActiveView('timeline');
      setSelectedImage(null);
    }
  }, [snapshots]);

  const currentSnapshot = snapshots.length > 0 ? snapshots[currentIndex] : null;
  const maxCount = densityBuckets.length > 0
    ? Math.max(...densityBuckets.map(b => b.count), 1)
    : 1;
  // Timeline: left = older (high index), right = newer (low index)
  // So we invert: index 0 (newest) = 100% (right), index N-1 (oldest) = 0% (left)
  const thumbPosition = totalSnapshots > 1 ? ((totalSnapshots - 1 - currentIndex) / (totalSnapshots - 1)) * 100 : 100;

  const formatTimestamp = (ts: string | null): string => {
    if (!ts || ts.length !== 12) return '';
    const year = 2000 + parseInt(ts.slice(0, 2));
    const month = parseInt(ts.slice(2, 4));
    const day = parseInt(ts.slice(4, 6));
    const hour = parseInt(ts.slice(6, 8));
    const minute = parseInt(ts.slice(8, 10));
    const date = new Date(year, month - 1, day, hour, minute);
    return date.toLocaleString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    });
  };

  const isRecording = status?.recording.is_recording ?? false;
  const isSyncing = syncStatus?.is_syncing ?? false;
  const unsynced = status?.database.unsynced ?? 0;
  const modelLoaded = status?.model?.loaded ?? false;

  return (
    <div className="min-h-screen bg-black flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-black/95 backdrop-blur border-b border-[#1e1e1e]">
        <div className="flex items-center justify-between h-14 px-5">
          {/* Left - Logo */}
          <div className="flex items-center gap-8">
            <span className="text-lg font-semibold text-[#f5f5f5]">LiveRecall</span>

            {/* Nav Tabs */}
            <nav className="flex items-center gap-1">
              <button
                onClick={() => setActiveView('timeline')}
                className={`px-4 py-2 text-sm font-medium rounded-lg transition-all ${
                  activeView === 'timeline'
                    ? 'bg-[#86efac]/10 text-[#86efac]'
                    : 'text-[#8a8a8a] hover:text-[#f5f5f5] hover:bg-[#1c1c1c]'
                }`}
              >
                Timeline
              </button>
              <button
                onClick={() => setActiveView('search')}
                className={`px-4 py-2 text-sm font-medium rounded-lg transition-all ${
                  activeView === 'search'
                    ? 'bg-[#86efac]/10 text-[#86efac]'
                    : 'text-[#8a8a8a] hover:text-[#f5f5f5] hover:bg-[#1c1c1c]'
                }`}
              >
                Search
              </button>
            </nav>
          </div>

          {/* Right - Incognito, Recording & Settings */}
          <div className="flex items-center gap-3">
            {/* Incognito Toggle */}
            <IncognitoIndicator
              status={incognitoStatus}
              onSetDuration={handleIncognitoToggle}
              onStop={() => handleIncognitoToggle(0)}
              isLoading={isIncognitoLoading}
            />

            {/* Recording Toggle */}
            <button
              onClick={handleRecordingToggle}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                isRecording
                  ? 'bg-[#ef4444]/10 text-[#ef4444] hover:bg-[#ef4444]/20'
                  : 'bg-[#1c1c1c] text-[#8a8a8a] hover:text-[#f5f5f5] hover:bg-[#2a2a2a]'
              }`}
            >
              <span className={`w-2.5 h-2.5 rounded-full ${isRecording ? 'bg-[#ef4444] animate-pulse' : 'bg-[#555]'}`} />
              {isRecording ? 'Recording' : 'Record'}
            </button>

            {/* Settings */}
            <Link
              href="/settings"
              className="p-2.5 rounded-lg text-[#8a8a8a] hover:text-[#f5f5f5] hover:bg-[#1c1c1c] transition-all"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </Link>
          </div>
        </div>
      </header>

      {/* Search Bar - Always Visible */}
      <div className="bg-black py-3 px-4">
        <div className="max-w-xl mx-auto">
          <div className="relative">
            <svg
              className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#555]"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              ref={searchInputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onFocus={handleSearchFocus}
              placeholder="Search snapshots..."
              className="w-full h-9 pl-9 pr-3 bg-[#0f0f0f] border border-[#1e1e1e] rounded-lg text-sm text-[#f5f5f5] placeholder-[#555] focus:border-[#86efac]/50 focus:outline-none transition-colors"
            />
            {isSearching && (
              <div className="absolute right-3 top-1/2 -translate-y-1/2">
                <div className="w-4 h-4 border border-[#333] border-t-[#86efac] rounded-full animate-spin" />
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-h-0">
        {activeView === 'timeline' ? (
          <>
            {/* Current snapshot info */}
            {currentSnapshot && (
              <div className="px-4 py-2 flex items-center justify-between text-xs">
                <span className="text-[#8a8a8a]">{formatTimestamp(currentSnapshot.timestamp)}</span>
                <span className="text-[#555]">{currentIndex + 1} / {totalSnapshots}</span>
              </div>
            )}

            {/* Main Image Area */}
            <div className="flex-1 flex items-center justify-center px-4 pb-2 min-h-0">
              {currentSnapshot ? (
                <div
                  className={`group relative cursor-pointer transition-all duration-300 ${
                    highlightedId === currentSnapshot.id
                      ? 'ring-2 ring-[#86efac] ring-offset-2 ring-offset-black rounded'
                      : selection.isSelected(currentSnapshot.id)
                      ? 'ring-2 ring-[#86efac] ring-offset-2 ring-offset-black rounded'
                      : ''
                  }`}
                  onClick={(e) => {
                    // If shift/meta key pressed or already have selections, toggle selection
                    if (e.shiftKey || e.metaKey || e.ctrlKey || selection.selectedIds.size > 0) {
                      selection.toggleSelection(currentSnapshot.id, currentIndex, e.shiftKey);
                    } else {
                      setSelectedImage(currentSnapshot);
                    }
                  }}
                >
                  <img
                    ref={mainImageRef}
                    src={getImageUrl(currentSnapshot.image_path)}
                    alt=""
                    className={`max-w-full max-h-[calc(100vh-280px)] object-contain rounded border ${
                      highlightedId === currentSnapshot.id || selection.isSelected(currentSnapshot.id)
                        ? 'border-[#86efac]'
                        : 'border-[#1e1e1e]'
                    } transition-colors`}
                    onError={(e) => console.error('Image failed to load:', currentSnapshot.image_path)}
                  />
                  {/* Selection checkbox */}
                  <div
                    className={`absolute top-3 left-3 w-6 h-6 rounded border-2 flex items-center justify-center transition-all ${
                      selection.isSelected(currentSnapshot.id)
                        ? 'bg-[#86efac] border-[#86efac]'
                        : 'bg-black/50 border-white/40 opacity-0 group-hover:opacity-100'
                    }`}
                    onClick={(e) => {
                      e.stopPropagation();
                      selection.toggleSelection(currentSnapshot.id, currentIndex, e.shiftKey);
                    }}
                  >
                    {selection.isSelected(currentSnapshot.id) && (
                      <svg className="w-4 h-4 text-black" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                  </div>
                  {/* Hidden indicator */}
                  {currentSnapshot.is_hidden && (
                    <div className="absolute top-3 right-3 px-2 py-1 bg-[#7c3aed]/80 rounded text-xs text-white font-medium">
                      Hidden
                    </div>
                  )}
                  {highlightedId === currentSnapshot.id && (
                    <div className="absolute -top-8 left-1/2 -translate-x-1/2 px-2 py-1 bg-[#86efac] text-black text-xs font-medium rounded">
                      From Search
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center">
                  {isLoading ? (
                    <>
                      <div className="w-6 h-6 border-2 border-[#86efac]/30 border-t-[#86efac] rounded-full animate-spin mx-auto mb-2" />
                      <p className="text-[#555] text-sm">Loading snapshots...</p>
                    </>
                  ) : (
                    <>
                      <p className="text-[#555] text-sm">No snapshots yet</p>
                      <p className="text-[#444] text-xs mt-1">Start recording to capture your screen</p>
                    </>
                  )}
                </div>
              )}
            </div>

            {/* Timeline Scrubber */}
            <div className="px-4 py-3 bg-[#080808] border-t border-[#1e1e1e]">
              <div className="flex items-center gap-3 mb-2">
                <button
                  onClick={() => setCurrentIndex(i => Math.min(totalSnapshots - 1, i + 1))}
                  disabled={currentIndex >= totalSnapshots - 1}
                  className="p-1.5 rounded bg-[#0f0f0f] text-[#8a8a8a] hover:text-[#f5f5f5] disabled:opacity-30 transition-colors"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
                  </svg>
                </button>
                <button
                  onClick={() => setCurrentIndex(i => Math.max(0, i - 1))}
                  disabled={currentIndex <= 0}
                  className="p-1.5 rounded bg-[#0f0f0f] text-[#8a8a8a] hover:text-[#f5f5f5] disabled:opacity-30 transition-colors"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                  </svg>
                </button>
                <span className="text-[10px] text-[#555]">Arrow keys • Shift = 10 • ⇧⌘ = fast</span>
              </div>

              {/* Density Timeline */}
              <div
                className="relative h-10 bg-[#0f0f0f] rounded cursor-pointer overflow-hidden"
                onClick={(e) => {
                  const rect = e.currentTarget.getBoundingClientRect();
                  const x = e.clientX - rect.left;
                  const percentage = Math.max(0, Math.min(1, x / rect.width));
                  // Left = older (high index), Right = newer (low index)
                  // percentage 0 (left) → index N-1 (oldest)
                  // percentage 1 (right) → index 0 (newest)
                  setCurrentIndex(Math.round((1 - percentage) * (totalSnapshots - 1)));
                }}
              >
                <div className="absolute inset-0 flex items-end gap-px px-1 py-1">
                  {densityBuckets.length > 0 ? (
                    densityBuckets.map((bucket, i) => {
                      const height = bucket.count > 0
                        ? Math.max(20, (bucket.count / maxCount) * 100)
                        : 8;
                      return (
                        <div key={i} className="flex-1 flex items-end">
                          <div
                            className={`w-full rounded-sm transition-colors ${
                              bucket.count > 0
                                ? 'bg-[#86efac]/40 hover:bg-[#86efac]/60'
                                : 'bg-[#1e1e1e]'
                            }`}
                            style={{ height: `${height}%` }}
                          />
                        </div>
                      );
                    })
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-xs text-[#555]">
                      {totalSnapshots > 0 ? 'Loading...' : 'No data'}
                    </div>
                  )}
                </div>

                {totalSnapshots > 0 && (
                  <div
                    className="absolute top-0 bottom-0 w-0.5 bg-[#86efac]"
                    style={{ left: `${thumbPosition}%` }}
                  >
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-3 h-3 bg-[#86efac] rounded-full" />
                  </div>
                )}
              </div>
            </div>
          </>
        ) : (
          /* Search View */
          <div className="flex-1 flex flex-col min-h-0">
            {/* Filters */}
            <div className="px-4 py-2 border-b border-[#1e1e1e] flex items-center justify-between">
              <div className="flex items-center gap-1">
                {['1h', '24h', '7d', '30d', 'all'].map((preset) => (
                  <button
                    key={preset}
                    onClick={() => handleDatePreset(preset)}
                    className={`px-2.5 py-1 rounded text-xs transition-colors ${
                      datePreset === preset
                        ? 'bg-[#86efac]/20 text-[#86efac]'
                        : 'text-[#555] hover:text-[#8a8a8a]'
                    }`}
                  >
                    {preset === 'all' ? 'All' : preset}
                  </button>
                ))}
              </div>
              {/* Safe mode controls */}
              <div className="flex items-center gap-2">
                <button
                  onClick={handleSafeModeToggle}
                  className={`flex items-center gap-1.5 px-2 py-1 rounded text-xs transition-colors ${
                    safeMode ? 'text-[#86efac]' : 'text-[#555]'
                  }`}
                >
                  <span className={`w-1.5 h-1.5 rounded-full ${safeMode ? 'bg-[#86efac]' : 'bg-[#555]'}`} />
                  Safe
                </button>
                {safeMode && (
                  <select
                    value={safeModeLevel}
                    onChange={(e) => handleSafeModeLevelChange(e.target.value)}
                    className="bg-[#0f0f0f] text-[#8a8a8a] px-1.5 py-0.5 rounded border border-[#1e1e1e] text-xs focus:border-[#86efac]/50 focus:outline-none"
                  >
                    {SAFE_MODE_LEVELS.map((level) => (
                      <option key={level.value} value={level.value}>{level.label}</option>
                    ))}
                  </select>
                )}
              </div>
            </div>

            {/* Results info */}
            <div className="px-4 py-2 text-xs text-[#555]">
              {query.trim() ? (
                <>
                  {searchResults.length} results
                  {searchTime != null && <span className="ml-2 text-[#444]">{searchTime.toFixed(0)}ms</span>}
                </>
              ) : (
                <>{galleryTotal} snapshots (gallery)</>
              )}
            </div>

            {/* Results / Gallery */}
            <div ref={gridContainerRef} className="flex-1 overflow-y-auto p-4">
              {(() => {
                const itemsToShow = query.trim() ? searchResults : gallerySnapshots;
                if (itemsToShow.length > 0) {
                  return (
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-2">
                      {/* Top sentinel for bidirectional scroll - only show for gallery (not search results) */}
                      {!query.trim() && hasMoreGalleryBefore && (
                        <div
                          ref={loadMoreBeforeRef}
                          className="col-span-full h-12 flex items-center justify-center"
                        >
                          {isLoadingMoreBefore && (
                            <div className="flex items-center gap-2 text-[#555]">
                              <div className="w-4 h-4 border-2 border-[#333] border-t-[#86efac] rounded-full animate-spin" />
                              <span className="text-xs">Loading older...</span>
                            </div>
                          )}
                        </div>
                      )}
                      {itemsToShow.map((snapshot, index) => {
                        const isSelected = selection.isSelected(snapshot.id);
                        const isHighlighted = highlightedId === snapshot.id;
                        return (
                          <div
                            key={snapshot.id}
                            id={`grid-item-${snapshot.id}`}
                            onClick={(e) => {
                              if (e.shiftKey || e.metaKey || e.ctrlKey) {
                                selection.toggleSelection(snapshot.id, index, e.shiftKey);
                              } else if (selection.selectedIds.size > 0) {
                                selection.toggleSelection(snapshot.id, index, false);
                              } else {
                                setSelectedImage(snapshot);
                              }
                            }}
                            className={`group relative aspect-video bg-[#0f0f0f] rounded overflow-hidden cursor-pointer border-2 transition-all ${
                              isHighlighted
                                ? 'border-[#86efac] ring-2 ring-[#86efac] ring-offset-2 ring-offset-black'
                                : isSelected
                                ? 'border-[#86efac] ring-2 ring-[#86efac]/20'
                                : 'border-[#1e1e1e] hover:border-[#86efac]/50'
                            }`}
                          >
                            <img
                              src={getImageUrl(snapshot.image_path)}
                              alt=""
                              className="w-full h-full object-cover"
                              loading="lazy"
                            />
                            {/* Selection checkbox */}
                            <div
                              className={`absolute top-2 left-2 w-5 h-5 rounded border-2 flex items-center justify-center transition-all ${
                                isSelected
                                  ? 'bg-[#86efac] border-[#86efac]'
                                  : 'bg-black/50 border-white/40 opacity-0 group-hover:opacity-100'
                              }`}
                              onClick={(e) => {
                                e.stopPropagation();
                                selection.toggleSelection(snapshot.id, index, e.shiftKey);
                              }}
                            >
                              {isSelected && (
                                <svg className="w-3 h-3 text-black" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                                </svg>
                              )}
                            </div>
                            {/* Hidden indicator */}
                            {snapshot.is_hidden && (
                              <div className="absolute top-2 right-2 px-1.5 py-0.5 bg-[#7c3aed]/80 rounded text-[10px] text-white">
                                Hidden
                              </div>
                            )}
                            {/* Similarity score for search results */}
                            {query.trim() && snapshot.similarity !== undefined && (
                              <div className="absolute bottom-2 right-2 px-1.5 py-0.5 bg-black/70 rounded text-[10px] text-[#86efac]">
                                {(snapshot.similarity * 100).toFixed(0)}%
                              </div>
                            )}
                          </div>
                        );
                      })}
                      {/* Infinite scroll sentinel - only show for gallery (not search results) */}
                      {!query.trim() && (
                        <div
                          ref={loadMoreRef}
                          className="col-span-full h-16 flex items-center justify-center"
                        >
                          {isLoadingMore ? (
                            <div className="flex items-center gap-2 text-[#555]">
                              <div className="w-4 h-4 border-2 border-[#333] border-t-[#86efac] rounded-full animate-spin" />
                              <span className="text-xs">Loading more...</span>
                            </div>
                          ) : !hasMoreGallery && gallerySnapshots.length > 0 ? (
                            <span className="text-xs text-[#555]">All {galleryTotal} snapshots loaded</span>
                          ) : null}
                        </div>
                      )}
                    </div>
                  );
                } else if (query.trim()) {
                  return (
                    <div className="flex items-center justify-center h-full">
                      <p className="text-sm text-[#555]">No results found</p>
                    </div>
                  );
                } else {
                  return (
                    <div className="flex items-center justify-center h-full">
                      <p className="text-sm text-[#555]">No snapshots yet</p>
                    </div>
                  );
                }
              })()}
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-[#080808] border-t border-[#1e1e1e] py-2.5 px-5">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-6">
            {/* Sync Status */}
            {isSyncing ? (
              <div className="flex items-center gap-2 text-[#86efac]">
                <div className="w-3 h-3 border-2 border-[#86efac]/30 border-t-[#86efac] rounded-full animate-spin" />
                <span>Syncing...</span>
              </div>
            ) : unsynced > 0 ? (
              <button
                onClick={() => startSync()}
                className="flex items-center gap-2 text-[#fbbf24] hover:text-[#fcd34d] transition-colors"
              >
                <span className="w-2 h-2 rounded-full bg-[#fbbf24]" />
                <span>{unsynced} pending sync</span>
              </button>
            ) : (
              <div className="flex items-center gap-2 text-[#555]">
                <span className="w-2 h-2 rounded-full bg-[#86efac]" />
                <span>Synced</span>
              </div>
            )}

            {/* Model Status */}
            <div className={`flex items-center gap-2 ${modelLoaded ? 'text-[#86efac]' : 'text-[#555]'}`}>
              <span className={`w-2 h-2 rounded-full ${modelLoaded ? 'bg-[#86efac]' : 'bg-[#555]'}`} />
              <span>Model {modelLoaded ? 'loaded' : 'unloaded'}</span>
            </div>
          </div>

          <div className="flex items-center gap-4 text-[#555]">
            <span>{totalSnapshots} snapshots</span>
            <span>v0.1.1</span>
          </div>
        </div>
      </footer>

      {/* Lightbox */}
      {selectedImage && (
        <div
          className="fixed inset-0 z-50 bg-black/95 flex items-center justify-center"
          onClick={() => setSelectedImage(null)}
        >
          <button
            onClick={() => setSelectedImage(null)}
            className="absolute top-3 right-3 p-2 text-[#555] hover:text-[#f5f5f5] transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
          <img
            src={getImageUrl(selectedImage.image_path)}
            alt=""
            onClick={(e) => e.stopPropagation()}
            className="max-w-[90vw] max-h-[90vh] object-contain"
          />
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-3">
            <div className="px-3 py-1.5 bg-[#0f0f0f] rounded text-xs text-[#8a8a8a] border border-[#1e1e1e]">
              {formatTimestamp(selectedImage.timestamp)}
              {selectedImage.similarity !== undefined && (
                <span className="ml-2 text-[#86efac]">{(selectedImage.similarity * 100).toFixed(0)}%</span>
              )}
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                navigateToTimeline(selectedImage);
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-[#86efac]/10 hover:bg-[#86efac]/20 text-[#86efac] rounded text-xs border border-[#86efac]/30 transition-colors"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              View in Timeline
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                navigateToGrid(selectedImage);
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-[#a78bfa]/10 hover:bg-[#a78bfa]/20 text-[#a78bfa] rounded text-xs border border-[#a78bfa]/30 transition-colors"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
              </svg>
              View in Grid
            </button>
          </div>
        </div>
      )}

      {/* Selection Toolbar */}
      <SelectionToolbar
        selectedCount={selection.selectedIds.size}
        onDelete={() => setShowDeleteConfirm(true)}
        onHide={() => setShowHideConfirm(true)}
        onUnhide={handleBulkUnhide}
        onClear={selection.clearSelection}
        onSelectAll={selection.selectAll}
        showUnhide={visibilityFilter === 'hidden_only'}
        showToggle={visibilityFilter === 'all'}
        onToggleVisibility={handleToggleVisibility}
        isLoading={isBulkOperationLoading}
      />

      {/* Delete Confirmation Dialog */}
      <ConfirmationDialog
        isOpen={showDeleteConfirm}
        onClose={() => setShowDeleteConfirm(false)}
        onConfirm={handleBulkDelete}
        title="Delete Screenshots"
        message={`Are you sure you want to permanently delete ${selection.selectedIds.size} screenshot${selection.selectedIds.size === 1 ? '' : 's'}?`}
        confirmText="Delete"
        confirmVariant="danger"
        isLoading={isBulkOperationLoading}
      />

      {/* Hide Confirmation Dialog */}
      <ConfirmationDialog
        isOpen={showHideConfirm}
        onClose={() => setShowHideConfirm(false)}
        onConfirm={handleBulkHide}
        title="Hide Screenshots"
        message={`Hide ${selection.selectedIds.size} screenshot${selection.selectedIds.size === 1 ? '' : 's'}? They won't appear in normal views but can be restored later.`}
        confirmText="Hide"
        confirmVariant="warning"
        isLoading={isBulkOperationLoading}
      />
    </div>
  );
}
