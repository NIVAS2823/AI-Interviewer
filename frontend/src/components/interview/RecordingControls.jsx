// src/components/interview/RecordingControls.jsx
import React from "react";
import { Mic, MicOff } from "lucide-react";

export function RecordingControls({
  isListening,
  isSpeaking,
  isProcessing,
  processingMessage,
  recordingTimeLeft,
  questionProgress,
  onStartListening,
  onStopListening,
}) {
  const currentCount = questionProgress.current || 0;
  const maxCount = questionProgress.total || 0;

  const getStatusMessage = () => {
    if (isProcessing) return processingMessage || "Processing your answer...";
    if (isListening) return "Recording... Click mic to stop";
    if (isSpeaking) return "AI is speaking...";
    return "Click mic to answer";
  };

  return (
    <div className="border-t border-gray-700 p-4 shrink-0 bg-darkbg-card">
      <div className="flex items-center justify-between max-w-4xl mx-auto">
        <div className="hidden md:flex items-center gap-4 text-sm text-gray-400">
          <span>Press the mic to answer</span>
          <span className="px-2 py-1 rounded bg-white/5">
            Auto-stop at 90s + send
          </span>
        </div>

        <div className="flex items-center gap-4">
          {/* Mic toggle */}
          {isListening ? (
            <button
              onClick={onStopListening}
              className="w-16 h-16 rounded-full bg-red-600 hover:bg-red-700 flex items-center justify-center shadow-lg transition-all animate-pulse"
              aria-label="Stop recording"
            >
              <MicOff className="w-6 h-6 text-white" />
            </button>
          ) : (
            <button
              onClick={onStartListening}
              disabled={isSpeaking || isProcessing}
              className="w-16 h-16 rounded-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed flex items-center justify-center shadow-lg transition-all"
              aria-label="Start recording"
            >
              <Mic className="w-6 h-6 text-white" />
            </button>
          )}

          {/* Recording timer */}
          {isListening && (
            <div className="flex items-center gap-2 ml-2 text-sm">
              <div className="animate-pulse h-3 w-3 bg-red-500 rounded-full" />
              <span className="text-gray-300">Recording</span>
              <span
                className={`ml-1 ${
                  recordingTimeLeft <= 10
                    ? "text-red-400 font-bold"
                    : "text-gray-300"
                }`}
              >
                {recordingTimeLeft}s
              </span>
            </div>
          )}

          {/* Progress */}
          <div className="text-right ml-4">
            <div className="text-xs text-gray-400">Question</div>
            <div className="text-sm font-medium">
              {currentCount} / {maxCount}
            </div>
          </div>
        </div>
      </div>

      <p className="text-center text-gray-500 text-xs mt-3">
        {getStatusMessage()}
      </p>
    </div>
  );
}