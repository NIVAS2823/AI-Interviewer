// src/components/interview/InterviewHeader.jsx
import React from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Clock } from "lucide-react";

export function InterviewHeader({
  interviewId,
  interviewData,
  formattedTime,
  questionProgress,
  onEndInterview,
}) {
  const navigate = useNavigate();

  const currentCount = questionProgress.current || 0;
  const maxCount = questionProgress.total || interviewData?.max_questions || 0;
  const progressPercent = maxCount > 0 ? Math.round((currentCount / maxCount) * 100) : 0;

  return (
    <header className="flex items-center justify-between px-5 py-3 border-b border-white/6 bg-darkbg-card z-20">
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate(`/interviews/${interviewId}`)}
          className="text-gray-300 hover:text-neon-primary transition"
          aria-label="Back to interview overview"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>

        <div>
          <h1 className="text-xl font-bold text-neon-primary drop-shadow-[0_0_6px_var(--neon-primary)]">
            Voice Interview
          </h1>
          <p className="text-xs text-gray-400 capitalize">
            {interviewData?.interview_type?.replace("_", " ")} • {interviewData?.difficulty}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-6">
        <div className="hidden md:flex items-center gap-2 bg-white/5 px-3 py-1 rounded-full">
          <Clock className="w-4 h-4 text-neon-primary" />
          <span className="font-mono text-sm">{formattedTime}</span>
        </div>

        <div className="hidden md:flex items-center gap-3">
          <div className="w-36 bg-white/5 h-2 rounded-full overflow-hidden">
            <div
              className="h-full bg-neon-primary transition-all"
              style={{ width: `${progressPercent}%` }}
              aria-hidden
            />
          </div>
          <div className="px-3 py-1 rounded-full bg-white/5 text-sm font-medium">
            {currentCount} / {maxCount}
          </div>
        </div>

        <button
          onClick={onEndInterview}
          className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg"
          aria-label="End interview"
        >
          End
        </button>
      </div>
    </header>
  );
}