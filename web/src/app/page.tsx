'use client';

import { useState, useEffect, useRef, useCallback, Suspense } from 'react';
import Link from 'next/link';
import { useSearchParams, useRouter } from 'next/navigation';
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
  getScreenshotOCR,
  type ScreenshotOCR,
} from '@/lib/api';
import type { Screenshot, SystemStatus, SyncStatus, DensityBucket, IncognitoStatus, VisibilityFilter, SearchMode } from '@/types';
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

function HomeContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [activeView, setActiveView] = useState<'timeline' | 'search'>('timeline');
  const [status, setStatus] = useState<SystemStatus | null>(null);

  // Timeline date filter from URL params (for heatmap navigation)
  const [timelineStartDate, setTimelineStartDate] = useState<string | undefined>();
  const [timelineEndDate, setTimelineEndDate] = useState<string | undefined>();
  const [showDateRangePicker, setShowDateRangePicker] = useState(false);
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
  const [showOCRModal, setShowOCRModal] = useState(false);
  const [ocrData, setOcrData] = useState<ScreenshotOCR | null>(null);
  const [isLoadingOCR, setIsLoadingOCR] = useState(false);
  const [datePreset, setDatePreset] = useState<string>('all');
  const [safeMode, setSafeMode] = useState(true);
  const [safeModeLevel, setSafeModeLevel] = useState<string>('mid');
  const [searchMode, setSearchMode] = useState<SearchMode>('auto');
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

  // Timeline sliding window state
  const WINDOW_SIZE = 500;
  const PREFETCH_THRESHOLD = 100;
  const [windowOffset, setWindowOffset] = useState(0);
  const [isLoadingWindow, setIsLoadingWindow] = useState(false);
  const loadingRef = useRef(false);

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

  // Clear selection when switching views to prevent stale selections
  useEffect(() => {
    selection.clearSelection();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeView]);

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

  // Read URL params for timeline date filter (from analytics heatmap clicks)
  useEffect(() => {
    const start = searchParams.get('start');
    const end = searchParams.get('end');
    if (start && end) {
      setTimelineStartDate(start);
      setTimelineEndDate(end);
      // Switch to search/gallery view to show filtered results
      setActiveView('search');
    }
  }, [searchParams]);

  // Clear timeline date filter
  const clearTimelineFilter = useCallback(() => {
    setTimelineStartDate(undefined);
    setTimelineEndDate(undefined);
    // Clear URL params
    router.push('/', { scroll: false });
  }, [router]);

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
        getScreenshots(WINDOW_SIZE, 0, undefined, undefined, visibilityFilter),
        getDensity(100, visibilityFilter),
      ]);
      if (snapshotsData?.screenshots) {
        setSnapshots(snapshotsData.screenshots);
        setTotalSnapshots(snapshotsData.total);
        setWindowOffset(0);
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

  // Load a window of screenshots centered on target offset
  const loadWindowAtOffset = useCallback(async (targetOffset: number, totalCount?: number) => {
    if (loadingRef.current) return;
    loadingRef.current = true;
    setIsLoadingWindow(true);

    try {
      const total = totalCount ?? totalSnapshots;
      const halfWindow = Math.floor(WINDOW_SIZE / 2);
      const maxOffset = Math.max(0, total - WINDOW_SIZE);
      const startOffset = Math.max(0, Math.min(targetOffset - halfWindow, maxOffset));

      const data = await getScreenshots(WINDOW_SIZE, startOffset, undefined, undefined, visibilityFilter);
      if (data?.screenshots) {
        setSnapshots(data.screenshots);
        setWindowOffset(startOffset);
        setTotalSnapshots(data.total);
      }
    } finally {
      loadingRef.current = false;
      setIsLoadingWindow(false);
    }
  }, [visibilityFilter, totalSnapshots]);

  // Ensure the window covers the target index, prefetching if needed
  const ensureWindowCoversIndex = useCallback(async (targetIndex: number) => {
    const localIndex = targetIndex - windowOffset;
    const windowEnd = windowOffset + snapshots.length;

    // Out of bounds - load new window centered on target
    if (localIndex < 0 || localIndex >= snapshots.length) {
      await loadWindowAtOffset(targetIndex);
      return;
    }

    // Prefetch near start of window
    if (localIndex < PREFETCH_THRESHOLD && windowOffset > 0) {
      loadWindowAtOffset(targetIndex); // Fire and forget
    }

    // Prefetch near end of window
    if (localIndex > snapshots.length - PREFETCH_THRESHOLD && windowEnd < totalSnapshots) {
      loadWindowAtOffset(targetIndex); // Fire and forget
    }
  }, [windowOffset, snapshots.length, totalSnapshots, loadWindowAtOffset]);

  // Navigate timeline by delta (positive = older, negative = newer)
  const navigateTimeline = useCallback(async (delta: number) => {
    const newIndex = Math.max(0, Math.min(totalSnapshots - 1, currentIndex + delta));
    setCurrentIndex(newIndex);
    ensureWindowCoversIndex(newIndex);
  }, [currentIndex, totalSnapshots, ensureWindowCoversIndex]);

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
          const data = await getScreenshots(GALLERY_PAGE_SIZE, 0, timelineStartDate, timelineEndDate, visibilityFilter);
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
  }, [activeView, query, visibilityFilter, timelineStartDate, timelineEndDate]);

  // Load more gallery images for infinite scroll
  // galleryOffset is the START of the loaded window, so next offset is galleryOffset + current count
  const loadMoreGallery = useCallback(async () => {
    if (isLoadingMore || !hasMoreGallery || query.trim()) return;

    setIsLoadingMore(true);
    try {
      // Calculate next offset based on start offset + current loaded count
      const nextOffset = galleryOffset + gallerySnapshots.length;
      const data = await getScreenshots(GALLERY_PAGE_SIZE, nextOffset, timelineStartDate, timelineEndDate, visibilityFilter);

      if (data?.screenshots?.length) {
        setGallerySnapshots(prev => [...prev, ...data.screenshots]);
        // Don't update galleryOffset - it still represents the START of our window
        const newTotal = galleryOffset + gallerySnapshots.length + data.screenshots.length;
        setHasMoreGallery(data.screenshots.length === GALLERY_PAGE_SIZE && newTotal < data.total);
      } else {
        setHasMoreGallery(false);
      }
    } catch (err) {
      console.error('Failed to load more gallery:', err);
    } finally {
      setIsLoadingMore(false);
    }
  }, [isLoadingMore, hasMoreGallery, galleryOffset, visibilityFilter, query, gallerySnapshots.length, timelineStartDate, timelineEndDate]);

  // Load more gallery images before current position (for bidirectional scroll)
  const loadMoreGalleryBefore = useCallback(async () => {
    // Skip if flag is set (navigation in progress, flag cleared after scroll completes)
    if (skipLoadBeforeRef.current) return;

    if (isLoadingMoreBefore || !hasMoreGalleryBefore || galleryOffset <= 0 || query.trim()) return;

    setIsLoadingMoreBefore(true);
    try {
      const loadCount = Math.min(GALLERY_PAGE_SIZE, galleryOffset);
      const newOffset = galleryOffset - loadCount;

      // Store the ID of the first currently visible item for scroll restoration
      // This is more reliable than tracking scrollHeight which can change if user scrolls during fetch
      const firstVisibleId = gallerySnapshots[0]?.id;

      const data = await getScreenshots(loadCount, newOffset, timelineStartDate, timelineEndDate, visibilityFilter);

      if (data?.screenshots?.length) {
        // Prepend to existing screenshots
        setGallerySnapshots(prev => [...data.screenshots, ...prev]);
        setGalleryOffset(newOffset);
        setHasMoreGalleryBefore(newOffset > 0);

        // Restore scroll position by scrolling to the previously first visible item
        if (firstVisibleId) {
          requestAnimationFrame(() => {
            const element = document.getElementById(`grid-item-${firstVisibleId}`);
            if (element) {
              element.scrollIntoView({ block: 'start', behavior: 'instant' });
            }
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
  }, [isLoadingMoreBefore, hasMoreGalleryBefore, galleryOffset, visibilityFilter, query, gallerySnapshots, timelineStartDate, timelineEndDate]);

  // Intersection observer for infinite scroll (load more at bottom)
  // Note: We check isLoadingMore and call loadMoreGallery inside the callback,
  // so we don't need them in dependencies. This prevents observer recreation on every load.
  useEffect(() => {
    if (activeView !== 'search' || query.trim()) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          loadMoreGallery();
        }
      },
      { threshold: 0.1, rootMargin: '100px' }
    );

    if (loadMoreRef.current) {
      observer.observe(loadMoreRef.current);
    }

    return () => observer.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeView, query, hasMoreGallery]);

  // Intersection observer for bidirectional scroll (load more at top)
  useEffect(() => {
    if (activeView !== 'search' || query.trim() || !hasMoreGalleryBefore) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          loadMoreGalleryBefore();
        }
      },
      { threshold: 0.1, rootMargin: '100px' }
    );

    if (loadMoreBeforeRef.current) {
      observer.observe(loadMoreBeforeRef.current);
    }

    return () => observer.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeView, query, hasMoreGalleryBefore]);

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
        const data = await search(query, 50, safeMode, safeModeLevel, searchStartDate, searchEndDate, visibilityFilter, searchMode);
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
  }, [query, searchStartDate, searchEndDate, safeMode, safeModeLevel, visibilityFilter, searchMode]);

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
          navigateTimeline(step);
        } else if (e.key === 'ArrowRight') {
          e.preventDefault();
          navigateTimeline(-step);
        } else if (e.key === 'Home') {
          e.preventDefault();
          // Jump to oldest - need to load window first
          const targetIndex = totalSnapshots - 1;
          const localIdx = targetIndex - windowOffset;
          if (localIdx < 0 || localIdx >= snapshots.length) {
            loadWindowAtOffset(targetIndex).then(() => setCurrentIndex(targetIndex));
          } else {
            setCurrentIndex(targetIndex);
          }
        } else if (e.key === 'End') {
          e.preventDefault();
          // Jump to newest - need to load window first
          const targetIndex = 0;
          const localIdx = targetIndex - windowOffset;
          if (localIdx < 0 || localIdx >= snapshots.length) {
            loadWindowAtOffset(targetIndex).then(() => setCurrentIndex(targetIndex));
          } else {
            setCurrentIndex(targetIndex);
          }
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [activeView, selectedImage, query, totalSnapshots, selection, incognitoStatus.active, navigateTimeline, windowOffset, snapshots.length, loadWindowAtOffset]);

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
        // Filter out deleted items
        const currentSnapshotsFiltered = snapshots.filter(s => !idSet.has(s.id));
        const newTotal = Math.max(0, totalSnapshots - ids.length);

        // Calculate what the local index will be after removal
        const newLocalIndex = currentIndex - windowOffset;

        // If we're running low on items in the window, or local index is now out of bounds
        if (currentSnapshotsFiltered.length < 50 || newLocalIndex >= currentSnapshotsFiltered.length) {
          // Reload window centered on current position
          const safeIndex = Math.min(currentIndex, newTotal - 1);
          loadWindowAtOffset(Math.max(0, safeIndex), newTotal);
          setCurrentIndex(Math.max(0, safeIndex));
        } else {
          // Just update the snapshots in place
          setSnapshots(currentSnapshotsFiltered);
        }

        // Update total count
        setTotalSnapshots(newTotal);
      }

      selection.clearSelection();
      // Refresh density data only (not the full window which would reset position)
      getDensity(100, visibilityFilter).then(data => {
        if (data?.buckets) setDensityBuckets(data.buckets);
      });
    } catch (err) {
      console.error('Failed to delete screenshots:', err);
      const message = err instanceof Error ? err.message : 'Unknown error';
      alert(`Failed to delete: ${message}`);
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
          // Filter out hidden items
          const currentSnapshotsFiltered = snapshots.filter(s => !idSet.has(s.id));
          const newTotal = Math.max(0, totalSnapshots - ids.length);

          // Calculate what the local index will be after removal
          const newLocalIndex = currentIndex - windowOffset;

          // If we're running low on items in the window, or local index is now out of bounds
          if (currentSnapshotsFiltered.length < 50 || newLocalIndex >= currentSnapshotsFiltered.length) {
            // Reload window centered on current position
            const safeIndex = Math.min(currentIndex, newTotal - 1);
            loadWindowAtOffset(Math.max(0, safeIndex), newTotal);
            setCurrentIndex(Math.max(0, safeIndex));
          } else {
            // Just update the snapshots in place
            setSnapshots(currentSnapshotsFiltered);
          }

          // Update total count
          setTotalSnapshots(newTotal);
        }
      }

      selection.clearSelection();
      // Refresh density data only (not the full window which would reset position)
      getDensity(100, visibilityFilter).then(data => {
        if (data?.buckets) setDensityBuckets(data.buckets);
      });
    } catch (err) {
      console.error('Failed to hide screenshots:', err);
      const message = err instanceof Error ? err.message : 'Unknown error';
      alert(`Failed to hide: ${message}`);
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
          // Filter out unhidden items
          const currentSnapshotsFiltered = snapshots.filter(s => !idSet.has(s.id));
          const newTotal = Math.max(0, totalSnapshots - ids.length);

          // Calculate what the local index will be after removal
          const newLocalIndex = currentIndex - windowOffset;

          // If we're running low on items in the window, or local index is now out of bounds
          if (currentSnapshotsFiltered.length < 50 || newLocalIndex >= currentSnapshotsFiltered.length) {
            // Reload window centered on current position
            const safeIndex = Math.min(currentIndex, newTotal - 1);
            loadWindowAtOffset(Math.max(0, safeIndex), newTotal);
            setCurrentIndex(Math.max(0, safeIndex));
          } else {
            // Just update the snapshots in place
            setSnapshots(currentSnapshotsFiltered);
          }

          // Update total count
          setTotalSnapshots(newTotal);
        }
      }

      selection.clearSelection();
      // Refresh density data only (not the full window which would reset position)
      getDensity(100, visibilityFilter).then(data => {
        if (data?.buckets) setDensityBuckets(data.buckets);
      });
    } catch (err) {
      console.error('Failed to unhide screenshots:', err);
      const message = err instanceof Error ? err.message : 'Unknown error';
      alert(`Failed to unhide: ${message}`);
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

      // Update is_hidden flag in place for timeline view (all filter shows both)
      if (activeView === 'timeline') {
        const hiddenSet = new Set(hiddenIds);
        const visibleSet = new Set(visibleIds);
        setSnapshots(prev => prev.map(s => {
          if (hiddenSet.has(s.id)) return { ...s, is_hidden: false };
          if (visibleSet.has(s.id)) return { ...s, is_hidden: true };
          return s;
        }));
        // Refresh density data only
        getDensity(100, visibilityFilter).then(data => {
          if (data?.buckets) setDensityBuckets(data.buckets);
        });
      } else if (activeView === 'search') {
        if (query.trim()) {
          const data = await search(query, 50, safeMode, safeModeLevel, searchStartDate, searchEndDate, visibilityFilter, searchMode);
          setSearchResults(data?.results || []);
        } else {
          const data = await getScreenshots(100, 0, timelineStartDate, timelineEndDate, visibilityFilter);
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
      const data = await getScreenshots(GALLERY_PAGE_SIZE * 2, startOffset, timelineStartDate, timelineEndDate, visibilityFilter);

      if (data?.screenshots) {
        // Verify target is in loaded data
        const targetInData = data.screenshots.some(s => s.id === screenshot.id);
        if (!targetInData) {
          console.warn(`Target screenshot ${screenshot.id} not found in loaded data. Offset: ${targetOffset}, StartOffset: ${startOffset}, Loaded: ${data.screenshots.length}`);
        }

        setGallerySnapshots(data.screenshots);
        setGalleryTotal(data.total);
        // galleryOffset represents START of loaded window
        setGalleryOffset(startOffset);
        // Allow loading more in both directions
        // End of window is startOffset + loaded count
        const endOffset = startOffset + data.screenshots.length;
        setHasMoreGallery(endOffset < data.total);
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
      // IMPORTANT: Clear the skip flag on error to prevent permanently broken scroll-up
      skipLoadBeforeRef.current = false;

      // Fallback to loading from start
      try {
        const data = await getScreenshots(GALLERY_PAGE_SIZE, 0, timelineStartDate, timelineEndDate, visibilityFilter);
        if (data?.screenshots) {
          setGallerySnapshots(data.screenshots);
          setGalleryTotal(data.total);
          setGalleryOffset(0);
          setHasMoreGallery(data.screenshots.length < data.total);
          setHasMoreGalleryBefore(false);
        }
      } catch (fallbackErr) {
        console.error('Fallback gallery load failed:', fallbackErr);
      }
    }
  }, [visibilityFilter, timelineStartDate, timelineEndDate]);

  // Navigate to a specific screenshot in the timeline
  const navigateToTimeline = useCallback(async (screenshot: Screenshot) => {
    try {
      // Get the target screenshot's offset (position in full sorted list)
      const { offset: targetOffset } = await getScreenshotOffset(screenshot.id, visibilityFilter);

      // Load window centered on this screenshot
      await loadWindowAtOffset(targetOffset);

      // Set the index and highlight
      setCurrentIndex(targetOffset);
      setHighlightedId(screenshot.id);
      setActiveView('timeline');
      setSelectedImage(null);
      setTimeout(() => setHighlightedId(null), 2000);
    } catch (err) {
      console.error('Failed to navigate to timeline:', err);
      // Fallback - just switch to timeline
      setActiveView('timeline');
      setSelectedImage(null);
    }
  }, [visibilityFilter, loadWindowAtOffset]);

  // View OCR text for a screenshot
  const viewOCRText = useCallback(async (screenshot: Screenshot) => {
    setIsLoadingOCR(true);
    setOcrData(null);
    setShowOCRModal(true);
    try {
      const data = await getScreenshotOCR(screenshot.id);
      setOcrData(data);
    } catch (err) {
      console.error('Failed to fetch OCR text:', err);
      setOcrData({ has_ocr: false, text: '', confidence: null, word_count: 0 });
    } finally {
      setIsLoadingOCR(false);
    }
  }, []);

  // Copy OCR text to clipboard
  const copyOCRText = useCallback(() => {
    if (ocrData?.text) {
      navigator.clipboard.writeText(ocrData.text);
    }
  }, [ocrData]);

  // Calculate local index within the loaded window
  const localIndex = currentIndex - windowOffset;
  const currentSnapshot = (snapshots.length > 0 && localIndex >= 0 && localIndex < snapshots.length)
    ? snapshots[localIndex]
    : null;
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
              <Link
                href="/analytics"
                className="px-4 py-2 text-sm font-medium rounded-lg text-[#8a8a8a] hover:text-[#f5f5f5] hover:bg-[#1c1c1c] transition-all"
              >
                Analytics
              </Link>
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
                  {isLoading || isLoadingWindow ? (
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
                  onClick={() => navigateTimeline(1)}
                  disabled={currentIndex >= totalSnapshots - 1}
                  className="p-1.5 rounded bg-[#0f0f0f] text-[#8a8a8a] hover:text-[#f5f5f5] disabled:opacity-30 transition-colors"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
                  </svg>
                </button>
                <button
                  onClick={() => navigateTimeline(-1)}
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
                onClick={async (e) => {
                  const rect = e.currentTarget.getBoundingClientRect();
                  const x = e.clientX - rect.left;
                  const percentage = Math.max(0, Math.min(1, x / rect.width));
                  // Left = older (high index), Right = newer (low index)
                  // percentage 0 (left) → index N-1 (oldest)
                  // percentage 1 (right) → index 0 (newest)
                  const targetIndex = Math.round((1 - percentage) * (totalSnapshots - 1));

                  // Check if target is outside current window
                  const localIdx = targetIndex - windowOffset;
                  if (localIdx < 0 || localIdx >= snapshots.length) {
                    await loadWindowAtOffset(targetIndex);
                  }
                  setCurrentIndex(targetIndex);
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
                    onClick={() => {
                      handleDatePreset(preset);
                      // Clear custom date filter when using presets
                      setTimelineStartDate(undefined);
                      setTimelineEndDate(undefined);
                    }}
                    className={`px-2.5 py-1 rounded text-xs transition-colors ${
                      datePreset === preset && !timelineStartDate
                        ? 'bg-[#86efac]/20 text-[#86efac]'
                        : 'text-[#555] hover:text-[#8a8a8a]'
                    }`}
                  >
                    {preset === 'all' ? 'All' : preset}
                  </button>
                ))}
                {/* Custom date range button/chip */}
                {timelineStartDate && timelineEndDate ? (
                  <button
                    onClick={() => setShowDateRangePicker(true)}
                    className="flex items-center gap-1.5 px-2.5 py-1 rounded text-xs bg-[#86efac]/20 text-[#86efac] hover:bg-[#86efac]/30 transition-colors"
                  >
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" />
                    </svg>
                    {(() => {
                      const parseTs = (ts: string) => {
                        if (ts.length !== 12) return null;
                        return new Date(2000 + parseInt(ts.slice(0, 2)), parseInt(ts.slice(2, 4)) - 1, parseInt(ts.slice(4, 6)), parseInt(ts.slice(6, 8)), parseInt(ts.slice(8, 10)));
                      };
                      const start = parseTs(timelineStartDate);
                      const end = parseTs(timelineEndDate);
                      if (!start || !end) return 'Custom';
                      const sameDay = start.toDateString() === end.toDateString();
                      if (sameDay) return `${start.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} ${start.getHours()}:${String(start.getMinutes()).padStart(2,'0')}-${end.getHours()}:${String(end.getMinutes()).padStart(2,'0')}`;
                      return `${start.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${end.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`;
                    })()}
                    <svg
                      className="w-3 h-3 text-[#86efac]/60 hover:text-[#ef4444]"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={2}
                      onClick={(e) => { e.stopPropagation(); clearTimelineFilter(); }}
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                ) : (
                  <button
                    onClick={() => setShowDateRangePicker(true)}
                    className="flex items-center gap-1 px-2.5 py-1 rounded text-xs text-[#555] hover:text-[#8a8a8a] transition-colors"
                  >
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" />
                    </svg>
                    Custom
                  </button>
                )}
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
              {/* Search mode selector */}
              <select
                value={searchMode}
                onChange={(e) => setSearchMode(e.target.value as SearchMode)}
                className="bg-[#0f0f0f] text-[#8a8a8a] px-2 py-1 rounded border border-[#1e1e1e] text-xs focus:border-[#86efac]/50 focus:outline-none"
                title="Search mode"
              >
                <option value="auto">Auto (Hybrid)</option>
                <option value="image">Image Only</option>
                <option value="text_fuzzy">Text (Fuzzy)</option>
                <option value="text_semantic">Text (Semantic)</option>
              </select>
            </div>

            {/* Results info */}
            <div className="px-4 py-2 text-xs text-[#555]">
              {query.trim() ? (
                <>
                  {searchResults.length} results
                  {searchTime != null && <span className="ml-2 text-[#444]">{searchTime.toFixed(0)}ms</span>}
                </>
              ) : (
                <>{galleryTotal} snapshots {timelineStartDate ? '(filtered)' : '(gallery)'}</>
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
            <button
              onClick={(e) => {
                e.stopPropagation();
                viewOCRText(selectedImage);
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-[#fbbf24]/10 hover:bg-[#fbbf24]/20 text-[#fbbf24] rounded text-xs border border-[#fbbf24]/30 transition-colors"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
              </svg>
              View Text
            </button>
          </div>
        </div>
      )}

      {/* OCR Text Modal */}
      {showOCRModal && (
        <div
          className="fixed inset-0 z-[60] bg-black/95 flex items-center justify-center p-4"
          onClick={() => setShowOCRModal(false)}
        >
          <div
            className="bg-[#0f0f0f] border border-[#2a2a2a] rounded-lg w-full max-w-2xl max-h-[80vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-[#2a2a2a]">
              <h3 className="text-sm font-medium text-[#f5f5f5]">Extracted Text</h3>
              <button
                onClick={() => setShowOCRModal(false)}
                className="p-1 text-[#555] hover:text-[#f5f5f5] transition-colors"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-auto p-4">
              {isLoadingOCR ? (
                <div className="flex items-center justify-center py-8">
                  <div className="w-5 h-5 border-2 border-[#86efac] border-t-transparent rounded-full animate-spin" />
                  <span className="ml-2 text-sm text-[#8a8a8a]">Loading...</span>
                </div>
              ) : ocrData?.has_ocr === false ? (
                <div className="text-center py-8 text-[#8a8a8a]">
                  <svg className="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <p className="text-sm">OCR not yet processed for this screenshot</p>
                </div>
              ) : ocrData?.text ? (
                <pre className="text-sm text-[#d4d4d4] whitespace-pre-wrap font-mono leading-relaxed">
                  {ocrData.text}
                </pre>
              ) : (
                <div className="text-center py-8 text-[#8a8a8a]">
                  <svg className="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m5.231 13.481L15 17.25m-4.5-15H5.625c-.621 0-1.125.504-1.125 1.125v16.5c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9zm3.75 11.625a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
                  </svg>
                  <p className="text-sm">No text found in this screenshot</p>
                </div>
              )}
            </div>

            {/* Footer */}
            {ocrData?.has_ocr && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-[#2a2a2a]">
                <div className="flex items-center gap-4 text-xs text-[#8a8a8a]">
                  <span>{ocrData.word_count} words</span>
                  {ocrData.confidence !== null && (
                    <span>{(ocrData.confidence * 100).toFixed(0)}% confidence</span>
                  )}
                </div>
                {ocrData.text && (
                  <button
                    onClick={copyOCRText}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-[#86efac]/10 hover:bg-[#86efac]/20 text-[#86efac] rounded text-xs border border-[#86efac]/30 transition-colors"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
                    </svg>
                    Copy to Clipboard
                  </button>
                )}
              </div>
            )}
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

      {/* Date Range Picker Modal */}
      {showDateRangePicker && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            onClick={() => setShowDateRangePicker(false)}
          />
          <div className="relative bg-[#0f0f0f] border border-[#2a2a2a] rounded-xl p-5 w-[420px] max-w-[90vw] shadow-2xl">
            <h3 className="text-lg font-medium text-[#f5f5f5] mb-4">Set Date Range</h3>

            <div className="space-y-4">
              {/* Start Date/Time */}
              <div>
                <label className="block text-xs text-[#8a8a8a] mb-2">Start</label>
                <div className="flex gap-2">
                  <input
                    type="date"
                    id="range-start-date"
                    defaultValue={(() => {
                      if (!timelineStartDate || timelineStartDate.length !== 12) {
                        const d = new Date();
                        d.setDate(d.getDate() - 1);
                        return d.toISOString().split('T')[0];
                      }
                      const year = 2000 + parseInt(timelineStartDate.slice(0, 2));
                      return `${year}-${timelineStartDate.slice(2, 4)}-${timelineStartDate.slice(4, 6)}`;
                    })()}
                    className="flex-1 bg-[#1a1a1a] text-[#f5f5f5] text-sm px-3 py-2 rounded-lg border border-[#333] focus:border-[#86efac]/50 focus:outline-none"
                  />
                  <select
                    id="range-start-hour"
                    defaultValue={timelineStartDate?.length === 12 ? timelineStartDate.slice(6, 8) : '00'}
                    className="w-16 bg-[#1a1a1a] text-[#f5f5f5] text-sm px-2 py-2 rounded-lg border border-[#333] focus:border-[#86efac]/50 focus:outline-none"
                  >
                    {Array.from({ length: 24 }, (_, i) => (
                      <option key={i} value={String(i).padStart(2, '0')}>{String(i).padStart(2, '0')}</option>
                    ))}
                  </select>
                  <span className="text-[#555] self-center">:</span>
                  <select
                    id="range-start-min"
                    defaultValue={timelineStartDate?.length === 12 ? timelineStartDate.slice(8, 10) : '00'}
                    className="w-16 bg-[#1a1a1a] text-[#f5f5f5] text-sm px-2 py-2 rounded-lg border border-[#333] focus:border-[#86efac]/50 focus:outline-none"
                  >
                    {Array.from({ length: 60 }, (_, i) => (
                      <option key={i} value={String(i).padStart(2, '0')}>{String(i).padStart(2, '0')}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* End Date/Time */}
              <div>
                <label className="block text-xs text-[#8a8a8a] mb-2">End</label>
                <div className="flex gap-2">
                  <input
                    type="date"
                    id="range-end-date"
                    defaultValue={(() => {
                      if (!timelineEndDate || timelineEndDate.length !== 12) {
                        return new Date().toISOString().split('T')[0];
                      }
                      const year = 2000 + parseInt(timelineEndDate.slice(0, 2));
                      return `${year}-${timelineEndDate.slice(2, 4)}-${timelineEndDate.slice(4, 6)}`;
                    })()}
                    className="flex-1 bg-[#1a1a1a] text-[#f5f5f5] text-sm px-3 py-2 rounded-lg border border-[#333] focus:border-[#86efac]/50 focus:outline-none"
                  />
                  <select
                    id="range-end-hour"
                    defaultValue={timelineEndDate?.length === 12 ? timelineEndDate.slice(6, 8) : '23'}
                    className="w-16 bg-[#1a1a1a] text-[#f5f5f5] text-sm px-2 py-2 rounded-lg border border-[#333] focus:border-[#86efac]/50 focus:outline-none"
                  >
                    {Array.from({ length: 24 }, (_, i) => (
                      <option key={i} value={String(i).padStart(2, '0')}>{String(i).padStart(2, '0')}</option>
                    ))}
                  </select>
                  <span className="text-[#555] self-center">:</span>
                  <select
                    id="range-end-min"
                    defaultValue={timelineEndDate?.length === 12 ? timelineEndDate.slice(8, 10) : '59'}
                    className="w-16 bg-[#1a1a1a] text-[#f5f5f5] text-sm px-2 py-2 rounded-lg border border-[#333] focus:border-[#86efac]/50 focus:outline-none"
                  >
                    {Array.from({ length: 60 }, (_, i) => (
                      <option key={i} value={String(i).padStart(2, '0')}>{String(i).padStart(2, '0')}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Validation error */}
              <div id="range-error" className="text-xs text-[#ef4444] hidden">
                Start date/time must be before end date/time
              </div>
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => setShowDateRangePicker(false)}
                className="px-4 py-2 text-sm text-[#8a8a8a] hover:text-[#f5f5f5] rounded-lg hover:bg-[#1a1a1a] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  const startDate = (document.getElementById('range-start-date') as HTMLInputElement)?.value;
                  const startHour = (document.getElementById('range-start-hour') as HTMLSelectElement)?.value || '00';
                  const startMin = (document.getElementById('range-start-min') as HTMLSelectElement)?.value || '00';
                  const endDate = (document.getElementById('range-end-date') as HTMLInputElement)?.value;
                  const endHour = (document.getElementById('range-end-hour') as HTMLSelectElement)?.value || '23';
                  const endMin = (document.getElementById('range-end-min') as HTMLSelectElement)?.value || '59';
                  const errorEl = document.getElementById('range-error');

                  if (startDate && endDate) {
                    // Validate: start must be before end
                    const startDt = new Date(`${startDate}T${startHour}:${startMin}:00`);
                    const endDt = new Date(`${endDate}T${endHour}:${endMin}:00`);

                    if (startDt >= endDt) {
                      if (errorEl) errorEl.classList.remove('hidden');
                      return;
                    }
                    if (errorEl) errorEl.classList.add('hidden');

                    const formatTs = (date: string, hour: string, min: string) => {
                      const [year, month, day] = date.split('-');
                      return `${year.slice(-2)}${month}${day}${hour}${min}00`;
                    };
                    setTimelineStartDate(formatTs(startDate, startHour, startMin));
                    setTimelineEndDate(formatTs(endDate, endHour, endMin));
                    setShowDateRangePicker(false);
                  }
                }}
                className="px-4 py-2 text-sm bg-[#86efac] text-black font-medium rounded-lg hover:bg-[#6ee7a0] transition-colors"
              >
                Apply
              </button>
            </div>
          </div>
        </div>
      )}

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

// Wrapper component with Suspense for useSearchParams
export default function Home() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-[#86efac]/30 border-t-[#86efac] rounded-full animate-spin" />
      </div>
    }>
      <HomeContent />
    </Suspense>
  );
}
