"""Simple in-memory session storage (production should use Redis)"""

from typing import Dict, List
from .chat_schemas import ChatMessage

# In-memory storage: session_id -> list of messages
_sessions: Dict[str, List[ChatMessage]] = {}


async def get_session_history(session_id: str, max_messages: int = 10) -> List[ChatMessage]:
    """Get conversation history for a session"""
    history = _sessions.get(session_id, [])
    return history[-max_messages:] if history else []


async def save_to_history(session_id: str, messages: List[ChatMessage]) -> None:
    """Append messages to session history"""
    if session_id not in _sessions:
        _sessions[session_id] = []
    _sessions[session_id].extend(messages)


async def clear_session(session_id: str) -> None:
    """Clear a session's history"""
    if session_id in _sessions:
        del _sessions[session_id]
