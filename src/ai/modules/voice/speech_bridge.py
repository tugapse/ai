import re
import random
from typing import Any
import ai.functions as func
from ai.color import Color, format_text

class SpeechBridge:
    """
    Manages the interface between textual content processing and the voice synthesis module.

    This class buffers incoming text, cleans it by removing formatting and special characters,
    and intelligently splits the text into chunks based on sentence boundaries. It handles
    special cases like code blocks and file path transformations to ensure natural
    speech output.
    """
    def __init__(self, voice_module: Any, debug: bool = False):
        """
        Initializes the SpeechBridge.

        Args:
            voice_module: An object conforming to the voice processing interface.
            debug: If True, prints processed text chunks to the console for debugging.
        """
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
        """
        Feeds a chunk of text into the bridge for processing.

        Handles the detection of code blocks (delimited by ```) and processes
        text accordingly.

        Args:
            text: The string chunk received from the source.
        """
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

    def _replace_path_for_voice(self, match):
        """
        Transforms file paths found in text into a more natural phrasing for voice synthesis.

        Replaces internal slashes with spaces to aid pronunciation.

        Args:
            match: The regex match object containing the path content.

        Returns:
            str: The path formatted as a natural phrase (e.g., ", path to file").
        """
        path_content = match.group('path_content')
        # Replace internal slashes with spaces for natural pronunciation
        processed_path = path_content.replace('/', ' ')
        return f", {processed_path}"

    def _process_text_chunk(self, text: str):
        """
        Cleans, transforms, and buffers a chunk of text before sending it to the voice module.

        Removes markdown formatting, list markers, and transforms file paths.
        It splits the text into sentences and sends each complete sentence chunk.

        Args:
            text: The text chunk to be processed.
        """
        text = re.sub(r'#+\s+', '', text) # Remove headers
        text = re.sub(r'\*\*|\*', '', text) # Remove bold/italic markers
        text = re.sub(r'^\s*(\d+\.|[\-\*])\s+', '', text, flags=re.MULTILINE) # Remove list markers
        
        # Transform file paths and commands for voice synthesis
        # Matches a leading slash followed by one or more word characters, dots, slashes, or hyphens.
        text = re.sub(r'/(?P<path_content>[\w./-]+)', self._replace_path_for_voice, text)
        
        self.buffer += text
        matches = list(self.sentence_regex.finditer(self.buffer))
        if matches:
            last_match = matches[-1]
            split_point = last_match.end()
            chunk = self.buffer[:split_point]
            self.buffer = self.buffer[split_point:]
            self._send_to_voice(chunk)

    def flush(self):
        """
        Sends any remaining text in the buffer to the voice module and clears the buffer.

        This should be called when text input ends.
        """
        if self.buffer.strip() and not self.in_code_block:
            self._send_to_voice(self.buffer)
        self.buffer = ""

    def _send_to_voice(self, text: str):
        """
        Cleans the final text and passes it to the voice module for synthesis.

        Args:
            text: The sentence or text chunk to be spoken.
        """
        cleaned_text = re.sub(r'`+', '', text).strip()
        if cleaned_text:
            if self.debug:
                func.out(format_text(f"\n[BRIDGE VOICE]: '{cleaned_text}'\n", Color.YELLOW))
            self.voice.process_token(cleaned_text)

    def abort(self):
        """
        Stops any ongoing speech synthesis and clears the internal buffer state.
        """
        self.buffer = ""
        self.in_code_block = False
        if self.voice: self.voice.abort()