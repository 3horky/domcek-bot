/// <reference types="vitest/config" />

import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': '/src',
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/health': process.env.CARLO_E2E_API_TARGET ?? 'http://api:8000',
      '/api': process.env.CARLO_E2E_API_TARGET ?? 'http://api:8000',
      '/media': process.env.CARLO_E2E_API_TARGET ?? 'http://api:8000',
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: true,
    include: ['src/**/*.test.{ts,tsx}'],
  },
})
