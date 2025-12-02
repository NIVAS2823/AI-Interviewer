import React, { useEffect, useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { interviewAPI } from "../lib/api";
import { AudioRecorder, AudioPlayer } from "../lib/audioUtils";
import { VoiceInterviewClient } from "../lib/voiceClient";
import {
  Mic,
  MicOff,
  Loader2,
  Volume2,
  ArrowLeft,
  Clock,
  MessageSquare,
  CheckCircle,
  XCircle,
  ChevronUp,
} from "lucide-react";
import toast from "react-hot-toast";

/**
 * VoiceInterviewRoom.jsx
 * - Neon-themed, responsive layout matching InterviewRoom.jsx
 * - Hybrid layout: avatar + message area (scrollable), mic fixed in bottom bar
 * - Desktop: right sidebar with Current Question + Tips (static)
 * - Mobile: same right content available in a bottom drawer
 * - No conversation history panel (removed)
 * - Neon confirm modal for ending interview
 *
 * NOTE: Keep your existing audio/ws implementations; import paths assumed.
 */

export default function VoiceInterviewRoom() {
  const { id } = useParams();
  const navigate = useNavigate();

  // Basic state
  const [loading, setLoading] = useState(true);
  const [interviewData, setInterviewData] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState("connecting"); // connecting | connected | error | disconnected
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [currentMessage, setCurrentMessage] = useState("");
  const [questionProgress, setQuestionProgress] = useState({ current: 0, total: 0 });
  const [elapsedTime, setElapsedTime] = useState(0);
  const [startTime] = useState(Date.now());

  // UI state
  const [drawerOpen, setDrawerOpen] = useState(false); // mobile drawer for question & tips
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const confirmActionRef = useRef(null);
  const askConfirm = (text, action) => {
    setConfirmText(text);
    confirmActionRef.current = action;
    setConfirmOpen(true);
  };

  // Refs for audio/ws
  const recorderRef = useRef(null);
  const playerRef = useRef(null);
  const wsClientRef = useRef(null);
  const hasInitRef = useRef(false);

  // Scroll ref for main message area
  const mainPanelRef = useRef(null);

  // Timer
  useEffect(() => {
    const t = setInterval(() => {
      setElapsedTime(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);
    return () => clearInterval(t);
  }, [startTime]);

  // Initialize interview on mount or id change
  useEffect(() => {
    if (!hasInitRef.current) {
      hasInitRef.current = true;
      initializeInterview();
    }
    return () => {
      // cleanup on unmount
      cleanup();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // Keep transcript visible while relevant; no flicker on short updates
  useEffect(() => {
    if (transcript) {
      // scroll main panel down so user sees transcript
      requestAnimationFrame(() => {
        mainPanelRef.current?.scrollIntoView?.({ behavior: "smooth", block: "end" });
      });
    }
  }, [transcript, currentMessage]);

  // -----------------------
  // Initialization
  // -----------------------
  const initializeInterview = async () => {
    try {
      setLoading(true);

      // load interview
      const res = await interviewAPI.get(id);
      const interview = res.data;

      if (interview.status === "completed") {
        toast.error("This interview has already been completed.");
        navigate(`/interviews/${id}`);
        return;
      }

      if (interview.status === "created") {
        await interviewAPI.start(id);
        // slight pause to allow backend to set up
        await new Promise((r) => setTimeout(r, 1200));
        const updated = await interviewAPI.get(id);
        setInterviewData(updated.data);
      } else {
        setInterviewData(interview);
      }

      // audio init
      if (!recorderRef.current) {
        await initAudio();
      }
      // websocket init
      if (!wsClientRef.current) {
        await initWebSocket();
      }

      setLoading(false);
    } catch (err) {
      console.error("Init error:", err);
      toast.error("Failed to initialize interview");
      navigate("/interviews");
    }
  };

  const initAudio = async () => {
    try {
      recorderRef.current = new AudioRecorder();
      const ok = await recorderRef.current.initialize();
      if (!ok) throw new Error("Microphone access denied");

      playerRef.current = new AudioPlayer();
      await playerRef.current.initialize?.();

      console.log("Audio initialized");
    } catch (err) {
      console.error("Audio init error:", err);
      toast.error("Microphone access required");
      throw err;
    }
  };

  const initWebSocket = async () => {
    try {
      const token = localStorage.getItem("token");
      if (!token) throw new Error("Authentication token missing");

      const client = new VoiceInterviewClient(id, token);
      client.maxReconnectAttempts = 0;
      wsClientRef.current = client;

      client.on("open", () => {
        setConnectionStatus("connected");
        toast.success("Connected to AI interviewer");
      });

      client.on("message", handleMessage);

      client.on("error", (e) => {
        console.error("WS error:", e);
        setConnectionStatus("error");
        toast.error("Connection lost");
      });

      client.on("close", () => {
        setConnectionStatus("disconnected");
      });

      await client.connect();
      console.log("WS connected");
    } catch (err) {
      console.error("WS init error:", err);
      toast.error("Cannot connect to interviewer");
      throw err;
    }
  };

  // -----------------------
  // WS Message Handler
  // -----------------------
  const handleMessage = async (data) => {
    if (!data || !data.type) return;

    switch (data.type) {
      case "greeting":
      case "question":
      case "acknowledgment":
      case "closing":
        await handleAIMessage(data);
        break;

      case "transcription":
        // update transcript (do not clear immediately to avoid flicker)
        setTranscript(data.text || "");
        break;

      case "metadata":
        if (data.metadata) {
          setQuestionProgress({
            current: data.metadata.question_number || questionProgress.current,
            total: data.metadata.total_questions || questionProgress.total,
          });
        }
        break;

      case "interview_complete":
        handleInterviewComplete();
        break;

      case "error":
        toast.error(data.message || "Speech recognition failed");
        break;

      default:
        console.log("Unknown WS message:", data);
    }
  };

  // -----------------------
  // Handle AI message (text + audio)
  // -----------------------
  const handleAIMessage = async (data) => {
    try {
      const text = data.text || "";
      setCurrentMessage(text);
      // update progress if present
      if (data.metadata) {
        setQuestionProgress({
          current: data.metadata.question_number || questionProgress.current,
          total: data.metadata.total_questions || questionProgress.total,
        });
      }

      if (data.audio && playerRef.current) {
        setIsSpeaking(true);
        try {
          await playerRef.current.playBase64Audio(data.audio);
        } catch (e) {
          console.error("playback error:", e);
        } finally {
          setIsSpeaking(false);
        }

        // short delay before listening starts
        await new Promise((r) => setTimeout(r, 400));
      }

      // start listening for candidate answers after question/acknowledgment
      if (data.type === "question" || data.type === "acknowledgment") {
        // reset transcript before listening
        setTranscript("");
        await startListening();
      }

      // if greeting or closing, we do not auto-start listening
    } catch (err) {
      console.error("handleAIMessage error:", err);
      setIsSpeaking(false);
    }
  };

  // -----------------------
  // Listening controls
  // -----------------------
  const startListening = async () => {
    try {
      if (!recorderRef.current) {
        toast.error("Recorder not available");
        return;
      }
      setTranscript("");
      setIsListening(true);
      await recorderRef.current.startRecording();
      // scroll to bottom so user sees transcript
      requestAnimationFrame(() => {
        mainPanelRef.current?.scrollIntoView?.({ behavior: "smooth", block: "end" });
      });
    } catch (err) {
      console.error("startListening error:", err);
      setIsListening(false);
      toast.error("Cannot start recording");
    }
  };

  const stopListening = async () => {
    try {
      setIsListening(false);
      if (!recorderRef.current) {
        toast.error("Recorder not available");
        return;
      }

      const audioBlob = await recorderRef.current.stopRecording();

      if (audioBlob && audioBlob.size > 0) {
        try {
          await wsClientRef.current?.sendAudio(audioBlob);
        } catch (err) {
          console.error("sendAudio failed:", err);
          toast.error("Failed to send audio");
        }
      } else {
        toast.error("No audio recorded");
        // re-enable listening so user can retry
        setTimeout(() => startListening(), 300);
      }
    } catch (err) {
      console.error("stopListening error:", err);
      toast.error("Failed to stop recording");
    }
  };

  // -----------------------
  // End interview (with neon modal)
  // -----------------------
  const handleEndInterview = () => {
    askConfirm("End interview and generate evaluation?", async () => {
      setConfirmOpen(false);
      try {
        toast.loading("Ending interview...");
        // stop ws/audio gracefully
        try {
          wsClientRef.current?.stop?.();
          wsClientRef.current?.disconnect?.();
        } catch (e) {
          console.warn("ws stop/disconnect error", e);
        }

        try {
          playerRef.current?.stop?.();
        } catch (e) {}

        try {
          if (recorderRef.current && isListening) {
            await recorderRef.current.stopRecording();
          }
        } catch (e) {}

        await interviewAPI.end(id);
        toast.dismiss();
        toast.success("Interview completed!");
        // small delay for UX
        setTimeout(() => navigate(`/interviews/${id}`), 400);
      } catch (err) {
        toast.dismiss();
        console.error("end interview error:", err);
        toast.error("Failed to end interview");
        // still navigate back as fallback
        setTimeout(() => navigate(`/interviews/${id}`), 800);
      }
    });
  };

  // -----------------------
  // Interview complete (server-side)
  // -----------------------
  const handleInterviewComplete = () => {
    toast.success("Interview complete!");
    // ensure cleanup then navigate
    setTimeout(() => navigate(`/interviews/${id}`), 1200);
  };

  // -----------------------
  // Cleanup resources
  // -----------------------
  const cleanup = async () => {
    try {
      recorderRef.current?.cleanup?.();
    } catch (e) {}
    try {
      playerRef.current?.cleanup?.();
    } catch (e) {}
    try {
      wsClientRef.current?.disconnect?.();
    } catch (e) {}

    recorderRef.current = null;
    playerRef.current = null;
    wsClientRef.current = null;
  };

  const formatTime = (sec) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  /* ---------- RENDER ---------- */

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-darkbg">
        <Loader2 className="w-12 h-12 text-neon-primary animate-spin" />
        <p className="text-gray-400 mt-3">Initializing voice interview...</p>
      </div>
    );
  }

  // defensive interviewData
  const currentCount = questionProgress.current || 0;
  const maxCount = questionProgress.total || interviewData?.max_questions || 0;
  const progressPercent = maxCount > 0 ? Math.round((currentCount / maxCount) * 100) : 0;

  return (
    <>
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
              <span className="font-mono text-sm">{formatTime(elapsedTime)}</span>
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
              onClick={handleEndInterview}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg"
              aria-label="End interview"
            >
              End
            </button>
          </div>
        </header>

        {/* MAIN GRID */}
        <div className="flex-1 min-h-0 overflow-hidden">
          <div className="h-full grid grid-cols-1 lg:grid-cols-4 gap-6 p-5 min-h-0">
            {/* MAIN PANEL - left (hybrid InterviewRoom style) */}
            <section className="lg:col-span-3 flex flex-col bg-darkbg-card rounded-xl border border-white/6 shadow-2xl min-h-0 overflow-hidden">
              <div className="flex-1 overflow-y-auto p-8 flex flex-col items-center" id="mainPanel">
                {/* AI Avatar */}
                <div
                  className={`w-48 h-48 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center mb-6 transition-all ${
                    isSpeaking ? "scale-110 shadow-2xl shadow-blue-500/50" : "scale-100"
                  }`}
                >
                  <span className="text-6xl">🎤</span>
                </div>

                {/* Status */}
                <div className="text-center mb-6">
                  <h2 className="text-2xl font-bold text-white mb-2">Sarah - AI Interviewer</h2>
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
                  {!isSpeaking && !isListening && <div className="text-gray-400">Ready</div>}
                </div>

                {/* Current Message */}
                {currentMessage ? (
                  <div className="max-w-2xl bg-gray-700 rounded-2xl p-6 mb-4">
                    <p className="text-gray-200 text-lg leading-relaxed">{currentMessage}</p>
                  </div>
                ) : (
                  <div className="max-w-2xl text-center text-gray-400 mb-4">
                    Waiting for the interviewer...
                  </div>
                )}

                {/* Transcript (kept) */}
                {transcript && (
                  <div className="mt-2 max-w-2xl bg-white/3 rounded-2xl p-3 border border-white/6">
                    <p className="text-green-200 text-sm">
                      <strong>You said:</strong> {transcript}
                    </p>
                  </div>
                )}

                {/* spacer so content isn't hidden behind fixed bottom bar */}
                <div style={{ height: 140 }} />
                <div ref={mainPanelRef} />
              </div>

              {/* BOTTOM FIXED CONTROL (mic) */}
              <div className="border-t border-gray-700 p-4 shrink-0 bg-darkbg-card">
                <div className="flex items-center justify-between max-w-4xl mx-auto">
                  <div className="hidden md:flex items-center gap-4 text-sm text-gray-400">
                    <span>Press the mic to answer</span>
                    <span className="px-2 py-1 rounded bg-white/5">Auto-stop + send</span>
                  </div>

                  <div className="flex items-center gap-4">
                    {/* Mic toggle */}
                    {isListening ? (
                      <button
                        onClick={stopListening}
                        className="w-16 h-16 rounded-full bg-red-600 hover:bg-red-700 flex items-center justify-center shadow-lg transition-all animate-pulse"
                        aria-label="Stop recording"
                      >
                        <MicOff className="w-6 h-6 text-white" />
                      </button>
                    ) : (
                      <button
                        onClick={startListening}
                        disabled={isSpeaking}
                        className="w-16 h-16 rounded-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed flex items-center justify-center shadow-lg transition-all"
                        aria-label="Start recording"
                      >
                        <Mic className="w-6 h-6 text-white" />
                      </button>
                    )}

                    {/* small status / progress */}
                    <div className="text-right">
                      <div className="text-xs text-gray-400">Question</div>
                      <div className="text-sm font-medium">{currentCount} / {maxCount}</div>
                    </div>
                  </div>
                </div>

                <p className="text-center text-gray-500 text-xs mt-3">
                  {isListening ? "Recording... Click mic to stop" : isSpeaking ? "AI is speaking..." : "Click mic to answer"}
                </p>
              </div>
            </section>

            {/* RIGHT SIDEBAR desktop-only: Current Question + Tips */}
            <aside className="hidden lg:flex flex-col space-y-6 h-full">
              <div className="p-4 rounded-xl bg-[#07121a] border border-neon-primary/10 shadow-[0_0_20px_var(--neon-primary)/10]">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-neon-primary font-semibold flex items-center gap-2">
                    <MessageSquare className="w-4 h-4" /> Current Question
                  </h3>
                  <div className="px-2 py-0.5 rounded-full bg-white/5 text-sm">{currentCount} / {maxCount}</div>
                </div>

                <p className="text-sm text-gray-200 bg-white/5 p-3 rounded-lg leading-relaxed">
                  {interviewData?.questions?.[currentCount - 1]?.question_text || "Waiting for next question..."}
                </p>
              </div>

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
      </div>

      {/* MOBILE BOTTOM DRAWER */}
      <div
        className={`fixed left-0 right-0 bottom-0 z-40 md:hidden transition-transform duration-300 ${
          drawerOpen ? "translate-y-0" : "translate-y-full"
        }`}
        aria-hidden={!drawerOpen}
      >
        <div className="mx-4 mb-4 bg-darkbg-card border border-white/6 rounded-t-xl shadow-xl overflow-hidden max-h-[70vh]">
          <div className="p-4 flex items-center justify-between border-b border-white/6">
            <h4 className="text-neon-primary font-semibold flex items-center gap-2">
              <MessageSquare className="w-4 h-4" /> Questions & Tips
            </h4>

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
                {interviewData?.questions?.[currentCount - 1]?.question_text || "Waiting for next question..."}
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

      {/* CONFIRM MODAL */}
      {confirmOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-darkbg-card p-6 rounded-xl border border-white/10 shadow-xl w-[90%] max-w-md text-center">
            <h3 className="text-xl font-semibold text-white mb-4">Are you sure?</h3>

            <p className="text-gray-300 mb-6">{confirmText}</p>

            <div className="flex items-center justify-center space-x-4">
              <button
                className="px-5 py-2 rounded-lg bg-red-600/20 text-red-400 border border-red-400/40 hover:bg-red-600/30 transition"
                onClick={() => {
                  try {
                    const action = confirmActionRef.current;
                    if (action) action();
                  } catch (e) {
                    console.error("confirm action error:", e);
                  } finally {
                    confirmActionRef.current = null;
                    setConfirmOpen(false);
                  }
                }}
              >
                Yes, Continue
              </button>

              <button
                className="px-5 py-2 rounded-lg border border-white/20 text-gray-300 hover:bg-white/10 transition"
                onClick={() => {
                  confirmActionRef.current = null;
                  setConfirmOpen(false);
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
