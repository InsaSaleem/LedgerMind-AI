import React, { useState } from 'react';
import './index.css';
import Uploader from './components/Uploader';
import Chat from './components/Chat';
import Dashboard from './components/Dashboard';

function App() {
  const [appState, setAppState] = useState({
    stats: null,
    anomalies: [],
    uploaded: false,
    filename: ''
  });

  const handleUploadSuccess = (data) => {
    setAppState({
      stats: data.stats,
      anomalies: data.anomalies || [],
      uploaded: true,
      filename: data.filename || 'statement.csv'
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
    <div className="app-container">
      <header className="header" style={{ flexWrap: 'wrap' }}>
        <div className="header-left">
          <h1 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span role="img" aria-label="brain">🧠</span> LedgerMind AI
          </h1>
        </div>
        {appState.uploaded && (
          <div style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>
            Analyzing: {appState.filename}
          </div>
        )}
        <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
          <div className="status-indicator">
            <div className={`status-dot ${!appState.uploaded ? '' : 'pulsing'}`}></div>
            {appState.uploaded ? 'Agent Ready' : 'System Online'}
          </div>
          {appState.uploaded && (
            <button className="btn btn-secondary" onClick={handleExport}>
              Export Report
            </button>
          )}
        </div>
      </header>

      {!appState.uploaded ? (
        <div className="card">
          <h2>Upload Financial Data</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>
            Supports PDF bank statements, CSV, and Excel exports.
          </p>
          <Uploader onSuccess={handleUploadSuccess} />
        </div>
      ) : (
        <div className="main-content">
          <div className="left-panel">
            <Dashboard stats={appState.stats} anomalies={appState.anomalies} />
          </div>
          <div className="right-panel">
            <Chat />
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
