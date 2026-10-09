// @vitest-environment jsdom
import {afterEach, describe, expect, it, vi} from 'vitest';
import {cleanup, render, screen} from '@testing-library/react';
import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import {MemoryRouter} from 'react-router-dom';
import {request} from '../api/client';
import {RunsPage, formatStarted} from './Runs';

vi.mock('../api/client', () => ({request: vi.fn(), fileUrl: vi.fn()}));

afterEach(cleanup);

const run = (id: string, created_at: string) => ({
  id, created_at, status: 'done', provider: 'claude', video: false,
  brief: {storyline: `Story ${id}`, level: 'low', duration: 60, format: '16:9'},
});

describe('Runs screen', () => {
  it('shows when each run started, in the order the server returns them', async () => {
    vi.mocked(request).mockResolvedValue([run('newest', '2026-10-09T14:30:00Z'), run('oldest', '2026-10-08T09:05:00Z')]);
    const client = new QueryClient({defaultOptions: {queries: {retry: false}}});
    render(<QueryClientProvider client={client}><MemoryRouter><RunsPage/></MemoryRouter></QueryClientProvider>);
    await screen.findByText('Story newest');
    expect(screen.getByText('Started')).toBeTruthy();
    const times = Array.from(document.querySelectorAll('time')).map(time => time.getAttribute('datetime'));
    expect(times).toEqual(['2026-10-09T14:30:00Z', '2026-10-08T09:05:00Z']);
    expect(screen.getByText(formatStarted('2026-10-09T14:30:00Z'))).toBeTruthy();
    const titles = screen.getAllByRole('link').map(link => link.textContent).filter(text => text?.startsWith('Story'));
    expect(titles).toEqual(['Story newest', 'Story oldest']);
  });
});
