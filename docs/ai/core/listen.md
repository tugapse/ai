## Module Purpose
This file defines the `Microphone` class, which is responsible for recording audio from the system's microphone, managing the recording process, and providing functionality to save the recorded audio to a WAV file. It operates asynchronously and provides visual feedback during recording.

## Interface & Exports
*   `Microphone` (class): The primary class for audio recording.
    *   `start_recording(callback=None)` (method): Initiates audio recording in a separate thread.
    *   `stop_recording()` (method): Halts the audio recording and returns the collected frames.
    *   `save_as_wave(filename)` (method): Writes the recorded audio frames to a specified WAV file.
    *   `is_recording()` (method): Returns a boolean indicating if recording is active.
    *   `output_requested()` (method): Stops recording if it is currently active.

## Internal Logic
The `Microphone` class extends `AsyncExecutor` to manage asynchronous operations. Audio recording is performed in the `_run_thread` method using the `pyaudio` library, where audio chunks are continuously read and appended to `self.frames`. During recording, the console output is dynamically updated to show elapsed time. A separate mechanism, implicitly managed by `super().run()` and `_check_input`, handles user input (e.g., pressing Enter) to trigger the `stop_recording()` method. Recording can also be stopped programmatically or when the `max_record_seconds` limit is reached.

## Dependencies
*   `threading`
*   `pyaudio`
*   `wave`
*   `time`
*   `core.command_executor`
*   `color`

## Constants & Environment
*   `FORMAT`: `pyaudio.paInt16` (Audio format)
*   `CHANNELS`: `2` (Number of audio channels)
*   `RATE`: `44100` (Sample rate in Hz)
*   `CHUNK`: `1024` (Buffer size for audio frames)
*   `RECORD_SECONDS`: `10` (Default maximum recording time in seconds)
*   `LINE_CLEAR`: `'\x1b[2K'` (ANSI escape sequence for clearing the current console line)