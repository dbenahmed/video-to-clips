/**
 * YouTubeInputZone Component
 * ==========================
 * Handles YouTube video ingestion by communicating with the backend's yt-dlp downloader.
 */

import React, { useState } from 'react';
import { downloadYouTubeVideo } from '../services/api';

export default function YouTubeInputZone({ onDownloadSuccess }) {
  const [url, setUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const isValidYouTubeUrl = (input) => {
    const pattern = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+$/;
    return pattern.test(input.trim());
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const cleanUrl = url.trim();

    if (!cleanUrl) {
      setErrorMessage('Please enter a YouTube video URL.');
      return;
    }

    if (!isValidYouTubeUrl(cleanUrl)) {
      setErrorMessage('Please enter a valid YouTube link (e.g., https://www.youtube.com/watch?v=...)');
      return;
    }

    setErrorMessage('');
    setIsLoading(true);

    try {
      const data = await downloadYouTubeVideo(cleanUrl);
      onDownloadSuccess(data);
    } catch (err) {
      console.error('YouTube download failed:', err);
      const detail = err.response?.data?.detail || 'Failed to download YouTube video. Please verify the URL.';
      setErrorMessage(detail);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="youtube-form">
      <div style={{ textAlign: 'center', marginBottom: '1rem' }}>
        <h3 style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>Import from YouTube</h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
          Paste any YouTube link and our server will fetch the highest quality stream.
        </p>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="input-group">
          <input
            type="text"
            className="input-field"
            placeholder="https://www.youtube.com/watch?v=..."
            value={url}
            onChange={(e) => {
              setUrl(e.target.value);
              if (errorMessage) setErrorMessage('');
            }}
            disabled={isLoading}
          />
          <button
            type="submit"
            className="btn-primary"
            disabled={isLoading || !url.trim()}
          >
            {isLoading ? (
              <>
                <div className="spinner" />
                <span>Downloading...</span>
              </>
            ) : (
              <>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M19.615 3.184c-3.604-.246-11.631-.245-15.23 0-3.897.266-4.356 2.62-4.385 8.816.029 6.185.484 8.549 4.385 8.816 3.6.245 11.626.246 15.23 0 3.897-.266 4.356-2.62 4.385-8.816-.029-6.185-.484-8.549-4.385-8.816zm-10.615 12.816v-8l8 3.993-8 4.007z" />
                </svg>
                <span>Fetch Video</span>
              </>
            )}
          </button>
        </div>
      </form>

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
