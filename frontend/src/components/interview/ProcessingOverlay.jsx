// src/components/interview/ProcessingOverlay.jsx
import React from "react";

export function ProcessingOverlay({ isProcessing, processingMessage }) {
  if (!isProcessing) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
        <div className="flex flex-col items-center gap-4">
          {/* Spinner */}
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>

          {/* Message */}
          <p className="text-lg font-medium text-gray-800 text-center">
            {processingMessage || "Processing your answer..."}
          </p>

          {/* Progress dots */}
          <div className="flex gap-1 mt-1">
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"></div>
            <div
              className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"
              style={{ animationDelay: "0.1s" }}
            ></div>
            <div
              className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"
              style={{ animationDelay: "0.2s" }}
            ></div>
          </div>
        </div>
      </div>
    </div>
  );
}