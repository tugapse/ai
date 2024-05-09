
import threading
import pyaudio
import wave
import time
from ai.command_executor import AsyncExecutor, ExecutorResult
from ai.color import Color

FORMAT = pyaudio.paInt16  # Audio format (16-bit integer)
CHANNELS = 2  # Number of channels (stereo)
RATE = 44100  # Sample rate (44.1 kHz)
CHUNK = 1024  # Chunk size for reading audio data
RECORD_SECONDS = 10  # Maximum recording time in seconds

LINE_CLEAR = '\x1b[2K'  # ANSI sequence to clear the line

class Microphone(AsyncExecutor):
    """
    Class for recording and processing audio.
    """

    def __init__(self, 
                 max_record_seconds=RECORD_SECONDS,
                 start_recording_text="Start recording...",
                 recording_text="{b_ color}* Recording {s_color}{time} : {max_seconds} {b_color}seconds (press enter to stop recording)",
                 end_recording_text="Recording ended."
                 ) -> None:
        """
        Initializes the Microphone class.
        
        Args:
            max_record_seconds (int): Maximum recording time in seconds. Defaults to 10.
            start_recording_text (str): Text displayed when starting a new recording. Defaults to "Start recording...".
            recording_text (str): Text displayed during the recording process. Defaults to "{b_color}* Recording {s_color}{time} : {max_seconds} {b_color}seconds (press enter to stop recording)".
            end_recording_text (str): Text displayed when a recording ends. Defaults to "Recording ended.".
        """
        super().__init__("/listen", None)
        self.audio = None
        self.frames = []
        self._stream = None
        self._is_running = False
        self.max_record_seconds = max_record_seconds
        self.recording_text = recording_text
        self.start_recording_text = start_recording_text
        self.end_recording_text = end_recording_text

    def _check_input(self):
        """
        Checks for user input and stops the recording if necessary.
        
        Returns:
            None
        """
        user_input = input("")  # Wait for user input (e.g., pressing Enter)
        self.stop_recording()  # Stop the recording
        return None

    def _run_thread(self):
        """
        Internal method to start recording audio.
        """
        # Start recording
        self.audio = pyaudio.PyAudio()
        start_time = time.time()
        self._is_running = True
        self._stream = self.audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
        self.frames = []

        for i in range(0, int(RATE / CHUNK * self.max_record_seconds)):
            data = self._stream.read(CHUNK)
            self.frames.append(data)

            print(end=LINE_CLEAR)  # Clear the line where the cursor is located
            print(self.recording_text
                   .replace("{time}", str(int(time.time() - start_time)))
                   .replace("{max_seconds}", str(RECORD_SECONDS))
                   .replace("{b_color}", Color.RESET)
                   .replace("{s_color}", Color.BLUE), end="\r")  # Update the recording text

            if self._is_running is False:  # Stop the recording if requested
                break

        self.stop_recording()  # Stop the recording
        return None

    def run(self, auto_start=True, wait=True, **kargs):
        """
        Handles user input and starts the recording thread.
        
        Args:
            auto_start (bool): Whether to start the recording automatically. Defaults to True.
            wait (bool): Whether to wait for the recording to finish before returning. Defaults to True.
        """
        super().run(auto_start, wait, **kargs)
        """Handle user input thread"""

    def start_recording(self, callback=None):
        """
        Starts recording audio in a separate thread.
        
        Args:
            callback (function): A function to call when the recording is finished. Defaults to None.
        """
        self.finished_callback = callback
        print(self.start_recording_text)  # Display the start recording text
        self.run()  # Start the recording

    def stop_recording(self):
        """
        Stops recording audio and returns the recorded frames.
        
        Returns:
            frames (list): A list of recorded audio frames.
        """
        self._is_running = False
        self._stream.stop_stream()
        self._stream.close()
        self.audio.terminate()
        print(self.end_recording_text)  # Display the end recording text
        self._trigger_callback(self.frames)
        return self.frames

    def save_as_wave(self, filename):
        """
        Saves the recorded frames as a wave file.
        
        Args:
            filename (str): The name of the output wave file.
        """
        waveFile = wave.open(filename, 'wb')
        waveFile.setnchannels(CHANNELS)
        waveFile.setsampwidth(self.audio.get_sample_size(FORMAT))
        waveFile.setframerate(RATE)
        waveFile.writeframes(b''.join(self.frames))
        waveFile.close()

    def is_recording(self):
        """
        Checks if the microphone is currently recording.
        
        Returns:
            bool: Whether the microphone is recording or not.
        """
        return self._is_running

    def output_requested(self):
        if self.is_recording():  # Stop the recording if requested
            self.stop_recording()