import httpx

from app.config import settings


class LettaTtsClient:
    def __init__(self) -> None:
        self._base_url = settings.letta_api_base_url.rstrip("/")
        self._api_key = settings.letta_api_key

    async def synthesize(self, text: str, emotion: str = "neutral") -> bytes:
        url = f"{self._base_url}/tts"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        payload = {
            "text": text,
            "emotion": emotion,
            "format": "wav",
        }
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.content
