import { apiClient } from './apiClient';

/**
 * Triggers the AI segmentation and tracking pipeline.
 * Now starts a background task on the backend to prevent browser connection timeouts.
 * @param {string} savedFilename - The exact filename on the backend.
 * @param {object} segmentationOptions - Segmentation options.
 * @param {object} trackingOptions - Tracking options.
 * @param {boolean} skipSegmentation - Whether to bypass the segmentation step.
 * @returns {Promise<any>}
 */
export async function runAiPipeline(savedFilename, segmentationOptions, trackingOptions, skipSegmentation = false) {
  const response = await apiClient.post('/api/v1/pipeline/process', {
    saved_filename: savedFilename,
    skip_segmentation: skipSegmentation,
    segmentation_options: segmentationOptions,
    tracking_options: trackingOptions
  });
  return response.data;
}

/**
 * Polls the backend for the real-time progress of a video processing job.
 * @param {string} savedFilename - The exact filename on the backend.
 * @returns {Promise<{step: string, progress: number, result?: any, error_detail?: string}>}
 */
export async function getPipelineProgress(savedFilename) {
  const response = await apiClient.get(`/api/v1/pipeline/progress/${encodeURIComponent(savedFilename)}`);
  return response.data;
}
