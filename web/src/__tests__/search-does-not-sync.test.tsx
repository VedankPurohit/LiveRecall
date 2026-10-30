import '@testing-library/jest-dom';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import Home from '@/app/page';
import * as api from '@/lib/api';

jest.mock('@/lib/api');
jest.mock('next/navigation', () => {
  const parameters = new URLSearchParams();
  const router = { push: jest.fn() };
  return { useSearchParams: () => parameters, useRouter: () => router };
});
jest.mock('@/components/CompressionSuggestion', () => ({ CompressionSuggestion: () => null }));
jest.mock('@/components/IncognitoIndicator', () => ({ IncognitoIndicator: () => null }));

test.each(['auto', 'text_fuzzy'] as const)('%s search leaves bulk sync to the explicit control', async (mode) => {
  const screenshot = {
    id: 651991, timestamp: '260830000000', image_path: '/retained.jpg', has_embedding: 0,
    has_ocr: 1, is_hidden: false, similarity: 0.9,
  };
  (api.getStatus as jest.Mock).mockResolvedValue({
    healthy: true, recording: { is_recording: false },
    database: { total_screenshots: 78288, synced: 0, unsynced: 78288, compressed: 0 },
    model: { loaded: false },
  });
  (api.getSyncStatus as jest.Mock).mockResolvedValue({ is_syncing: false });
  (api.getIncognitoStatus as jest.Mock).mockResolvedValue({ active: false, remaining_seconds: 0 });
  (api.getScreenshots as jest.Mock).mockResolvedValue({ total: 1, screenshots: [screenshot] });
  (api.getDensity as jest.Mock).mockResolvedValue({ buckets: [] });
  (api.getImageUrl as jest.Mock).mockReturnValue('/fixture-retained.jpg');
  (api.search as jest.Mock).mockResolvedValue({ results: [screenshot] });
  (api.startSync as jest.Mock).mockResolvedValue({ success: true });
  global.IntersectionObserver = class {
    observe() {}
    disconnect() {}
    unobserve() {}
  } as unknown as typeof IntersectionObserver;

  const { container } = render(<Home />);
  await screen.findByRole('button', { name: /78288 pending sync/ });
  expect(container.querySelector('img[src="/fixture-retained.jpg"]')).not.toBeNull();
  const input = screen.getByPlaceholderText('Search snapshots...');
  fireEvent.focus(input);
  if (mode !== 'auto') fireEvent.change(screen.getByTitle('Search mode'), { target: { value: mode } });
  fireEvent.change(input, { target: { value: 'project' } });
  await waitFor(() => expect(api.search).toHaveBeenCalledWith('project', 50, expect.any(Boolean), expect.any(String), undefined, undefined, 'visible_only', mode));
  expect(api.startSync).not.toHaveBeenCalled();

  fireEvent.click(screen.getByRole('button', { name: /78288 pending sync/ }));
  expect(api.startSync).toHaveBeenCalledTimes(1);
});
