// API Response Types

export interface Screenshot {
  id: number;
  image_path: string;
  timestamp: string;
  has_embedding: number;
  is_compressed: number;
  original_size_bytes: number | null;
  compressed_at: string | null;
  created_at: string;
  similarity?: number;
}

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

export interface SystemStatus {
  healthy: boolean;
  recording: RecordingStatus;
  database: DatabaseStats;
  model: ModelStatus;
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

// Search with date filters
export interface SearchParams {
  query: string;
  limit?: number;
  safe_mode?: boolean;
  safe_mode_level?: string;
  start_date?: string;
  end_date?: string;
}
