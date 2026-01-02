// src/utils/voice-interview/validators.js

import { INTERVIEW_STATUS } from './constants';

/**
 * Validates if an audio blob is valid and has content
 * @param {Blob} blob - Audio blob to validate
 * @returns {boolean} True if valid, false otherwise
 */
export const validateAudioBlob = (blob) => {
  return blob && blob.size > 0;
};

/**
 * Validates if interview status is a valid status
 * @param {string} status - Status to validate
 * @returns {boolean} True if valid, false otherwise
 */
export const validateInterviewStatus = (status) => {
  return Object.values(INTERVIEW_STATUS).includes(status);
};

/**
 * Checks if recording can be started based on current states
 * @param {boolean} isListening - Whether currently listening
 * @param {boolean} isSpeaking - Whether AI is speaking
 * @param {boolean} isProcessing - Whether processing audio
 * @returns {boolean} True if can start recording
 */
export const canStartRecording = (isListening, isSpeaking, isProcessing) => {
  return !isListening && !isSpeaking && !isProcessing;
};