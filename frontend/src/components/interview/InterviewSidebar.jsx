// src/components/interview/InterviewSidebar.jsx
import React from "react";

export function InterviewSidebar() {
  return (
    <aside className="hidden lg:flex flex-col space-y-6 h-full">
      {/* Tips Card */}
      <div className="p-4 rounded-xl bg-[#002f24] border border-green-600/20 shadow-[0_0_12px_#00ffbf20]">
        <h4 className="text-green-300 font-semibold mb-2">Tips</h4>
        <ul className="text-green-100 text-sm space-y-2">
          <li>• Use examples (STAR method)</li>
          <li>• Speak clearly and confidently</li>
          <li>• Provide examples & metrics</li>
          <li>• Pause and collect your thoughts</li>
        </ul>
      </div>
    </aside>
  );
}