import React, { useState, useRef, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getFullVideoUrl } from '../services/videoApi';
import mockRecipe from '../mock_recipe.json';

// Mock data to work on the UI without relying on the backend
const MOCK_CLIPS = [
  { id: 'clip_1', start_time: 15.0, end_time: 45.0, text: "This is the most incredible thing I've ever seen...", title: "Viral Hook 1" },
  { id: 'clip_2', start_time: 60.5, end_time: 90.0, text: "If you want to succeed, you have to stop doing this.", title: "Advice Segment" },
  { id: 'clip_3', start_time: 120.0, end_time: 155.0, text: "And that's why the market is crashing right now.", title: "Market Analysis" }
];

export default function EditorPage() {
  const { savedFilename } = useParams();
  const navigate = useNavigate();
  const videoRef = useRef(null);
  
  const [activeClipId, setActiveClipId] = useState(MOCK_CLIPS[0].id);
  const [clips, setClips] = useState(MOCK_CLIPS);
  
  const activeClip = clips.find(c => c.id === activeClipId);

  // For the Zero-CPU Preview overlay box
  const [boxPosition, setBoxPosition] = useState({ x: 50, y: 50 }); // percentage
  const [trackingData, setTrackingData] = useState([]);
  const [videoWidth, setVideoWidth] = useState(1920);
  const [videoHeight, setVideoHeight] = useState(1080);
  const [videoDuration, setVideoDuration] = useState(300);
  const [currentVideoTime, setCurrentVideoTime] = useState(0);

  // Load the real AI tracking data directly from the generated recipe file
  useEffect(() => {
    if (mockRecipe) {
      if (mockRecipe.global_tracking) {
        setTrackingData(mockRecipe.global_tracking);
      }
    }
  }, []);

  const handleTimeUpdate = () => {
    if (!videoRef.current) return;
    const currentTime = videoRef.current.currentTime;
    setCurrentVideoTime(currentTime);
    
    if (trackingData.length === 0) return;
    
    // Find the active tracking block for this timestamp
    const currentBlock = trackingData.find(b => currentTime >= b.start_time_seconds && currentTime <= b.end_time_seconds);
    
    if (currentBlock) {
      let pX = (currentBlock.center_x_coordinate / videoWidth) * 100;
      let pY = (currentBlock.center_y_coordinate / videoHeight) * 100;
      setBoxPosition({ x: pX, y: pY });
    }
  };

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setVideoDuration(videoRef.current.duration);
      if (videoRef.current.videoWidth) setVideoWidth(videoRef.current.videoWidth);
      if (videoRef.current.videoHeight) setVideoHeight(videoRef.current.videoHeight);
    }
  };

  const handleNumberChange = (val, field) => {
    let num = parseFloat(val);
    if (isNaN(num)) num = 0;
    setClips(clips.map(c => c.id === activeClipId ? { ...c, [field]: num } : c));
    
    // Seek video to the new time so user can preview their cut
    if (videoRef.current) {
      videoRef.current.currentTime = num;
    }
  };

  const handleExport = () => {
    alert(`Ready for Milestone 5!\nExporting ${activeClip.title} from ${activeClip.start_time}s to ${activeClip.end_time}s`);
  };

  return (
    <div className="editor-page-root" style={{ padding: '2rem 3rem', minHeight: 'calc(100vh - 80px)', display: 'flex', flexDirection: 'column', boxSizing: 'border-box' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h2>Interactive Clip Editor <span style={{ color: '#00ffcc' }}>🎬</span></h2>
        <button className="btn-secondary" onClick={() => navigate('/')}>
          ⬅️ Back to Pipeline
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 350px', gap: '2rem', flex: 1, minHeight: 0 }}>
        
        {/* LEFT COLUMN: Zero-CPU Preview Player */}
        <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <h3 style={{ color: '#00ffcc', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="23 7 16 12 23 17 23 7"></polygon><rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect></svg>
            Zero-CPU Tracking Preview
          </h3>
          
          <div style={{ position: 'relative', width: '100%', backgroundColor: '#050505', borderRadius: '12px', overflow: 'hidden', display: 'inline-block' }}>
            <video 
              ref={videoRef}
              src={getFullVideoUrl(`/storage/uploads/${savedFilename}`)}
              controls
              onTimeUpdate={handleTimeUpdate}
              onLoadedMetadata={handleLoadedMetadata}
              style={{ width: '100%', maxHeight: '60vh', display: 'block' }}
            />
            
            {/* The 9:16 tracking overlay box */}
            <div style={{
              position: 'absolute',
              top: 0,
              height: '100%',
              aspectRatio: '9 / 16',
              border: '3px solid #00ffcc',
              boxShadow: '0 0 0 9999px rgba(0,0,0,0.6), inset 0 0 15px rgba(0, 255, 204, 0.3)',
              left: `${boxPosition.x}%`,
              transform: 'translateX(-50%)',
              pointerEvents: 'none',
              display: 'flex',
              flexDirection: 'column',
              padding: '10px'
            }}>
              <div style={{ background: 'rgba(0, 255, 204, 0.9)', color: '#000', fontSize: '0.7rem', padding: '2px 8px', borderRadius: '4px', alignSelf: 'flex-start', fontWeight: 'bold' }}>
                9:16 CROP AREA
              </div>
            </div>
          </div>
          
          {/* Scrollable Visual Timeline Bar */}
          <div style={{ marginTop: '1.5rem', width: '100%', overflowX: 'auto', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(0,0,0,0.5)' }}>
            <div 
              style={{ width: `${Math.max(100, videoDuration * 15)}px`, minWidth: '100%', height: '40px', position: 'relative', cursor: 'pointer', flexShrink: 0 }}
              onClick={(e) => {
                const rect = e.currentTarget.getBoundingClientRect();
                const percentage = (e.clientX - rect.left) / rect.width;
                if (videoRef.current) videoRef.current.currentTime = Math.max(0, Math.min(videoDuration, percentage * videoDuration));
              }}
            >
            {/* The active clip highlighted region */}
            <div style={{
              position: 'absolute',
              left: `${(activeClip.start_time / videoDuration) * 100}%`,
              width: `${((activeClip.end_time - activeClip.start_time) / videoDuration) * 100}%`,
              height: '100%',
              background: 'rgba(0, 255, 204, 0.3)',
              borderLeft: '2px solid #00ffcc',
              borderRight: '2px solid #00ffcc',
              pointerEvents: 'none',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <span style={{ color: '#00ffcc', fontSize: '0.8rem', fontWeight: 'bold', textShadow: '0 0 5px #000' }}>Active Clip</span>
            </div>
            
              {/* Playhead */}
              <div style={{
                position: 'absolute',
                left: `${(currentVideoTime / videoDuration) * 100}%`,
                top: 0,
                bottom: 0,
                width: '2px',
                backgroundColor: '#ff0055',
                boxShadow: '0 0 10px #ff0055',
                pointerEvents: 'none',
                zIndex: 10
              }} />
            </div>
          </div>

          <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem', flexShrink: 0 }}>
            <button className="btn-secondary" style={{ flex: 1, padding: '0.8rem', fontSize: '1rem', border: '1px solid rgba(0, 255, 204, 0.5)', color: '#00ffcc', fontWeight: 'bold' }} onClick={() => handleNumberChange(currentVideoTime, 'start_time')}>
               ⬅️ Set Start Here
            </button>
            <button className="btn-secondary" style={{ flex: 1, padding: '0.8rem', fontSize: '1rem', border: '1px solid rgba(0, 255, 204, 0.5)', color: '#00ffcc', fontWeight: 'bold' }} onClick={() => handleNumberChange(currentVideoTime, 'end_time')}>
               Set End Here ➡️
            </button>
          </div>

          <div style={{ marginTop: '0.5rem', display: 'flex', justifyContent: 'space-between', color: '#888', fontSize: '0.9rem', flexShrink: 0 }}>
            <span>Click timeline to jump. Use buttons to lock bounds.</span>
            <span>Video remains completely unedited on disk.</span>
          </div>
        </div>

        {/* RIGHT COLUMN: Clip Selector & Editor */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          
          {/* Active Clip Editor Panel */}
          <div className="glass-panel" style={{ padding: '1.5rem', flexShrink: 0 }}>
            <h3 style={{ color: '#fff', marginBottom: '1rem' }}>Editing: <span style={{ color: '#00ffcc' }}>{activeClip.title}</span></h3>
            
            <p style={{ color: '#aaa', fontSize: '0.95rem', fontStyle: 'italic', marginBottom: '1.5rem', background: 'rgba(0,0,0,0.3)', padding: '1rem', borderRadius: '8px' }}>
              "{activeClip.text}"
            </p>

            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{ display: 'block', color: '#ccc', marginBottom: '0.5rem' }}>
                Start Time (seconds)
              </label>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <button className="btn-secondary" style={{ padding: '0.5rem', flexShrink: 0, fontSize: '0.9rem' }} onClick={() => handleNumberChange(activeClip.start_time - 0.5, 'start_time')}>-0.5s</button>
                <input 
                  type="number" 
                  step="0.1" 
                  min="0"
                  value={activeClip.start_time} 
                  onChange={(e) => handleNumberChange(e.target.value, 'start_time')}
                  style={{ flex: 1, minWidth: 0, padding: '0.6rem', background: 'rgba(0,0,0,0.5)', border: '1px solid rgba(255,255,255,0.2)', color: '#00ffcc', borderRadius: '8px', fontSize: '1rem', textAlign: 'center', fontWeight: 'bold' }} 
                />
                <button className="btn-secondary" style={{ padding: '0.5rem', flexShrink: 0, fontSize: '0.9rem' }} onClick={() => handleNumberChange(activeClip.start_time + 0.5, 'start_time')}>+0.5s</button>
              </div>
            </div>

            <div style={{ marginBottom: '2rem' }}>
              <label style={{ display: 'block', color: '#ccc', marginBottom: '0.5rem' }}>
                End Time (seconds)
              </label>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <button className="btn-secondary" style={{ padding: '0.5rem', flexShrink: 0, fontSize: '0.9rem' }} onClick={() => handleNumberChange(activeClip.end_time - 0.5, 'end_time')}>-0.5s</button>
                <input 
                  type="number" 
                  step="0.1" 
                  min="0"
                  value={activeClip.end_time} 
                  onChange={(e) => handleNumberChange(e.target.value, 'end_time')}
                  style={{ flex: 1, minWidth: 0, padding: '0.6rem', background: 'rgba(0,0,0,0.5)', border: '1px solid rgba(255,255,255,0.2)', color: '#00ffcc', borderRadius: '8px', fontSize: '1rem', textAlign: 'center', fontWeight: 'bold' }} 
                />
                <button className="btn-secondary" style={{ padding: '0.5rem', flexShrink: 0, fontSize: '0.9rem' }} onClick={() => handleNumberChange(activeClip.end_time + 0.5, 'end_time')}>+0.5s</button>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '1.5rem' }}>
              <span style={{ color: '#888' }}>
                Duration: <strong>{(activeClip.end_time - activeClip.start_time).toFixed(1)}s</strong>
              </span>
              <button className="btn-primary" onClick={handleExport} style={{ padding: '0.6rem 1.2rem' }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '0.5rem', display: 'inline' }}><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                Export Clip
              </button>
            </div>
          </div>

          {/* Clips List */}
          <div className="glass-panel" style={{ padding: '1.5rem', flex: 1, overflowY: 'auto' }}>
            <h3 style={{ color: '#fff', marginBottom: '1rem', fontSize: '1.1rem' }}>Generated Clips</h3>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
              {clips.map(clip => (
                <div 
                  key={clip.id} 
                  onClick={() => setActiveClipId(clip.id)}
                  style={{ 
                    padding: '1rem', 
                    background: activeClipId === clip.id ? 'rgba(0, 255, 204, 0.1)' : 'rgba(255,255,255,0.03)', 
                    border: `1px solid ${activeClipId === clip.id ? '#00ffcc' : 'rgba(255,255,255,0.1)'}`,
                    borderRadius: '8px',
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                    <strong style={{ color: activeClipId === clip.id ? '#00ffcc' : '#eee' }}>{clip.title}</strong>
                    <span style={{ color: '#888', fontSize: '0.85rem' }}>{(clip.end_time - clip.start_time).toFixed(1)}s</span>
                  </div>
                  <div style={{ color: '#aaa', fontSize: '0.85rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {clip.text}
                  </div>
                </div>
              ))}
            </div>
          </div>
          
        </div>
      </div>
    </div>
  );
}
