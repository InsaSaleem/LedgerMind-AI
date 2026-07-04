import React, { useState } from 'react';

const FEATURE_PILLS = [
  { icon: '⚡', label: 'Instant Analysis' },
  { icon: '🔍', label: 'Anomaly Detection' },
  { icon: '💬', label: 'Natural Language Q&A' },
];

const STAT_BOXES = [
  { emoji: '📁', title: 'Any Format', sub: 'PDF · CSV · Excel · IMG' },
  { emoji: '⚡', title: '< 5 Seconds', sub: 'Instant AI Analysis' },
  { emoji: '🔒', title: 'Private', sub: 'Processed Locally' },
];

const Uploader = ({ onSuccess }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setIsDragging(true);
    } else if (e.type === 'dragleave') {
      setIsDragging(false);
    }
  };

  const handleDrop = (e) => {
    setErrorMsg('');
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files && files.length > 0) uploadFile(files[0]);
  };

  const handleFileChange = (e) => {
    setErrorMsg('');
    if (e.target.files && e.target.files.length > 0) uploadFile(e.target.files[0]);
  };

  const uploadFile = async (file) => {
    setIsUploading(true);
    setErrorMsg('');
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/upload`, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (response.ok) {
        onSuccess(data);
      } else {
        // Always show the actual server error message for accurate debugging
        setErrorMsg(data.error || 'Upload failed. Please try again.');
      }
    } catch (error) {
      console.error(error);
      setErrorMsg('Error connecting to server. Make sure the backend is running and accessible.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="upload-page">
      {/* ── HERO ── */}
      <div className="hero-section">
        <span className="badge-pill">✦ Powered by Gemini AI</span>

        <h1 className="hero-heading">
          Your Personal<br />
          <span className="hero-heading-accent">AI</span> Financial Analyst
        </h1>

        <p className="hero-subtitle">
          Upload any bank statement and LedgerMind AI instantly detects anomalies, maps spending
          patterns, and answers your financial questions — in seconds.
        </p>

        <div className="feature-pills">
          {FEATURE_PILLS.map((p, i) => (
            <span key={i} className="feature-pill">
              {p.icon} {p.label}
            </span>
          ))}
        </div>
      </div>

      {/* ── UPLOAD CARD ── */}
      <div className="upload-card">
        <div
          className={`dropzone ${isDragging ? 'dropzone--dragging' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => !isUploading && document.getElementById('fileUpload').click()}
        >
          {isUploading ? (
            <div className="dropzone-loading">
              <div className="status-dot pulsing" />
              Analyzing your statement...
            </div>
          ) : (
            <>
              {/* Cloud upload icon */}
              <div className="dropzone-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                    d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                </svg>
              </div>
              <p className="dropzone-title">Drop your bank statement here</p>
              <span
                className="dropzone-browse"
                onClick={(e) => { e.stopPropagation(); document.getElementById('fileUpload').click(); }}
              >
                or browse files
              </span>
              <span className="dropzone-hint">Supports PDF, CSV, Excel, JPG, PNG</span>
            </>
          )}

          <input
            type="file"
            id="fileUpload"
            style={{ display: 'none' }}
            onChange={handleFileChange}
            accept=".pdf,.csv,.xlsx,.xls,.jpg,.jpeg,.png"
          />
        </div>

        {/* Inline error message */}
        {errorMsg && (
          <div className="upload-error">
            {errorMsg}
          </div>
        )}

        {/* ── STAT BOXES ── */}
        <div className="upload-stat-row">
          {STAT_BOXES.map((b, i) => (
            <div key={i} className="upload-stat-box">
              <div className="upload-stat-emoji">{b.emoji}</div>
              <div className="upload-stat-title">{b.title}</div>
              <div className="upload-stat-sub">{b.sub}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Uploader;


