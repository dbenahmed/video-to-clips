import { apiClient, BACKEND_URL } from './apiClient';

/**
 * Uploads a local video file with upload progress tracking.
 * @param {File} file - The selected video file.
 * @param {(progressPercent: number) => void} onProgress - Optional callback for upload progress.
 * @returns {Promise<any>}
 */
export async function uploadVideoFile(file, onProgress) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiClient.post('/api/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (progressEvent) => {
      if (onProgress && progressEvent.total) {
        const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(percent);
      }
    },
  });

  return response.data;
}

/**
 * Triggers a YouTube video download via yt-dlp on the backend.
 * @param {string} url - Valid YouTube URL.
 * @returns {Promise<any>}
 */
export async function downloadYouTubeVideo(url) {
  const response = await apiClient.post('/api/download-youtube', { url });
  return response.data;
}

/**
 * Resolves a relative static storage URL from the backend into a fully qualified URL.
 * @param {string} relativeUrl - e.g. "/storage/uploads/xyz.mp4"
 * @returns {string} Fully qualified stream URL
 */
export function getFullVideoUrl(relativeUrl) {
  if (!relativeUrl) return '';
  if (relativeUrl.startsWith('http://') || relativeUrl.startsWith('https://')) {
    return relativeUrl;
  }
  return `${BACKEND_URL}${relativeUrl.startsWith('/') ? '' : '/'}${relativeUrl}`;
}
