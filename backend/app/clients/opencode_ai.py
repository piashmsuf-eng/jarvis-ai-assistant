import httpx

from app.config import settings


class OpencodeClient:
    def __init__(self) -> None:
        self._base_url = settings.opencode_api_base_url.rstrip("/")
        self._api_key = settings.opencode_api_key

    async def chat(self, messages: list[dict], model: str = "zed-code-v3") -> dict:
        url = f"{self._base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.4,
            "max_tokens": 1024,
        }
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
