from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.clients.cohere_stt import CohereSttClient
from app.clients.groq_ai import GroqClient
from app.clients.letta_tts import LettaTtsClient
from app.clients.opencode_ai import OpencodeClient
from app.clients.zen_ai import ZenAiClient

router = APIRouter()

zen_client = ZenAiClient()
opencode_client = OpencodeClient()
groq_client = GroqClient()
letta_client = LettaTtsClient()
cohere_client = CohereSttClient()


class NluRequest(BaseModel):
    text: str
    context: str = ""


class AgentRequest(BaseModel):
    text: str
    context: list[dict] = []
    provider: str = "opencode"


class TtsRequest(BaseModel):
    text: str
    emotion: str = "neutral"


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.post("/stt")
async def stt(audio: UploadFile = File(...)) -> dict:
    try:
        audio_bytes = await audio.read()
        return await cohere_client.transcribe(audio_bytes)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/nlu")
async def nlu(payload: NluRequest) -> dict:
    try:
        return await zen_client.analyze(payload.text, payload.context)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/agent")
async def agent(payload: AgentRequest) -> dict:
    messages = [{"role": "user", "content": payload.text}]
    if payload.context:
        messages = payload.context + messages

    try:
        if payload.provider == "groq":
            return await groq_client.chat(messages)
        return await opencode_client.chat(messages)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/tts")
async def tts(payload: TtsRequest) -> bytes:
    try:
        return await letta_client.synthesize(payload.text, payload.emotion)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
