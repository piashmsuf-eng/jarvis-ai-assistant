#!/usr/bin/env python3
"""
Jarvis AI Assistant - Modern Implementation
Integrates Groq LLM, Cartesia TTS, Letta Memory, and Whisper STT
"""

import os
import sys
import asyncio
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

# Third-party imports
import numpy as np
from dotenv import load_dotenv
from groq import Groq
import httpx
import websockets
import json
from faster_whisper import WhisperModel
import sounddevice as sd
from scipy.io.wavfile import write as write_wav
import tempfile
from tenacity import retry, stop_after_attempt, wait_exponential

# Kivy imports for mobile UI
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivymd.app import MDApp
from kivymd.uix.button import MDRaisedButton, MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.card import MDCard
from kivymd.uix.scrollview import MDScrollView
from plyer import tts as plyer_tts

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AssistantState(Enum):
    """States for the assistant"""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    ERROR = "error"


@dataclass
class AudioConfig:
    """Audio configuration settings"""
    sample_rate: int = int(os.getenv("AUDIO_SAMPLE_RATE", 16000))
    chunk_size: int = int(os.getenv("AUDIO_CHUNK_SIZE", 1024))
    channels: int = 1
    dtype: str = 'int16'


class GroqLLMEngine:
    """Groq API integration for ultra-fast LLM responses"""
    
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = os.getenv("GROQ_MODEL", "llama3-70b-8192")
        self.conversation_history = []
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def generate_response(self, prompt: str, context: Optional[Dict] = None) -> str:
        """Generate response using Groq LLM"""
        try:
            # Add user message to history
            self.conversation_history.append({"role": "user", "content": prompt})
            
            # Include context from Letta if available
            messages = []
            if context and "memory" in context:
                messages.append({
                    "role": "system",
                    "content": f"Context from memory: {context['memory']}"
                })
            
            messages.extend(self.conversation_history[-10:])  # Keep last 10 messages
            
            # Make API call
            completion = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1024,
                stream=False
            )
            
            response = completion.choices[0].message.content
            
            # Add assistant response to history
            self.conversation_history.append({"role": "assistant", "content": response})
            
            return response
            
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            raise


class CartesiaTTS:
    """Cartesia AI Sonic Model for ultra-low latency streaming TTS"""
    
    def __init__(self):
        self.api_key = os.getenv("CARTESIA_API_KEY")
        self.voice_id = os.getenv("CARTESIA_VOICE_ID", "sonic-english")
        self.model_id = os.getenv("CARTESIA_MODEL_ID", "sonic-multilingual-v1")
        self.ws_endpoint = os.getenv("CARTESIA_STREAM_ENDPOINT", "wss://api.cartesia.ai/v1/stream")
        self.audio_config = AudioConfig()
        self.audio_buffer = []
        
    async def stream_speech(self, text: str, callback=None):
        """Stream speech with ultra-low latency"""
        try:
            # Connect to Cartesia WebSocket
            async with websockets.connect(
                self.ws_endpoint,
                extra_headers={"Authorization": f"Bearer {self.api_key}"}
            ) as websocket:
                
                # Send synthesis request
                request = {
                    "type": "synthesize",
                    "text": text,
                    "voice_id": self.voice_id,
                    "model_id": self.model_id,
                    "output_format": {
                        "container": "raw",
                        "encoding": "pcm",
                        "sample_rate": self.audio_config.sample_rate
                    },
                    "streaming": True
                }
                
                await websocket.send(json.dumps(request))
                
                # Stream audio chunks
                async for message in websocket:
                    data = json.loads(message)
                    
                    if data["type"] == "audio":
                        audio_chunk = np.frombuffer(
                            bytes.fromhex(data["audio"]), 
                            dtype=np.int16
                        )
                        self.audio_buffer.append(audio_chunk)
                        
                        # Play audio immediately for low latency
                        if callback:
                            await callback(audio_chunk)
                        else:
                            sd.play(audio_chunk, self.audio_config.sample_rate)
                            
                    elif data["type"] == "done":
                        break
                    elif data["type"] == "error":
                        logger.error(f"Cartesia error: {data.get('message')}")
                        break
                        
        except Exception as e:
            logger.error(f"Cartesia streaming error: {e}")
            raise


