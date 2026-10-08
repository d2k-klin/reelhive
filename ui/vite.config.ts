import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';
import {resolve} from 'node:path';

export default defineConfig({
  plugins: [react({include: /ui\/src\/.*\.[jt]sx$/})],
  resolve: {alias: {'@brand': resolve(__dirname, '../assets/brand')}},
  server: {host: '127.0.0.1', proxy: {'/api': {target: 'http://127.0.0.1:8765', changeOrigin: true,
    configure(proxy) {proxy.on('proxyReq', request => request.setHeader('Origin', 'http://127.0.0.1:8765'));}}}},
  build: {outDir: 'dist', sourcemap: false},
});
