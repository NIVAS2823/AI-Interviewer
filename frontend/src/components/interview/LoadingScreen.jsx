// src/components/interview/LoadingScreen.jsx
import React from "react";
import { Loader2 } from "lucide-react";

export function LoadingScreen() {
  return (
    <div className="h-screen flex flex-col items-center justify-center bg-darkbg">
      <Loader2 className="w-12 h-12 text-neon-primary animate-spin" />
      <p className="text-gray-400 mt-3">Initializing voice interview...</p>
    </div>
  );
}