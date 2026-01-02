// src/hooks/useConfirmation.js
import { useState, useRef } from "react";

export function useConfirmation() {
  const [isOpen, setIsOpen] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const confirmActionRef = useRef(null);

  const askConfirm = (text, action) => {
    setConfirmText(text);
    confirmActionRef.current = action;
    setIsOpen(true);
  };

  const handleConfirm = () => {
    try {
      const action = confirmActionRef.current;
      if (action) action();
    } catch (e) {
      console.error("Confirmation action error:", e);
    } finally {
      confirmActionRef.current = null;
      setIsOpen(false);
    }
  };

  const handleCancel = () => {
    confirmActionRef.current = null;
    setIsOpen(false);
  };

  return {
    isOpen,
    confirmText,
    askConfirm,
    handleConfirm,
    handleCancel,
  };
}