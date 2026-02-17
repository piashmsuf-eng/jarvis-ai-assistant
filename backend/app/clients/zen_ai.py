import httpx

from app.config import settings


class ZenAiClient:
    def __init__(self) -> None:
        self._base_url = settings.zen_api_base_url.rstrip("/")
        self._api_key = settings.zen_api_key

    async def analyze(self, text: str, context: str = "") -> dict:
        url = f"{self._base_url}/analyze"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        payload = {
            "text": text,
            "context": context,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
