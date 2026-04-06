import os
import sys
import threading
import queue
import time
import numpy as np
import logging
import contextlib
from abc import ABC, abstractmethod
from typing import Optional

class BaseVoiceModule(ABC):
    def __init__(self, sample_rate=24000, device_index=13):
        self.sample_rate = sample_rate
        self.device_index = device_index
        
        self._text_buffer = ""
        self._audio_segments = []
        self._token_queue = queue.Queue()
        self._audio_queue = queue.Queue()
        
        self._abort_signal = threading.Event()
        self._initialized = False
        self._is_running = True
        
        self.pa = None      
        self.stream = None  
        self.sf = None

        self.gen_thread = threading.Thread(target=self._generation_loop, daemon=True)
        self.play_thread = threading.Thread(target=self._playback_loop, daemon=True)
        self.gen_thread.start()
        self.play_thread.start()

    @abstractmethod
    def _initialize_model(self): pass

    @abstractmethod
    def _run_inference(self, text) -> np.ndarray: pass

    def _init_audio_hardware(self):
        import pyaudio
        import soundfile as sf
        self.sf = sf
        if self.pa is None: self.pa = pyaudio.PyAudio()
        if self.stream is None:
            # Use Int16 for maximum Linux ALSA/Pipewire compatibility
            self.stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                output=True,
                output_device_index=self.device_index,
                frames_per_buffer=1024
            )

    @contextlib.contextmanager
    def _silence_system_stderr(self):
        try:
            new_target = os.open(os.devnull, os.O_WRONLY)
            old_target = os.dup(2)
            sys.stderr.flush()
            os.dup2(new_target, 2)
            os.close(new_target)
            yield
        finally:
            os.dup2(old_target, 2)
            os.close(old_target)

    def preload(self):
        self._lazy_init()

    def _lazy_init(self):
        if not self._initialized:
            # We only silence the C-level noise, Python errors will still show
            with self._silence_system_stderr():
                self._init_audio_hardware()
                self._initialize_model()
                self._initialized = True
            print(f"[*] {self.__class__.__name__}: Logic Integrated.", file=sys.stderr)

    def process_token(self, token: str):
        if not self._abort_signal.is_set():
            self._token_queue.put(token)

    def abort(self):
        """Emergency Stop: Wipes queues without breaking the internal counters."""
        self._abort_signal.set()
        
        try:
            while not self._token_queue.empty():
                self._token_queue.get_nowait()
                self._token_queue.task_done()
        except (queue.Empty, ValueError):
            pass

        try:
            while not self._audio_queue.empty():
                self._audio_queue.get_nowait()
                self._audio_queue.task_done()
        except (queue.Empty, ValueError):
            pass

        self._text_buffer = ""
        self._audio_segments = []
        
        time.sleep(0.1) 
        self._abort_signal.clear()

    def collect_audio(self) -> Optional[np.ndarray]:
        if not self._initialized: return None
        self._token_queue.put("<<FLUSH>>")
        try:
            while not self._token_queue.empty() or not self._audio_queue.empty():
                if self._abort_signal.is_set(): return None
                time.sleep(0.05)
        except KeyboardInterrupt:
            self.abort()
            return None
            
        if self._audio_segments:
            full_audio = np.concatenate(self._audio_segments)
            self._audio_segments = []
            return full_audio
        return None

    def _generation_loop(self):
        while self._is_running:
            try:
                token = self._token_queue.get(timeout=0.1)
                if token is None: break
                if self._abort_signal.is_set():
                    self._token_queue.task_done()
                    continue
                if token == "<<FLUSH>>":
                    if self._text_buffer.strip(): self._generate_chunk(self._text_buffer.strip())
                    self._text_buffer = ""
                    self._token_queue.task_done()
                    continue
                self._text_buffer += token
                if any(p in token for p in [".", "!", "?", ":"]) or len(self._text_buffer.split()) > 20:
                    self._generate_chunk(self._text_buffer.strip())
                    self._text_buffer = "" 
                self._token_queue.task_done()
            except queue.Empty: continue

    def _generate_chunk(self, text):
        if not text or self._abort_signal.is_set(): return
        self._lazy_init()
        try:
            # Get raw float32 [-1.0, 1.0] from child
            audio_np = self._run_inference(text)
            if audio_np is not None and not self._abort_signal.is_set():
                # Save high-quality float for recording segments
                self._audio_segments.append(audio_np)
                
                # CONVERSION: Scale float32 to int16 for the hardware
                audio_int16 = (audio_np * 32767).astype(np.int16)
                self._audio_queue.put(audio_int16)
        except Exception as e:
            print(f"[!] Gen Error: {e}", file=sys.stderr)

    def _playback_loop(self):
        while self._is_running:
            try:
                audio_chunk = self._audio_queue.get(timeout=0.1)
                if audio_chunk is None: break
                if not self._abort_signal.is_set() and self.stream:
                    # Write the raw int16 bytes to the soundcard
                    self.stream.write(audio_chunk.tobytes())
                self._audio_queue.task_done()
            except queue.Empty: continue

    def shutdown(self):
        self._is_running = False
        self._token_queue.put(None)
        if hasattr(self, 'gen_thread'): self.gen_thread.join(timeout=0.5)
        if hasattr(self, 'play_thread'): self.play_thread.join(timeout=0.5)
        if self.stream:
            try: self.stream.stop_stream(); self.stream.close()
            except: pass
        if self.pa: self.pa.terminate()