import os
import sys
import threading
import queue
import time
import numpy as np
import copy
import logging
import contextlib

# Kill HuggingFace/Transformers noise
logging.getLogger("transformers").setLevel(logging.ERROR)
os.environ["TOKENIZERS_PARALLELISM"] = "false"

class VibeVoiceEngine:
    
    def __init__(self, model_id="microsoft/VibeVoice-Realtime-0.5B", voice_file=None, device_index=13):
        self.model_id = model_id
        self.sample_rate = 24000
        self.voice_file = voice_file
        self.device_index = device_index 
        
        self._text_buffer = ""
        self._audio_segments = []
        self._token_queue = queue.Queue()
        self._audio_queue = queue.Queue()
        
        # THREAD SIGNALS
        self._abort_signal = threading.Event()
        self._initialized = False
        self._is_running = True
        
        self.torch = None
        self.sf = None
        self.pyaudio = None
        self.pa = None      
        self.stream = None  
        self.processor = None
        self.model = None
        self.device = None
        self.model_dtype = None
        self.voice_embeddings = None

        self.gen_thread = threading.Thread(target=self._generation_loop, daemon=True)
        self.play_thread = threading.Thread(target=self._playback_loop, daemon=True)
        self.gen_thread.start()
        self.play_thread.start()

    @contextlib.contextmanager
    def _silence_system_stderr(self):
        """Redirects low-level system C-stderr to /dev/null to hide ALSA noise."""
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
            with self._silence_system_stderr():
                try:
                    import torch
                    import soundfile as sf
                    import pyaudio
                    from vibevoice import VibeVoiceStreamingForConditionalGenerationInference, VibeVoiceStreamingProcessor
                    
                    self.torch = torch
                    self.sf = sf
                    self.pyaudio = pyaudio
                    self.device = "cuda" if torch.cuda.is_available() else "cpu"
                    self.model_dtype = torch.float16 if "cuda" in self.device else torch.float32
                    
                    if self.pa is None: self.pa = pyaudio.PyAudio()
                    if self.stream is None:
                        self.stream = self.pa.open(
                            format=pyaudio.paFloat32,
                            channels=1,
                            rate=self.sample_rate,
                            output=True,
                            output_device_index=self.device_index,
                            frames_per_buffer=1024
                        )

                    current_file_path = os.path.dirname(os.path.abspath(__file__))
                    voices_dir = os.path.abspath(os.path.join(current_file_path, "..", "..", "..", "voices"))
                    if not os.path.exists(voices_dir):
                        voices_dir = os.path.abspath(os.path.join(current_file_path, "..", "..", "voices"))

                    available_voices = [f for f in os.listdir(voices_dir) if f.endswith('.pt')]
                    selected_voice = self.voice_file if self.voice_file in available_voices else available_voices[0]
                    
                    raw_embeddings = torch.load(os.path.join(voices_dir, selected_voice), map_location=self.device, weights_only=False)
                    self.voice_embeddings = self._recursive_cast(raw_embeddings)
                    self.processor = VibeVoiceStreamingProcessor.from_pretrained(self.model_id)
                    self.model = VibeVoiceStreamingForConditionalGenerationInference.from_pretrained(self.model_id, torch_dtype=self.model_dtype).to(self.device)
                    self._initialized = True
                except Exception: pass

           

    def abort(self):
        """Instantly clears queues. Playback loop will skip current chunk if writing."""
        self._abort_signal.set()
        
        # Clear Text Queue
        with self._token_queue.mutex:
            self._token_queue.queue.clear()
            self._token_queue.unfinished_tasks = 0
            self._token_queue.all_tasks_done.notify_all()
            
        # Clear Audio Queue
        with self._audio_queue.mutex:
            self._audio_queue.queue.clear()
            self._audio_queue.unfinished_tasks = 0
            self._audio_queue.all_tasks_done.notify_all()

        self._text_buffer = ""
        self._audio_segments = []
        
        # We don't stop the stream here anymore to avoid the ALSA deadlock.
        # The _playback_loop will check the signal before/after writes.
        time.sleep(0.1) 
        self._abort_signal.clear()

    def process_token(self, token: str):
        if not self._abort_signal.is_set():
            self._token_queue.put(token)

    def _recursive_cast(self, obj):
        if isinstance(obj, self.torch.Tensor):
            if obj.is_floating_point():
                return obj.to(device=self.device, dtype=self.model_dtype)
            return obj.to(device=self.device)
        elif isinstance(obj, dict):
            for k, v in list(obj.items()):
                obj[k] = self._recursive_cast(v)
            return obj
        elif isinstance(obj, list):
            return [self._recursive_cast(v) for v in obj]
        return obj

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
                if any(p in token for p in [".", "!", "?", "\n", ":"]) or len(self._text_buffer.split()) > 20:
                    self._generate_chunk(self._text_buffer.strip())
                    self._text_buffer = "" 
                self._token_queue.task_done()
            except queue.Empty: continue

    def _generate_chunk(self, text):
        if not text or self._abort_signal.is_set(): return
        self._lazy_init()
        try:
            raw_inputs = self.processor.process_input_with_cached_prompt(text=text, cached_prompt=self.voice_embeddings, padding=True, return_tensors="pt")
            inputs = self._recursive_cast(raw_inputs)
            tokenizer = getattr(self.processor, "tokenizer", self.processor)
            with self.torch.no_grad():
                prompt_cache = self._recursive_cast(copy.deepcopy(self.voice_embeddings))
                autocast_device = "cuda" if "cuda" in self.device else "cpu"
                with self.torch.amp.autocast(device_type=autocast_device, dtype=self.model_dtype):
                    output = self.model.generate(**inputs, tokenizer=tokenizer, cfg_scale=1.5, all_prefilled_outputs=prompt_cache)
            
            if self._abort_signal.is_set(): return
            
            if hasattr(output, 'speech_outputs') and output.speech_outputs:
                audio_tensor = self.torch.cat(output.speech_outputs, dim=-1) if len(output.speech_outputs) > 1 else output.speech_outputs[0]
            else:
                audio_tensor = output.wav if hasattr(output, 'wav') else output.audio
            
            audio_np = audio_tensor.cpu().numpy().squeeze().astype(np.float32)
            self._audio_segments.append(audio_np)
            self._audio_queue.put(audio_np)
        except Exception: pass

    def _playback_loop(self):
        while self._is_running:
            try:
                audio_chunk = self._audio_queue.get(timeout=0.1)
                if audio_chunk is None: break
                
                # Check signal BEFORE writing to hardware
                if self._abort_signal.is_set():
                    self._audio_queue.task_done()
                    continue
                
                if self.stream:
                    # We write without the lock. If abort() clears the queue, 
                    # we finish this ONE chunk and then skip the rest.
                    try:
                        self.stream.write(audio_chunk.tobytes(), exception_on_underflow=False)
                    except Exception:
                        pass
                
                self._audio_queue.task_done()
            except queue.Empty: continue

    def finalize_speech(self, output_dir="outputs/audio"):
        if not self._initialized: return None
        self._token_queue.put("<<FLUSH>>")
        
        # Use a timeout loop to allow Abort to break the wait
        while not self._token_queue.empty() or not self._audio_queue.empty():
            if self._abort_signal.is_set(): return None
            time.sleep(0.05)
            
        if self._audio_segments:
            os.makedirs(output_dir, exist_ok=True)
            filename = os.path.join(output_dir, f"jarvis_{int(time.time())}.wav")
            full_audio = np.concatenate(self._audio_segments)
            self.sf.write(filename, full_audio, self.sample_rate)
            self._audio_segments = []
            return filename
        return None

    def shutdown(self):
        self._is_running = False
        self._token_queue.put(None)
        if hasattr(self, 'gen_thread'): self.gen_thread.join(timeout=0.5)
        if hasattr(self, 'play_thread'): self.play_thread.join(timeout=0.5)
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except: pass
        if self.pa: self.pa.terminate()