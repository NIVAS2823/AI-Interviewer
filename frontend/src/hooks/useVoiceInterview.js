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

  const [loading, setLoading] = useState(true);
  const [interviewData, setInterviewData] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState("connecting");
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [interimTranscript, setInterimTranscript] = useState("");
  const [currentMessage, setCurrentMessage] = useState("");
  const [questionProgress, setQuestionProgress] = useState({
    current: 0,
    total: 0,
  });
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingMessage, setProcessingMessage] = useState("");
  const [recordingTimer, setRecordingTimer] = useState(null);
  const [recordingTimeLeft, setRecordingTimeLeft] = useState(MAX_ANSWER_DURATION);

  const recorderRef = useRef(null);
  const playerRef = useRef(null);
  const wsClientRef = useRef(null);
  const hasInitRef = useRef(false);
  const isProcessingRef = useRef(false);
  const processingTimeoutRef = useRef(null);

  const initAudio = async () => {
    try {
      recorderRef.current = new AudioRecorder();
      const ok = await recorderRef.current.initialize();
      if (!ok) throw new Error("Microphone access denied");

      playerRef.current = new AudioPlayer();
      await playerRef.current.initialize?.();

    } catch (err) {
      console.error("❌ Audio init error:", err);
      toast.error("Microphone access required");
      throw err;
    }
  };

  const clearProcessingState = useCallback(() => {
    
    if (processingTimeoutRef.current) {
      clearTimeout(processingTimeoutRef.current);
      processingTimeoutRef.current = null;
    }
    
    setIsProcessing(false);
    isProcessingRef.current = false;
    setProcessingMessage("");
  }, []);

  const handleAIMessage = useCallback(async (data) => {
    try {
      const text = data.text || "";
      
      clearProcessingState();
      
      setCurrentMessage(text);

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
          console.error("❌ Playback error:", e);
        } finally {
          setIsSpeaking(false);
        }

        if (data.type === "greeting") {
          if (wsClientRef.current?.ws?.readyState === WebSocket.OPEN) {
            wsClientRef.current.ws.send(JSON.stringify({ type: "greeting_ack" }));
          }
          return;
        }

        await new Promise((r) => setTimeout(r, 400));
      }

      if (data.type === "question" || data.type === "acknowledgment") {
        setTranscript("");
        setInterimTranscript("");
      }

      if (data.type === "closing") {
      }
    } catch (err) {
      console.error("❌ handleAIMessage error:", err);
      setIsSpeaking(false);
      clearProcessingState();
    }
  }, [clearProcessingState, questionProgress]);

  const handleInterviewComplete = useCallback(() => {
    clearProcessingState();
    toast.success("Interview complete!");
    setTimeout(() => navigate(`/interviews/${interviewId}`), 1200);
  }, [clearProcessingState, navigate, interviewId]);

  const handleMessage = useCallback(async (data) => {
    const timestamp = new Date().toISOString().split('T')[1].split('.')[0];

    if (!data || !data.type) {
      console.warn("⚠️ Invalid message received:", data);
      return;
    }

    switch (data.type) {
      case "greeting":
      case "question":
      case "acknowledgment":
      case "closing":
        await handleAIMessage(data);
        break;

      case "transcription":
        clearProcessingState();
        setTranscript(data.text || "");
        break;
      
      case "interim_transcript":
        setInterimTranscript(data.text || "");
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
        if (data.code === "AUDIO_LIMIT_EXCEEDED") {
    toast.error("Answer too long. Please keep it under 1 minute.");
  } else {
    toast.error(data.message || "Error occurred");
  }
  break;

      case "pong":
        break;

      case "binary":
        break;

      default:
        console.warn("❓ Unknown WS message type:", data.type);
    }
  }, [handleAIMessage, handleInterviewComplete, clearProcessingState, questionProgress]);

  const initWebSocket = async () => {
    try {
      const token = localStorage.getItem("token");
      if (!token) throw new Error("Authentication token missing");

      const client = new VoiceInterviewClient(interviewId, token);
      client.maxReconnectAttempts = 0;
      wsClientRef.current = client;

      client.on("open", () => {
        setConnectionStatus("connected");
        toast.success("Connected to AI interviewer");
      });

      client.on("message", handleMessage);

      client.on("error", (e) => {
        console.error("❌ WS error:", e);
        setConnectionStatus("error");
        clearProcessingState();
        toast.error("Connection lost");
      });

      client.on("close", () => {
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

  const sendAudioToBackend = async (audioBlob) => {
    try {
      
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

      setTranscript("");
      setInterimTranscript("");
      setIsListening(true);
      setRecordingTimeLeft(Math.min(MAX_ANSWER_DURATION, MAX_DYNAMIC_DURATION));

      if (wsClientRef.current) {
        const started = wsClientRef.current.startStreaming();
        if (!started) {
          console.warn("⚠️ Failed to start streaming, continuing anyway");
        }
      }



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
          toast("Max answer length reached. Submitting...");
          stopListening();
        },
        (pcmBuffer) => {
          if (wsClientRef.current) {
            const sent = wsClientRef.current.sendPCMChunk(pcmBuffer);
            if (!sent) {
              console.warn('⚠️ Failed to send PCM chunk');
            } else {
            }
          } else {
            console.error('❌ No WebSocket client available!');
          }
        }
      );

      let timeLeft = MAX_ANSWER_DURATION;
      const timerId = setInterval(() => {
        timeLeft -= 1;
        setRecordingTimeLeft(timeLeft);

        if (timeLeft === WARNING_TIME) {
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
        }

        if (timeLeft <= 0) {
          clearInterval(timerId);
          setRecordingTimer(null);
          toast("Time limit reached. Submitting your answer...");
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

  const stopListening = async () => {
    try {
      
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

      if (wsClientRef.current) {
        wsClientRef.current.stopStreaming();
        await new Promise(r => setTimeout(r, 100));
      }
      const audioBlob = await recorderRef.current.stopRecording();

      if (audioBlob && audioBlob.size > 0) {
        await sendAudioToBackend(audioBlob);
      } else {
        console.warn("⚠️ No audio recorded");
        toast.error("No audio recorded. Please try again.");
      }
    } catch (err) {
      console.error("❌ stopListening error:", err);
      toast.error("Failed to stop recording");
      clearProcessingState();
    }
  };

  const endInterview = async () => {
    try {
      toast.loading("Ending interview...");

      if (recordingTimer) {
        clearInterval(recordingTimer);
        setRecordingTimer(null);
      }

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

  const cleanup = async () => {
    
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

  useEffect(() => {
    if (!hasInitRef.current) {
      hasInitRef.current = true;
      initializeInterview();
    }
    return () => {
      cleanup();
    };
  }, [interviewId]);

  return {
    loading,
    interviewData,
    connectionStatus,
    isListening,
    isSpeaking,
    transcript,
    interimTranscript,
    currentMessage,
    questionProgress,
    isProcessing,
    processingMessage,
    recordingTimeLeft,
    
    startListening,
    stopListening,
    endInterview,
  };
}