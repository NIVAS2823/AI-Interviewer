// src/components/interview/MessageDisplay.jsx
import React from "react";

export function MessageDisplay({ 
  currentMessage, 
  transcript, 
  interimTranscript,
  isListening 
}) {
  return (
    <>
      {/* Current Message from AI */}
      {currentMessage ? (
        <div className="max-w-2xl bg-gray-700 rounded-2xl p-6 mb-4">
          <p className="text-gray-200 text-lg leading-relaxed">
            {currentMessage}
          </p>
        </div>
      ) : (
        <div className="max-w-2xl text-center text-gray-400 mb-4">
          Waiting for the interviewer...
        </div>
      )}

      {/* ✅ ENHANCED: Interim Transcript (while speaking) - BIGGER & MORE PROMINENT */}
      {isListening && interimTranscript && (
        <div className="mt-4 max-w-3xl bg-gradient-to-br from-blue-900/40 to-blue-800/30 rounded-3xl p-8 border-2 border-blue-500/50 shadow-2xl shadow-blue-500/20 backdrop-blur-sm">
          <div className="flex items-start gap-4">
            {/* Animated microphone icon */}
            <div className="flex-shrink-0">
              <div className="w-12 h-12 bg-blue-500/20 rounded-full flex items-center justify-center border-2 border-blue-400/50">
                <svg 
                  className="w-6 h-6 text-blue-400 animate-pulse" 
                  fill="currentColor" 
                  viewBox="0 0 20 20"
                >
                  <path 
                    fillRule="evenodd" 
                    d="M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4zm4 10.93A7.001 7.001 0 0017 8a1 1 0 10-2 0A5 5 0 015 8a1 1 0 00-2 0 7.001 7.001 0 006 6.93V17H6a1 1 0 100 2h8a1 1 0 100-2h-3v-2.07z" 
                    clipRule="evenodd" 
                  />
                </svg>
              </div>
            </div>

            {/* Transcript text */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-blue-400 font-semibold text-sm uppercase tracking-wider">
                  Speaking
                </span>
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-blue-400 rounded-full animate-pulse"></span>
                  <span className="w-2 h-2 bg-blue-400 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></span>
                  <span className="w-2 h-2 bg-blue-400 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></span>
                </div>
              </div>
              
              <p className="text-blue-100 text-xl leading-relaxed font-medium">
                {interimTranscript}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ✅ ENHANCED: Empty State (while listening but no transcript yet) */}
      {isListening && !interimTranscript && (
        <div className="mt-4 max-w-3xl bg-gradient-to-br from-blue-900/20 to-blue-800/10 rounded-3xl p-8 border-2 border-blue-500/30 border-dashed">
          <div className="flex items-center justify-center gap-3 text-blue-400/60">
            <svg 
              className="w-8 h-8 animate-pulse" 
              fill="currentColor" 
              viewBox="0 0 20 20"
            >
              <path 
                fillRule="evenodd" 
                d="M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4zm4 10.93A7.001 7.001 0 0017 8a1 1 0 10-2 0A5 5 0 015 8a1 1 0 00-2 0 7.001 7.001 0 006 6.93V17H6a1 1 0 100 2h8a1 1 0 100-2h-3v-2.07z" 
                clipRule="evenodd" 
              />
            </svg>
            <span className="text-lg italic">Listening... start speaking</span>
          </div>
        </div>
      )}

      {/* User's Final Transcript (after recording stops) */}
      {transcript && !isListening && (
        <div className="mt-4 max-w-3xl bg-gradient-to-br from-green-900/20 to-emerald-800/10 rounded-2xl p-6 border border-green-500/30 shadow-lg">
          <div className="flex items-start gap-3">
            {/* Checkmark icon */}
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-green-500/20 rounded-full flex items-center justify-center">
                <svg 
                  className="w-5 h-5 text-green-400" 
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24"
                >
                  <path 
                    strokeLinecap="round" 
                    strokeLinejoin="round" 
                    strokeWidth={2} 
                    d="M5 13l4 4L19 7" 
                  />
                </svg>
              </div>
            </div>

            {/* Transcript text */}
            <div className="flex-1 min-w-0">
              <p className="text-green-400 text-xs font-semibold uppercase tracking-wider mb-2">
                Your Answer:
              </p>
              <p className="text-green-100 text-base leading-relaxed">
                {transcript}
              </p>
            </div>
          </div>
        </div>
      )}
    </>
  );
}