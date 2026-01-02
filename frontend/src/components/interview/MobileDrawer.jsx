// src/components/interview/MobileDrawer.jsx
import React from "react";
import { MessageSquare, ChevronUp } from "lucide-react";

export function MobileDrawer({
  isOpen,
  onClose,
  interviewData,
  questionProgress,
}) {
  const currentCount = questionProgress.current || 0;
  const maxCount = questionProgress.total || interviewData?.max_questions || 0;

  return (
    <div
      className={`fixed left-0 right-0 bottom-0 z-40 md:hidden transition-transform duration-300 ${
        isOpen ? "translate-y-0" : "translate-y-full"
      }`}
      aria-hidden={!isOpen}
    >
      <div className="mx-4 mb-4 bg-darkbg-card border border-white/6 rounded-t-xl shadow-xl overflow-hidden max-h-[70vh]">
        <div className="p-4 flex items-center justify-between border-b border-white/6">
          <h4 className="text-neon-primary font-semibold flex items-center gap-2">
            <MessageSquare className="w-4 h-4" /> Questions & Tips
          </h4>

          <button
            onClick={onClose}
            className="p-2 rounded-md bg-white/5"
            aria-label="Close drawer"
          >
            <ChevronUp className="w-4 h-4 transform rotate-180" />
          </button>
        </div>

        <div className="p-4 max-h-[56vh] overflow-y-auto space-y-4">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-300">Current</span>
              <span className="text-sm text-gray-200">
                {currentCount} / {maxCount}
              </span>
            </div>
            <p className="text-sm text-gray-200 bg-white/5 p-3 rounded-lg">
              {interviewData?.questions?.[currentCount - 1]?.question_text ||
                "Waiting for next question..."}
            </p>
          </div>

          <div className="p-3 rounded-lg bg-[#002f24] border border-green-600/20">
            <h5 className="text-green-300 font-semibold mb-2">Tips</h5>
            <ul className="text-green-100 text-sm space-y-1">
              <li>• Use STAR: Situation, Task, Action, Result</li>
              <li>• Be specific and use numbers</li>
              <li>• Speak clearly and at a steady pace</li>
              <li>• Pause briefly before answering</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}