from pydantic import BaseSettings

class Settings(BaseSettings):
    mode: str = "offline_local_ollama"  # or 'online_watsonx'
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    chatterbox_url: str = "http://localhost:4123"

    watsonx_url: str | None = None
    watsonx_project_id: str | None = None
    watsonx_model_id: str | None = None
    watsonx_api_key: str | None = None

    class Config:
        env_file = ".env"

settings = Settings()
