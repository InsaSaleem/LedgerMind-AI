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
      // localhost ko hata kar Vercel ka live URL laga diya
      const res = await fetch('https://ledger-mind-ai.vercel.app/api/export', { method: 'POST' });
      const data = await res.json();
      if (data.report_url) {
        const link = document.createElement('a');
        // Yahan bhi live URL update kar diya
        link.href = `https://ledger-mind-ai.vercel.app${data.report_url}`;
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
        <div className="panels-row" style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
          padding: '16px 20px',
          flex: 1,
          minHeight: 0,
          overflow: 'hidden'
        }}>
          <div className="panel-columns" style={{
            display: 'flex',
            flexDirection: 'row',
            alignItems: 'stretch',
            gap: '16px',
            flex: 1,
            minHeight: 0
          }}>
            {/* Unified Scrollable Left Panel */}
            <div className="left-panel" style={{
              width: '40%',
              height: '100%',
              overflowY: 'scroll',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
              paddingRight: '4px'
            }}>
              <Dashboard stats={appState.stats} anomalies={appState.anomalies} parsingMethod={appState.parsing_method} />
              <Tasks theme={theme} />
            </div>
            {/* Right Panel — AI Chat remains fixed */}
            <div className="right-panel" style={{
              width: '60%',
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              minHeight: 0
            }}>
              <Chat theme={theme} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
