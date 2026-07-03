import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: process.env.VERCEL ? 'dist' : '../docs',
    emptyOutDir: true,
  },
  base: process.env.VERCEL ? '/' : '/LedgerMind-AI/', // Ensures assets load correctly on GitHub Pages
})
