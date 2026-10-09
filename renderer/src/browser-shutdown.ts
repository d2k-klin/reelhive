import type {Browser} from 'puppeteer';
import {createRequire} from 'node:module';

export function installBrowserShutdownGuard(): void {
  // tsx loads separate ESM and CommonJS instances. Guard the instance Revideo actually requires.
  const require = createRequire(import.meta.url);
  const rendererRequire = createRequire(require.resolve('@revideo/renderer'));
  const puppeteer = rendererRequire('puppeteer').default as typeof import('puppeteer').default;
  const launch = puppeteer.launch.bind(puppeteer);
  puppeteer.launch = async options => boundBrowserShutdown(await launch(options));
}

// Chrome's single-process mode can deadlock on macOS after Browser.close.
// Revideo requests closure after the worker finishes or fails, so this never ends an active render.
export function boundBrowserShutdown<T extends Pick<Browser, 'close' | 'process'>>(browser: T): T {
  const close = browser.close.bind(browser);
  browser.close = async () => {
    const child = browser.process();
    const timer = setTimeout(() => {
      if (child && child.exitCode === null && child.signalCode === null) {
        console.warn('Rendering browser did not close in 5 seconds; terminating it.');
        child.kill('SIGKILL');
      }
    }, 5000);
    timer.unref();
    try {
      await close();
    } finally {
      clearTimeout(timer);
    }
  };
  return browser;
}
