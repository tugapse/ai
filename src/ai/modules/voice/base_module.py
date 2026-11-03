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
import ai.functions as func

class BaseVoiceModule(ABC):
    """
    Core Voice Orchestrator.

    This abstract base class manages the entire pipeline for text-to-speech (TTS)
    generation and audio playback. It handles threading, hardware initialization,
    volume control, and ensures proper buffer draining to prevent audio clipping.
    """
    def __init__(self, sample_rate: int = 24000, device_index: Optional[int] = None, volume: float = 1.0):
        """
        Initializes the voice module components.

        Args:
            sample_rate: The desired sample rate for audio processing (default 24000 Hz).
            device_index: Optional index of the audio output device to use.
            volume: The playback volume multiplier (clamped between 0.0 and 2.0).
        """
        self.sample_rate = sample_rate
        self.device_index = device_index
        self.volume = np.clip(volume, 0.0, 2.0)  # Store and sanitize volume (0x to 2x)
        
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
        """
        Suppresses ALSA/JACK/PortAudio noise by redirecting stderr to /dev/null.

        Yields:
            None
        """
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
        """
        Initializes the PyAudio stream, attempting to find a compatible sample rate.

        If initialization fails for all tested rates, it logs a critical error.
        """
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
        """
        Abstract method to be implemented by subclasses.

        Runs the core TTS model inference on the given text.

        Args:
            text: The input string to be converted to speech.

        Returns:
            A numpy array representing the generated audio waveform, or None if generation fails.
        """
        pass

    def process_token(self, text: str):
        """
        Adds a new piece of text to the processing queue.

        Args:
            text: The text string to be queued for TTS generation.
        """
        if text and self._is_running:
            self._text_queue.put(text)

    def abort(self):
        """
        Stops all ongoing generation and playback processes immediately.

        Clears both the text and audio queues and signals the worker threads to terminate.
        """
        self._abort_signal.set()
        while not self._text_queue.empty():
            try: self._text_queue.get_nowait(); self._text_queue.task_done()
            except: break
        while not self._audio_queue.empty():
            try: self._audio_queue.get_nowait(); self._audio_queue.task_done()
            except: break
        self._abort_signal.clear()

    def _generation_loop(self):
        """
        The dedicated thread loop responsible for consuming text and generating audio.

        It pulls text from _text_queue, calls _run_inference, and places the resulting
        audio data into _audio_queue.
        """
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
        """
        The dedicated thread loop responsible for consuming audio and playing it via hardware.

        It pulls audio from _audio_queue, handles resampling, applies volume, and writes
        the data to the active audio stream.
        """
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

                    # Apply volume adjustment
                    if self.volume != 1.0:
                        audio_chunk *= self.volume

                    try:
                        self.stream.write(audio_chunk.tobytes())
                    except Exception:
                        self.stream = None 
                
                self._audio_queue.task_done()
            except queue.Empty:
                continue

    def collect_audio(self):
        """
        Waits for the entire speech sequence to complete playback.

        This method ensures that all queued text has been processed into audio,
        and critically, it waits for the underlying audio hardware buffer to drain
        completely before returning, preventing abrupt audio cuts.
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
        """
        Gracefully stops all threads and releases all audio hardware resources.

        Signals the running flag to false, sends termination signals to queues,
        and closes the PyAudio stream and terminates the PyAudio instance.
        """
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