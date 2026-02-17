from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    zen_api_base_url: str = "https://api.zen.ai/v1"
    zen_api_key: str = ""

    opencode_api_base_url: str = "https://api.opencode.ai/v1"
    opencode_api_key: str = ""

    groq_api_base_url: str = "https://api.groq.com/openai/v1"
    groq_api_key: str = ""

    letta_api_base_url: str = "https://api.letta.ai/v1"
    letta_api_key: str = ""

    cohere_stt_base_url: str = "https://api.cohere.ai/v1"
    cohere_stt_api_key: str = ""
    cohere_voice_id: str = ""

    backend_secret: str = ""


settings = Settings()
