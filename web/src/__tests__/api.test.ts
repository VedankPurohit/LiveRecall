/**
 * Tests for lib/api.ts
 */

import {
  getHealth,
  getStatus,
  getConfig,
  updateConfig,
  search,
  searchWithParams,
  startRecording,
  stopRecording,
  getRecordingStatus,
  startSync,
  stopSync,
  getSyncStatus,
  startCompression,
  stopCompression,
  getCompressionStatus,
  getCompressionStats,
  getScreenshots,
  getScreenshotById,
  getScreenshotOffset,
  getDateRange,
  getDensity,
  deleteScreenshot,
  getImageUrl,
  getSetupStatus,
  resetPermissions,
  completeSetup,
  bulkDeleteScreenshots,
  bulkHideScreenshots,
  bulkUnhideScreenshots,
  getIncognitoStatus,
  setIncognitoMode,
  stopIncognitoMode,
} from '@/lib/api';

// Helper to mock fetch responses
const mockFetch = (data: unknown, ok = true, status = 200) => {
  (global.fetch as jest.Mock).mockResolvedValueOnce({
    ok,
    status,
    json: () => Promise.resolve(data),
  });
};

const mockFetchError = (detail: string) => {
  (global.fetch as jest.Mock).mockResolvedValueOnce({
    ok: false,
    status: 500,
    json: () => Promise.resolve({ detail }),
  });
};

