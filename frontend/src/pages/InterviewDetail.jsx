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
  User,
  Bot,
} from "lucide-react";
import toast from "react-hot-toast";
import { formatDateTime, formatDuration, getScoreColor } from "../lib/utils";

export default function InterviewDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [interview, setInterview] = useState(null);
  const [evaluation, setEvaluation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  const pollingRef = useRef(null);

  // Confirm modal state
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [confirmAction, setConfirmAction] = useState(null);

  const askConfirm = (text, action) => {
    setConfirmText(text);
    setConfirmAction(() => action);
    setConfirmOpen(true);
  };

  /* -------------------------- LOAD INTERVIEW -------------------------- */
  useEffect(() => {
    loadInterview();
    return () => stopPolling();
  }, [id]);

  const loadInterview = async () => {
    try {
      const res = await interviewAPI.get(id);
      setInterview(res.data);

      if (res.data.status === "completed") {
        loadEvaluation();
      }
    } catch (err) {
      toast.error("Failed to load interview");
      navigate("/interviews");
    } finally {
      setLoading(false);
    }
  };

  /* -------------------------- LOAD EVALUATION -------------------------- */
  const loadEvaluation = async () => {
    try {
      const res = await evaluationAPI.get(id);
      setEvaluation(res.data);
      stopPolling();
    } catch (err) {
      if (err?.response?.status === 404) {
        // No evaluation created → treat as skipped
        setEvaluation({ skipped_interview: true });
        stopPolling();
      }
    }
  };

  const startPolling = () => {
    if (pollingRef.current) return;
    pollingRef.current = setInterval(loadEvaluation, 3000);
  };

  const stopPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  };

  /* -------------------------- SIMULATE -------------------------- */
  const handleSimulate = async () => {
    askConfirm("Simulate this interview?", async () => {
      setConfirmOpen(false);
      setActionLoading(true);

      try {
        await interviewAPI.simulate(id);
        toast.success("Interview simulated");
        await loadInterview();
      } catch {
        toast.error("Simulation failed");
      } finally {
        setActionLoading(false);
      }
    });
  };

  /* -------------------------- END INTERVIEW -------------------------- */
  const handleEnd = async () => {
    askConfirm("End interview and generate evaluation?", async () => {
      setConfirmOpen(false);
      setActionLoading(true);

      try {
        await interviewAPI.end(id);
        toast.success("Interview ended — generating evaluation...");
        setTimeout(() => loadInterview(), 1500);
        startPolling();
      } catch {
        toast.error("Failed to end interview");
      } finally {
        setActionLoading(false);
      }
    });
  };

  /* -------------------------- LOADING -------------------------- */
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-neon-primary" />
      </div>
    );
  }

  if (!interview) return null;

  /* ====================================================================== */
  /*                            MAIN RENDER                                 */
  /* ====================================================================== */

  return (
    <div className="space-y-10 text-gray-200">
      {/* Back Link */}
      <Link
        to="/interviews"
        className="inline-flex items-center text-gray-400 hover:text-neon-primary transition"
      >
        <ArrowLeft className="w-4 h-4 mr-2" />
        Back to Interviews
      </Link>

      {/* Header */}
      <HeaderSection
        interview={interview}
        id={id}
        handleSimulate={handleSimulate}
        handleEnd={handleEnd}
      />

      {/* Configuration */}
      <ConfigSection interview={interview} />

      {/* Evaluation */}
      <EvaluationWrapper interview={interview} evaluation={evaluation} />

      {/* Questions */}
      {!evaluation?.skipped_interview && (
        <QuestionsList interview={interview} />
      )}

      {/* Transcript */}
      {!evaluation?.skipped_interview &&
        interview.conversation?.length > 0 && (
          <Conversation conversation={interview.conversation} />
        )}

      {/* ===================== CONFIRM MODAL ===================== */}
      {confirmOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-darkbg-card p-6 rounded-xl border border-white/10 shadow-xl w-[90%] max-w-md text-center">
            <h3 className="text-xl font-semibold text-white mb-4">
              Are you sure?
            </h3>

            <p className="text-gray-300 mb-6">{confirmText}</p>

            <div className="flex items-center justify-center space-x-4">
              <button
                className="px-5 py-2 rounded-lg bg-red-600/20 text-red-400 border border-red-400/40 hover:bg-red-600/30 transition"
                onClick={() => confirmAction && confirmAction()}
              >
                Yes, Continue
              </button>

              <button
                className="px-5 py-2 rounded-lg border border-white/20 text-gray-300 hover:bg-white/10 transition"
                onClick={() => setConfirmOpen(false)}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ====================================================================== */
/*                               SUB COMPONENTS                            */
/* ====================================================================== */

function HeaderSection({ interview, id, handleSimulate, handleEnd }) {
  return (
    <div className="flex items-start justify-between">
      <div>
        <h1 className="text-3xl font-bold capitalize text-neon-primary">
          {interview.interview_type.replace("_", " ")} Interview
        </h1>
        <p className="text-gray-400 mt-1">
          Created {formatDateTime(interview.created_at)}{" "}
          {interview.duration_minutes &&
            `• ${formatDuration(interview.duration_minutes)}`}
        </p>
      </div>

      <div className="flex items-center space-x-3">
        {interview.status === "created" && (
          <>
            <Link
              to={`/interviews/${id}/room`}
              className="px-5 py-2 rounded-lg bg-neon-primary text-black font-semibold shadow flex items-center"
            >
              <PlayCircle className="w-4 h-4 mr-2" /> Join Interview
            </Link>

            <button
              onClick={handleSimulate}
              className="px-5 py-2 rounded-lg border border-white/10 text-gray-300 hover:text-neon-primary transition"
            >
              Simulate
            </button>
          </>
        )}

        {interview.status === "in_progress" && (
          <Link
            to={`/interviews/${id}/room`}
            className="px-5 py-2 rounded-lg bg-neon-primary text-black font-semibold animate-pulse flex items-center shadow"
          >
            <PlayCircle className="w-4 h-4 mr-2" /> Rejoin Interview
          </Link>
        )}

        {(interview.status === "created" ||
          interview.status === "in_progress") && (
          <button
            onClick={handleEnd}
            className="px-5 py-2 rounded-lg border border-red-500/40 text-red-400 hover:bg-red-500/10 transition flex items-center"
          >
            <StopCircle className="w-4 h-4 mr-2" /> End Interview
          </button>
        )}
      </div>
    </div>
  );
}

/* --------------------------- CONFIG SECTION --------------------------- */

function ConfigSection({ interview }) {
  return (
    <div className="bg-darkbg-card p-6 border border-white/10 rounded-xl shadow">
      <h2 className="text-lg font-semibold mb-4 text-neon-primary">
        Configuration
      </h2>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
        <ConfigItem label="Type" value={interview.interview_type} />
        <ConfigItem label="Difficulty" value={interview.difficulty} />
        <ConfigItem
          label="Questions"
          value={`${interview.questions?.length || 0} / ${
            interview.max_questions || 5
          }`}
        />
        <ConfigItem label="Status" value={interview.status} />
      </div>
    </div>
  );
}

function ConfigItem({ label, value }) {
  return (
    <div>
      <p className="text-sm text-gray-400">{label}</p>
      <p className="font-medium capitalize">{value}</p>
    </div>
  );
}

/* ------------------------ EVALUATION HANDLING ------------------------ */

function EvaluationWrapper({ interview, evaluation }) {
  if (!evaluation) {
    if (interview.status === "completed") return <PendingEvaluation />;
    return null;
  }

  if (evaluation.skipped_interview) return <SkippedInterviewBanner />;

  return <EvaluationSection evaluation={evaluation} />;
}

function SkippedInterviewBanner() {
  return (
    <div className="bg-yellow-500/10 border border-yellow-500/40 p-6 rounded-xl text-center">
      <p className="text-yellow-300 text-xl font-bold mb-2">
        Interview Skipped
      </p>
      <p className="text-gray-300">
        No questions were answered. No evaluation was generated.
      </p>
    </div>
  );
}

function PendingEvaluation() {
  return (
    <div className="bg-yellow-500/10 border border-yellow-500/40 p-6 rounded-xl text-center">
      <Loader2 className="w-6 h-6 animate-spin text-yellow-300 mx-auto mb-2" />
      <p className="text-yellow-200 font-medium">Evaluation is being generated...</p>
    </div>
  );
}

function EvaluationSection({ evaluation }) {
  const scores = evaluation.scores || {};

  return (
    <>
      {/* Overall Score */}
      <div className="bg-darkbg-card border border-white/10 rounded-xl shadow p-8 text-center">
        <Award className="w-12 h-12 text-neon-primary mx-auto mb-4" />
        <p className="text-gray-400 mb-2">Overall Score</p>
        <p
          className={`text-6xl font-bold ${getScoreColor(
            scores.overall_score
          )}`}
        >
          {scores.overall_score}%
        </p>
      </div>

      {/* Score Breakdown */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
        {["technical", "communication", "confidence", "behavioral"].map((s) => (
          <div
            key={s}
            className="bg-darkbg-card p-6 rounded-xl border border-white/10 text-center shadow"
          >
            <p className="text-sm text-gray-400 capitalize">{s}</p>
            <p
              className={`text-3xl font-bold ${getScoreColor(
                scores[`${s}_score`]
              )}`}
            >
              {scores[`${s}_score`]}%
            </p>
          </div>
        ))}
      </div>

      {/* Strengths */}
      <DetailBlock title="Strengths" items={evaluation.strengths} icon={CheckCircle2} />

      {/* Improvements */}
      <DetailBlock title="Areas for Improvement" items={evaluation.improvements} icon={TrendingUp} />

      {/* Detailed Feedback */}
      <div className="bg-darkbg-card p-6 rounded-xl border border-white/10 shadow">
        <h2 className="text-xl font-bold text-neon-primary mb-4">
          Detailed Feedback
        </h2>
        <pre className="text-gray-300 whitespace-pre-wrap">
          {evaluation.detailed_feedback}
        </pre>
      </div>
    </>
  );
}

function DetailBlock({ title, items, icon: Icon }) {
  return (
    <div className="bg-darkbg-card p-6 rounded-xl border border-white/10 shadow">
      <h2 className="text-xl font-bold text-neon-primary mb-4">{title}</h2>
      <ul className="space-y-2 text-gray-300">
        {items?.map((txt, i) => (
          <li key={i} className="flex items-center space-x-2">
            <Icon className="w-4 h-4 text-neon-primary" />
            <span>{txt}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/* ------------------------------ QUESTIONS ------------------------------ */

function QuestionsList({ interview }) {
  return (
    <div className="bg-darkbg-card p-6 rounded-xl border border-white/10 shadow">
      <h2 className="text-xl font-bold text-neon-primary mb-4">
        Interview Questions
      </h2>

      <div className="space-y-4">
        {interview.questions?.map((q, i) => (
          <div key={i} className="border-l-4 border-neon-primary/40 pl-4">
            <p className="font-medium text-gray-200">
              Q{i + 1}: {q.question_text}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ----------------------------- CONVERSATION ----------------------------- */

function Conversation({ conversation }) {
  return (
    <div className="bg-darkbg-card p-6 rounded-xl border border-white/10 shadow">
      <h2 className="text-xl font-bold text-neon-primary mb-4">
        Conversation Transcript
      </h2>

      <div className="space-y-4 max-h-96 overflow-y-auto pr-2">
        {conversation.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${
              msg.speaker === "candidate" ? "justify-end" : "justify-start"
            }`}
          >
            <div
              className={`max-w-[80%] p-4 rounded-lg shadow ${
                msg.speaker === "candidate"
                  ? "bg-neon-primary text-black shadow-[0_0_15px_var(--neon-primary)]"
                  : "bg-[#6a00ff20] border border-neon-secondary/40 text-neon-secondary shadow-[0_0_12px_var(--neon-secondary)]"
              }`}
            >
              <div className="flex items-center space-x-2 mb-1">
                {msg.speaker === "ai" ? (
                  <Bot className="w-4 h-4" />
                ) : (
                  <User className="w-4 h-4" />
                )}
                <span className="text-xs font-medium">
                  {msg.speaker === "ai" ? "AI Interviewer" : "You"}
                </span>
              </div>

              <p className="text-sm">{msg.text}</p>

              <p className="text-xs opacity-70 mt-1">
                {new Date(msg.timestamp).toLocaleTimeString()}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
