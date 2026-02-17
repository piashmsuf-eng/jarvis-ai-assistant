import httpx

from app.config import settings


class CohereSttClient:
    def __init__(self) -> None:
        self._base_url = settings.cohere_stt_base_url.rstrip("/")
        self._api_key = settings.cohere_stt_api_key
        self._voice_id = settings.cohere_voice_id

    async def transcribe(self, audio_bytes: bytes) -> dict:
        url = f"{self._base_url}/speech-to-text"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "X-Voice-ID": self._voice_id,
        }
        files = {"audio": ("audio.wav", audio_bytes, "audio/wav")}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, headers=headers, files=files)
            response.raise_for_status()
            return response.json()
