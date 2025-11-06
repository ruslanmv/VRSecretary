# backend/gateway/vrsecretary_gateway/models/session_store.py
"""
Simple in-memory session storage for conversation history.

NOTE:
- This is fine for local / development.
- For production you should swap this for a shared store (Redis, database, etc.)
  to support multiple processes / instances.
"""

from __future__ import annotations

from typing import Dict, List

from .chat_schemas import ChatMessage

# In-memory storage: session_id -> list[ChatMessage]
_sessions: Dict[str, List[ChatMessage]] = {}


async def get_session_history(session_id: str, max_messages: int = 10) -> List[ChatMessage]:
    """
    Get recent conversation history for a session.

    Parameters
    ----------
    session_id:
        Identifier for the session whose history we want.
    max_messages:
        Maximum number of most recent messages to return.

    Returns
    -------
    List[ChatMessage]
        Up to `max_messages` most recent messages for the given session,
        or an empty list if the session has no history.
    """
    history = _sessions.get(session_id, [])
    if not history:
        return []
    return history[-max_messages:]


async def save_to_history(session_id: str, messages: List[ChatMessage]) -> None:
    """
    Append messages to a session's history.

    Parameters
    ----------
    session_id:
        Identifier for the session to update.
    messages:
        List of ChatMessage instances to append.
    """
    if session_id not in _sessions:
        _sessions[session_id] = []
    _sessions[session_id].extend(messages)


async def clear_session(session_id: str) -> None:
    """
    Clear a session's history.

    Parameters
    ----------
    session_id:
        Identifier for the session to clear.
    """
    if session_id in _sessions:
        del _sessions[session_id]
