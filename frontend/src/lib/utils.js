import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

// Merge tailwind classes
export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

// Format date
export function formatDate(date) {
  return new Date(date).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

// Format datetime
export function formatDateTime(date) {
  return new Date(date).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

// Format duration
export function formatDuration(minutes) {
  if (minutes < 60) {
    return `${minutes} min`;
  }
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${hours}h ${mins}m`;
}

// Get score color
export function getScoreColor(score) {
  if (score >= 80) return 'text-green-600';
  if (score >= 60) return 'text-yellow-600';
  return 'text-red-600';
}

// Get score background color
export function getScoreBgColor(score) {
  if (score >= 80) return 'bg-green-100';
  if (score >= 60) return 'bg-yellow-100';
  return 'bg-red-100';
}

// Truncate text
export function truncate(text, length = 100) {
  if (text.length <= length) return text;
  return text.substring(0, length) + '...';
}