describe('API Client', () => {
  describe('Health & Status', () => {
    it('should fetch health status', async () => {
      const healthData = { status: 'ok', version: '0.1.2' };
      mockFetch(healthData);

      const result = await getHealth();

      expect(result).toEqual(healthData);
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/health',
        expect.objectContaining({
          headers: { 'Content-Type': 'application/json' },
        })
      );
    });

    it('should fetch system status', async () => {
      const statusData = {
        healthy: true,
        recording: { is_recording: true },
        database: { total_screenshots: 100 },
      };
      mockFetch(statusData);

      const result = await getStatus();

      expect(result).toEqual(statusData);
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/status',
        expect.any(Object)
      );
    });
  });

  describe('Config', () => {
    it('should fetch config', async () => {
      const configData = {
        capture: { mode: 'normal', quality: 95 },
        compression: { enabled: false },
      };
      mockFetch(configData);

      const result = await getConfig();

      expect(result).toEqual(configData);
    });

    it('should update config', async () => {
      mockFetch({ success: true });

      const result = await updateConfig({ capture_quality: 90 });

      expect(result).toEqual({ success: true });
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/config',
        expect.objectContaining({
          method: 'PUT',
          body: JSON.stringify({ capture_quality: 90 }),
        })
      );
    });
  });

  describe('Search', () => {
    it('should perform search with default params', async () => {
      const searchResults = {
        query: 'test',
        total_results: 1,
        results: [{ id: 1, similarity: 0.9 }],
      };
      mockFetch(searchResults);

      const result = await search('test');

      expect(result).toEqual(searchResults);
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/search',
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('"query":"test"'),
        })
      );
    });

    it('should perform search with custom params', async () => {
      mockFetch({ results: [] });

      await search('blue shirt', 50, false, 'low', '2024-01-01', '2024-12-31');

      const body = JSON.parse(
        (global.fetch as jest.Mock).mock.calls[0][1].body
      );
      expect(body).toEqual({
        query: 'blue shirt',
        limit: 50,
        safe_mode: false,
        safe_mode_level: 'low',
        start_date: '2024-01-01',
        end_date: '2024-12-31',
        visibility: 'visible_only',
      });
    });

    it('should perform search with SearchParams object', async () => {
      mockFetch({ results: [] });

      await searchWithParams({
        query: 'test query',
        limit: 100,
        safe_mode: true,
        safe_mode_level: 'high',
      });

      const body = JSON.parse(
        (global.fetch as jest.Mock).mock.calls[0][1].body
      );
      expect(body.query).toBe('test query');
      expect(body.limit).toBe(100);
      expect(body.safe_mode).toBe(true);
    });
  });

  describe('Recording', () => {
    it('should start recording', async () => {
      mockFetch({ success: true });

      const result = await startRecording();

      expect(result).toEqual({ success: true });
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/recording/start',
        expect.objectContaining({ method: 'POST' })
      );
    });

    it('should stop recording', async () => {
      mockFetch({ success: true });

      const result = await stopRecording();

      expect(result).toEqual({ success: true });
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/recording/stop',
        expect.objectContaining({ method: 'POST' })
      );
    });

    it('should get recording status', async () => {
      const statusData = {
        is_recording: true,
        mode: 'normal',
        interval: 2.0,
        threshold: 0.9,
      };
      mockFetch(statusData);

      const result = await getRecordingStatus();

      expect(result).toEqual(statusData);
    });
  });

  describe('Sync', () => {
    it('should start sync', async () => {
      mockFetch({ success: true });

      const result = await startSync();

      expect(result).toEqual({ success: true });
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/sync/start',
        expect.objectContaining({ method: 'POST' })
      );
    });

    it('should stop sync', async () => {
      mockFetch({ success: true });

      const result = await stopSync();

      expect(result).toEqual({ success: true });
    });

    it('should get sync status', async () => {
      const syncStatus = {
        is_syncing: true,
        processed: 50,
        total: 100,
      };
      mockFetch(syncStatus);

      const result = await getSyncStatus();

      expect(result).toEqual(syncStatus);
    });
  });

  describe('Compression', () => {
    it('should start compression', async () => {
      mockFetch({ success: true, compressible_count: 50 });

      const result = await startCompression();

      expect(result).toEqual({ success: true, compressible_count: 50 });
    });

    it('should stop compression', async () => {
      mockFetch({ success: true });

      const result = await stopCompression();

      expect(result).toEqual({ success: true });
    });

    it('should get compression status', async () => {
      const status = {
        is_compressing: true,
        total: 100,
        processed: 25,
      };
      mockFetch(status);

      const result = await getCompressionStatus();

      expect(result).toEqual(status);
    });

    it('should get compression stats', async () => {
      const stats = {
        compressed_count: 500,
        uncompressed_count: 100,
        bytes_saved: 1000000,
      };
      mockFetch(stats);

      const result = await getCompressionStats();

      expect(result).toEqual(stats);
    });
  });

  describe('Screenshots', () => {
    it('should get screenshots with default params', async () => {
      const data = {
        total: 100,
        screenshots: [{ id: 1, image_path: '/path/1.jpg' }],
      };
      mockFetch(data);

      const result = await getScreenshots();

      expect(result).toEqual(data);
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/screenshots?limit=50&offset=0&visibility=visible_only',
        expect.any(Object)
      );
    });

    it('should get screenshots with custom params', async () => {
      mockFetch({ total: 0, screenshots: [] });

      await getScreenshots(100, 50, '2024-01-01', '2024-12-31');

      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/screenshots?limit=100&offset=50&visibility=visible_only&start_date=2024-01-01&end_date=2024-12-31',
        expect.any(Object)
      );
    });

    it('should get screenshot by id', async () => {
      const screenshot = { id: 123, image_path: '/path/123.jpg' };
      mockFetch(screenshot);

      const result = await getScreenshotById(123);

      expect(result).toEqual(screenshot);
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/screenshots/123',
        expect.any(Object)
      );
    });

    it('should delete screenshot', async () => {
      mockFetch({ success: true });

      const result = await deleteScreenshot(123);

      expect(result).toEqual({ success: true });
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/screenshots/123',
        expect.objectContaining({ method: 'DELETE' })
      );
    });
  });

  describe('Timeline', () => {
    it('should get date range', async () => {
      const dateRange = {
        start_date: '2024-01-01',
        end_date: '2024-12-31',
      };
      mockFetch(dateRange);

      const result = await getDateRange();

      expect(result).toEqual(dateRange);
    });

    it('should get density with default buckets', async () => {
      const density = { buckets: [], total: 1000 };
      mockFetch(density);

      const result = await getDensity();

      expect(result).toEqual(density);
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/screenshots/density?buckets=100&visibility=visible_only',
        expect.any(Object)
      );
    });

    it('should get density with custom buckets', async () => {
      mockFetch({ buckets: [], total: 0 });

      await getDensity(50);

      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/screenshots/density?buckets=50&visibility=visible_only',
        expect.any(Object)
      );
    });
  });

  describe('Image URL Helper', () => {
    it('should generate correct image URL', () => {
      const path = '/Users/test/screenshots/image.jpg';
      const url = getImageUrl(path);

      expect(url).toBe(
        `/api/v1/screenshots/image?path=${encodeURIComponent(path)}`
      );
    });

    it('should handle special characters in path', () => {
      const path = '/path/with spaces/and&special.jpg';
      const url = getImageUrl(path);

      expect(url).toContain(encodeURIComponent(path));
    });
  });

  describe('Error Handling', () => {
    it('should throw error on failed request', async () => {
      mockFetchError('Not found');

      await expect(getHealth()).rejects.toThrow('Not found');
    });

    it('should handle non-JSON error response', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: () => Promise.reject(new Error('Invalid JSON')),
      });

      await expect(getHealth()).rejects.toThrow('Request failed');
    });
  });

  describe('Setup', () => {
    it('should fetch setup status', async () => {
      const setupData = {
        current_version: '0.1.2',
        last_seen_version: '0.1.1',
        needs_setup: true,
      };
      mockFetch(setupData);

      const result = await getSetupStatus();

      expect(result).toEqual(setupData);
      expect(fetch).toHaveBeenCalledWith('/api/v1/setup/status', expect.any(Object));
    });

    it('should reset permissions', async () => {
      const response = { success: true, message: 'Permissions reset' };
      mockFetch(response);

      const result = await resetPermissions();

      expect(result).toEqual(response);
      expect(fetch).toHaveBeenCalledWith(
        '/api/v1/setup/reset-permissions',
        expect.objectContaining({ method: 'POST' })
      );
    });

    it('should complete setup', async () => {
      const response = { success: true, message: 'Setup completed' };
      mockFetch(response);

      const result = await completeSetup();

      expect(result).toEqual(response);
      expect(fetch).toHaveBeenCalledWith(
        '/api/v1/setup/complete',
        expect.objectContaining({ method: 'POST' })
      );
    });
  });

  describe('Screenshot Offset', () => {
    it('should get screenshot offset with default visibility', async () => {
      const offsetData = { offset: 42 };
      mockFetch(offsetData);

      const result = await getScreenshotOffset(123);

      expect(result).toEqual(offsetData);
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/screenshots/123/offset?visibility=visible_only',
        expect.any(Object)
      );
    });

    it('should get screenshot offset with custom visibility', async () => {
      const offsetData = { offset: 10 };
      mockFetch(offsetData);

      const result = await getScreenshotOffset(456, 'hidden_only');

      expect(result).toEqual(offsetData);
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/screenshots/456/offset?visibility=hidden_only',
        expect.any(Object)
      );
    });
  });

  describe('Bulk Operations', () => {
    it('should bulk delete screenshots', async () => {
      const response = {
        success: true,
        affected_count: 3,
        message: 'Deleted 3 screenshots and 3 files',
      };
      mockFetch(response);

      const result = await bulkDeleteScreenshots([1, 2, 3]);

      expect(result).toEqual(response);
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/screenshots/bulk',
        expect.objectContaining({
          method: 'DELETE',
          body: JSON.stringify({ screenshot_ids: [1, 2, 3] }),
        })
      );
    });

    it('should bulk hide screenshots', async () => {
      const response = {
        success: true,
        affected_count: 5,
        message: 'Hidden 5 screenshots',
      };
      mockFetch(response);

      const result = await bulkHideScreenshots([10, 20, 30, 40, 50]);

      expect(result).toEqual(response);
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/screenshots/bulk/hide',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ screenshot_ids: [10, 20, 30, 40, 50] }),
        })
      );
    });

    it('should bulk unhide screenshots', async () => {
      const response = {
        success: true,
        affected_count: 2,
        message: 'Unhidden 2 screenshots',
      };
      mockFetch(response);

      const result = await bulkUnhideScreenshots([100, 200]);

      expect(result).toEqual(response);
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/screenshots/bulk/unhide',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ screenshot_ids: [100, 200] }),
        })
      );
    });
  });

  describe('Incognito Mode', () => {
    it('should get incognito status', async () => {
      const status = {
        is_active: true,
        remaining_seconds: 1800,
        started_at: '2024-01-15T10:00:00Z',
      };
      mockFetch(status);

      const result = await getIncognitoStatus();

      expect(result).toEqual(status);
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/incognito/status',
        expect.any(Object)
      );
    });

    it('should set incognito mode with duration', async () => {
      mockFetch({ success: true });

      const result = await setIncognitoMode(30);

      expect(result).toEqual({ success: true });
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/incognito/set',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ duration_minutes: 30 }),
        })
      );
    });

    it('should stop incognito mode', async () => {
      mockFetch({ success: true });

      const result = await stopIncognitoMode();

      expect(result).toEqual({ success: true });
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/incognito/stop',
        expect.objectContaining({ method: 'POST' })
      );
    });
  });
});
