import React, { useState, useRef } from 'react';
import { AudioRecorder, AudioPlayer } from '../lib/audioUtils';
import { Mic, Square, Play } from 'lucide-react';

export default function TestAudio() {
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [status, setStatus] = useState('');

  const recorderRef = useRef(null);
  const playerRef = useRef(new AudioPlayer());

  const handleStartRecording = async () => {
    try {
      setStatus('🎤 Initializing microphone...');

      // Initialize recorder
      if (!recorderRef.current) {
        recorderRef.current = new AudioRecorder();
        const success = await recorderRef.current.initialize();

        if (!success) {
          setStatus('❌ Microphone access denied');
          return;
        }
      }

      // Start recording
      await recorderRef.current.startRecording();
      setIsRecording(true);
      setStatus('🔴 Recording... Speak now!');
    } catch (error) {
      console.error('Recording error:', error);
      setStatus(`❌ Error: ${error.message}`);
    }
  };

  const handleStopRecording = async () => {
    try {
      setStatus('⏹️ Stopping recording...');

      const blob = await recorderRef.current.stopRecording();

      if (blob) {
        setAudioBlob(blob);
        setStatus(`✅ Recorded ${(blob.size / 1024).toFixed(2)} KB`);
      }

      setIsRecording(false);
    } catch (error) {
      console.error('Stop error:', error);
      setStatus(`❌ Error: ${error.message}`);
    }
  };

  const handlePlayback = async () => {
    if (!audioBlob) return;

    try {
      setStatus('▶️ Playing recording...');

      // Create audio URL and play
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);

      audio.onended = () => {
        setStatus('✅ Playback complete');
        URL.revokeObjectURL(audioUrl);
      };

      await audio.play();
    } catch (error) {
      console.error('Playback error:', error);
      setStatus(`❌ Playback error: ${error.message}`);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center p-6">
      <div className="max-w-md w-full bg-gray-800 rounded-2xl p-8 shadow-2xl">
        <h1 className="text-2xl font-bold text-white mb-6 text-center">
          🎤 Audio Test
        </h1>

        {/* Status */}
        <div className="bg-gray-700 rounded-lg p-4 mb-6">
          <p className="text-gray-300 text-sm text-center">{status || 'Ready'}</p>
        </div>

        {/* Controls */}
        <div className="space-y-4">
          {/* Record Button */}
          {!isRecording ? (
            <button
              onClick={handleStartRecording}
              className="w-full bg-red-600 hover:bg-red-700 text-white py-4 rounded-lg font-semibold flex items-center justify-center space-x-2 transition-colors"
            >
              <Mic className="w-5 h-5" />
              <span>Start Recording</span>
            </button>
          ) : (
            <button
              onClick={handleStopRecording}
              className="w-full bg-gray-600 hover:bg-gray-700 text-white py-4 rounded-lg font-semibold flex items-center justify-center space-x-2 transition-colors animate-pulse"
            >
              <Square className="w-5 h-5" />
              <span>Stop Recording</span>
            </button>
          )}

          {/* Playback Button */}
          {audioBlob && (
            <button
              onClick={handlePlayback}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white py-4 rounded-lg font-semibold flex items-center justify-center space-x-2 transition-colors"
            >
              <Play className="w-5 h-5" />
              <span>Play Recording</span>
            </button>
          )}
        </div>

        {/* Instructions */}
        <div className="mt-6 p-4 bg-blue-900 bg-opacity-30 rounded-lg border border-blue-700">
          <p className="text-blue-200 text-sm">
            <strong>Test Steps:</strong>
          </p>
          <ol className="text-blue-200 text-sm mt-2 space-y-1 list-decimal list-inside">
            <li>Click "Start Recording"</li>
            <li>Allow microphone access</li>
            <li>Speak for a few seconds</li>
            <li>Click "Stop Recording"</li>
            <li>Click "Play Recording" to hear it</li>
          </ol>
        </div>
      </div>
    </div>
  );
}