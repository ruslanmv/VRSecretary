from pydantic import BaseModel

class VRChatRequest(BaseModel):
    session_id: str
    user_text: str

class VRChatResponse(BaseModel):
    assistant_text: str
    audio_wav_base64: str

class ChatMessage(BaseModel):
    role: str
    content: str
