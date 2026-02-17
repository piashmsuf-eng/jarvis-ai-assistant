#!/usr/bin/env python3
"""
Jarvis AI Assistant - Simplified Android Version
Focused on core functionality with better Android compatibility
"""

import os
import sys
import json
import asyncio
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

# Third-party imports - only essentials
import requests
from dotenv import load_dotenv

# Kivy imports for mobile UI
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
from kivymd.app import MDApp
from kivymd.uix.button import MDRaisedButton, MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.card import MDCard

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GroqLLMEngine:
    """Groq API integration for ultra-fast LLM responses"""
    
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY", "")
        self.model = os.getenv("GROQ_MODEL", "llama3-70b-8192")
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.conversation_history = []
        
    def generate_response(self, prompt: str) -> str:
        """Generate response using Groq LLM"""
        try:
            if not self.api_key:
                return "Please set GROQ_API_KEY in your environment"
            
            # Add user message to history
            self.conversation_history.append({"role": "user", "content": prompt})
            
            # Keep last 10 messages
            messages = self.conversation_history[-10:]
            
            # Make API call
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1024
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result['choices'][0]['message']['content']
                
                # Add assistant response to history
                self.conversation_history.append({
                    "role": "assistant", 
                    "content": ai_response
                })
                
                return ai_response
            else:
                return f"Error: {response.status_code} - {response.text}"
                
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return f"Error generating response: {str(e)}"


class SimpleTTS:
    """Simple TTS using Android's built-in TTS or fallback"""
    
    def speak(self, text: str):
        """Speak text using available TTS"""
        try:
            # Try to use plyer TTS (works on Android)
            from plyer import tts
            tts.speak(text)
        except Exception as e:
            logger.warning(f"TTS not available: {e}")
            # Fallback - just log the text
            logger.info(f"Would speak: {text}")


class JarvisAssistant:
    """Main Jarvis Assistant class"""
    
    def __init__(self):
        self.llm = GroqLLMEngine()
        self.tts = SimpleTTS()
        
    def generate_response(self, user_input: str) -> str:
        """Generate AI response"""
        return self.llm.generate_response(user_input)
        
    def speak_response(self, text: str):
        """Speak the response"""
        self.tts.speak(text)


class JarvisApp(MDApp):
    """Kivy/KivyMD Mobile UI Application"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.assistant = JarvisAssistant()
        
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
            text="Welcome to Jarvis AI Assistant\n\nNote: This is a simplified version for better Android compatibility.\n\n",
            readonly=True,
            multiline=True,
            size_hint=(1, 0.6)
        )
        main_layout.add_widget(self.chat_display)
        
        # Input area
        input_layout = BoxLayout(size_hint=(1, 0.15), spacing=10)
        
        self.text_input = MDTextField(
            hint_text="Type your message...",
            size_hint=(0.8, 1)
        )
        input_layout.add_widget(self.text_input)
        
        # Send button
        send_btn = MDRaisedButton(
            text="Send",
            size_hint=(0.2, 1),
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
            
    def send_message(self, instance):
        """Send text message"""
        message = self.text_input.text.strip()
        if message:
            self.chat_display.text += f"\nYou: {message}\n"
            self.text_input.text = ""
            self.status_label.text = "Processing..."
            
            # Process in a thread to avoid blocking UI
            Clock.schedule_once(lambda dt: self.process_message(message), 0.1)
            
    def process_message(self, message: str):
        """Process the message and get response"""
        try:
            response = self.assistant.generate_response(message)
            self.chat_display.text += f"Jarvis: {response}\n"
            
            # Try to speak the response
            try:
                self.assistant.speak_response(response)
            except:
                pass  # Ignore TTS errors
                
        except Exception as e:
            logger.error(f"Message processing error: {e}")
            self.chat_display.text += f"Error: {str(e)}\n"
        finally:
            self.status_label.text = "Ready"


def main():
    """Main entry point"""
    app = JarvisApp()
    app.run()


if __name__ == "__main__":
    main()