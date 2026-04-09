import re
import random
from typing import Any
from color import Color, format_text
import functions as func

class SpeechBridge:
    def __init__(self, voice_module: Any, debug: bool = False):
        self.voice = voice_module
        self.debug = debug
        self.buffer = ""
        self.in_code_block = False
        self.code_announcements = [
            "I've updated the console with the code.",
            "Technical details are on screen.",
            "Displaying the script now.",
            "Visualizing the logic for you.",
            "The data is on your monitor."
        ]
        self.sentence_regex = re.compile(r'[.?!]+["\']*(?=\s|\n|$)')

    def feed(self, text: str):
        if not self.voice: return
        if "```" in text:
            parts = text.split("```")
            for i, part in enumerate(parts):
                if i > 0:
                    self.in_code_block = not self.in_code_block
                    if self.in_code_block:
                        self._send_to_voice(random.choice(self.code_announcements))
                if not self.in_code_block:
                    self._process_text_chunk(part)
        else:
            if not self.in_code_block:
                self._process_text_chunk(text)

    def _process_text_chunk(self, text: str):
        text = re.sub(r'#+\s+', '', text)
        text = re.sub(r'\*\*|\*', '', text)
        text = re.sub(r'^\s*(\d+\.|[\-\*])\s+', '', text, flags=re.MULTILINE)
        self.buffer += text
        matches = list(self.sentence_regex.finditer(self.buffer))
        if matches:
            last_match = matches[-1]
            split_point = last_match.end()
            chunk = self.buffer[:split_point]
            self.buffer = self.buffer[split_point:]
            self._send_to_voice(chunk)

    def flush(self):
        if self.buffer.strip() and not self.in_code_block:
            self._send_to_voice(self.buffer)
        self.buffer = ""

    def _send_to_voice(self, text: str):
        cleaned_text = re.sub(r'`+', '', text).strip()
        if cleaned_text:
            if self.debug:
                func.out(format_text(f"\n[BRIDGE VOICE]: '{cleaned_text}'\n", Color.YELLOW))
            self.voice.process_token(cleaned_text)

    def abort(self):
        self.buffer = ""
        self.in_code_block = False
        if self.voice: self.voice.abort()