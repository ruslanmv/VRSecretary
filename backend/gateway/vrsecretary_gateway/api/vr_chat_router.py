import logging
from typing import List

from fastapi import APIRouter, Depends

from ..config import settings
from ..llm.base_client import BaseLLMClient, get_llm_client
from ..models.chat_schemas import VRChatRequest, VRChatResponse, ChatMessage
from ..models.session_store import get_session_history, save_to_history
from ..tts.chatterbox_client import tts_wav_base64_async, ChatterboxTtsError

router = APIRouter()
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are Ailey, a helpful, professional VR secretary. "
    "You work in a virtual office, talk to the user through voice, and keep your "
    "answers concise because they will be spoken aloud. "
    "Be friendly but efficient, and focus on practical help (planning, drafting, "
    "summaries, next steps)."
)


@router.post("/vr_chat", response_model=VRChatResponse)
async def vr_chat(
    req: VRChatRequest,
    llm: BaseLLMClient = Depends(get_llm_client),
) -> VRChatResponse:
    """
    Main chat endpoint used by the Unreal VRSecretaryComponent (Gateway mode).

    Unreal sends:
      {
        "session_id": "<session>",
        "user_text": "Hello Ailey..."
      }

    We:
      1. Load recent history for this session.
      2. Build a message list with system prompt + history + new user message.
      3. Call the LLM (Ollama).
      4. Call Chatterbox TTS (non-streaming) on the assistant text.
      5. Return assistant_text + audio_wav_base64.
    """
    session_id = req.session_id or "default"

    # 1) Get recent history
    history: List[ChatMessage] = await get_session_history(
        session_id=session_id,
        max_messages=settings.session_max_history,
    )

    # 2) Build messages (system + history + new user message)
    messages: List[ChatMessage] = [ChatMessage(role="system", content=SYSTEM_PROMPT)]
    messages.extend(history)

    user_msg = ChatMessage(role="user", content=req.user_text)
    messages.append(user_msg)

    # 3) Call LLM
    assistant_text = await llm.generate(messages)
    assistant_msg = ChatMessage(role="assistant", content=assistant_text)

    # Persist conversation for this session
    await save_to_history(session_id, [user_msg, assistant_msg])

    # 4) Call TTS – non-streaming, one WAV
    audio_b64 = ""
    try:
        audio_b64 = await tts_wav_base64_async(assistant_text)
    except ChatterboxTtsError as exc:
        logger.warning("TTS failed for session %s: %s", session_id, exc)
        # We still return the text; Unreal can handle text-only replies.

    # 5) Return in the shape the Unreal plugin expects
    return VRChatResponse(
        assistant_text=assistant_text,
        audio_wav_base64=audio_b64,
    )
