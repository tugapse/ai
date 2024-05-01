from threading import Thread
from command_executor import AsyncExecutor, ExecutorResult
import pyaudio
import wave
import time
from color import  Color
 
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
CHUNK = 1024
RECORD_SECONDS = 10

LINE_CLEAR = '\x1b[2K' # <-- ANSI sequence
 
class Microphone(AsyncExecutor):

    def __init__(self, 
                 max_record_seconds= RECORD_SECONDS,
                 start_recording_text="Start recording...",
                 recording_text="{b_color}* Recording {s_color}{time} : {max_seconds} {b_color}seconds (press enter to stop recording)",
                 end_recording_text="Recording ended."
                 ) -> None:
        super().__init__("/listen", None)
        self.audio = None
        self.frames = []
        self._stream = None
        self._is_running = False
        self.max_record_seconds = max_record_seconds
        self.recording_text = recording_text
        self.start_recording_text = start_recording_text
        self.end_recording_text =end_recording_text
        

    def _check_input(self):
        user_input = input("")
        self.stop_recording()
        return None


    def _run_thread(self):
        """
        Internal method to start recording audio.
        """
        # Start recording
        self.audio= pyaudio.PyAudio()
        start_time  = time.time()
        self._is_running = True
        self._stream = self.audio.open(format=FORMAT, channels=CHANNELS,rate=RATE, input=True,frames_per_buffer=CHUNK)
        self.frames = []
        
        for i in range(0, int(RATE / CHUNK * self.max_record_seconds) ):
            data = self._stream.read(CHUNK)
            self.frames.append(data)
            
            print(end=LINE_CLEAR) # <-- clear the line where cursor is located
            print(self.recording_text
                  .replace( "{time}", str(int(time.time() - start_time)))
                  .replace( "{max_seconds}",str(RECORD_SECONDS)) 
                  .replace( "{b_color}" ,Color.RESET)
                  .replace( "{s_color}" ,Color.BLUE) , end="\r")
            
            if self._is_running is False:    
                break

        self.stop_recording()
        return None

    def run(self, auto_start=True, wait=True, **kargs):
        super().run(auto_start, wait, **kargs)
        """handle user input thread"""
        
    
    def start_recording(self,callback=None):
        """
        Starts recording audio in a separate thread.
        """
        self.finished_callback = callback
        print(self.start_recording_text)
        self.run()
       
        
    
    def stop_recording(self):
        """
        Stops recording audio and returns the recorded frames.
        """
        self._is_running = False
        self._stream.stop_stream()
        self._stream.close()
        self.audio.terminate()
        print(self.end_recording_text)
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
        return self._is_running

    def output_requested(self):
        if self.is_recording() : self.stop_recording()