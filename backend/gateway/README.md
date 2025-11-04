# VRSecretary Gateway

FastAPI backend service for VRSecretary that orchestrates LLM and TTS requests.

## Features

- **Multi-backend LLM support**: Ollama (local) and IBM watsonx.ai (cloud)
- **TTS integration**: Chatterbox for high-quality voice synthesis
- **Session management**: Track conversation context
- **Engine-agnostic API**: Works with Unreal, Unity, or any HTTP client

## Installation

```bash
pip install -e .
```

With watsonx support:
```bash
pip install -e ".[watsonx]"
```

Development tools:
```bash
pip install -e ".[dev]"
```

## Configuration

Copy the example environment file:
```bash
cp ../docker/env.example .env
```

Edit `.env` with your settings:

```env
# Backend mode: offline_local_ollama | online_watsonx
MODE=offline_local_ollama

# Ollama settings
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3

# Chatterbox TTS settings
CHATTERBOX_URL=http://localhost:4123

# watsonx.ai settings (if using online mode)
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_PROJECT_ID=your-project-id
WATSONX_MODEL_ID=ibm/granite-13b-chat-v2
WATSONX_API_KEY=your-api-key
```

## Running

### Development
```bash
uvicorn vrsecretary_gateway.main:app --reload --host 0.0.0.0 --port 8000
```

### Production
```bash
uvicorn vrsecretary_gateway.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### With Docker
```bash
cd ../docker
docker-compose -f docker-compose.dev.yml up
```

## API Endpoints

### Health Check
```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "ok",
  "mode": "offline_local_ollama",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### VR Chat
```bash
curl -X POST http://localhost:8000/api/vr_chat   -H "Content-Type: application/json"   -d '{"session_id": "test-123", "user_text": "Hello, how are you?"}'
```

Response:
```json
{
  "assistant_text": "Hello! I'm doing well, thank you...",
  "audio_wav_base64": "UklGRiQAAABXQVZF..."
}
```

## Testing

```bash
pytest
```

With coverage:
```bash
pytest --cov=vrsecretary_gateway --cov-report=html
```

## Architecture

```
main.py
  └── FastAPI app
       ├── /health → health_router
       └── /api/vr_chat → vr_chat_router
            ├── LLM Client (Ollama or Watsonx)
            └── TTS Client (Chatterbox)
```

## Development

### Adding a New LLM Backend

1. Create `vrsecretary_gateway/llm/your_client.py`:
```python
from .base_client import BaseLLMClient
from typing import List
from ..models.chat_schemas import ChatMessage

class YourClient(BaseLLMClient):
    async def generate(self, messages: List[ChatMessage]) -> str:
        # Your implementation
        pass
```

2. Register in `base_client.py`:
```python
def get_llm_client() -> BaseLLMClient:
    if settings.mode == "your_mode":
        return YourClient()
    # ...
```

### Code Style

Format with Black:
```bash
black vrsecretary_gateway/
```

Lint with Ruff:
```bash
ruff check vrsecretary_gateway/
```

Type check with mypy:
```bash
mypy vrsecretary_gateway/
```

## License

MIT License - see [LICENSE](../../LICENSE)
