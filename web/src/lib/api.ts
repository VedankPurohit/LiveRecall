import type {
  SystemStatus,
  HealthResponse,
  AppConfig,
  SearchResult,
  CompressionStatus,
  CompressionStats,
  SyncStatus,
  ApiResponse,
  DateRange,
  DensityResponse,
  SearchParams,
  Screenshot,
  VisibilityFilter,
  IncognitoStatus,
  BulkOperationResponse,
} from '@/types';

const API_BASE = '/api/v1';

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

// Health & Status
export async function getHealth(): Promise<HealthResponse> {
  return fetchApi('/health');
}

export async function getStatus(): Promise<SystemStatus> {
  return fetchApi('/status');
}

// Config
export async function getConfig(): Promise<AppConfig> {
  return fetchApi('/config');
}

export async function updateConfig(updates: Partial<{
  capture_mode: string;
  capture_interval: number;
  capture_threshold: number;
  capture_save_threshold: number;
  capture_quality: number;
  compression_enabled: boolean;
  compression_after_days: number;
  compression_quality: number;
  safe_mode_enabled: boolean;
  safe_mode_level: string;
  similarity_metric: 'cosine' | 'distance';
  model_auto_unload_seconds: number;
}>): Promise<ApiResponse<void>> {
  return fetchApi('/config', {
    method: 'PUT',
    body: JSON.stringify(updates),
  });
}

// Search
export async function search(
  query: string,
  limit: number = 20,
  safeMode: boolean = true,
  safeModeLevel?: string,
  startDate?: string,
  endDate?: string,
  visibility: VisibilityFilter = 'visible_only'
): Promise<SearchResult> {
  return fetchApi('/search', {
    method: 'POST',
    body: JSON.stringify({
      query,
      limit,
      safe_mode: safeMode,
      safe_mode_level: safeModeLevel ?? 'mid',
      start_date: startDate,
      end_date: endDate,
      visibility,
    }),
  });
}

export async function searchWithParams(params: SearchParams): Promise<SearchResult> {
  return fetchApi('/search', {
    method: 'POST',
    body: JSON.stringify({
      query: params.query,
      limit: params.limit ?? 50,
      safe_mode: params.safe_mode ?? true,
      safe_mode_level: params.safe_mode_level ?? 'mid',
      start_date: params.start_date,
      end_date: params.end_date,
      visibility: params.visibility ?? 'visible_only',
    }),
  });
}

// Recording
export async function startRecording(): Promise<ApiResponse<void>> {
  return fetchApi('/recording/start', { method: 'POST' });
}

export async function stopRecording(): Promise<ApiResponse<void>> {
  return fetchApi('/recording/stop', { method: 'POST' });
}

export async function getRecordingStatus(): Promise<{
  is_recording: boolean;
  mode: string;
  interval: number;
  threshold: number;
}> {
  return fetchApi('/recording/status');
}

// Sync
export async function startSync(): Promise<ApiResponse<void>> {
  return fetchApi('/sync/start', { method: 'POST' });
}

export async function stopSync(): Promise<ApiResponse<void>> {
  return fetchApi('/sync/stop', { method: 'POST' });
}

export async function getSyncStatus(): Promise<SyncStatus> {
  return fetchApi('/sync/status');
}

// Compression
export async function startCompression(): Promise<ApiResponse<{ compressible_count: number }>> {
  return fetchApi('/compression/start', { method: 'POST' });
}

export async function stopCompression(): Promise<ApiResponse<void>> {
  return fetchApi('/compression/stop', { method: 'POST' });
}

export async function getCompressionStatus(): Promise<CompressionStatus> {
  return fetchApi('/compression/status');
}

export async function getCompressionStats(): Promise<CompressionStats> {
  return fetchApi('/compression/stats');
}

// Screenshots
export async function getScreenshots(
  limit: number = 50,
  offset: number = 0,
  startDate?: string,
  endDate?: string,
  visibility: VisibilityFilter = 'visible_only'
): Promise<{ total: number; screenshots: Screenshot[] }> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
    visibility,
  });
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);
  return fetchApi(`/screenshots?${params}`);
}

export async function getScreenshotById(id: number): Promise<Screenshot> {
  return fetchApi(`/screenshots/${id}`);
}

export async function getScreenshotOffset(
  screenshotId: number,
  visibility: VisibilityFilter = 'visible_only'
): Promise<{ offset: number }> {
  const params = new URLSearchParams({ visibility });
  return fetchApi(`/screenshots/${screenshotId}/offset?${params}`);
}

// Timeline
export async function getDateRange(visibility: VisibilityFilter = 'visible_only'): Promise<DateRange> {
  return fetchApi(`/screenshots/date-range?visibility=${visibility}`);
}

export async function getDensity(buckets: number = 100, visibility: VisibilityFilter = 'visible_only'): Promise<DensityResponse> {
  return fetchApi(`/screenshots/density?buckets=${buckets}&visibility=${visibility}`);
}

export async function deleteScreenshot(id: number): Promise<ApiResponse<void>> {
  return fetchApi(`/screenshots/${id}`, { method: 'DELETE' });
}

// Image URL helper
export function getImageUrl(imagePath: string): string {
  // The API serves images via /api/v1/screenshots/image endpoint
  return `${API_BASE}/screenshots/image?path=${encodeURIComponent(imagePath)}`;
}

// Setup
export async function getSetupStatus(): Promise<{
  current_version: string;
  last_seen_version: string;
  needs_setup: boolean;
}> {
  return fetchApi('/setup/status');
}

export async function resetPermissions(): Promise<{ success: boolean; message: string }> {
  return fetchApi('/setup/reset-permissions', { method: 'POST' });
}

export async function completeSetup(): Promise<{ success: boolean; message: string }> {
  return fetchApi('/setup/complete', { method: 'POST' });
}

// Bulk Operations
export async function bulkDeleteScreenshots(ids: number[]): Promise<BulkOperationResponse> {
  return fetchApi('/screenshots/bulk', {
    method: 'DELETE',
    body: JSON.stringify({ screenshot_ids: ids }),
  });
}

export async function bulkHideScreenshots(ids: number[]): Promise<BulkOperationResponse> {
  return fetchApi('/screenshots/bulk/hide', {
    method: 'POST',
    body: JSON.stringify({ screenshot_ids: ids }),
  });
}

export async function bulkUnhideScreenshots(ids: number[]): Promise<BulkOperationResponse> {
  return fetchApi('/screenshots/bulk/unhide', {
    method: 'POST',
    body: JSON.stringify({ screenshot_ids: ids }),
  });
}

// Incognito Mode
export async function getIncognitoStatus(): Promise<IncognitoStatus> {
  return fetchApi('/incognito/status');
}

export async function setIncognitoMode(durationMinutes: number): Promise<ApiResponse<void>> {
  return fetchApi('/incognito/set', {
    method: 'POST',
    body: JSON.stringify({ duration_minutes: durationMinutes }),
  });
}

export async function stopIncognitoMode(): Promise<ApiResponse<void>> {
  return fetchApi('/incognito/stop', { method: 'POST' });
}
