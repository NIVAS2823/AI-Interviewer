// src/pages/InterviewDetail.jsx
import React, { useEffect, useState, useRef } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { interviewAPI, evaluationAPI } from "../lib/api";
import {
  Loader2,
  ArrowLeft,
  PlayCircle,
  StopCircle,
  Award,
  MessageSquare,
  TrendingUp,
  CheckCircle2,
} from "lucide-react";
import toast from "react-hot-toast";
import {
  formatDateTime,
  formatDuration,
  getScoreColor,
  getScoreBgColor,
} from "../lib/utils";

export default function InterviewDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [interview, setInterview] = useState(null);
  const [evaluation, setEvaluation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  const pollingRef = useRef(null);

  useEffect(() => {
    loadInterview();
    return () => stopPolling();
    // eslint-disable-next-line
  }, [id]);

  /* -------------------------------------------------------------
     Load Interview
  ------------------------------------------------------------- */
  const loadInterview = async () => {
    try {
      const res = await interviewAPI.get(id);
      setInterview(res.data);

      // If completed → check evaluation
      if (res.data.status === "completed") {
        loadEvaluation();
      }
    } catch (err) {
      console.error("Failed to load interview:", err);
      toast.error("Failed to load interview");
      navigate("/interviews");
    } finally {
      setLoading(false);
    }
  };

  /* -------------------------------------------------------------
     Load Evaluation (with safe polling)
  ------------------------------------------------------------- */
  const loadEvaluation = async () => {
    try {
      const res = await evaluationAPI.get(id);
      setEvaluation(res.data);
      stopPolling();
    } catch (err) {
      if (err.response?.status === 404) {
        // Evaluation NOT ready yet → start polling
        startPolling();
      } else {
        console.error("Evaluation load failed:", err);
      }
    }
  };

  /* -------------------------------------------------------------
     Polling System (every 3 seconds)
  ------------------------------------------------------------- */
  const startPolling = () => {
    if (pollingRef.current) return; // Prevent duplicates

    pollingRef.current = setInterval(async () => {
      try {
        const res = await evaluationAPI.get(id);
        setEvaluation(res.data);
        stopPolling();
        toast.success("Evaluation ready!");
      } catch (err) {
        // Ignore 404 → still processing
      }
    }, 3000);
  };

  const stopPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  };

  /* -------------------------------------------------------------
     Start Interview
  ------------------------------------------------------------- */
  const handleStart = async () => {
    if (!id) return;
    setActionLoading(true);

    try {
      await interviewAPI.start(id);
      toast.success("Interview started!");
      await loadInterview();
    } catch (err) {
      toast.error("Failed to start interview");
    } finally {
      setActionLoading(false);
    }
  };

  /* -------------------------------------------------------------
     Simulate Interview (for testing)
  ------------------------------------------------------------- */
  const handleSimulate = async () => {
    if (!id) return;
    if (!window.confirm("Simulate an interview for testing?")) return;

    setActionLoading(true);
    try {
      await interviewAPI.simulate(id);
      toast.success("Conversation simulated!");
      await loadInterview();
    } catch (err) {
      toast.error("Simulation failed");
    } finally {
      setActionLoading(false);
    }
  };

  /* -------------------------------------------------------------
     END Interview
  ------------------------------------------------------------- */
  const handleEnd = async () => {
    if (!id) return;
    if (!window.confirm("End interview and generate evaluation?")) return;

    setActionLoading(true);

    try {
      await interviewAPI.end(id);
      toast.success("Interview ended. Generating evaluation...");

      // Wait 3s before first check (backend needs transcript)
      setTimeout(() => loadInterview(), 3000);
    } catch (err) {
      toast.error("Failed to end interview");
    } finally {
      setActionLoading(false);
    }
  };

  /* -------------------------------------------------------------
     Render
  ------------------------------------------------------------- */
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    );
  }

  if (!interview) return null;

  return (
    <div className="space-y-8">
      {/* Back button */}
      <Link to="/interviews" className="inline-flex items-center text-gray-600 hover:text-gray-900 mb-4">
        <ArrowLeft className="w-4 h-4 mr-2" />
        Back to Interviews
      </Link>

      {/* Interview Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold mb-2 capitalize">
            {interview.interview_type.replace("_", " ")} Interview
          </h1>
          <p className="text-gray-600">
            Created {formatDateTime(interview.created_at)}
            {interview.duration_minutes &&
              ` • ${formatDuration(interview.duration_minutes)}`}
          </p>
        </div>

        {/* Buttons */}
        <div className="flex items-center space-x-3">
          {interview.status === "created" && (
            <>
              <Link to={`/interviews/${id}/room`} className="btn btn-primary flex items-center">
                <PlayCircle className="w-4 h-4 mr-2" />
                Join Interview
              </Link>

              <button onClick={handleSimulate} className="btn btn-secondary flex items-center">
                Simulate
              </button>
            </>
          )}

          {interview.status === "in_progress" && (
            <Link
              to={`/interviews/${id}/room`}
              className="btn btn-primary flex items-center animate-pulse"
            >
              <PlayCircle className="w-4 h-4 mr-2" />
              Rejoin Interview
            </Link>
          )}

          {(interview.status === "created" || interview.status === "in_progress") && (
            <button onClick={handleEnd} className="btn btn-outline flex items-center">
              <StopCircle className="w-4 h-4 mr-2" />
              End Interview
            </button>
          )}
        </div>
      </div>

      {/* Interview Config */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Configuration</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <ConfigItem label="Type" value={interview.interview_type} />
          <ConfigItem label="Difficulty" value={interview.difficulty} />
          <ConfigItem label="Questions" value={interview.questions?.length} />
          <ConfigItem label="Status" value={interview.status} />
        </div>
      </div>

      {/* Evaluation Section */}
      {evaluation ? (
        <EvaluationSection evaluation={evaluation} />
      ) : interview.status === "completed" ? (
        <PendingEvaluation />
      ) : null}

      {/* Questions List */}
      <QuestionsList interview={interview} />

      {/* Transcript */}
      {interview.conversation?.length > 0 && (
        <Transcript conversation={interview.conversation} />
      )}
    </div>
  );
}

