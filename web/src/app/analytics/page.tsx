'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import {
  getAnalyticsOverview,
  getAnalyticsStorage,
  getAnalyticsActivity,
  getAnalyticsGaps,
  getAnalyticsQuality,
  getAnalyticsTrends,
  getAnalyticsActivityWeek,
} from '@/lib/api';
import type {
  AnalyticsOverview,
  AnalyticsStorage,
  AnalyticsActivity,
  AnalyticsGaps,
  AnalyticsQuality,
  AnalyticsTrends,
  AnalyticsActivityWeek,
} from '@/types';
import { useRouter } from 'next/navigation';

// Animated counter component
function AnimatedCounter({
  value,
  duration = 1000,
  formatter = (v: number) => v.toLocaleString(),
}: {
  value: number;
  duration?: number;
  formatter?: (v: number) => string;
}) {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    let startTime: number;
    let animationFrame: number;

    const animate = (currentTime: number) => {
      if (!startTime) startTime = currentTime;
      const progress = Math.min((currentTime - startTime) / duration, 1);

      // Ease out cubic
      const easeOut = 1 - Math.pow(1 - progress, 3);
      setDisplayValue(Math.floor(value * easeOut));

      if (progress < 1) {
        animationFrame = requestAnimationFrame(animate);
      }
    };

    animationFrame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animationFrame);
  }, [value, duration]);

  return <span>{formatter(displayValue)}</span>;
}

// Format bytes to human readable
function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

// Format duration
function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  return `${Math.floor(seconds / 86400)}d ${Math.floor((seconds % 86400) / 3600)}h`;
}

