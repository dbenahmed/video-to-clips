/**
 * Navbar Component
 * ================
 * Displays application branding, roadmap milestone status, and live backend connection badge.
 */

import React, { useEffect, useState } from 'react';
import { checkBackendHealth } from '../services/api';

export default function Navbar() {
  const [isOnline, setIsOnline] = useState(null);

  useEffect(() => {
    let isMounted = true;
    checkBackendHealth().then((res) => {
      if (isMounted) setIsOnline(res.online);
    });

    const interval = setInterval(() => {
      checkBackendHealth().then((res) => {
        if (isMounted) setIsOnline(res.online);
      });
    }, 15000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <header className="navbar">
      <div className="nav-brand">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: '#818cf8' }}>
          <polygon points="23 7 16 12 23 17 23 7"></polygon>
          <rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect>
        </svg>
        <span>ClipForge <span className="brand-gradient">AI</span></span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <div className="nav-status-badge">
          <span className={`status-dot ${isOnline === true ? 'status-online' : isOnline === false ? 'status-offline' : ''}`} />
          <span>{isOnline === true ? 'FastAPI Online' : isOnline === false ? 'Backend Offline' : 'Connecting...'}</span>
        </div>
      </div>
    </header>
  );
}
