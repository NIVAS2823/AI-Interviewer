// src/utils/voice-interview/formatters.js

/**
 * Formats seconds into MM:SS format
 * @param {number} seconds - The number of seconds
 * @returns {string} Formatted time string (e.g., "1:05")
 */
export const formatTime = (seconds) => {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
};

/**
 * Formats interview type by replacing underscores with spaces
 * @param {string} type - Interview type (e.g., "technical_interview")
 * @returns {string} Formatted type (e.g., "technical interview")
 */
export const formatInterviewType = (type) => {
  return type?.replace(/_/g, ' ') || 'Interview';
};

/**
 * Calculates progress percentage
 * @param {number} current - Current question number
 * @param {number} total - Total number of questions
 * @returns {number} Progress percentage (0-100)
 */
export const calculateProgress = (current, total) => {
  if (!total || total === 0) return 0;
  return Math.round((current / total) * 100);
};