// Format timestamp
function formatTimestamp(ts: string): string {
  if (!ts || ts.length !== 12) return '';
  const year = 2000 + parseInt(ts.slice(0, 2));
  const month = parseInt(ts.slice(2, 4));
  const day = parseInt(ts.slice(4, 6));
  const hour = parseInt(ts.slice(6, 8));
  const minute = parseInt(ts.slice(8, 10));
  const date = new Date(year, month - 1, day, hour, minute);
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

// Info tooltip component
function InfoTooltip({ text }: { text: string }) {
  const [isVisible, setIsVisible] = useState(false);

  return (
    <div className="relative inline-block ml-2">
      <button
        className="w-4 h-4 rounded-full bg-[#1e1e1e] text-[#555] hover:text-[#8a8a8a] hover:bg-[#2a2a2a] text-[10px] flex items-center justify-center transition-colors"
        onMouseEnter={() => setIsVisible(true)}
        onMouseLeave={() => setIsVisible(false)}
        onClick={() => setIsVisible(!isVisible)}
      >
        i
      </button>
      <AnimatePresence>
        {isVisible && (
          <motion.div
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 5 }}
            className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-56 p-2 bg-[#1a1a1a] border border-[#2a2a2a] rounded-lg text-xs text-[#8a8a8a] shadow-xl"
          >
            {text}
            <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-1/2 w-2 h-2 bg-[#1a1a1a] border-r border-b border-[#2a2a2a] rotate-45" />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// Card wrapper with animation
function Card({
  children,
  className = '',
  delay = 0
}: {
  children: React.ReactNode;
  className?: string;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
      className={`bg-[#0f0f0f] border border-[#1e1e1e] rounded-xl p-5 hover:border-[#2a2a2a] transition-colors ${className}`}
    >
      {children}
    </motion.div>
  );
}

// Stat card component
function StatCard({
  label,
  value,
  formatter = (v: number) => v.toLocaleString(),
  trend,
  icon,
  delay = 0,
}: {
  label: string;
  value: number;
  formatter?: (v: number) => string;
  trend?: { value: number; isPositive: boolean };
  icon?: React.ReactNode;
  delay?: number;
}) {
  return (
    <Card delay={delay}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-[#8a8a8a] text-sm mb-1">{label}</p>
          <p className="text-2xl font-semibold text-[#f5f5f5]">
            <AnimatedCounter value={value} formatter={formatter} />
          </p>
          {trend && (
            <div className={`flex items-center gap-1 mt-1 text-xs ${trend.isPositive ? 'text-[#86efac]' : 'text-[#ef4444]'}`}>
              <svg
                className={`w-3 h-3 ${trend.isPositive ? '' : 'rotate-180'}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
              </svg>
              <span>{Math.abs(trend.value)}% from yesterday</span>
            </div>
          )}
        </div>
        {icon && (
          <div className="p-2 bg-[#86efac]/10 rounded-lg text-[#86efac]">
            {icon}
          </div>
        )}
      </div>
    </Card>
  );
}

// Week Activity Heatmap component with navigation
function WeekActivityHeatmap({
  weekOffset,
  onWeekChange,
  onCellClick,
}: {
  weekOffset: number;
  onWeekChange: (offset: number) => void;
  onCellClick: (date: string, hour: number, screenshotIds: number[]) => void;
}) {
  const [weekData, setWeekData] = useState<AnalyticsActivityWeek | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadWeekData = async () => {
      setIsLoading(true);
      try {
        const data = await getAnalyticsActivityWeek(weekOffset);
        setWeekData(data);
      } catch (err) {
        console.error('Failed to load week data:', err);
      } finally {
        setIsLoading(false);
      }
    };
    loadWeekData();
  }, [weekOffset]);

  // Create a lookup map for quick access: key = "date-hour" → cell data
  const dataMap = new Map<string, { count: number; screenshot_ids: number[] }>();
  let maxCount = 1;

  if (weekData) {
    weekData.heatmap_data.forEach(d => {
      const key = `${d.date}-${d.hour}`;
      dataMap.set(key, { count: d.count, screenshot_ids: d.screenshot_ids });
      if (d.count > maxCount) maxCount = d.count;
    });
  }

  const getIntensity = (count: number): string => {
    if (count === 0) return 'bg-[#1e1e1e]';
    const ratio = count / maxCount;
    if (ratio < 0.25) return 'bg-[#86efac]/20';
    if (ratio < 0.5) return 'bg-[#86efac]/40';
    if (ratio < 0.75) return 'bg-[#86efac]/60';
    return 'bg-[#86efac]/90';
  };

  // Parse "YYYY-MM-DD" as local date (not UTC) to avoid timezone shift
  const parseLocalDate = (dateStr: string): Date => {
    const [y, m, d] = dateStr.split('-').map(Number);
    return new Date(y, m - 1, d);
  };

  // Get array of dates for the week (Mon-Sun)
  const getWeekDates = (): { date: string; label: string; dayLabel: string }[] => {
    if (!weekData) return [];
    const dates: { date: string; label: string; dayLabel: string }[] = [];
    const dayLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

    const start = parseLocalDate(weekData.week_start);
    for (let i = 0; i < 7; i++) {
      const d = new Date(start);
      d.setDate(start.getDate() + i);
      const yyyy = d.getFullYear();
      const mm = String(d.getMonth() + 1).padStart(2, '0');
      const dd = String(d.getDate()).padStart(2, '0');
      dates.push({
        date: `${yyyy}-${mm}-${dd}`,
        label: d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        dayLabel: dayLabels[i],
      });
    }
    return dates;
  };

  const weekDates = getWeekDates();

  const formatDateRange = () => {
    if (!weekData) return '';
    const start = parseLocalDate(weekData.week_start);
    const end = parseLocalDate(weekData.week_end);
    return `${start.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${end.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`;
  };

  if (isLoading) {
    return (
      <div className="h-48 flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-[#86efac]/30 border-t-[#86efac] rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Week Navigation */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => onWeekChange(weekOffset - 1)}
          className="p-1.5 rounded-lg text-[#8a8a8a] hover:text-[#f5f5f5] hover:bg-[#1e1e1e] transition-colors"
          disabled={weekOffset <= -52}
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <div className="text-center">
          <p className="text-sm font-medium text-[#f5f5f5]">{formatDateRange()}</p>
          <p className="text-xs text-[#555]">
            {weekOffset === 0 ? 'Current Week' : weekOffset === -1 ? 'Last Week' : `${Math.abs(weekOffset)} weeks ago`}
          </p>
        </div>
        <button
          onClick={() => onWeekChange(weekOffset + 1)}
          className="p-1.5 rounded-lg text-[#8a8a8a] hover:text-[#f5f5f5] hover:bg-[#1e1e1e] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          disabled={weekOffset >= 0}
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </div>

      {/* Heatmap Grid */}
      <div className="overflow-x-auto">
        <div className="min-w-[600px]">
          {/* Hour labels */}
          <div className="flex gap-1 ml-24 mb-1">
            {Array.from({ length: 24 }, (_, i) => (
              <div key={i} className="w-4 text-[10px] text-[#555] text-center">
                {i % 3 === 0 ? i : ''}
              </div>
            ))}
          </div>
          {/* Grid */}
          {weekDates.map((day) => (
            <div key={day.date} className="flex items-center gap-1 mb-1">
              <div className="w-8 text-xs text-[#8a8a8a]">{day.dayLabel}</div>
              <div className="w-14 text-[10px] text-[#555]">{day.label}</div>
              {Array.from({ length: 24 }, (_, hour) => {
                const cellData = dataMap.get(`${day.date}-${hour}`);
                const count = cellData?.count || 0;
                const screenshotIds = cellData?.screenshot_ids || [];
                return (
                  <div
                    key={hour}
                    onClick={() => count > 0 && onCellClick(day.date, hour, screenshotIds)}
                    className={`w-4 h-4 rounded-sm ${getIntensity(count)} transition-colors ${count > 0 ? 'hover:ring-1 hover:ring-[#86efac] cursor-pointer' : ''}`}
                    title={`${day.label} ${hour}:00 - ${count} screenshots`}
                  />
                );
              })}
            </div>
          ))}
          {/* Legend */}
          <div className="flex items-center gap-2 mt-3 ml-24">
            <span className="text-[10px] text-[#555]">Less</span>
            <div className="w-3 h-3 rounded-sm bg-[#1e1e1e]" />
            <div className="w-3 h-3 rounded-sm bg-[#86efac]/20" />
            <div className="w-3 h-3 rounded-sm bg-[#86efac]/40" />
            <div className="w-3 h-3 rounded-sm bg-[#86efac]/60" />
            <div className="w-3 h-3 rounded-sm bg-[#86efac]/90" />
            <span className="text-[10px] text-[#555]">More</span>
          </div>
        </div>
      </div>

      {/* Week Stats */}
      {weekData && (
        <div className="pt-3 border-t border-[#1e1e1e] flex items-center justify-between text-sm">
          <span className="text-[#8a8a8a]">
            {weekData.total_screenshots} screenshots this week
          </span>
          {weekData.peak && (
            <span className="text-[#86efac]">
              Peak: {weekData.peak.day} at {weekData.peak.hour}:00 ({weekData.peak.count})
            </span>
          )}
        </div>
      )}
    </div>
  );
}

// Gap Timeline component
function GapTimeline({ gaps }: { gaps: AnalyticsGaps }) {
  if (gaps.gaps.length === 0) {
    return (
      <div className="text-center py-8 text-[#555]">
        <p>No significant gaps detected</p>
      </div>
    );
  }

  return (
    <div className="space-y-3 max-h-64 overflow-y-auto pr-2">
      {gaps.gaps.slice(0, 10).map((gap, idx) => (
        <div
          key={idx}
          className={`flex items-center gap-3 p-3 rounded-lg border ${
            gap.type === 'incognito'
              ? 'bg-[#7c3aed]/10 border-[#7c3aed]/30'
              : 'bg-[#fbbf24]/10 border-[#fbbf24]/30'
          }`}
        >
          <div className={`w-2 h-2 rounded-full ${gap.type === 'incognito' ? 'bg-[#7c3aed]' : 'bg-[#fbbf24]'}`} />
          <div className="flex-1">
            <div className="flex items-center gap-2 text-sm">
              <span className="text-[#f5f5f5]">{formatDuration(gap.duration_seconds)}</span>
            </div>
            <div className="text-xs text-[#555] mt-0.5">
              {formatTimestamp(gap.start_time)} - {formatTimestamp(gap.end_time)}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function AnalyticsPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [weekOffset, setWeekOffset] = useState(0);

  // Data states
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [storage, setStorage] = useState<AnalyticsStorage | null>(null);
  const [activity, setActivity] = useState<AnalyticsActivity | null>(null);
  const [gaps, setGaps] = useState<AnalyticsGaps | null>(null);
  const [quality, setQuality] = useState<AnalyticsQuality | null>(null);
  const [trends, setTrends] = useState<AnalyticsTrends | null>(null);

  // Handle clicking a heatmap cell - navigate to timeline with that hour's screenshots
  const handleHeatmapCellClick = useCallback((date: string, hour: number, _screenshotIds: number[]) => {
    // Navigate to timeline with date filter
    // The timeline page will show screenshots from this specific hour
    const startDate = new Date(`${date}T${hour.toString().padStart(2, '0')}:00:00`);
    const endDate = new Date(startDate);
    endDate.setHours(endDate.getHours() + 1);

    // Format as YYMMDDHHMMSS for the API
    const formatTimestamp = (d: Date): string => {
      const yy = String(d.getFullYear()).slice(-2);
      const mm = String(d.getMonth() + 1).padStart(2, '0');
      const dd = String(d.getDate()).padStart(2, '0');
      const hh = String(d.getHours()).padStart(2, '0');
      const min = String(d.getMinutes()).padStart(2, '0');
      const ss = String(d.getSeconds()).padStart(2, '0');
      return `${yy}${mm}${dd}${hh}${min}${ss}`;
    };

    const startStr = formatTimestamp(startDate);
    const endStr = formatTimestamp(endDate);

    router.push(`/?start=${startStr}&end=${endStr}`);
  }, [router]);

  // Load all analytics data
  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const [
        overviewData,
        storageData,
        activityData,
        gapsData,
        qualityData,
        trendsData,
      ] = await Promise.all([
        getAnalyticsOverview(),
        getAnalyticsStorage(30),
        getAnalyticsActivity(12),
        getAnalyticsGaps(5, 50),
        getAnalyticsQuality(),
        getAnalyticsTrends(30),
      ]);

      setOverview(overviewData);
      setStorage(storageData);
      setActivity(activityData);
      setGaps(gapsData);
      setQuality(qualityData);
      setTrends(trendsData);
    } catch (err) {
      console.error('Failed to load analytics:', err);
      setError('Failed to load analytics data');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Calculate trend for today vs yesterday
  const todayTrend = overview ? {
    value: overview.screenshots_yesterday > 0
      ? Math.round(((overview.screenshots_today - overview.screenshots_yesterday) / overview.screenshots_yesterday) * 100)
      : 0,
    isPositive: overview.screenshots_today >= overview.screenshots_yesterday,
  } : undefined;

  // Pie chart colors
  const COLORS = ['#86efac', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];

  return (
    <div className="min-h-screen bg-black">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-black/95 backdrop-blur border-b border-[#1e1e1e]">
        <div className="flex items-center justify-between h-14 px-5">
          {/* Left - Logo */}
          <div className="flex items-center gap-8">
            <Link href="/" className="text-lg font-semibold text-[#f5f5f5] hover:text-[#86efac] transition-colors">
              LiveRecall
            </Link>

            {/* Nav Tabs */}
            <nav className="flex items-center gap-1">
              <Link
                href="/"
                className="px-4 py-2 text-sm font-medium rounded-lg text-[#8a8a8a] hover:text-[#f5f5f5] hover:bg-[#1c1c1c] transition-all"
              >
                Timeline
              </Link>
              <Link
                href="/"
                className="px-4 py-2 text-sm font-medium rounded-lg text-[#8a8a8a] hover:text-[#f5f5f5] hover:bg-[#1c1c1c] transition-all"
              >
                Search
              </Link>
              <button
                className="px-4 py-2 text-sm font-medium rounded-lg bg-[#86efac]/10 text-[#86efac] transition-all"
              >
                Analytics
              </button>
            </nav>
          </div>

          {/* Right - Settings */}
          <div className="flex items-center gap-3">
            <button
              onClick={loadData}
              className="p-2.5 rounded-lg text-[#8a8a8a] hover:text-[#f5f5f5] hover:bg-[#1c1c1c] transition-all"
              title="Refresh"
            >
              <svg className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
              </svg>
            </button>
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

      {/* Main Content */}
      <main className="p-6 max-w-7xl mx-auto">
        <AnimatePresence mode="wait">
          {isLoading && !overview ? (
            <motion.div
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex items-center justify-center h-96"
            >
              <div className="text-center">
                <div className="w-8 h-8 border-2 border-[#86efac]/30 border-t-[#86efac] rounded-full animate-spin mx-auto mb-4" />
                <p className="text-[#8a8a8a]">Loading analytics...</p>
              </div>
            </motion.div>
          ) : error ? (
            <motion.div
              key="error"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex items-center justify-center h-96"
            >
              <div className="text-center">
                <p className="text-[#ef4444] mb-4">{error}</p>
                <button
                  onClick={loadData}
                  className="px-4 py-2 bg-[#86efac]/10 text-[#86efac] rounded-lg hover:bg-[#86efac]/20 transition-colors"
                >
                  Try Again
                </button>
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="content"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-6"
            >
              {/* Header Stats Row */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard
                  label="Total Screenshots"
                  value={overview?.total_screenshots || 0}
                  trend={todayTrend}
                  delay={0}
                  icon={
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
                    </svg>
                  }
                />
                <StatCard
                  label="Total Storage"
                  value={overview?.total_storage_bytes || 0}
                  formatter={formatBytes}
                  delay={0.1}
                  icon={
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125" />
                    </svg>
                  }
                />
                <StatCard
                  label="Screenshots Today"
                  value={overview?.screenshots_today || 0}
                  delay={0.2}
                  icon={
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" />
                    </svg>
                  }
                />
                <StatCard
                  label="Avg File Size"
                  value={overview?.avg_file_size || 0}
                  formatter={formatBytes}
                  delay={0.3}
                  icon={
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                    </svg>
                  }
                />
              </div>

              {/* Main Grid */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Storage Growth Chart */}
                <Card delay={0.4} className="lg:col-span-2">
                  <div className="flex items-center mb-4">
                    <h3 className="text-lg font-medium text-[#f5f5f5]">Storage Growth</h3>
                    <InfoTooltip text="Cumulative storage used over the last 30 days. Shows how your screenshot archive grows over time." />
                  </div>
                  {storage && storage.daily_data.length > 0 ? (
                    <ResponsiveContainer width="100%" height={250}>
                      <AreaChart data={storage.daily_data}>
                        <defs>
                          <linearGradient id="storageGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#86efac" stopOpacity={0.3}/>
                            <stop offset="95%" stopColor="#86efac" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e1e1e" />
                        <XAxis
                          dataKey="date"
                          stroke="#555"
                          fontSize={11}
                          tickFormatter={(value) => {
                            const d = new Date(value);
                            return d.getDate().toString();
                          }}
                        />
                        <YAxis
                          stroke="#555"
                          fontSize={11}
                          tickFormatter={(value) => formatBytes(value)}
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#0f0f0f',
                            border: '1px solid #2a2a2a',
                            borderRadius: '8px',
                            color: '#f5f5f5',
                          }}
                          formatter={(value) => [formatBytes(value as number), 'Storage']}
                          labelFormatter={(label) => new Date(label).toLocaleDateString()}
                        />
                        <Area
                          type="monotone"
                          dataKey="cumulative_bytes"
                          stroke="#86efac"
                          fill="url(#storageGradient)"
                          strokeWidth={2}
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-64 flex items-center justify-center text-[#555]">
                      No storage data available
                    </div>
                  )}
                </Card>

                {/* Activity Heatmap */}
                <Card delay={0.5}>
                  <div className="flex items-center mb-4">
                    <h3 className="text-lg font-medium text-[#f5f5f5]">Activity Heatmap</h3>
                    <InfoTooltip text="Shows screenshot activity for a specific week. Each cell represents an hour. Brighter colors = more screenshots. Click any cell to view those screenshots in the timeline." />
                  </div>
                  <WeekActivityHeatmap
                    weekOffset={weekOffset}
                    onWeekChange={setWeekOffset}
                    onCellClick={handleHeatmapCellClick}
                  />
                </Card>

                {/* Hourly Distribution */}
                <Card delay={0.6}>
                  <div className="flex items-center mb-4">
                    <h3 className="text-lg font-medium text-[#f5f5f5]">Hourly Distribution</h3>
                    <InfoTooltip text="Average screenshots per hour across all recorded days (last 12 weeks). Shows your typical daily activity patterns." />
                  </div>
                  {activity && activity.hourly_distribution.length > 0 ? (
                    <ResponsiveContainer width="100%" height={200}>
                      <BarChart data={activity.hourly_distribution}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e1e1e" />
                        <XAxis
                          dataKey="hour"
                          stroke="#555"
                          fontSize={11}
                          tickFormatter={(v) => `${v}h`}
                        />
                        <YAxis stroke="#555" fontSize={11} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#0f0f0f',
                            border: '1px solid #2a2a2a',
                            borderRadius: '8px',
                            color: '#f5f5f5',
                          }}
                          formatter={(value) => [value, 'Screenshots']}
                          labelFormatter={(label) => `${label}:00`}
                        />
                        <Bar dataKey="count" fill="#86efac" radius={[2, 2, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-48 flex items-center justify-center text-[#555]">
                      No hourly data available
                    </div>
                  )}
                </Card>

                {/* Recording Trends */}
                <Card delay={0.7}>
                  <div className="flex items-center mb-4">
                    <h3 className="text-lg font-medium text-[#f5f5f5]">Daily Recording Trend</h3>
                    <InfoTooltip text="Screenshot count per day (blue) with 7-day moving average (green dashed). Useful for spotting trends in your recording consistency." />
                  </div>
                  {trends && trends.daily_data.length > 0 ? (
                    <ResponsiveContainer width="100%" height={200}>
                      <AreaChart data={trends.daily_data}>
                        <defs>
                          <linearGradient id="trendGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e1e1e" />
                        <XAxis
                          dataKey="date"
                          stroke="#555"
                          fontSize={11}
                          tickFormatter={(value) => {
                            const d = new Date(value);
                            return d.getDate().toString();
                          }}
                        />
                        <YAxis stroke="#555" fontSize={11} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#0f0f0f',
                            border: '1px solid #2a2a2a',
                            borderRadius: '8px',
                            color: '#f5f5f5',
                          }}
                          formatter={(value, name) => [
                            value,
                            name === 'count' ? 'Screenshots' : '7-day Avg',
                          ]}
                          labelFormatter={(label) => new Date(label).toLocaleDateString()}
                        />
                        <Area
                          type="monotone"
                          dataKey="count"
                          stroke="#3b82f6"
                          fill="url(#trendGradient)"
                          strokeWidth={2}
                        />
                        <Area
                          type="monotone"
                          dataKey="moving_avg"
                          stroke="#86efac"
                          fill="none"
                          strokeWidth={2}
                          strokeDasharray="5 5"
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-48 flex items-center justify-center text-[#555]">
                      No trend data available
                    </div>
                  )}
                  {trends?.summary && (
                    <div className="mt-3 pt-3 border-t border-[#1e1e1e] flex items-center justify-between text-xs text-[#8a8a8a]">
                      <span>Avg: {trends.summary.avg_per_day}/day</span>
                      {trends.summary.best_day?.date && (
                        <span className="text-[#86efac]">
                          Best: {new Date(trends.summary.best_day.date).toLocaleDateString()} ({trends.summary.best_day.count})
                        </span>
                      )}
                    </div>
                  )}
                </Card>

                {/* Timeline Gaps */}
                <Card delay={0.8}>
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center">
                      <h3 className="text-lg font-medium text-[#f5f5f5]">Timeline Gaps</h3>
                      <InfoTooltip text="Periods of 5+ minutes without screenshots. Yellow = normal gaps (computer off, etc). Purple = intentional incognito mode periods." />
                    </div>
                    {gaps && gaps.gap_count > 0 && (
                      <span className="text-xs text-[#8a8a8a] bg-[#1e1e1e] px-2 py-1 rounded">
                        {gaps.gap_count} gaps
                      </span>
                    )}
                  </div>
                  {gaps ? (
                    <>
                      <GapTimeline gaps={gaps} />
                      {gaps.gap_count > 0 && (
                        <div className="mt-4 pt-4 border-t border-[#1e1e1e] grid grid-cols-3 gap-4 text-center">
                          <div>
                            <p className="text-xs text-[#555]">Total Gap Time</p>
                            <p className="text-sm text-[#f5f5f5] font-medium">
                              {formatDuration(gaps.total_gap_time_seconds)}
                            </p>
                          </div>
                          <div>
                            <p className="text-xs text-[#555]">Longest</p>
                            <p className="text-sm text-[#fbbf24] font-medium">
                              {formatDuration(gaps.longest_gap_seconds)}
                            </p>
                          </div>
                          <div>
                            <p className="text-xs text-[#555]">Average</p>
                            <p className="text-sm text-[#f5f5f5] font-medium">
                              {formatDuration(gaps.avg_gap_seconds)}
                            </p>
                          </div>
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="h-48 flex items-center justify-center text-[#555]">
                      No gap data available
                    </div>
                  )}
                </Card>

                {/* File Size Distribution */}
                <Card delay={0.9}>
                  <div className="flex items-center mb-4">
                    <h3 className="text-lg font-medium text-[#f5f5f5]">File Size Distribution</h3>
                    <InfoTooltip text="Breakdown of screenshot file sizes. Helps identify if your compression settings are working well or if you have unusually large files." />
                  </div>
                  {quality && quality.size_distribution.length > 0 ? (
                    <div className="flex items-center gap-6">
                      <div className="w-40 h-40">
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie
                              data={quality.size_distribution.filter(d => d.count > 0)}
                              cx="50%"
                              cy="50%"
                              innerRadius={35}
                              outerRadius={60}
                              paddingAngle={2}
                              dataKey="count"
                            >
                              {quality.size_distribution.filter(d => d.count > 0).map((_, index) => (
                                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                              ))}
                            </Pie>
                            <Tooltip
                              contentStyle={{
                                backgroundColor: '#0f0f0f',
                                border: '1px solid #2a2a2a',
                                borderRadius: '8px',
                                color: '#f5f5f5',
                              }}
                              formatter={(value, _name, props) => [
                                `${value} (${(props.payload as { percentage?: number })?.percentage || 0}%)`,
                                '',
                              ]}
                            />
                          </PieChart>
                        </ResponsiveContainer>
                      </div>
                      <div className="flex-1 space-y-2">
                        {quality.size_distribution.map((item, idx) => (
                          <div key={item.label} className="flex items-center justify-between text-xs">
                            <div className="flex items-center gap-2">
                              <div
                                className="w-2.5 h-2.5 rounded-sm"
                                style={{ backgroundColor: COLORS[idx % COLORS.length] }}
                              />
                              <span className="text-[#8a8a8a]">{item.label}</span>
                            </div>
                            <span className="text-[#f5f5f5]">{item.count}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="h-48 flex items-center justify-center text-[#555]">
                      No quality data available
                    </div>
                  )}
                </Card>

                {/* Compression Stats */}
                <Card delay={1.0}>
                  <div className="flex items-center mb-4">
                    <h3 className="text-lg font-medium text-[#f5f5f5]">Compression Status</h3>
                    <InfoTooltip text="Auto-compression progress. Screenshots older than your configured threshold get compressed to save storage space." />
                  </div>
                  {storage?.compression ? (
                    <div className="space-y-4">
                      {/* Progress bar */}
                      <div>
                        <div className="flex justify-between text-xs mb-2">
                          <span className="text-[#8a8a8a]">Compressed</span>
                          <span className="text-[#86efac]">
                            {storage.compression.compressed_count} / {storage.compression.compressed_count + storage.compression.uncompressed_count}
                          </span>
                        </div>
                        <div className="h-2 bg-[#1e1e1e] rounded-full overflow-hidden">
                          <div
                            className="h-full bg-[#86efac] rounded-full transition-all duration-500"
                            style={{
                              width: `${(storage.compression.compressed_count / (storage.compression.compressed_count + storage.compression.uncompressed_count || 1)) * 100}%`
                            }}
                          />
                        </div>
                      </div>
                      {/* Stats */}
                      <div className="grid grid-cols-2 gap-4">
                        <div className="p-3 bg-[#1e1e1e]/50 rounded-lg">
                          <p className="text-xs text-[#555]">Original Size</p>
                          <p className="text-lg text-[#f5f5f5] font-semibold">
                            {formatBytes(storage.compression.original_bytes)}
                          </p>
                        </div>
                        <div className="p-3 bg-[#86efac]/10 rounded-lg">
                          <p className="text-xs text-[#86efac]/70">Space Saved</p>
                          <p className="text-lg text-[#86efac] font-semibold">
                            {formatBytes(storage.compression.bytes_saved)}
                          </p>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="h-32 flex items-center justify-center text-[#555]">
                      No compression data available
                    </div>
                  )}
                </Card>

                {/* Processing Stats */}
                <Card delay={1.1}>
                  <div className="flex items-center mb-4">
                    <h3 className="text-lg font-medium text-[#f5f5f5]">Processing Status</h3>
                    <InfoTooltip text="OCR text extraction progress. Screenshots are processed in the background to extract text for semantic search." />
                  </div>
                  <div className="space-y-4">
                    {/* OCR Progress */}
                    <div>
                      <div className="flex justify-between text-xs mb-2">
                        <span className="text-[#8a8a8a]">OCR Processed</span>
                        <span className="text-[#a78bfa]">
                          {overview?.ocr_processed_count || 0} / {overview?.total_screenshots || 0}
                        </span>
                      </div>
                      <div className="h-2 bg-[#1e1e1e] rounded-full overflow-hidden">
                        <div
                          className="h-full bg-[#a78bfa] rounded-full transition-all duration-500"
                          style={{
                            width: `${((overview?.ocr_processed_count || 0) / (overview?.total_screenshots || 1)) * 100}%`
                          }}
                        />
                      </div>
                    </div>
                    {/* Quick stats */}
                    <div className="grid grid-cols-2 gap-3 text-center">
                      <div className="p-3 bg-[#1e1e1e]/50 rounded-lg">
                        <p className="text-2xl font-semibold text-[#f5f5f5]">
                          {overview?.screenshots_this_week || 0}
                        </p>
                        <p className="text-xs text-[#555]">This Week</p>
                      </div>
                      <div className="p-3 bg-[#1e1e1e]/50 rounded-lg">
                        <p className="text-2xl font-semibold text-[#f5f5f5]">
                          {overview?.compressed_count || 0}
                        </p>
                        <p className="text-xs text-[#555]">Compressed</p>
                      </div>
                    </div>
                  </div>
                </Card>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
