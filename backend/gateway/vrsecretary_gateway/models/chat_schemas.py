from pydantic import BaseModel


class VRChatRequest(BaseModel):
    """
    Request from Unreal’s VRSecretaryComponent (Gateway mode).

    The plugin sends:
      {
        "session_id": "<GUID or any string>",
        "user_text": "Hello Ailey, ..."
      }
    """
    session_id: str
    user_text: str


class VRChatResponse(BaseModel):
    """
    Response consumed by the Unreal plugin.

    - assistant_text: AI text reply (for subtitles, logs, etc.)
    - audio_wav_base64: base64-encoded WAV (for TTS playback)
    """
    assistant_text: str
    audio_wav_base64: str


class ChatMessage(BaseModel):
    """
    Internal representation of chat messages used by LLMs.
    Compatible with OpenAI-style chat completions.
    """
    role: str   # "system", "user", "assistant"
    content: str
