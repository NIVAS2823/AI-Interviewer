// src/pages/VoiceInterviewRoom.jsx
import React, { useState, useRef } from "react";
import { useParams } from "react-router-dom";
import { useVoiceInterview } from "../hooks/useVoiceInterview";
import { useElapsedTime } from "../hooks/useElapsedTime";
import { useConfirmation } from "../hooks/useConfirmation";
import { InterviewHeader } from "../components/interview/InterviewHeader";
import { AIAvatar } from "../components/interview/AIAvatar";
import { MessageDisplay } from "../components/interview/MessageDisplay";
import { RecordingControls } from "../components/interview/RecordingControls";
import { InterviewSidebar } from "../components/interview/InterviewSidebar";
import { MobileDrawer } from "../components/interview/MobileDrawer";
import { ConfirmationModal } from "../components/interview/ConfirmationModal";
import { ProcessingOverlay } from "../components/interview/ProcessingOverlay";
import { LoadingScreen } from "../components/interview/LoadingScreen";

export default function VoiceInterviewRoom() {
  const { id } = useParams();
  
  // Custom hooks
  const {
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
    startListening,
    stopListening,
    endInterview,
  } = useVoiceInterview(id);

  const { formattedTime } = useElapsedTime();
  
  const {
    isOpen: confirmOpen,
    confirmText,
    askConfirm,
    handleConfirm,
    handleCancel,
  } = useConfirmation();

  // Local state
  const [drawerOpen, setDrawerOpen] = useState(false);
  const mainPanelRef = useRef(null);

  // Handle end interview with confirmation
  const handleEndInterview = () => {
    askConfirm("End interview and generate evaluation?", endInterview);
  };

  // Show loading screen
  if (loading) {
    return <LoadingScreen />;
  }

  return (
    <>
      <div className="h-screen flex flex-col bg-darkbg text-gray-200">
        {/* Header */}
        <InterviewHeader
          interviewId={id}
          interviewData={interviewData}
          formattedTime={formattedTime}
          questionProgress={questionProgress}
          onEndInterview={handleEndInterview}
        />

        {/* Main Content Grid */}
        <div className="flex-1 min-h-0 overflow-hidden">
          <div className="h-full grid grid-cols-1 lg:grid-cols-4 gap-6 p-5 min-h-0">
            
            {/* Main Panel */}
            <section className="lg:col-span-3 flex flex-col bg-darkbg-card rounded-xl border border-white/6 shadow-2xl min-h-0 overflow-hidden">
              <div
                className="flex-1 overflow-y-auto p-8 flex flex-col items-center"
                id="mainPanel"
              >
                {/* AI Avatar */}
                <AIAvatar
                  isSpeaking={isSpeaking}
                  isListening={isListening}
                  connectionStatus={connectionStatus}
                />

                {/* Messages */}
                <MessageDisplay
                  currentMessage={currentMessage}
                  transcript={transcript}
                />

                {/* Spacer for fixed controls */}
                <div style={{ height: 140 }} />
                <div ref={mainPanelRef} />
              </div>

              {/* Recording Controls */}
              <RecordingControls
                isListening={isListening}
                isSpeaking={isSpeaking}
                isProcessing={isProcessing}
                processingMessage={processingMessage}
                recordingTimeLeft={recordingTimeLeft}
                questionProgress={questionProgress}
                onStartListening={startListening}
                onStopListening={stopListening}
              />
            </section>

            {/* Sidebar - Desktop only */}
            <InterviewSidebar />
          </div>
        </div>
      </div>

      {/* Mobile Drawer */}
      <MobileDrawer
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        interviewData={interviewData}
        questionProgress={questionProgress}
      />

      {/* Confirmation Modal */}
      <ConfirmationModal
        isOpen={confirmOpen}
        confirmText={confirmText}
        onConfirm={handleConfirm}
        onCancel={handleCancel}
      />

      {/* Processing Overlay */}
      <ProcessingOverlay
        isProcessing={isProcessing}
        processingMessage={processingMessage}
      />
    </>
  );
}