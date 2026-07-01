import React, { useCallback, useState } from 'react';

const Uploader = ({ onSuccess }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setIsDragging(true);
    } else if (e.type === 'dragleave') {
      setIsDragging(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      uploadFile(files[0]);
    }
  }, []);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      uploadFile(e.target.files[0]);
    }
  };

  const uploadFile = async (file) => {
    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://localhost:5000/api/upload', {
        method: 'POST',
        body: formData,
      });
      
      const data = await response.json();
      if (response.ok) {
        onSuccess(data);
      } else {
        alert(data.error || 'Upload failed');
      }
    } catch (error) {
      console.error(error);
      alert('Error connecting to server');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div 
      className={`uploader ${isDragging ? 'dragging' : ''}`}
      onDragEnter={handleDrag}
      onDragLeave={handleDrag}
      onDragOver={handleDrag}
      onDrop={handleDrop}
      onClick={() => document.getElementById('fileUpload').click()}
    >
      <div style={{ marginBottom: '16px', color: 'var(--accent)' }}>
        <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
        </svg>
      </div>
      {isUploading ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-primary)', fontSize: '14px' }}>
          <div className="status-dot pulsing"></div>
          Analyzing...
        </div>
      ) : (
        <>
          <p>Drop your bank statement here</p>
          <span className="subtext">Supports PDF, CSV, Excel, JPG, PNG</span>
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
  );
};

export default Uploader;
