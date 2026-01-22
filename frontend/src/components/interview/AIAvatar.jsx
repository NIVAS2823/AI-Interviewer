// src/components/interview/AIAvatar.jsx
import React from "react";
import { Volume2, Mic } from "lucide-react";

export function AIAvatar({ isSpeaking, isListening, connectionStatus }) {
  return (
    <div className="flex flex-col items-center space-y-3">
      {/* Avatar */}
      <div
        className={`w-28 h-28 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 
        flex items-center justify-center transition-all duration-300
        ${
          isSpeaking
            ? "scale-105 shadow-lg shadow-blue-500/40"
            : "scale-100"
        }`}
      >
        <span className="text-4xl">🎤</span>
      </div>

      {/* Status */}
      <div className="text-center">
        <h2 className="text-lg font-semibold text-white">
          Sarah · AI Interviewer
        </h2>

        {isSpeaking && (
          <div className="flex items-center justify-center gap-1 text-blue-400 text-sm mt-1">
            <Volume2 className="w-4 h-4 animate-pulse" />
            <span>Speaking</span>
          </div>
        )}

        {isListening && (
          <div className="flex items-center justify-center gap-1 text-green-400 text-sm mt-1">
            <Mic className="w-4 h-4 animate-pulse" />
            <span>Listening</span>
          </div>
        )}

        {!isSpeaking && !isListening && (
          <div className="text-gray-400 text-sm mt-1">
            {connectionStatus === "connected"
              ? "Ready"
              : connectionStatus === "connecting"
              ? "Connecting..."
              : "Reconnecting..."}
          </div>
        )}
      </div>
    </div>
  );
}
