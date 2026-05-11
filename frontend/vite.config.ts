/// <reference types="vitest" />
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiProxyTarget = env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8000'

  return {
    plugins: [react()],
    server: {
      host: '127.0.0.1',
      port: 5173,
      proxy: {
        '/api': {
          target: apiProxyTarget,
          changeOrigin: true,
        },
      },
    },
    test: {
      environment: 'jsdom',
      setupFiles: ['./vitest.setup.ts'],
      globals: true,
      pool: 'threads',
      minWorkers: 1,
      maxWorkers: 1,
      include: [
        'testing/unit/**/*.test.ts',
        'testing/unit/**/*.test.tsx',
        'testing/unit/**/*.spec.ts',
        'testing/unit/**/*.spec.tsx',
      ],
      exclude: ['node_modules', 'dist', 'e2e/**', 'tests/e2e/**', 'testing/e2e/**'],
    },
  }
})
