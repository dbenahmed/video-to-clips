import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { runAiPipeline, getPipelineProgress, cancelPipeline } from '../services/pipelineApi';

export default function PipelineOptionsPage() {
  const { savedFilename } = useParams();
  const navigate = useNavigate();

  const [isProcessing, setIsProcessing] = useState(false);
  const [progressData, setProgressData] = useState({ step: 'waiting', progress: 0.0 });
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [skipSegmentation, setSkipSegmentation] = useState(false);

  // Reference to prevent memory leaks in polling
  const pollingIntervalRef = useRef(null);

  // Default AI Configuration Models
  const [segOptions, setSegOptions] = useState({
    similarity_drop_threshold: 0.2,
    min_clip_duration_seconds: 30.0,
    max_clip_duration_seconds: 60.0,
    whisper_model_size: 'tiny' // Default to tiny for fastest CPU evaluation
  });

  const [trackOptions, setTrackOptions] = useState({
    target_frames_per_second: 1,
    pixel_movement_threshold: 50
  });

  // Check background tasks cache on mount (Refresh Recovery)
  useEffect(() => {
    const checkExistingJob = async () => {
      try {
        const data = await getPipelineProgress(savedFilename);
        // If the task exists in the backend cache and is actively crunching
        if (data && data.step !== 'waiting' && data.step !== 'completed' && data.step !== 'error') {
          setProgressData(data);
          setIsProcessing(true); // Instantly snap UI back to Loading View
        } else if (data && data.step === 'completed' && data.result) {
          // If the user refreshes after it finished, we can just show them the results instantly!
          setResults(data.result);
        }
      } catch (err) {
        console.error("Failed to check existing job status:", err);
      }
    };
    checkExistingJob();
  }, [savedFilename]);

  // Progress Polling Effect
  useEffect(() => {
    if (isProcessing) {
      pollingIntervalRef.current = setInterval(async () => {
        try {
          const data = await getPipelineProgress(savedFilename);
          setProgressData(data);

          if (data.step === 'completed' && data.result) {
            setResults(data.result);
            setIsProcessing(false);
          } else if (data.step === 'error') {
            setError(data.error_detail || 'An unknown error occurred during AI processing.');
            setIsProcessing(false);
          }
        } catch (err) {
          console.error("Failed to fetch progress", err);
        }
      }, 5000);
    } else {
      if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
    }

    return () => {
      if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
    };
  }, [isProcessing, savedFilename]);

  const handleStartPipeline = async () => {
    try {
      setIsProcessing(true);
      setError(null);
      setProgressData({ step: 'queued', progress: 0.0 });
      // Triggers the background task (returns instantly)
      await runAiPipeline(savedFilename, segOptions, trackOptions, skipSegmentation);
      // The polling loop will now take over and wait for step === 'completed'
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
      setIsProcessing(false);
    }
  };

  const handleCancelPipeline = async () => {
    try {
      await cancelPipeline(savedFilename);
      setIsProcessing(false);
      setProgressData({ step: 'waiting', progress: 0.0 });
      if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
    } catch (err) {
      console.error("Failed to cancel job", err);
    }
  };

  // -------------------------------------------------------------------------
  // VIEW 1: RESULTS VIEW
  // -------------------------------------------------------------------------
  if (results) {
    return (
      <div>
        <div className="page-header">
          <h1 className="page-title" style={{ color: '#00ffcc' }}>✨ Pipeline Complete!</h1>
          <p className="page-subtitle">Extracted {results.extracted_clips?.length || 0} viral clips.</p>
        </div>
        <div className="glass-panel" style={{ padding: '2rem' }}>
          <h3>Extracted Golden Clips</h3>
          <div style={{ display: 'grid', gap: '1rem', marginTop: '1.5rem' }}>
            {results.extracted_clips.length === 0 ? (
              <p style={{ color: '#aaa' }}>No clips could be extracted using the current configuration. Try lowering the minimum clip duration or adjusting the similarity threshold.</p>
            ) : (
              results.extracted_clips.map(clip => (
                <div key={clip.clip_id} style={{ padding: '1.5rem', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                    <strong style={{ color: '#00ffcc', fontSize: '1.2rem' }}>{clip.duration_seconds.toFixed(1)}s</strong>
                    <span style={{ background: 'rgba(0, 255, 204, 0.1)', color: '#00ffcc', padding: '0.2rem 0.6rem', borderRadius: '12px', fontSize: '0.8rem' }}>
                      {clip.extraction_reasoning}
                    </span>
                  </div>
                  <p style={{ color: '#eee', fontSize: '1.05rem', lineHeight: '1.5' }}>"{clip.text_transcript}"</p>
                </div>
              ))
            )}
          </div>
          <div style={{ marginTop: '2rem', display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
            <button className="btn-primary" onClick={() => navigate(`/editor/${encodeURIComponent(savedFilename)}`)}>
              Proceed to Video Editor 🎬
            </button>
            <button className="btn-secondary" onClick={() => setResults(null)}>
              ⚙️ Tweak Settings & Re-run
            </button>
            <button className="btn-secondary" onClick={() => navigate('/')} style={{ background: 'transparent', border: '1px solid rgba(255,255,255,0.2)' }}>
              Upload New Video
            </button>
          </div>
        </div>
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // VIEW 2: LOADING VIEW
  // -------------------------------------------------------------------------
  if (isProcessing) {
    const isTracking = progressData.step === 'tracking';
    const isSegmentation = progressData.step === 'segmentation';

    return (
      <div>
        <div className="glass-panel" style={{ padding: '6rem 2rem', textAlign: 'center' }}>
          <div className="spinner" style={{ margin: '0 auto 2rem auto', width: '60px', height: '60px', border: '5px solid rgba(255,255,255,0.1)', borderTopColor: '#00ffcc', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></div>

          <h2 style={{ color: '#00ffcc', marginBottom: '1rem' }}>
            {progressData.step === 'initializing' && "Initializing Pipeline..."}
            {isTracking && "Running Hybrid Subject Tracking..."}
            {isSegmentation && "Running Semantic Segmentation..."}
            {progressData.step === 'completed' && "Finalizing Results..."}
            {progressData.step === 'waiting' && "AI is Analyzing Video..."}
          </h2>

          {/* Progress Bar Container */}
          <div style={{ maxWidth: '400px', margin: '2rem auto', background: 'rgba(0,0,0,0.5)', borderRadius: '20px', height: '24px', overflow: 'hidden', border: '1px solid rgba(255,255,255,0.1)' }}>
            <div style={{
              width: `${progressData.progress}%`,
              height: '100%',
              background: 'linear-gradient(90deg, #00ffcc, #00b3ff)',
              transition: 'width 0.5s ease-out'
            }}></div>
          </div>

          <p style={{ color: '#fff', fontSize: '1.2rem', fontWeight: 'bold' }}>
            {progressData.progress.toFixed(1)}%
          </p>

          <div style={{ marginTop: '2rem', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1.5rem' }}>
            <div style={{ 
              padding: '1rem', borderRadius: '8px', display: 'inline-block', border: '1px solid',
              ...(progressData.hardware === 'gpu' 
                  ? { background: 'rgba(0,255,204,0.1)', color: '#00ffcc', borderColor: 'rgba(0,255,204,0.3)' }
                  : { background: 'rgba(255,165,0,0.1)', color: '#ffa500', borderColor: 'rgba(255,165,0,0.2)' }
              )}}>
              {!progressData.hardware ? "🔍 Detecting available hardware..." 
                : progressData.hardware === 'gpu' 
                  ? "🚀 Hardware Acceleration ENABLED. Processing with NVIDIA CUDA/GPU."
                  : "⚠️ Hardware Acceleration UNAVAILABLE. Processing with CPU fallback. Please allow several minutes."
              }
            </div>

            <button 
              onClick={handleCancelPipeline} 
              style={{
                background: 'rgba(255, 50, 50, 0.1)',
                color: '#ff4d4d',
                border: '1px solid rgba(255, 50, 50, 0.3)',
                padding: '0.8rem 1.5rem',
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '1rem',
                transition: 'background 0.2s',
                fontWeight: 'bold'
              }}
              onMouseOver={(e) => e.target.style.background = 'rgba(255, 50, 50, 0.2)'}
              onMouseOut={(e) => e.target.style.background = 'rgba(255, 50, 50, 0.1)'}
            >
              🛑 Cancel Analysis
            </button>
          </div>
          <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
        </div>
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // VIEW 3: CONFIGURATION VIEW
  // -------------------------------------------------------------------------
  return (
    <div>
      <div className="page-header">
        <div className="page-badge">
          <span>⚙️ Milestone 3</span>
          <span>•</span>
          <span>AI Configuration</span>
        </div>
        <h1 className="page-title">Configure AI Pipeline</h1>
        <p className="page-subtitle">File: <code style={{ color: '#00ffcc' }}>{savedFilename}</code></p>
      </div>

      <div className="glass-panel" style={{ padding: '2.5rem' }}>
        {error && (
          <div style={{ padding: '1.5rem', background: 'rgba(255, 50, 50, 0.1)', color: '#ff6b6b', borderRadius: '8px', marginBottom: '2rem', border: '1px solid rgba(255, 50, 50, 0.3)' }}>
            <strong>Error:</strong> {error}
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '3rem' }}>
          {/* SEGMENTATION CONFIG */}
          <div style={{ opacity: skipSegmentation ? 0.4 : 1, transition: 'opacity 0.3s', pointerEvents: skipSegmentation ? 'none' : 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '0.8rem' }}>
              <h3 style={{ color: '#00ffcc', display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>
                Segmentation Options
              </h3>
            </div>

            <div style={{ marginBottom: '2rem' }}>
              <label style={{ display: 'block', marginBottom: '0.8rem', color: '#eee', fontWeight: 'bold' }}>Similarity Drop Threshold: <span style={{ color: '#00ffcc' }}>{segOptions.similarity_drop_threshold}</span></label>
              <input type="range" min="0.1" max="0.5" step="0.05" value={segOptions.similarity_drop_threshold} onChange={e => setSegOptions({ ...segOptions, similarity_drop_threshold: parseFloat(e.target.value) })} style={{ width: '100%', cursor: 'pointer' }} />
              <small style={{ color: '#888', display: 'block', marginTop: '0.5rem' }}>Lower cuts less often (longer clips). Higher cuts more aggressively.</small>
            </div>

            <div style={{ marginBottom: '2rem', display: 'flex', gap: '1.5rem' }}>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', marginBottom: '0.8rem', color: '#eee', fontWeight: 'bold' }}>Min Length (s)</label>
                <input type="number" value={segOptions.min_clip_duration_seconds} onChange={e => setSegOptions({ ...segOptions, min_clip_duration_seconds: parseFloat(e.target.value) })} style={{ width: '100%', padding: '0.8rem', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', borderRadius: '8px' }} />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', marginBottom: '0.8rem', color: '#eee', fontWeight: 'bold' }}>Max Length (s)</label>
                <input type="number" value={segOptions.max_clip_duration_seconds} onChange={e => setSegOptions({ ...segOptions, max_clip_duration_seconds: parseFloat(e.target.value) })} style={{ width: '100%', padding: '0.8rem', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', borderRadius: '8px' }} />
              </div>
            </div>

            <div style={{ marginBottom: '2rem' }}>
              <label style={{ display: 'block', marginBottom: '0.8rem', color: '#eee', fontWeight: 'bold' }}>Whisper Model Size</label>
              <select value={segOptions.whisper_model_size} onChange={e => setSegOptions({ ...segOptions, whisper_model_size: e.target.value })} style={{ width: '100%', padding: '0.8rem', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', borderRadius: '8px', appearance: 'none', cursor: 'pointer' }}>
                <option value="tiny">Tiny (Fastest, least accurate)</option>
                <option value="base">Base (Recommended balance)</option>
                <option value="small">Small</option>
                <option value="medium">Medium</option>
              </select>
              <small style={{ color: '#888', display: 'block', marginTop: '0.5rem' }}>For better results, use the <strong>Base</strong> model, but note that it takes significantly more processing time on a CPU.</small>
            </div>
          </div>

          {/* TRACKING CONFIG */}
          <div>
            <h3 style={{ color: '#00ffcc', marginBottom: '1.5rem', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
              Tracking Options
            </h3>

            <div style={{ marginBottom: '2rem' }}>
              <label style={{ display: 'block', marginBottom: '0.8rem', color: '#eee', fontWeight: 'bold' }}>Target FPS: <span style={{ color: '#00ffcc' }}>{trackOptions.target_frames_per_second}</span></label>
              <input type="range" min="1" max="15" step="1" value={trackOptions.target_frames_per_second} onChange={e => setTrackOptions({ ...trackOptions, target_frames_per_second: parseInt(e.target.value) })} style={{ width: '100%', cursor: 'pointer' }} />
              <small style={{ color: '#888', display: 'block', marginTop: '0.5rem' }}>Higher FPS = smoother camera panning, but significantly increases processing time.</small>
            </div>

            <div style={{ marginBottom: '2rem' }}>
              <label style={{ display: 'block', marginBottom: '0.8rem', color: '#eee', fontWeight: 'bold' }}>Pixel Movement Threshold</label>
              <input type="number" value={trackOptions.pixel_movement_threshold} onChange={e => setTrackOptions({ ...trackOptions, pixel_movement_threshold: parseInt(e.target.value) })} style={{ width: '100%', padding: '0.8rem', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', borderRadius: '8px' }} />
              <small style={{ color: '#888', display: 'block', marginTop: '0.5rem' }}>Amount of pixels the subject must move before the virtual camera reframes to follow them.</small>
            </div>
          </div>
        </div>

        <div style={{ marginTop: '3rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '2rem' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.8rem', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={skipSegmentation}
              onChange={(e) => setSkipSegmentation(e.target.checked)}
              style={{ width: '20px', height: '20px', accentColor: '#00ffcc' }}
            />
            <span style={{ color: '#fff', fontSize: '1.1rem' }}>Skip Semantic Segmentation (Tracking Only)</span>
          </label>

          <button className="btn-primary" onClick={handleStartPipeline} style={{ padding: '1rem 2.5rem', fontSize: '1.1rem' }}>
            <span style={{ marginRight: '0.5rem' }}>🚀</span> Start AI Analysis
          </button>
        </div>
      </div>
    </div>
  );
}
