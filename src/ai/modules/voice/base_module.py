import os
import time
import threading
import queue
import numpy as np
import pyaudio
import contextlib
import sys
from abc import ABC, abstractmethod
from typing import Optional
import functions as func

class BaseVoiceModule(ABC):
    """
    Core Voice Orchestrator.
    Updated with 'Buffer Drain' logic to prevent cutting off the end of sentences.
    """
    def __init__(self, sample_rate: int = 24000, device_index: Optional[int] = None):
        self.sample_rate = sample_rate
        self.device_index = device_index
        
        self._text_queue = queue.Queue()
        self._audio_queue = queue.Queue()
        
        self.pa = None
        self.stream = None
        self.active_sample_rate = sample_rate
        
        self._is_running = True
        self._abort_signal = threading.Event()
        
        self._gen_thread = threading.Thread(target=self._generation_loop, daemon=True)
        self._play_thread = threading.Thread(target=self._playback_loop, daemon=True)
        
        self._gen_thread.start()
        self._play_thread.start()

    @contextlib.contextmanager
    def _silence_stderr(self):
        """Suppresses ALSA/JACK/PortAudio noise."""
        new_target = os.open(os.devnull, os.O_WRONLY)
        old_target = os.dup(sys.stderr.fileno())
        try:
            os.dup2(new_target, sys.stderr.fileno())
            yield
        finally:
            os.dup2(old_target, sys.stderr.fileno())
            os.close(old_target)
            os.close(new_target)

    def _init_audio_hardware(self):
        with self._silence_stderr():
            if self.pa is None:
                self.pa = pyaudio.PyAudio()

            rates = [int(self.sample_rate), 44100, 48000]
            for rate in rates:
                try:
                    self.stream = self.pa.open(
                        format=pyaudio.paFloat32,
                        channels=1,
                        rate=rate,
                        output=True,
                        output_device_index=self.device_index,
                        frames_per_buffer=1024
                    )
                    self.active_sample_rate = rate
                    return
                except Exception:
                    continue
        
        func.log("BaseVoice: CRITICAL - No supported sample rate found.", level="ERROR")

    @abstractmethod
    def _run_inference(self, text: str) -> np.ndarray:
        pass

    def process_token(self, text: str):
        if text and self._is_running:
            self._text_queue.put(text)

    def abort(self):
        """Clears queues and signals threads to stop current work."""
        self._abort_signal.set()
        while not self._text_queue.empty():
            try: self._text_queue.get_nowait(); self._text_queue.task_done()
            except: break
        while not self._audio_queue.empty():
            try: self._audio_queue.get_nowait(); self._audio_queue.task_done()
            except: break
        self._abort_signal.clear()

    def _generation_loop(self):
        while self._is_running:
            try:
                text = self._text_queue.get(timeout=0.5)
                if text is None: break
                if not self._abort_signal.is_set():
                    audio = self._run_inference(text)
                    if audio is not None and len(audio) > 0:
                        self._audio_queue.put(audio)
                self._text_queue.task_done()
            except queue.Empty:
                continue

    def _playback_loop(self):
        while self._is_running:
            try:
                audio_chunk = self._audio_queue.get(timeout=0.5)
                if audio_chunk is None: break

                if self.stream is None:
                    self._init_audio_hardware()

                if self.stream and not self._abort_signal.is_set():
                    # Resampling logic
                    if self.active_sample_rate != self.sample_rate:
                        duration = len(audio_chunk) / self.sample_rate
                        num_samples = int(duration * self.active_sample_rate)
                        audio_chunk = np.interp(
                            np.linspace(0, len(audio_chunk), num_samples),
                            np.arange(len(audio_chunk)),
                            audio_chunk
                        ).astype(np.float32)

                    try:
                        self.stream.write(audio_chunk.tobytes())
                    except Exception:
                        self.stream = None 
                
                self._audio_queue.task_done()
            except queue.Empty:
                continue

    def collect_audio(self):
        """
        Wait for all text to be generated and all audio to be played.
        Added a dynamic wait to ensure the hardware buffer drains.
        """
        # 1. Wait for the model to finish generating all chunks
        self._text_queue.join()
        
        # 2. Wait for the playback thread to finish sending chunks to the hardware
        self._audio_queue.join()
        
        # 3. THE FIX: Wait for the sound card's internal buffer to actually play.
        # Most hardware buffers are 200ms-500ms. A 0.8s wait is a safe 'tail'.
        if self.stream and self.stream.is_active():
            time.sleep(2)

    def shutdown(self):
        self._is_running = False
        self._text_queue.put(None)
        self._audio_queue.put(None)
        
        with self._silence_stderr():
            if self.stream:
                try:
                    self.stream.stop_stream()
                    self.stream.close()
                except: pass
            if self.pa:
                try: self.pa.terminate()
                except: pass
        
        func.log("BaseVoice: Hardware released.")