/* -------------------------------------------------------------
   COMPONENTS
------------------------------------------------------------- */

function ConfigItem({ label, value }) {
  return (
    <div>
      <p className="text-sm text-gray-600">{label}</p>
      <p className="font-medium capitalize">{value}</p>
    </div>
  );
}

function PendingEvaluation() {
  return (
    <div className="card bg-yellow-50 border-l-4 border-yellow-500">
      <Loader2 className="w-6 h-6 animate-spin text-yellow-600 mb-2" />
      <p className="text-gray-700 font-medium">Evaluation is being generated...</p>
      <p className="text-gray-600 text-sm">This may take 5–10 seconds.</p>
    </div>
  );
}

function EvaluationSection({ evaluation }) {
  return (
    <>
      {/* Overall Score */}
      <div className="card bg-gradient-to-br from-primary-50 to-primary-100">
        <div className="text-center py-6">
          <Award className="w-12 h-12 text-primary-600 mx-auto mb-4" />
          <p className="text-gray-700 mb-2">Overall Score</p>
          <p className={`text-6xl font-bold ${getScoreColor(evaluation.scores.overall_score)}`}>
            {evaluation.scores.overall_score}%
          </p>
        </div>
      </div>

      {/* Category Scores */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {["technical", "communication", "confidence", "behavioral"].map((s) => (
          <div key={s} className="card text-center">
            <p className="text-sm text-gray-600 capitalize">{s}</p>
            <p className={`text-3xl font-bold ${getScoreColor(evaluation.scores[`${s}_score`])}`}>
              {evaluation.scores[`${s}_score`]}%
            </p>
          </div>
        ))}
      </div>

      {/* Strengths */}
      <div className="card">
        <h2 className="text-xl font-bold mb-4">Strengths</h2>
        <ul className="space-y-2">
          {evaluation.strengths.map((s, i) => (
            <li key={i} className="flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4 text-green-600" />
              <span className="text-gray-700">{s}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Improvements */}
      <div className="card">
        <h2 className="text-xl font-bold mb-4">Areas for Improvement</h2>
        <ul className="space-y-2">
          {evaluation.improvements.map((imp, i) => (
            <li key={i} className="flex items-center space-x-2">
              <TrendingUp className="w-4 h-4 text-blue-600" />
              <span className="text-gray-700">{imp}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Feedback */}
      <div className="card">
        <h2 className="text-xl font-bold mb-4">Detailed Feedback</h2>
        <div className="prose max-w-none text-gray-700 whitespace-pre-line">
          {evaluation.detailed_feedback}
        </div>
      </div>
    </>
  );
}

function QuestionsList({ interview }) {
  return (
    <div className="card">
      <h2 className="text-xl font-bold mb-4">Interview Questions</h2>
      <div className="space-y-4">
        {interview.questions?.map((q, i) => (
          <div key={i} className="border-l-4 border-gray-300 pl-4">
            <p className="font-medium text-gray-900">
              Q{i + 1}: {q.question_text}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

function Transcript({ conversation }) {
  return (
    <div className="card">
      <h2 className="text-xl font-bold mb-4">Conversation Transcript</h2>
      <div className="space-y-4 max-h-96 overflow-y-auto">
        {conversation.map((msg, i) => (
          <div
            key={i}
            className={`p-4 rounded-lg ${
              msg.speaker === "ai"
                ? "bg-blue-50 border-l-4 border-blue-500"
                : "bg-green-50 border-l-4 border-green-500"
            }`}
          >
            <p className="text-sm font-medium text-gray-600 mb-1">
              {msg.speaker === "ai" ? "AI Interviewer" : "You"}
            </p>
            <p className="text-gray-900">{msg.text}</p>
            <p className="text-xs text-gray-500 mt-2">{formatDateTime(msg.timestamp)}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
