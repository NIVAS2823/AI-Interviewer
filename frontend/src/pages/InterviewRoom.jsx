import React, { useEffect, useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  MeetingProvider,
  useMeeting,
  useParticipant,
} from "@videosdk.live/react-sdk";
import { interviewAPI } from "../lib/api";
import {
  Mic,
  MicOff,
  Video as VideoIcon,
  VideoOff,
  PhoneOff,
  Loader2,
  Volume2,
  VolumeX,
  MessageSquare,
} from "lucide-react";
import toast from "react-hot-toast";

/* --------------------------------------------------------
   MEETING CONTROLS
--------------------------------------------------------- */
function MeetingControls({ onLeave }) {
  const { localMicOn, localWebcamOn, toggleMic, toggleWebcam, leave } =
    useMeeting();

  const [isMuted, setIsMuted] = useState(false);
  const [isVideoOff, setIsVideoOff] = useState(false);

  // Sync actual VideoSDK state into UI state
  useEffect(() => {
    setIsMuted(!localMicOn);
  }, [localMicOn]);

  useEffect(() => {
    setIsVideoOff(!localWebcamOn);
  }, [localWebcamOn]);

  const handleToggleMic = () => toggleMic();
  const handleToggleWebcam = () => toggleWebcam();

  const handleLeave = () => {
    leave();
    if (onLeave) onLeave();
  };

  return (
    <div className="fixed bottom-8 left-1/2 transform -translate-x-1/2 z-50">
      <div className="bg-gray-900 rounded-full px-6 py-4 flex items-center space-x-4 shadow-2xl">
        <button
          onClick={handleToggleMic}
          className={`w-12 h-12 rounded-full flex items-center justify-center transition-all ${
            isMuted ? "bg-red-500" : "bg-gray-700"
          }`}
        >
          {isMuted ? (
            <MicOff className="w-5 h-5 text-white" />
          ) : (
            <Mic className="w-5 h-5 text-white" />
          )}
        </button>

        <button
          onClick={handleToggleWebcam}
          className={`w-12 h-12 rounded-full flex items-center justify-center transition-all ${
            isVideoOff ? "bg-red-500" : "bg-gray-700"
          }`}
        >
          {isVideoOff ? (
            <VideoOff className="w-5 h-5 text-white" />
          ) : (
            <VideoIcon className="w-5 h-5 text-white" />
          )}
        </button>

        <button
          onClick={handleLeave}
          className="w-12 h-12 rounded-full bg-red-500 hover:bg-red-600 flex items-center justify-center transition-all"
        >
          <PhoneOff className="w-5 h-5 text-white" />
        </button>
      </div>
    </div>
  );
}

/* --------------------------------------------------------
   VIDEO COMPONENT FOR PARTICIPANT (AI or Human)
--------------------------------------------------------- */
function ParticipantView({ participantId }) {
  const { webcamStream, webcamOn, displayName, micOn } =
    useParticipant(participantId);
  const videoRef = useRef(null);

  // Attach video stream
  useEffect(() => {
    if (videoRef.current && webcamStream) {
      const mediaStream = new MediaStream();
      mediaStream.addTrack(webcamStream.track);
      videoRef.current.srcObject = mediaStream;
      videoRef.current.play().catch(() => {});
    }

    return () => {
      if (videoRef.current) videoRef.current.srcObject = null;
    };
  }, [webcamStream]);

  return (
    <div className="relative w-full h-full bg-gray-900 rounded-xl overflow-hidden">
      {webcamOn ? (
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="w-full h-full object-cover"
        />
      ) : (
        <div className="w-full h-full flex flex-col items-center justify-center">
          <div className="w-32 h-32 bg-gradient-to-br from-primary-500 to-primary-700 rounded-full flex items-center justify-center mb-4">
            <span className="text-4xl font-bold text-white">
              {(displayName || "AI").charAt(0).toUpperCase()}
            </span>
          </div>
          <p className="text-white text-lg font-medium">
            {displayName || "AI Interviewer"}
          </p>
        </div>
      )}

      {/* Microphone Status */}
      <div className="absolute bottom-4 left-4">
        {micOn ? (
          <div className="bg-green-500 px-3 py-1 rounded-full flex items-center space-x-2">
            <Volume2 className="w-4 h-4 text-white" />
            <span className="text-white text-sm font-medium">Speaking</span>
          </div>
        ) : (
          <div className="bg-gray-700 px-3 py-1 rounded-full flex items-center space-x-2">
            <VolumeX className="w-4 h-4 text-white" />
            <span className="text-white text-sm font-medium">Muted</span>
          </div>
        )}
      </div>

      {/* Name */}
      <div className="absolute top-4 left-4 bg-black bg-opacity-50 px-3 py-1 rounded-lg">
        <p className="text-white text-sm font-medium">
          {displayName || "AI Interviewer"}
        </p>
      </div>
    </div>
  );
}

