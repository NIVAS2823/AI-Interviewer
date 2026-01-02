from typing import Dict, Any
from app.models.interview import ConversationMessage

def normalize_message(msg: Any) -> Dict[str, str]:
    """
    Normalize ConversationMessage | dict into a dict
    """
    if isinstance(msg, ConversationMessage):
        return {
            "speaker": msg.speaker,
            "text": msg.text,
        }

    if isinstance(msg, dict):
        return {
            "speaker": msg.get("speaker") or msg.get("role"),
            "text": msg.get("text") or msg.get("content"),
        }

    return {"speaker": None, "text": None}
