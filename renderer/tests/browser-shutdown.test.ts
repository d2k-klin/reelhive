import {afterEach, expect, it, vi} from 'vitest';
import type {ChildProcess} from 'node:child_process';
import {boundBrowserShutdown} from '../src/browser-shutdown';

afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); });

it('leaves a normal shutdown alone and clears the timer', async () => {
  vi.useFakeTimers();
  const kill = vi.fn();
  const browser = boundBrowserShutdown({close: vi.fn().mockResolvedValue(undefined),
    process: () => ({exitCode: null, signalCode: null, kill}) as unknown as ChildProcess});
  await browser.close();
  await vi.advanceTimersByTimeAsync(10000);
  expect(kill).not.toHaveBeenCalled();
  expect(vi.getTimerCount()).toBe(0);
});

it('ends only its own browser when shutdown stalls', async () => {
  vi.useFakeTimers();
  vi.spyOn(console, 'warn').mockImplementation(() => {});
  let finish!: () => void;
  const closing = new Promise<void>(resolve => { finish = resolve; });
  const kill = vi.fn(() => { finish(); return true; });
  const browser = boundBrowserShutdown({close: () => closing,
    process: () => ({exitCode: null, signalCode: null, kill}) as unknown as ChildProcess});
  const done = browser.close();
  await vi.advanceTimersByTimeAsync(4999);
  expect(kill).not.toHaveBeenCalled();
  await vi.advanceTimersByTimeAsync(1);
  await done;
  expect(kill).toHaveBeenCalledOnce();
  expect(kill).toHaveBeenCalledWith('SIGKILL');
  expect(vi.getTimerCount()).toBe(0);
});

it('preserves shutdown errors', async () => {
  vi.useFakeTimers();
  const browser = boundBrowserShutdown({close: async () => { throw new Error('close failed'); }, process: () => null});
  await expect(browser.close()).rejects.toThrow('close failed');
  expect(vi.getTimerCount()).toBe(0);
});
