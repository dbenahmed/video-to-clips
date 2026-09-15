/**
 * IngestionPage Component
 * =======================
 * Primary view for Milestone 2: Video Ingestion.
 * Coordinates between local video uploading and YouTube link fetching.
 */

import React, { useState } from 'react';
import FileUploadZone from '../components/FileUploadZone';
import YouTubeInputZone from '../components/YouTubeInputZone';
import VideoResultCard from '../components/VideoResultCard';

export default function IngestionPage() {
  const [activeTab, setActiveTab] = useState('upload'); // 'upload' | 'youtube'
  const [ingestedVideo, setIngestedVideo] = useState(null);

  const handleIngestionSuccess = (videoData) => {
    setIngestedVideo(videoData);
  };

  const handleReset = () => {
    setIngestedVideo(null);
  };

  return (
    <div>
      <div className="page-header">
        <div className="page-badge">
          <span>🚀 Milestone 2</span>
          <span>•</span>
          <span>Video Ingestion Pipeline</span>
        </div>
        <h1 className="page-title">Transform Any Video Into Clips</h1>
        <p className="page-subtitle">
          Upload your raw MP4/MOV footage or paste a YouTube URL. Our pipeline prepares the stream for AI subject tracking.
        </p>
      </div>

      {ingestedVideo ? (
        <VideoResultCard videoData={ingestedVideo} onReset={handleReset} />
      ) : (
        <div className="glass-panel" style={{ padding: '2rem' }}>
          {/* Ingestion Source Tabs */}
          <div className="tabs-container">
            <button
              className={`tab-button ${activeTab === 'upload' ? 'active' : ''}`}
              onClick={() => setActiveTab('upload')}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="17 8 12 3 7 8"></polyline>
                <line x1="12" y1="3" x2="12" y2="15"></line>
              </svg>
              <span>Upload Video</span>
            </button>

            <button
              className={`tab-button ${activeTab === 'youtube' ? 'active' : ''}`}
              onClick={() => setActiveTab('youtube')}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <path d="M19.615 3.184c-3.604-.246-11.631-.245-15.23 0-3.897.266-4.356 2.62-4.385 8.816.029 6.185.484 8.549 4.385 8.816 3.6.245 11.626.246 15.23 0 3.897-.266 4.356-2.62 4.385-8.816-.029-6.185-.484-8.549-4.385-8.816zm-10.615 12.816v-8l8 3.993-8 4.007z" />
              </svg>
              <span>YouTube Link</span>
            </button>
          </div>

          {/* Tab Panes */}
          {activeTab === 'upload' ? (
            <FileUploadZone onUploadSuccess={handleIngestionSuccess} />
          ) : (
            <YouTubeInputZone onDownloadSuccess={handleIngestionSuccess} />
          )}
        </div>
      )}
    </div>
  );
}
