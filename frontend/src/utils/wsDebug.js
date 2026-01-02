// src/utils/wsDebug.js
// Temporary debug utility to log all WebSocket messages

export const logWSMessage = (data, source = "WS") => {
  const timestamp = new Date().toISOString().split('T')[1].split('.')[0];
  
  console.group(`📨 ${source} Message @ ${timestamp}`);
//   console.log("Type:", data?.type);
//   console.log("Full Data:", data);
  
  if (data?.type === "question" || data?.type === "acknowledgment") {
    // console.log("Text:", data?.text?.substring(0, 100));
    // console.log("Audio present:", !!data?.audio);
    // console.log("Metadata:", data?.metadata);
  }
  
  if (data?.type === "transcription") {
    // console.log("Transcript:", data?.text);
  }
  
  console.groupEnd();
  
  return data;
};