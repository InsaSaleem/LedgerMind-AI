import React, { useState } from 'react';
import './index.css';
import Uploader from './components/Uploader';
import Chat from './components/Chat';
import Dashboard from './components/Dashboard';

function App() {
  const [appState, setAppState] = useState({
    stats: null,
    anomalies: [],
    uploaded: false
  });

  const handleUploadSuccess = (data) => {
    setAppState({
      stats: data.stats,
      anomalies: data.stats?.anomaly_count > 0 ? [] : [], // Real app would pass anomalies list
      uploaded: true
    });
  };

  const handleExport = async () => {
    try {
      const res = await fetch('http://localhost:5000/api/export', { method: 'POST' });
      const data = await res.json();
      if (data.report_url) {
        alert(`Report generated: ${data.report_url}`);
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="app-container">
      <header className="header">
        <h1>LedgerMind AI</h1>
        {appState.uploaded && (
          <button className="btn btn-secondary" onClick={handleExport}>
            Export Report
          </button>
        )}
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
            <Dashboard stats={appState.stats} />
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
