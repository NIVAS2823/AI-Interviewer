// src/hooks/useVoiceInterview.js
import { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { interviewAPI } from "../lib/api";
import { AudioRecorder, AudioPlayer } from "../lib/audioUtils";
import { VoiceInterviewClient } from "../lib/voiceClient";
import toast from "react-hot-toast";

const MAX_ANSWER_DURATION = 90;
const WARNING_TIME = 30;
const MAX_AUDIO_BYTES = 1_048_576;
const OPUS_BITRATE_BPS = 128_000;
const MAX_DYNAMIC_DURATION = Math.floor(
  MAX_AUDIO_BYTES / (OPUS_BITRATE_BPS / 8));

export function useVoiceInterview(interviewId) {
  const navigate = useNavigate();

  // State
  const [loading, setLoading] = useState(true);
  const [interviewData, setInterviewData] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState("connecting");
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [currentMessage, setCurrentMessage] = useState("");
  const [questionProgress, setQuestionProgress] = useState({
    current: 0,
    total: 0,
  });
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingMessage, setProcessingMessage] = useState("");
  const [recordingTimer, setRecordingTimer] = useState(null);
  const [recordingTimeLeft, setRecordingTimeLeft] = useState(MAX_ANSWER_DURATION);

  // Refs
  const recorderRef = useRef(null);
  const playerRef = useRef(null);
  const wsClientRef = useRef(null);
  const hasInitRef = useRef(false);
  const isProcessingRef = useRef(false);
  const processingTimeoutRef = useRef(null);

  // Initialize audio
  const initAudio = async () => {
    try {
      recorderRef.current = new AudioRecorder();
      const ok = await recorderRef.current.initialize();
      if (!ok) throw new Error("Microphone access denied");

      playerRef.current = new AudioPlayer();
      await playerRef.current.initialize?.();

      // console.log("✅ Audio initialized");
    } catch (err) {
      console.error("❌ Audio init error:", err);
      toast.error("Microphone access required");
      throw err;
    }
  };

  // Clear processing state
  const clearProcessingState = useCallback(() => {
    // console.log("🧹 Clearing processing state");
    
    // Clear timeout if exists
    if (processingTimeoutRef.current) {
      clearTimeout(processingTimeoutRef.current);
      processingTimeoutRef.current = null;
    }
    
    setIsProcessing(false);
    isProcessingRef.current = false;
    setProcessingMessage("");
  }, []);

  // Handle AI messages
  const handleAIMessage = useCallback(async (data) => {
    try {
      const text = data.text || "";
      // console.log("🤖 AI Message:", data.type, "| Text length:", text.length);
      
      // CRITICAL: Clear processing state immediately
      clearProcessingState();
      
      setCurrentMessage(text);

      if (data.metadata) {
        // console.log("📊 Metadata:", data.metadata);
        setQuestionProgress({
          current: data.metadata.question_number || questionProgress.current,
          total: data.metadata.total_questions || questionProgress.total,
        });
      }

      // Play audio
      if (data.audio && playerRef.current) {
        // console.log("🔊 Playing audio...");
        setIsSpeaking(true);
        try {
          await playerRef.current.playBase64Audio(data.audio);
          // console.log("✅ Audio playback complete");
        } catch (e) {
          console.error("❌ Playback error:", e);
        } finally {
          setIsSpeaking(false);
        }

        // Handle greeting acknowledgment
        if (data.type === "greeting") {
          // console.log("👋 Sending greeting_ack");
          if (wsClientRef.current?.ws?.readyState === WebSocket.OPEN) {
            wsClientRef.current.ws.send(JSON.stringify({ type: "greeting_ack" }));
          }
          return;
        }

        // Small delay before ready state
        await new Promise((r) => setTimeout(r, 400));
      }

      // ✅ DO NOT auto-start listening
      // After question or acknowledgment, just clear transcript and wait for user to click mic
      if (data.type === "question" || data.type === "acknowledgment") {
        // console.log("✅ Ready for user to start answering (waiting for mic click)");
        setTranscript("");
        // User must manually click the mic button to start recording
      }

      // For closing message, don't start listening
      if (data.type === "closing") {
        // console.log("👋 Interview closing, no more recording needed");
      }
    } catch (err) {
      console.error("❌ handleAIMessage error:", err);
      setIsSpeaking(false);
      clearProcessingState();
    }
  }, [clearProcessingState, questionProgress]);

  // Handle interview complete
  const handleInterviewComplete = useCallback(() => {
    // console.log("✅ Interview completed by server");
    clearProcessingState();
    toast.success("Interview complete!");
    setTimeout(() => navigate(`/interviews/${interviewId}`), 1200);
  }, [clearProcessingState, navigate, interviewId]);

  // Handle WebSocket messages
  const handleMessage = useCallback(async (data) => {
    // Debug logging
    const timestamp = new Date().toISOString().split('T')[1].split('.')[0];
    // console.log(`📨 [${timestamp}] WS Message:`, data?.type);

    if (!data || !data.type) {
      console.warn("⚠️ Invalid message received:", data);
      return;
    }

    switch (data.type) {
      case "greeting":
      case "question":
      case "acknowledgment":
      case "closing":
        // console.log(`✅ Handling ${data.type} message`);
        await handleAIMessage(data);
        break;

      case "transcription":
        // console.log("📝 Transcription received:", data.text?.substring(0, 100));
        clearProcessingState();
        setTranscript(data.text || "");
        break;

      case "metadata":
        // console.log("📊 Metadata update:", data.metadata);
        if (data.metadata) {
          setQuestionProgress({
            current: data.metadata.question_number || questionProgress.current,
            total: data.metadata.total_questions || questionProgress.total,
          });
        }
        break;

      case "interview_complete":
        // console.log("🏁 Interview complete message received");
        handleInterviewComplete();
        break;

      case "error":
        if (data.code === "AUDIO_LIMIT_EXCEEDED") {
    toast.error("Answer too long. Please keep it under 1 minute.");
  } else {
    toast.error(data.message || "Error occurred");
  }
        // console.error("❌ WS Error message:", data.message);
        // clearProcessingState();
        // toast.error(data.message || "Speech recognition failed");
        // // Don't auto-restart - let user click mic when ready
        // break;

      case "pong":
        // Heartbeat response - ignore
        break;

      case "binary":
        // console.log("📦 Binary message received");
        break;

      default:
        console.warn("❓ Unknown WS message type:", data.type);
    }
  }, [handleAIMessage, handleInterviewComplete, clearProcessingState, questionProgress]);

  // Initialize WebSocket
  const initWebSocket = async () => {
    try {
      const token = localStorage.getItem("token");
      if (!token) throw new Error("Authentication token missing");

      const client = new VoiceInterviewClient(interviewId, token);
      client.maxReconnectAttempts = 0;
      wsClientRef.current = client;

      client.on("open", () => {
        // console.log("✅ WebSocket connected");
        setConnectionStatus("connected");
        toast.success("Connected to AI interviewer");
      });

      // IMPORTANT: Bind handleMessage
      client.on("message", handleMessage);

      client.on("error", (e) => {
        console.error("❌ WS error:", e);
        setConnectionStatus("error");
        clearProcessingState();
        toast.error("Connection lost");
      });

      client.on("close", () => {
        // console.log("🔌 WebSocket closed");
        setConnectionStatus("disconnected");
        clearProcessingState();
      });

      await client.connect();
    } catch (err) {
      console.error("❌ WS init error:", err);
      toast.error("Cannot connect to interviewer");
      throw err;
    }
  };

  // Send audio to backend
  const sendAudioToBackend = async (audioBlob) => {
    try {
      // console.log("📤 Sending audio:", audioBlob.size, "bytes");
      
      setIsProcessing(true);
      isProcessingRef.current = true;
      setProcessingMessage("Processing your answer...");

      if (wsClientRef.current && wsClientRef.current.sendAudio) {
        await wsClientRef.current.sendAudio(audioBlob);
      } else if (
        wsClientRef.current?.ws &&
        wsClientRef.current.ws.readyState === WebSocket.OPEN
      ) {
        wsClientRef.current.ws.send(audioBlob);
      } else {
        throw new Error("WebSocket not connected");
      }

      // Progressive messages
      setTimeout(() => {
        if (isProcessingRef.current) {
          setProcessingMessage("Transcribing your answer...");
        }
      }, 5000);

      setTimeout(() => {
        if (isProcessingRef.current) {
          setProcessingMessage("Generating next question...");
        }
      }, 10000);

      setTimeout(() => {
        if (isProcessingRef.current) {
          setProcessingMessage("This is taking longer than usual, please wait...");
        }
      }, 20000);

      // Safety timeout - if still processing after 40s, clear state
      processingTimeoutRef.current = setTimeout(() => {
        if (isProcessingRef.current) {
          console.warn("⚠️ Processing timeout (40s) - forcing clear");
          clearProcessingState();
          toast.error("Processing timeout. Please try answering again.");
        }
      }, 40000);
    } catch (error) {
      console.error("❌ Failed to send audio:", error);
      toast.error("Failed to send audio");
      clearProcessingState();
    }
  };

  // Start listening - ONLY called when user clicks mic button
  const startListening = async () => {
    try {
      if (!recorderRef.current) {
        console.error("❌ Recorder not available");
        toast.error("Recorder not available");
        return;
      }

      if (isProcessingRef.current) {
        console.warn("⚠️ Still processing previous answer");
        toast.error("Still processing your previous answer...");
        return;
      }

      if (isListening) {
        console.warn("⚠️ Already listening");
        return;
      }

      if (isSpeaking) {
        console.warn("⚠️ AI is still speaking");
        toast.error("Please wait for the interviewer to finish speaking");
        return;
      }

      // console.log("🎤 Starting to record (user clicked mic)");
      setTranscript("");
      setIsListening(true);
      setRecordingTimeLeft(Math.min(MAX_ANSWER_DURATION, MAX_DYNAMIC_DURATION));


      await recorderRef.current.startRecording(
  (bytes) => {
    const remainingBytes = MAX_AUDIO_BYTES - bytes;
    const remainingSeconds = Math.max(
      0,
      Math.floor(remainingBytes / (OPUS_BITRATE_BPS / 8))
    );
    setRecordingTimeLeft(remainingSeconds);
  },
  () => {
    toast.info("Max answer length reached. Submitting...");
    stopListening();
  }
);

      // Start countdown timer - FRESH TIMER every time
      let timeLeft = MAX_ANSWER_DURATION;
      const timerId = setInterval(() => {
        timeLeft -= 1;
        setRecordingTimeLeft(timeLeft);

        if (timeLeft === WARNING_TIME) {
          // console.log(`⚠️ ${WARNING_TIME} seconds left`);
          toast(`⚠️ ${WARNING_TIME} seconds remaining`, { 
            duration: 2000,
            icon: '⏰',
            style: {
              background: '#f59e0b',
              color: '#fff',
            }
          });
        }

        if (timeLeft <= 10 && timeLeft > 0) {
          // Visual warning in last 10 seconds
          // console.log(`⏰ ${timeLeft} seconds left`);
        }

        if (timeLeft <= 0) {
          clearInterval(timerId);
          setRecordingTimer(null);
          // console.log("⏱️ Maximum answer duration reached - auto-stopping");
          toast.info("Time limit reached. Submitting your answer...");
          stopListening();
        }
      }, 1000);

      setRecordingTimer(timerId);
    } catch (err) {
      console.error("❌ startListening error:", err);
      setIsListening(false);
      if (recordingTimer) {
        clearInterval(recordingTimer);
        setRecordingTimer(null);
      }
      toast.error("Cannot start recording");
    }
  };

  // Stop listening
  const stopListening = async () => {
    try {
      // console.log("🛑 Stopping recording");
      
      // Clear timer FIRST
      if (recordingTimer) {
        clearInterval(recordingTimer);
        setRecordingTimer(null);
      }

      if (!recorderRef.current) {
        toast.error("Recorder not available");
        setIsListening(false);
        return;
      }

      setIsListening(false);

      const audioBlob = await recorderRef.current.stopRecording();

      if (audioBlob && audioBlob.size > 0) {
        await sendAudioToBackend(audioBlob);
      } else {
        console.warn("⚠️ No audio recorded");
        toast.error("No audio recorded. Please try again.");
        // Don't auto-restart - user must click mic again
      }
    } catch (err) {
      console.error("❌ stopListening error:", err);
      toast.error("Failed to stop recording");
      clearProcessingState();
    }
  };

  // End interview
  const endInterview = async () => {
    try {
      // console.log("🏁 Ending interview");
      toast.loading("Ending interview...");

      // Stop any ongoing recording
      if (recordingTimer) {
        clearInterval(recordingTimer);
        setRecordingTimer(null);
      }

      // Cleanup
      try {
        wsClientRef.current?.stop?.();
        wsClientRef.current?.disconnect?.();
      } catch (e) {
        console.warn("ws cleanup error", e);
      }

      try {
        playerRef.current?.stop?.();
      } catch (e) {}

      try {
        if (recorderRef.current && isListening) {
          await recorderRef.current.stopRecording();
        }
      } catch (e) {}

      await interviewAPI.end(interviewId);
      toast.dismiss();
      toast.success("Interview completed!");
      setTimeout(() => navigate(`/interviews/${interviewId}`), 400);
    } catch (err) {
      toast.dismiss();
      console.error("❌ end interview error:", err);
      toast.error("Failed to end interview");
      setTimeout(() => navigate(`/interviews/${interviewId}`), 800);
    }
  };

  // Initialize interview
  const initializeInterview = async () => {
    try {
      setLoading(true);

      const res = await interviewAPI.get(interviewId);
      const interview = res.data;

      if (interview.status === "completed") {
        toast.error("This interview has already been completed.");
        navigate(`/interviews/${interviewId}`);
        return;
      }

      if (interview.status === "created") {
        await interviewAPI.start(interviewId);
        await new Promise((r) => setTimeout(r, 1200));
        const updated = await interviewAPI.get(interviewId);
        setInterviewData(updated.data);
      } else {
        setInterviewData(interview);
      }

      if (!recorderRef.current) {
        await initAudio();
      }
      if (!wsClientRef.current) {
        await initWebSocket();
      }

      setLoading(false);
    } catch (err) {
      console.error("❌ Init error:", err);
      toast.error("Failed to initialize interview");
      navigate("/interviews");
    }
  };

  // Cleanup
  const cleanup = async () => {
    // console.log("🧹 Cleaning up resources");
    
    if (processingTimeoutRef.current) {
      clearTimeout(processingTimeoutRef.current);
    }
    
    if (recordingTimer) {
      clearInterval(recordingTimer);
    }

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

  // Initialize on mount
  useEffect(() => {
    if (!hasInitRef.current) {
      hasInitRef.current = true;
      initializeInterview();
    }
    return () => {
      cleanup();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [interviewId]);

  return {
    // State
    loading,
    interviewData,
    connectionStatus,
    isListening,
    isSpeaking,
    transcript,
    currentMessage,
    questionProgress,
    isProcessing,
    processingMessage,
    recordingTimeLeft,
    
    // Actions
    startListening,
    stopListening,
    endInterview,
  };
}