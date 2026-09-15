/**
 * VideoResultCard Component
 * =========================
 * Displays an interactive video preview for newly uploaded or downloaded videos,
 * along with extracted metadata and actions for subsequent milestones.
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getFullVideoUrl } from '../services/videoApi';

export default function VideoResultCard({ videoData, onReset }) {
  const [copied, setCopied] = useState(false);
  const navigate = useNavigate();
  const streamUrl = getFullVideoUrl(videoData.url);

  const formatBytes = (bytes) => {
    if (!bytes || bytes === 0) return 'N/A';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDuration = (seconds) => {
    if (!seconds && seconds !== 0) return 'N/A';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  const copyUrlToClipboard = () => {
    navigator.clipboard.writeText(streamUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="glass-panel result-card">
      <div className="result-header">
        <div>
          <span className="result-badge">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            Video Ingestion Successful
          </span>
          <h2 style={{ fontSize: '1.4rem', marginTop: '0.5rem' }}>
            {videoData.title || videoData.original_name || 'Processed Video'}
          </h2>
        </div>

        <button className="btn-secondary" onClick={onReset}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/>
          </svg>
          Ingest Another
        </button>
      </div>

      {/* HTML5 Video Streaming Preview */}
      <div className="video-player-container">
        <video
          className="video-player"
          controls
          preload="metadata"
          src={streamUrl}
        >
          Your browser does not support the video tag.
        </video>
      </div>

      {/* Video Metadata Grid */}
      <div className="meta-grid">
        <div className="meta-item">
          <div className="meta-label">Unique Video ID</div>
          <div className="meta-value" title={videoData.id}>{videoData.id.slice(0, 12)}...</div>
        </div>

        <div className="meta-item">
          <div className="meta-label">Storage Filename</div>
          <div className="meta-value" title={videoData.saved_filename}>{videoData.saved_filename}</div>
        </div>

        <div className="meta-item">
          <div className="meta-label">File Size</div>
          <div className="meta-value">{formatBytes(videoData.size_bytes)}</div>
        </div>

        <div className="meta-item">
          <div className="meta-label">Duration</div>
          <div className="meta-value">{formatDuration(videoData.duration_seconds)}</div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="action-row">
        <button className="btn-secondary" onClick={copyUrlToClipboard}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
          </svg>
          {copied ? 'Copied URL!' : 'Copy Stream URL'}
        </button>

        <button
          className="btn-primary"
          onClick={() => navigate(`/pipeline/${encodeURIComponent(videoData.saved_filename)}`)}
        >
          <span>Proceed to Milestone 3: AI Analysis</span>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
        </button>
      </div>
    </div>
  );
}
