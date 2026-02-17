#!/usr/bin/env python3
"""
Minimal test script to verify build environment
"""

from kivy.app import App
from kivy.uix.label import Label

class TestApp(App):
    def build(self):
        return Label(text='Hello Jarvis!')

if __name__ == '__main__':
    TestApp().run()