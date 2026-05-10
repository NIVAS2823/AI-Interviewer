import axios from 'axios';
import toast from 'react-hot-toast';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Create axios instance
const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 seconds
});

// Request interceptor - add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor - handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // Server responded with error
      const message = error.response.data?.detail || 'An error occurred';
      
      if (error.response.status === 401) {
        // Unauthorized - clear token and redirect to login
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '/login';
        toast.error('Session expired. Please login again.');
      } else if (error.response.status === 404) {
        toast.error('Resource not found');
      } else if (error.response.status === 500) {
        toast.error('Server error. Please try again later.');
      } else {
        toast.error(message);
      }
    } else if (error.request) {
      // Request made but no response
      toast.error('Cannot connect to server. Please check your connection.');
    } else {
      // Something else happened
      toast.error('An unexpected error occurred');
    }
    
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  getCurrentUser: () => api.get('/auth/me'),
};

// Resume API
export const resumeAPI = {
  upload: (file, onProgress) => {
    const formData = new FormData();
    formData.append('file', file);
    
    return api.post('/resume/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          onProgress(percentCompleted);
        }
      },
    });
  },
  list: () => api.get('/resume/'),
  get: (id) => api.get(`/resume/${id}`),
  delete: (id) => api.delete(`/resume/${id}`),
  parse: (id) => api.post(`/resume/${id}/parse`), // Trigger parsing
};

// Interview API
export const interviewAPI = {
  create: (data) => api.post('/interview/create', data),
  list: () => api.get('/interview/'),
  get: (id) => api.get(`/interview/${id}`),
  start: (id) => api.post(`/interview/${id}/start`),
  end: (id, reason = 'completed') => api.post(`/interview/${id}/end`, { reason }),
  sendMessage: (id, text) => api.post(`/interview/${id}/message`, { text }),
  simulate: (id) => api.post(`/interview/${id}/simulate`),
  delete: (id) => api.delete(`/interview/${id}`),
};

// Evaluation API
export const evaluationAPI = {
  get: (interviewId) => api.get(`/evaluation/${interviewId}`),
  evaluateAnswer: (data) => api.post('/evaluation/evaluate-answer', data),
};

// Health check
export const healthAPI = {
  check: () => api.get('/health'),
};

export default api;