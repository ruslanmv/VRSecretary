from fastapi import APIRouter, Depends
from ..models.chat_schemas import VRChatRequest, VRChatResponse, ChatMessage
from ..llm.base_client import get_llm_client
from ..tts.chatterbox_client import synthesize_with_chatterbox

router = APIRouter()

SYSTEM_PROMPT = (
    "You are Ailey, a helpful, professional VR secretary. "
    "You help with business tasks, planning, and polite conversation."
)

@router.post("/vr_chat", response_model=VRChatResponse)
async def vr_chat(req: VRChatRequest, llm = Depends(get_llm_client)):
    messages = [
        ChatMessage(role="system", content=SYSTEM_PROMPT),
        ChatMessage(role="user", content=req.user_text),
    ]
    assistant_text = await llm.generate(messages)
    wav_bytes = await synthesize_with_chatterbox(assistant_text)

    import base64
    audio_b64 = base64.b64encode(wav_bytes).decode("utf-8")

    return VRChatResponse(
        assistant_text=assistant_text,
        audio_wav_base64=audio_b64,
    )
