import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import SettingsPage from '@/app/settings/page';
import { getConfig, getStatus, getCompressionStats, getCompressionStatus, getSyncStatus, updateConfig } from '@/lib/api';
import type { AppConfig } from '@/types';

jest.mock('@/lib/api');

test('saves WebP from the storage selector and restores it when settings reopen', async () => {
  let config: AppConfig = {
    capture: { mode: 'normal', interval: 2, threshold: 0.9, save_threshold: 0.6, quality: 95, max_time_without_save: 40 },
    compression: { enabled: true, after_days: 14, quality: 85, image_format: 'jpeg' },
    encryption_enabled: false, safe_mode_enabled: false, safe_mode_level: 'mid',
    similarity_metric: 'cosine', model_auto_unload_seconds: 300,
  };
  (getConfig as jest.Mock).mockImplementation(async () => config);
  (getStatus as jest.Mock).mockResolvedValue({
    healthy: true, recording: { is_recording: false },
    database: { total_screenshots: 0, synced: 0, unsynced: 0, compressed: 0 },
    model: { loaded: false }, incognito: { active: false },
  });
  (getCompressionStats as jest.Mock).mockResolvedValue({ compressible_count: 0 });
  (getCompressionStatus as jest.Mock).mockResolvedValue({ is_compressing: false });
  (getSyncStatus as jest.Mock).mockResolvedValue({ is_syncing: false });
  (updateConfig as jest.Mock).mockImplementation(async (updates) => {
    config = { ...config, compression: { ...config.compression, image_format: updates.compression_image_format } };
    return { success: true };
  });

  const first = render(<SettingsPage />);
  const selector = await screen.findByRole('combobox', { name: 'Compression format' });
  expect(selector).toHaveValue('jpeg');
  fireEvent.change(selector, { target: { value: 'webp' } });
  await waitFor(() => expect(updateConfig).toHaveBeenCalledWith({ compression_image_format: 'webp' }));
  await waitFor(() => expect(selector).toHaveValue('webp'));
  first.unmount();
  render(<SettingsPage />);
  expect(await screen.findByRole('combobox', { name: 'Compression format' })).toHaveValue('webp');
  expect(screen.getByText(/Both formats reduce image quality/)).toBeInTheDocument();
});
