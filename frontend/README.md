# 💻 LedgerMind AI — Frontend Client

The frontend client for **LedgerMind AI** is built with **React 19** and **Vite**, featuring a responsive, dark-mode glassmorphic financial dashboard, real-time agent reasoning narration, embedded Matplotlib charts, and intuitive drag-and-drop document upload.

---

## ⚡ Quick Start

```bash
# Install dependencies
npm install

# Start development server with API proxying
npm run dev

# Build for production
npm run build
```

---

## 🔗 Architecture & Features

- **Component Architecture**:
  - `src/components/Dashboard.jsx`: Glassmorphic summary cards (Total Spend, Anomalies, Category Distribution).
  - `src/components/Chat.jsx`: Interactive AI analyst with reasoning narration stream and dynamically rendered base64 plots.
  - `src/components/Uploader.jsx`: Drag-and-drop file uploader supporting CSV, Excel, PDF, and receipt images.
  - `src/components/Tasks.jsx`: Priority-based financial action item manager.
- **Proxying & Rewrites**:
  - In development (`vite.config.js`), all `/api/*` requests automatically proxy to `http://127.0.0.1:5000`.
  - In production (`vercel.json`), requests to `/api/*` rewrite to the deployed backend serverless function.

For full project documentation and local backend setup, see the main [Root README](../README.md).