/* --------------------------------------------------------
   MEETING VIEW
--------------------------------------------------------- */
function MeetingView({ interviewData, onMeetingLeft }) {
  const { participants } = useMeeting({
    onMeetingLeft: () => onMeetingLeft?.(),
  });

  // FIX: Correctly find AI agent participant
  const aiParticipant = [...participants.values()].find(
    (p) => !p.local && p.mode === "CONFERENCE"
  );

  return (
    <div className="h-screen bg-gray-900 flex flex-col">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <h1 className="text-xl font-bold text-white">Live Interview Session</h1>
        <p className="text-gray-400 text-sm capitalize">
          {interviewData.interview_type.replace("_", " ")} •{" "}
          {interviewData.difficulty}
        </p>
      </div>

      {/* Main layout */}
      <div className="flex-1 p-6 grid grid-cols-1 lg:grid-cols-3 gap-6 h-full">
        <div className="lg:col-span-2">
          {aiParticipant ? (
            <ParticipantView participantId={aiParticipant.id} />
          ) : (
            <div className="w-full h-full bg-gray-800 rounded-xl flex items-center justify-center">
              <div className="text-center">
                <Loader2 className="w-12 h-12 text-primary-500 animate-spin mx-auto mb-4" />
                <p className="text-white">Connecting to AI Interviewer...</p>
              </div>
            </div>
          )}
        </div>

        {/* Questions Sidebar */}
        <div className="space-y-6">
          <div className="bg-gray-800 rounded-xl p-6">
            <div className="flex items-center space-x-2 mb-4">
              <MessageSquare className="w-5 h-5 text-primary-500" />
              <h3 className="text-white font-semibold">Interview Questions</h3>
            </div>

            <div className="space-y-3 max-h-96 overflow-y-auto">
              {interviewData.questions.map((q, idx) => (
                <div key={idx} className="bg-gray-700 rounded-lg p-3">
                  <div className="flex items-start space-x-2">
                    <span className="bg-primary-500 text-white w-6 h-6 flex items-center justify-center rounded-full text-xs font-bold">
                      {idx + 1}
                    </span>
                    <p className="text-gray-200 text-sm">{q.question_text}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Tips */}
          <div className="bg-blue-900 bg-opacity-40 rounded-xl p-6 border border-blue-700">
            <h3 className="text-white font-semibold mb-3">💡 Tips</h3>
            <ul className="text-blue-100 text-sm space-y-1">
              <li>• Speak clearly</li>
              <li>• Maintain eye contact</li>
              <li>• Take pauses naturally</li>
              <li>• Use specific examples</li>
            </ul>
          </div>
        </div>
      </div>

      <MeetingControls onLeave={onMeetingLeft} />
    </div>
  );
}

/* --------------------------------------------------------
   MAIN INTERVIEW ROOM
--------------------------------------------------------- */
export default function InterviewRoom() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [interviewData, setInterviewData] = useState(null);

  useEffect(() => {
    loadInterview();
  }, [id]);

  const loadInterview = async () => {
    try {
      const res = await interviewAPI.get(id);
      setInterviewData(res.data);

      if (!res.data.session_id || !res.data.meeting_token) {
        toast.error("Meeting not initialized");
        navigate(`/interviews/${id}`);
        return;
      }

      if (res.data.status === "created") {
        await interviewAPI.start(id);
        toast.success("Interview starting...");
      }
    } catch (err) {
      console.error(err);
      toast.error("Failed to load interview");
      navigate("/interviews");
    } finally {
      setLoading(false);
    }
  };

  const handleMeetingLeft = async () => {
    try {
      await interviewAPI.end(id);
      toast.success("Interview completed!");
      navigate(`/interviews/${id}`);
    } catch {
      toast.error("Failed to end interview");
    }
  };

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-900">
        <Loader2 className="w-12 h-12 animate-spin text-primary-500" />
      </div>
    );
  }

  return (
    <MeetingProvider
      config={{
        meetingId: interviewData.session_id,
        micEnabled: true,
        webcamEnabled: true,
        name: "Candidate",
        mode: "CONFERENCE", // IMPORTANT!
      }}
      token={interviewData.meeting_token}
      joinWithoutUserInteraction
    >
      <MeetingView interviewData={interviewData} onMeetingLeft={handleMeetingLeft} />
    </MeetingProvider>
  );
}
