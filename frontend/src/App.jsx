import React, { useState, useEffect } from 'react';
import './index.css';
import Uploader from './components/Uploader';
import Chat from './components/Chat';
import Dashboard from './components/Dashboard';
import Tasks from './components/Tasks';

function App() {
  const [theme, setTheme] = useState(
    () => localStorage.getItem('ledger-theme') || 'dark'
  );

  const [appState, setAppState] = useState({
    stats: null,
    anomalies: [],
    uploaded: false,
    filename: '',
    parsing_method: 'standard',
  });

  useEffect(() => {
    localStorage.setItem('ledger-theme', theme);
  }, [theme]);

  const toggleTheme = () => setTheme(t => t === 'dark' ? 'light' : 'dark');

  const handleUploadSuccess = (data) => {
    setAppState({
      stats: data.stats,
      anomalies: data.anomalies || [],
      uploaded: true,
      filename: data.filename || 'statement',
      parsing_method: data.parsing_method || 'standard',
    });
  };

  const handleExport = async () => {
    try {
      const res = await fetch('http://localhost:5000/api/export', { method: 'POST' });
      const data = await res.json();
      if (data.report_url) {
        const link = document.createElement('a');
        link.href = `http://localhost:5000${data.report_url}`;
        link.download = 'LedgerMind_Report.pdf';
        link.click();
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className={`app-root theme-${theme}`}>
      {/* ── NAVBAR ── */}
      <header className="navbar">
        <div className="navbar-left">
          <h1 className="navbar-logo">
            <span role="img" aria-label="brain">🧠</span> LedgerMind AI
          </h1>
        </div>

        {appState.uploaded && (
          <div className="navbar-center">
            <span className="navbar-filename">
              Analyzing: {appState.filename}
            </span>
          </div>
        )}

        <div className="navbar-right">
          <div className="status-indicator">
            <div className={`status-dot ${appState.uploaded ? 'pulsing' : ''}`} />
            {appState.uploaded ? 'Agent Ready' : 'System Online'}
          </div>
          {appState.uploaded && (
            <button className="btn" onClick={handleExport}>
              Export Report
            </button>
          )}
          <button className="theme-toggle" onClick={toggleTheme} title="Toggle theme">
            {theme === 'dark' ? '☀️' : '🌙'}
          </button>
        </div>
      </header>

      {/* ── MAIN CONTENT ── */}
      {!appState.uploaded ? (
        <Uploader onSuccess={handleUploadSuccess} theme={theme} />
      ) : (
        <div className="panels-row">
          {/* OCR fallback notice */}
          {appState.parsing_method === 'ocr_fallback' && (
            <div className="ocr-notice">
              ⚠ AI Vision quota reached — used OCR fallback. Results may vary. Try again in 1 hour for full Gemini AI parsing.
            </div>
          )}
          <div className="panel-columns">
            <div className="left-panel">
              <Dashboard stats={appState.stats} anomalies={appState.anomalies} />
              <Tasks theme={theme} />
            </div>
            <div className="right-panel">
              <Chat theme={theme} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
