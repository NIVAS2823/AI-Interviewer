import React, { useEffect, useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { interviewAPI } from "../lib/api";
import {
  Loader2,
  MessageSquare,
  Send,
  Clock,
  AlertCircle,
  ArrowLeft,
  User,
  Bot,
  ChevronUp,
} from "lucide-react";
import toast from "react-hot-toast";

/**
 * InterviewRoom.jsx
 * - Removes "All Questions" everywhere
 * - Desktop: static right sidebar with Current Question + Tips
 * - Mobile: slide-up drawer with Current Question + Tips
 * - Fixed input bar; resilient to resizes (min-h-0 patterns)
 * - No backend logic changes
 */

export default function InterviewRoom() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [interviewData, setInterviewData] = useState(null);
  const [conversation, setConversation] = useState([]);
  const [currentInput, setCurrentInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [startTime] = useState(Date.now());
  const [elapsedTime, setElapsedTime] = useState(0);

  const [drawerOpen, setDrawerOpen] = useState(false);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const containerRef = useRef(null);
  const hasStartedRef = useRef(false);

  // timer
  useEffect(() => {
    const t = setInterval(() => {
      setElapsedTime(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);
    return () => clearInterval(t);
  }, [startTime]);

  // initial load
  useEffect(() => {
    if (!hasStartedRef.current) {
      hasStartedRef.current = true;
      loadInterview();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // scroll on new messages / sending
  useEffect(() => {
    scrollToBottom({ smooth: true });
  }, [conversation, isSending]);

  // handle resize -> ensure input visible & scroll
  useEffect(() => {
    const onResize = () => {
      requestAnimationFrame(() => scrollToBottom({ smooth: false }));
    };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  const scrollToBottom = ({ smooth = true } = {}) => {
    try {
      messagesEndRef.current?.scrollIntoView({ behavior: smooth ? "smooth" : "auto", block: "end" });
    } catch {}
  };

  const loadInterview = async () => {
    try {
      const res = await interviewAPI.get(id);
      const interview = res.data;

      if (interview.status === "completed") {
        toast.error("This interview is already completed.");
        navigate(`/interviews/${id}`);
        return;
      }

      if (interview.status === "created") {
        await interviewAPI.start(id);
        await new Promise((r) => setTimeout(r, 1200));
        const updated = await interviewAPI.get(id);
        setInterviewData(updated.data);
        initializeConversation(updated.data);
      } else {
        setInterviewData(interview);
        if (interview.conversation?.length > 0) setConversation(interview.conversation);
        else initializeConversation(interview);
      }
    } catch (err) {
      toast.error("Failed to load interview");
      navigate("/interviews");
    } finally {
      setLoading(false);
    }
  };

  const initializeConversation = (interview) => {
    const msgs = [
      {
        speaker: "ai",
        text: `Hello! I'm your AI interviewer. I'll be asking you ${interview.max_questions} questions today. Take your time and answer confidently.`,
        timestamp: new Date().toISOString(),
      },
    ];
    if (interview.questions?.length > 0) {
      msgs.push({
        speaker: "ai",
        text: interview.questions[0].question_text,
        timestamp: new Date().toISOString(),
      });
    }
    setConversation(msgs);
  };

  const handleSendMessage = async () => {
    if (!currentInput.trim() || isSending) return;

    const userMessage = {
      speaker: "candidate",
      text: currentInput.trim(),
      timestamp: new Date().toISOString(),
    };

    setConversation((p) => [...p, userMessage]);
    setCurrentInput("");
    setIsSending(true);

    try {
      const res = await interviewAPI.sendMessage(id, userMessage.text);
      const aiMessage = {
        speaker: "ai",
        text: res.data.ai_text,
        timestamp: res.data.timestamp,
      };
      setConversation((p) => [...p, aiMessage]);

      const updated = await interviewAPI.get(id);
      setInterviewData(updated.data);
    } catch {
      toast.error("Failed to send message");
    } finally {
      setIsSending(false);
      inputRef.current?.focus();
    }
  };

  const handleEndInterview = async () => {
    if (!confirm("End interview and generate evaluation?")) return;
    try {
      toast.loading("Ending interview...");
      await interviewAPI.end(id);
      toast.dismiss();
      toast.success("Interview completed!");
      navigate(`/interviews/${id}`);
    } catch {
      toast.dismiss();
      toast.error("Failed to end interview");
    }
  };

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-darkbg">
        <Loader2 className="w-12 h-12 text-neon-primary animate-spin" />
      </div>
    );
  }

  if (!interviewData) {
    return (
      <div className="h-screen flex items-center justify-center bg-darkbg">
        <AlertCircle className="w-12 h-12 text-red-500" />
        <p className="text-gray-400 mt-3">Interview not found.</p>
      </div>
    );
  }

  const currentCount = interviewData.questions?.length || 0;
  const maxCount = interviewData.max_questions || 5;
  const progressPercent = Math.round((currentCount / maxCount) * 100);

  return (
    <div className="h-screen flex flex-col bg-darkbg text-gray-200">

      {/* HEADER */}
      <header className="flex items-center justify-between px-5 py-3 border-b border-white/6 bg-darkbg-card z-20">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate(`/interviews/${id}`)}
            className="text-gray-300 hover:text-neon-primary transition"
            aria-label="Back to interview overview"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>

          <div>
            <h1 className="text-xl font-bold text-neon-primary drop-shadow-[0_0_6px_var(--neon-primary)]">
              Live Interview
            </h1>
            <p className="text-xs text-gray-400 capitalize">
              {interviewData.interview_type.replace("_", " ")} • {interviewData.difficulty}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-6">
          <div className="hidden md:flex items-center gap-2 bg-white/5 px-3 py-1 rounded-full">
            <Clock className="w-4 h-4 text-neon-primary" />
            <span className="font-mono text-sm">{formatTime(elapsedTime)}</span>
          </div>

          <div className="hidden md:flex items-center gap-3">
            <div className="w-36 bg-white/5 h-2 rounded-full overflow-hidden">
              <div className="h-full bg-neon-primary transition-all" style={{ width: `${progressPercent}%` }} />
            </div>
            <div className="px-3 py-1 rounded-full bg-white/5 text-sm font-medium">{currentCount} / {maxCount}</div>
          </div>

          <button onClick={handleEndInterview} className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg" aria-label="End interview">
            End
          </button>
        </div>
      </header>

      {/* MAIN AREA - ensure min-h-0 so children can shrink properly */}
      <div className="flex-1 min-h-0 overflow-hidden">

        {/* grid */}
        <div className="h-full grid grid-cols-1 lg:grid-cols-4 gap-6 p-5 min-h-0">

          {/* CHAT panel */}
          <section className="lg:col-span-3 flex flex-col bg-darkbg-card rounded-xl border border-white/6 shadow-lg min-h-0">

            {/* messages container */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4 min-h-0">
              {conversation.map((msg, idx) => {
                const isUser = msg.speaker === "candidate";
                return (
                  <div key={idx} className={`flex items-start gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${
                      isUser ? "bg-gradient-to-br from-neon-green to-teal-500" : "bg-gradient-to-br from-neon-primary to-purple-600"
                    }`}>
                      {isUser ? <User className="w-5 h-5 text-white" /> : <Bot className="w-5 h-5 text-white" />}
                    </div>

                    <div className="max-w-[80%]">
                      <div className={`p-3 rounded-2xl ${isUser ? "bg-neon-primary text-black shadow-[0_0_12px_var(--neon-primary)]" : "bg-darkbg text-gray-200 border border-white/6"}`}>
                        <p className="text-sm leading-relaxed break-words">{msg.text}</p>
                      </div>
                      <p className={`text-xs mt-1 ${isUser ? "text-gray-400 text-right" : "text-gray-500"}`}>{new Date(msg.timestamp).toLocaleTimeString()}</p>
                    </div>
                  </div>
                );
              })}

              {isSending && (
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-neon-primary to-purple-600 flex items-center justify-center">
                    <Bot className="w-5 h-5 text-white" />
                  </div>
                  <div className="px-4 py-3 bg-darkbg rounded-2xl border border-white/6 flex gap-2">
                    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100" />
                    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200" />
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* input - shrink-0 ensures it remains visible */}
            <div className="p-4 border-t border-white/6 bg-darkbg-card shrink-0">
              <div className="flex items-center gap-3">
                <input
                  ref={inputRef}
                  value={currentInput}
                  onChange={(e) => setCurrentInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleSendMessage();
                    }
                  }}
                  placeholder="Type your answer..."
                  className="flex-1 bg-[#2b3238] text-gray-200 rounded-lg px-4 py-3 focus:outline-none focus:ring-1 focus:ring-neon-primary"
                  aria-label="Type your answer"
                />

                <button
                  onClick={handleSendMessage}
                  disabled={!currentInput.trim() || isSending}
                  className="p-3 rounded-lg bg-neon-primary text-black shadow-[0_0_12px_var(--neon-primary)] hover:shadow-[0_0_20px_var(--neon-primary)] disabled:opacity-60"
                  aria-label="Send answer"
                >
                  <Send className="w-5 h-5" />
                </button>

                {/* drawer toggle (mobile only) */}
                <button
                  onClick={() => setDrawerOpen((s) => !s)}
                  className="ml-2 md:hidden p-3 rounded-lg bg-[#00f0ff] text-black shadow-lg"
                  aria-label="Open questions & tips"
                >
                  <ChevronUp className="w-5 h-5" />
                </button>
              </div>
              <p className="text-xs text-gray-500 mt-2">Press Enter to send • Shift+Enter for newline</p>
            </div>
          </section>

          {/* RIGHT SIDEBAR (desktop only) - only Current Question + Tips */}
          <aside className="hidden lg:flex flex-col space-y-6 h-full">

            {/* Current Question */}
            <div className="p-4 rounded-xl bg-[#07121a] border border-neon-primary/10 shadow-[0_0_20px_var(--neon-primary)/10]">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-neon-primary font-semibold flex items-center gap-2">
                  <MessageSquare className="w-4 h-4" /> Current Question
                </h3>
                <div className="px-2 py-0.5 rounded-full bg-white/5 text-sm">{currentCount} / {maxCount}</div>
              </div>

              <p className="text-sm text-gray-200 bg-white/5 p-3 rounded-lg leading-relaxed">
                {interviewData.questions?.[currentCount - 1]?.question_text || "Waiting for next question..."}
              </p>
            </div>

            {/* Tips */}
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

        </div>
      </div>

      {/* MOBILE BOTTOM DRAWER (Current Question + Tips) */}
      <div className={`fixed left-0 right-0 bottom-0 z-40 md:hidden transition-transform duration-300 ${drawerOpen ? "translate-y-0" : "translate-y-full"}`} aria-hidden={!drawerOpen}>
        <div className="mx-4 mb-4 bg-darkbg-card border border-white/6 rounded-t-xl shadow-xl overflow-hidden max-h-[70vh]">
          <div className="p-4 flex items-center justify-between border-b border-white/6">
            <h4 className="text-neon-primary font-semibold flex items-center gap-2"><MessageSquare className="w-4 h-4" /> Questions & Tips</h4>
            <button onClick={() => setDrawerOpen(false)} className="p-2 rounded-md bg-white/5" aria-label="Close drawer">
              <ChevronUp className="w-4 h-4 transform rotate-180" />
            </button>
          </div>

          <div className="p-4 max-h-[56vh] overflow-y-auto space-y-4">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-gray-300">Current</span>
                <span className="text-sm text-gray-200">{currentCount} / {maxCount}</span>
              </div>
              <p className="text-sm text-gray-200 bg-white/5 p-3 rounded-lg">
                {interviewData.questions?.[currentCount - 1]?.question_text || "Waiting for next question..."}
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
    </div>
  );
}
