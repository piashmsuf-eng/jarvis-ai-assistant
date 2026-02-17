# Jarvis AI Assistant (Android + Backend)

Jarvis-style assistant with:
- Zen AI API (NLU + decision making)
- OpenCode AI (primary agent)
- Groq AI (high performance fallback)
- Cohere Voice ID (STT)
- Letta.ai (TTS with emotional tones)

## Architecture
```
android/   -> Kotlin Android client (voice, wake word, tasks)
backend/   -> FastAPI backend (routing to AI engines)
```

## Backend (FastAPI)
### Setup
```
cd backend
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Endpoints
- `POST /v1/stt` (audio/wav) -> Cohere STT
- `POST /v1/nlu` -> Zen AI NLU
- `POST /v1/agent` -> OpenCode/Groq chat
- `POST /v1/tts` -> Letta TTS
- `GET /v1/health`

## Android (Kotlin)
### Build
```
cd android
gradle :app:assembleDebug
```

### Notes
- App sends WAV audio to backend `/v1/stt`
- Wake word: checks for `"hey jarvis"` in transcription
- TTS audio is played from `/v1/tts`

## CI/CD
GitHub Actions runs:
- Backend tests (`pytest backend/tests`)
- Android build (`gradle :app:assembleDebug`)

## Required API Keys
Set in `backend/.env`:
- `ZEN_API_KEY`
- `OPENCODE_API_KEY`
- `GROQ_API_KEY`
- `LETTA_API_KEY`
- `COHERE_STT_API_KEY`
- `COHERE_VOICE_ID`

## Security
- Store secrets in `.env` only
- Add encryption if storing any user data