class LettaMemory:
    """Letta.ai (MemGPT) for long-term memory and context retention"""
    
    def __init__(self):
        self.api_key = os.getenv("LETTA_API_KEY")
        self.agent_id = os.getenv("LETTA_AGENT_ID")
        self.user_id = os.getenv("LETTA_USER_ID", "default_user")
        self.api_url = os.getenv("LETTA_API_URL", "https://api.letta.ai/v1")
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        
    async def store_interaction(self, user_input: str, assistant_response: str):
        """Store interaction in long-term memory"""
        try:
            payload = {
                "agent_id": self.agent_id,
                "user_id": self.user_id,
                "messages": [
                    {"role": "user", "content": user_input},
                    {"role": "assistant", "content": assistant_response}
                ]
            }
            
            response = await self.client.post(
                f"{self.api_url}/memory/store",
                json=payload
            )
            
            if response.status_code == 200:
                logger.info("Memory stored successfully")
            else:
                logger.error(f"Memory storage failed: {response.text}")
                
        except Exception as e:
            logger.error(f"Letta memory error: {e}")
            
    async def retrieve_context(self, query: str) -> Dict:
        """Retrieve relevant context from memory"""
        try:
            response = await self.client.post(
                f"{self.api_url}/memory/retrieve",
                json={
                    "agent_id": self.agent_id,
                    "user_id": self.user_id,
                    "query": query,
                    "top_k": 5
                }
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Memory retrieval failed: {response.text}")
                return {}
                
        except Exception as e:
            logger.error(f"Letta retrieval error: {e}")
            return {}


class WhisperSTT:
    """Whisper-based Speech-to-Text using faster-whisper"""
    
    def __init__(self):
        model_name = os.getenv("WHISPER_MODEL", "base")
        device = os.getenv("WHISPER_DEVICE", "cpu")
        self.language = os.getenv("WHISPER_LANGUAGE", "en")
        
        # Initialize Whisper model
        self.model = WhisperModel(
            model_name, 
            device=device,
            compute_type="int8" if device == "cpu" else "float16"
        )
        self.audio_config = AudioConfig()
        
    async def transcribe_audio(self, audio_data: np.ndarray) -> str:
        """Transcribe audio to text"""
        try:
            # Save audio to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                write_wav(tmp_file.name, self.audio_config.sample_rate, audio_data)
                
                # Transcribe using faster-whisper
                segments, info = await asyncio.to_thread(
                    self.model.transcribe,
                    tmp_file.name,
                    language=self.language,
                    beam_size=5,
                    vad_filter=True
                )
                
                # Combine segments
                transcription = " ".join([segment.text for segment in segments])
                
                # Clean up
                os.unlink(tmp_file.name)
                
                return transcription.strip()
                
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            return ""
            
    def record_audio(self, duration: int = 5) -> np.ndarray:
        """Record audio from microphone"""
        logger.info(f"Recording for {duration} seconds...")
        recording = sd.rec(
            int(duration * self.audio_config.sample_rate),
            samplerate=self.audio_config.sample_rate,
            channels=self.audio_config.channels,
            dtype=self.audio_config.dtype
        )
        sd.wait()
        return recording.flatten()


class JarvisAssistant:
    """Main Jarvis Assistant class integrating all components"""
    
    def __init__(self):
        self.state = AssistantState.IDLE
        self.llm = GroqLLMEngine()
        self.tts = CartesiaTTS()
        self.memory = LettaMemory()
        self.stt = WhisperSTT()
        
    async def process_voice_input(self) -> str:
        """Process voice input pipeline"""
        self.state = AssistantState.LISTENING
        
        # Record audio
        audio_data = self.stt.record_audio(duration=5)
        
        # Transcribe
        self.state = AssistantState.PROCESSING
        transcription = await self.stt.transcribe_audio(audio_data)
        logger.info(f"Transcribed: {transcription}")
        
        return transcription
        
    async def generate_response(self, user_input: str) -> str:
        """Generate AI response with memory context"""
        # Retrieve relevant context
        context = await self.memory.retrieve_context(user_input)
        
        # Generate response
        response = await self.llm.generate_response(user_input, context)
        
        # Store interaction in memory
        await self.memory.store_interaction(user_input, response)
        
        return response
        
    async def speak_response(self, text: str):
        """Speak the response using streaming TTS"""
        self.state = AssistantState.SPEAKING
        await self.tts.stream_speech(text)
        self.state = AssistantState.IDLE
        
    async def run_interaction(self):
        """Run a complete interaction cycle"""
        try:
            # Get voice input
            user_input = await self.process_voice_input()
            
            if user_input:
                # Generate response
                response = await self.generate_response(user_input)
                
                # Speak response
                await self.speak_response(response)
                
        except Exception as e:
            logger.error(f"Interaction error: {e}")
            self.state = AssistantState.ERROR


class JarvisApp(MDApp):
    """Kivy/KivyMD Mobile UI Application"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.assistant = JarvisAssistant()
        self.is_listening = False
        
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Blue"
        
        # Main layout
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Header
        header = MDCard(
            orientation='vertical',
            size_hint=(1, 0.15),
            elevation=10,
            padding=10
        )
        header.add_widget(Label(
            text="JARVIS AI Assistant",
            font_size='24sp',
            bold=True
        ))
        main_layout.add_widget(header)
        
        # Chat display
        self.chat_display = TextInput(
            text="Welcome to Jarvis AI Assistant\n",
            readonly=True,
            multiline=True,
            size_hint=(1, 0.6)
        )
        main_layout.add_widget(self.chat_display)
        
        # Input area
        input_layout = BoxLayout(size_hint=(1, 0.15), spacing=10)
        
        self.text_input = MDTextField(
            hint_text="Type your message or use voice...",
            size_hint=(0.7, 1)
        )
        input_layout.add_widget(self.text_input)
        
        # Voice button
        self.voice_btn = MDIconButton(
            icon="microphone",
            size_hint=(0.15, 1),
            on_press=self.toggle_voice
        )
        input_layout.add_widget(self.voice_btn)
        
        # Send button
        send_btn = MDRaisedButton(
            text="Send",
            size_hint=(0.15, 1),
            on_press=self.send_message
        )
        input_layout.add_widget(send_btn)
        
        main_layout.add_widget(input_layout)
        
        # Status bar
        self.status_label = Label(
            text="Ready",
            size_hint=(1, 0.1)
        )
        main_layout.add_widget(self.status_label)
        
        return main_layout
        
    def toggle_voice(self, instance):
        """Toggle voice recording"""
        if not self.is_listening:
            self.is_listening = True
            self.voice_btn.icon = "stop"
            self.status_label.text = "Listening..."
            Clock.schedule_once(self.process_voice, 0.1)
        else:
            self.is_listening = False
            self.voice_btn.icon = "microphone"
            self.status_label.text = "Processing..."
            
    def process_voice(self, dt):
        """Process voice input asynchronously"""
        asyncio.create_task(self._async_process_voice())
        
    async def _async_process_voice(self):
        """Async voice processing"""
        try:
            # Get voice input
            user_input = await self.assistant.process_voice_input()
            
            if user_input:
                # Update UI
                self.chat_display.text += f"\nYou: {user_input}\n"
                
                # Generate and speak response
                response = await self.assistant.generate_response(user_input)
                self.chat_display.text += f"Jarvis: {response}\n"
                
                await self.assistant.speak_response(response)
                
        except Exception as e:
            logger.error(f"Voice processing error: {e}")
        finally:
            self.is_listening = False
            self.voice_btn.icon = "microphone"
            self.status_label.text = "Ready"
            
    def send_message(self, instance):
        """Send text message"""
        message = self.text_input.text.strip()
        if message:
            self.chat_display.text += f"\nYou: {message}\n"
            self.text_input.text = ""
            self.status_label.text = "Processing..."
            asyncio.create_task(self._async_send_message(message))
            
    async def _async_send_message(self, message: str):
        """Async message processing"""
        try:
            response = await self.assistant.generate_response(message)
            self.chat_display.text += f"Jarvis: {response}\n"
            await self.assistant.speak_response(response)
        except Exception as e:
            logger.error(f"Message processing error: {e}")
        finally:
            self.status_label.text = "Ready"


async def main():
    """Main entry point"""
    # Check for required environment variables
    required_vars = ["GROQ_API_KEY", "CARTESIA_API_KEY", "LETTA_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.info("Please copy .env.example to .env and fill in your API keys")
        sys.exit(1)
        
    # Run the Kivy app
    app = JarvisApp()
    
    # For mobile compatibility, run in async mode
    if sys.platform in ["android", "ios"]:
        await app.async_run()
    else:
        app.run()


if __name__ == "__main__":
    # Set up async event loop
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(main())