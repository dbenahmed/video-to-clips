import axios from 'axios';

// Backend base URL (can be customized via Vite environment variables if needed)
export const BACKEND_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export const apiClient = axios.create({
  baseURL: BACKEND_URL,
  timeout: 600000, // 10 minutes timeout for heavy video uploads/downloads
});

/**
 * Checks connectivity with the FastAPI backend.
 * @returns {Promise<{ online: boolean, message?: string }>}
 */
export async function checkBackendHealth() {
  try {
    const response = await apiClient.get('/api/test');
    return { online: true, message: response.data.message };
  } catch (error) {
    console.warn('Backend health check failed:', error.message);
    return { online: false, message: error.message };
  }
}
