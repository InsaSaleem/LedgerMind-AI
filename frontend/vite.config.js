import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  build: {
    outDir: process.env.VERCEL ? 'dist' : '../docs',
    emptyOutDir: true,
  },
  base: process.env.VERCEL ? '/' : '/LedgerMind-AI/', // Ensures assets load correctly on GitHub Pages
})
