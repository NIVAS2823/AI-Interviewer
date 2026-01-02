// src/utils/voice-interview/constants.js

export const RECORDING_CONSTANTS = {
  MAX_ANSWER_DURATION: 90, // seconds
  WARNING_TIME: 20, // show warning at this time
  AUTO_START_DELAY: 400, // delay after AI speaks
  GREETING_ACK_DELAY: 1200, // delay for greeting acknowledgment
};

export const CONNECTION_STATUS = {
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  ERROR: 'error',
  DISCONNECTED: 'disconnected',
};

export const MESSAGE_TYPES = {
  GREETING: 'greeting',
  QUESTION: 'question',
  ACKNOWLEDGMENT: 'acknowledgment',
  CLOSING: 'closing',
  TRANSCRIPTION: 'transcription',
  METADATA: 'metadata',
  INTERVIEW_COMPLETE: 'interview_complete',
  ERROR: 'error',
};

export const INTERVIEW_STATUS = {
  CREATED: 'created',
  IN_PROGRESS: 'in_progress',
  COMPLETED: 'completed',
};

export const PROCESSING_MESSAGES = {
  INITIAL: 'Processing your answer...',
  TRANSCRIBING: 'Transcribing your answer...',
  LONG_WAIT: 'This is taking longer than usual, please wait...',
};

export const PROCESSING_TIMEOUTS = {
  TRANSCRIBING: 5000,
  LONG_WAIT: 15000,
};