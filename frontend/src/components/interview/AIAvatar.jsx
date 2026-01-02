// src/components/interview/AIAvatar.jsx
import React from "react";
import { Volume2, Mic } from "lucide-react";

export function AIAvatar({ isSpeaking, isListening, connectionStatus }) {
  return (
    <div className="flex flex-col items-center">
      {/* Avatar */}
      <div
        className={`w-48 h-48 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center mb-6 transition-all ${
          isSpeaking
            ? "scale-110 shadow-2xl shadow-blue-500/50"
            : "scale-100"
        }`}
      >
        <span className="text-6xl">🎤</span>
      </div>

      {/* Status */}
      <div className="text-center mb-6">
        <h2 className="text-2xl font-bold text-white mb-2">
          Sarah - AI Interviewer
        </h2>
        {isSpeaking && (
          <div className="flex items-center justify-center space-x-2 text-blue-400">
            <Volume2 className="w-5 h-5 animate-pulse" />
            <span>Speaking...</span>
          </div>
        )}
        {isListening && (
          <div className="flex items-center justify-center space-x-2 text-green-400">
            <Mic className="w-5 h-5 animate-pulse" />
            <span>Listening...</span>
          </div>
        )}
        {!isSpeaking && !isListening && (
          <div className="text-gray-400">
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