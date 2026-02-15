// API Response Types

export interface Screenshot {
  id: number;
  image_path: string;
  timestamp: string;
  has_embedding: number;
  is_hidden: boolean;
  is_compressed: number;
  original_size_bytes: number | null;
  compressed_at: string | null;
  created_at: string;
  similarity?: number;
}

// Visibility filter for screenshots
export type VisibilityFilter = 'visible_only' | 'hidden_only' | 'all';

export interface SearchResult {
  query: string;
  total_results: number;
  results: Screenshot[];
  search_time_ms: number;
}

export interface DatabaseStats {
  total_screenshots: number;
  synced: number;
  unsynced: number;
  compressed: number;
}

export interface ModelStatus {
  loaded: boolean;
  device: string | null;
  idle_seconds: number;
  auto_unload_seconds: number;
}

export interface RecordingStatus {
  is_recording: boolean;
  mode: string;
  interval: number;
  threshold: number;
}

// Incognito mode status
export interface IncognitoStatus {
  active: boolean;
  remaining_seconds: number;
  until_timestamp: number | null;
}

export interface SystemStatus {
  healthy: boolean;
  recording: RecordingStatus;
  database: DatabaseStats;
  model: ModelStatus;
  incognito: IncognitoStatus;
  data_dir: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  timestamp: string;
}

export interface CaptureConfig {
  mode: string;
  interval: number;
  threshold: number;
  save_threshold: number;
  quality: number;
  max_time_without_save: number;
}

export interface CompressionConfig {
  enabled: boolean;
  after_days: number;
  quality: number;
}

export interface AppConfig {
  capture: CaptureConfig;
  compression: CompressionConfig;
  encryption_enabled: boolean;
  safe_mode_enabled: boolean;
  safe_mode_level: string;
  similarity_metric: 'cosine' | 'distance';
  model_auto_unload_seconds: number;
}

export interface CompressionStatus {
  is_compressing: boolean;
  total: number;
  processed: number;
  errors: number;
  bytes_saved: number;
  progress_percent: number;
}

export interface CompressionStats {
  compressed_count: number;
  uncompressed_count: number;
  compressible_count: number;
  original_size_bytes: number;
}

export interface ForceRecompressPreview {
  total_count: number;
  already_compressed_count: number;
  not_compressed_count: number;
  warning: string;
}

export interface SyncStatus {
  is_syncing: boolean;
  total: number;
  processed: number;
  errors: number;
  progress_percent: number;
}

export interface ApiResponse<T> {
  success: boolean;
  message?: string;
  data?: T;
}

// Timeline/Density Types
export interface DateRange {
  min_date: string | null;
  max_date: string | null;
}

export interface DensityBucket {
  start: string;
  end: string;
  count: number;
}

export interface DensityResponse {
  buckets: DensityBucket[];
  total: number;
  min_date: string | null;
  max_date: string | null;
}

// Search mode options
export type SearchMode = 'auto' | 'image' | 'text_fuzzy' | 'text_semantic';

// Search with date filters
export interface SearchParams {
  query: string;
  limit?: number;
  safe_mode?: boolean;
  safe_mode_level?: string;
  start_date?: string;
  end_date?: string;
  visibility?: VisibilityFilter;
  search_mode?: SearchMode;
}

// Bulk operations
export interface BulkOperationResponse {
  success: boolean;
  affected_count: number;
  message: string;
}

// Analytics Types
export interface AnalyticsOverview {
  total_screenshots: number;
  total_storage_bytes: number;
  compressed_count: number;
  avg_file_size: number;
  screenshots_today: number;
  screenshots_yesterday: number;
  screenshots_this_week: number;
  ocr_processed_count: number;
}

export interface DailyStorageData {
  date: string;
  screenshots: number;
  bytes_added: number;
  cumulative_bytes: number;
}

export interface LargestFile {
  id: number;
  path: string;
  timestamp: string;
  size_bytes: number;
}

export interface StorageByMonth {
  month: string;
  count: number;
}

export interface AnalyticsStorage {
  daily_data: DailyStorageData[];
  compression: {
    compressed_count: number;
    uncompressed_count: number;
    original_bytes: number;
    current_bytes: number;
    bytes_saved: number;
  };
  largest_files: LargestFile[];
  storage_by_month: StorageByMonth[];
}

export interface HeatmapData {
  day_of_week: number;
  hour: number;
  count: number;
}

export interface HourlyData {
  hour: number;
  count: number;
}

export interface DailyData {
  day: number;
  count: number;
}

export interface WeeklyTrend {
  week: string;
  count: number;
}

export interface AnalyticsActivity {
  heatmap_data: HeatmapData[];
  hourly_distribution: HourlyData[];
  daily_distribution: DailyData[];
  weekly_trend: WeeklyTrend[];
  peak_hour: number;
  peak_day: string;
  total_in_period: number;
}

export interface Gap {
  start_time: string;
  end_time: string;
  duration_seconds: number;
  type: 'gap' | 'incognito';
}

export interface AnalyticsGaps {
  gaps: Gap[];
  total_gap_time_seconds: number;
  longest_gap_seconds: number;
  avg_gap_seconds: number;
  gap_count: number;
}

export interface SizeDistribution {
  label: string;
  count: number;
  percentage: number;
}

export interface AnalyticsQuality {
  avg_file_size: number;
  min_file_size: number;
  max_file_size: number;
  median_file_size: number;
  size_distribution: SizeDistribution[];
  total_files: number;
  compression_stats: {
    compressed_count: number;
    uncompressed_count: number;
    original_bytes_before_compression: number;
  };
}

export interface TrendDailyData {
  date: string;
  count: number;
  moving_avg: number;
}

export interface AnalyticsTrends {
  daily_data: TrendDailyData[];
  summary: {
    total_screenshots: number;
    synced_count: number;
    ocr_processed_count: number;
    avg_per_day: number;
    days_with_recordings: number;
    best_day: { date: string | null; count: number };
    worst_day: { date: string | null; count: number } | null;
  };
}

// Week-specific activity data
export interface WeekHeatmapCell {
  date: string;
  day_of_week: number;
  day_label: string;
  hour: number;
  count: number;
  screenshot_ids: number[];
}

export interface AnalyticsActivityWeek {
  week_start: string;
  week_end: string;
  week_offset: number;
  heatmap_data: WeekHeatmapCell[];
  total_screenshots: number;
  peak: {
    day: string;
    hour: number;
    count: number;
  } | null;
}
