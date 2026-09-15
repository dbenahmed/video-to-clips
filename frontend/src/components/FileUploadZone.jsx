/**
 * FileUploadZone Component
 * ========================
 * Handles local video file uploads with drag-and-drop, format validation,
 * and live progress tracking.
 */

import React, { useState, useRef } from 'react';
import { uploadVideoFile } from '../services/videoApi';

const ALLOWED_EXTENSIONS = ['.mp4', '.mov', '.avi', '.mkv', '.webm'];

export default function FileUploadZone({ onUploadSuccess }) {
  const [isDragActive, setIsDragActive] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState('');
  const fileInputRef = useRef(null);

  const validateFile = (file) => {
    if (!file) return false;
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setErrorMessage(`Invalid format (${ext}). Allowed: ${ALLOWED_EXTENSIONS.join(', ')}`);
      return false;
    }
    setErrorMessage('');
    return true;
  };

  const processUpload = async (file) => {
    if (!validateFile(file)) return;

    setIsUploading(true);
    setProgress(0);
    setErrorMessage('');

    try {
      const data = await uploadVideoFile(file, (percent) => {
        setProgress(percent);
      });
      onUploadSuccess(data);
    } catch (err) {
      console.error('Upload failed:', err);
      const serverMsg = err.response?.data?.detail || 'Failed to upload video. Please check backend connection.';
      setErrorMessage(serverMsg);
    } finally {
      setIsUploading(false);
    }
  };

  const handleDragEnter = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFile = e.dataTransfer.files[0];
      processUpload(droppedFile);
    }
  };

  const handleFileInputChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      processUpload(e.target.files[0]);
    }
  };

  return (
    <div>
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileInputChange}
        accept={ALLOWED_EXTENSIONS.join(',')}
        style={{ display: 'none' }}
      />

      <div
        className={`dropzone ${isDragActive ? 'drag-active' : ''}`}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        onClick={() => !isUploading && fileInputRef.current?.click()}
      >
        <div className="dropzone-icon">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="17 8 12 3 7 8"></polyline>
            <line x1="12" y1="3" x2="12" y2="15"></line>
          </svg>
        </div>

        <h3 className="dropzone-title">
          {isDragActive ? 'Drop your video here' : 'Drag & drop your video file'}
        </h3>
        <p className="dropzone-desc">
          or click anywhere to browse from your computer
        </p>

        <div className="format-tags">
          {ALLOWED_EXTENSIONS.map((ext) => (
            <span key={ext} className="format-badge">{ext}</span>
          ))}
        </div>
      </div>

      {isUploading && (
        <div className="progress-box">
          <div className="progress-header">
            <span>Uploading video to server...</span>
            <span>{progress}%</span>
          </div>
          <div className="progress-track">
            <div className="progress-fill" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}

      {errorMessage && (
        <div className="error-banner">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          <span>{errorMessage}</span>
        </div>
      )}
    </div>
  );
}
