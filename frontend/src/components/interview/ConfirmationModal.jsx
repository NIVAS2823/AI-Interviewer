// src/components/interview/ConfirmationModal.jsx
import React from "react";

export function ConfirmationModal({
  isOpen,
  confirmText,
  onConfirm,
  onCancel,
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-darkbg-card p-6 rounded-xl border border-white/10 shadow-xl w-[90%] max-w-md text-center">
        <h3 className="text-xl font-semibold text-white mb-4">
          Are you sure?
        </h3>

        <p className="text-gray-300 mb-6">{confirmText}</p>

        <div className="flex items-center justify-center space-x-4">
          <button
            className="px-5 py-2 rounded-lg bg-red-600/20 text-red-400 border border-red-400/40 hover:bg-red-600/30 transition"
            onClick={onConfirm}
          >
            Yes, Continue
          </button>

          <button
            className="px-5 py-2 rounded-lg border border-white/20 text-gray-300 hover:bg-white/10 transition"
            onClick={onCancel}
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}