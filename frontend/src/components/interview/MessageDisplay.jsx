// src/components/interview/MessageDisplay.jsx
import React from "react";

export function MessageDisplay({ currentMessage, transcript }) {
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

      {/* User's Transcript */}
      {transcript && (
        <div className="mt-2 max-w-2xl bg-white/3 rounded-2xl p-3 border border-white/6">
          <p className="text-green-200 text-sm">
            <strong>You said:</strong> {transcript}
          </p>
        </div>
      )}
    </>
  );
}