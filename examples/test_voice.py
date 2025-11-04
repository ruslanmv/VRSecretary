"""
Optimized GUI client for VRSecretary Chatterbox TTS server with real-time streaming.

Fixes & improvements in this version
-----------------------------------
- Fixes `wave.Error: unknown format: 3` by handling IEEE float32 WAV audio
  (format code 3) without using the stdlib `wave` module.
- Uses a lightweight custom WAV header parser and feeds raw PCM/float data
  directly into PyAudio / simpleaudio.
- Reduces overhead in streaming by:
  * Avoiding storage of all audio chunks in memory (stream-only).
  * Using `iter_content(chunk_size=None)` so each server-sent chunk is
    handled as a single unit.
- Adds a UI toggle to enable/disable sentence chunking so you can compare
  natural streaming vs full-text single-chunk generation, using the
  `chunk_by_sentences` flag in the TTS server.
- Safe cancellation when starting a new request or pressing Stop:
  * Stops audio playback cleanly.
  * Cancels the previous HTTP stream (closes response).
  * Prevents overlapping generations and confusing audio.
- NEW: Fix long-text second-chunk timeout (`ReadTimeout`) by removing the
  per-request read timeout on streaming calls. The client now allows very
  long chunks without raising `HTTPConnectionPool...Read timeout`.
"""

import json
import os
import struct
import threading
import queue
from typing import Optional

import tkinter as tk
from tkinter import ttk, messagebox

# Audio playback
try:
    import simpleaudio as sa

    HAS_SIMPLEAUDIO = True
except ImportError:
    HAS_SIMPLEAUDIO = False
    print("[WARN] simpleaudio not installed. Audio playback will be limited.")

try:
    import pyaudio

    HAS_PYAUDIO = True
except ImportError:
    HAS_PYAUDIO = False
    print("[WARN] pyaudio not installed. Real-time streaming will be limited.")

# HTTP with streaming support
try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    import urllib.request
    import urllib.error


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

SERVER_URL = os.getenv("CHATTERBOX_URL", "http://localhost:4123")
STREAMING_ENDPOINT = "/v1/audio/speech/stream"  # Optimized streaming endpoint
STANDARD_ENDPOINT = "/v1/audio/speech"  # Fallback non-streaming
REQUEST_TIMEOUT = 60.0  # Used only for non-streaming calls

# Voice profiles with proper gender configuration
VOICE_PROFILES = {
    "🎀 Sophia – Friendly Assistant (Female)": {
        "voice": "female",
        "temperature": 0.7,
        "cfg_weight": 0.4,
        "exaggeration": 0.35,
        "speed": 1.0,
        "description": "Warm and professional female voice",
    },
    "🎀 Emma – Calm Professional (Female)": {
        "voice": "female",
        "temperature": 0.6,
        "cfg_weight": 0.5,
        "exaggeration": 0.3,
        "speed": 0.95,
        "description": "Composed and clear female voice",
    },
    "🎀 Luna – Energetic & Warm (Female)": {
        "voice": "female",
        "temperature": 0.8,
        "cfg_weight": 0.3,
        "exaggeration": 0.45,
        "speed": 1.05,
        "description": "Lively and expressive female voice",
    },
    "🎀 Maya – Soft & Gentle (Female)": {
        "voice": "female",
        "temperature": 0.65,
        "cfg_weight": 0.45,
        "exaggeration": 0.25,
        "speed": 0.9,
        "description": "Gentle and soothing female voice",
    },
    "👔 Marcus – Professional (Male)": {
        "voice": "male",
        "temperature": 0.7,
        "cfg_weight": 0.4,
        "exaggeration": 0.3,
        "speed": 1.0,
        "description": "Clear and authoritative male voice",
    },
    "👔 Ethan – Warm Baritone (Male)": {
        "voice": "male",
        "temperature": 0.65,
        "cfg_weight": 0.5,
        "exaggeration": 0.35,
        "speed": 0.95,
        "description": "Deep and reassuring male voice",
    },
    "👔 Noah – Neutral & Clear (Male)": {
        "voice": "male",
        "temperature": 0.7,
        "cfg_weight": 0.45,
        "exaggeration": 0.3,
        "speed": 1.0,
        "description": "Balanced and natural male voice",
    },
    "👔 Alex – Dynamic (Male)": {
        "voice": "male",
        "temperature": 0.75,
        "cfg_weight": 0.35,
        "exaggeration": 0.4,
        "speed": 1.05,
        "description": "Energetic and engaging male voice",
    },
    "⚪ Neutral Voice (No Cloning)": {
        "voice": "neutral",
        "temperature": 0.7,
        "cfg_weight": 0.4,
        "exaggeration": 0.35,
        "speed": 1.0,
        "description": "Default synthesized voice",
    },
}

# Sample texts for quick testing
SAMPLE_TEXTS = {
    "Greeting": "Hello! I'm your AI assistant. How can I help you today?",
    "Long Text": "The quick brown fox jumps over the lazy dog. This is a test of the text-to-speech system with a longer sentence to demonstrate streaming capabilities and natural voice quality.",
    "Question": "What would you like me to help you with? I'm here to assist with any questions you might have.",
    "Excited": "Wow! This is amazing! The voice sounds so natural and clear!",
    "Professional": "Thank you for contacting our support team. I'll be happy to assist you with your inquiry today.",
}


# -----------------------------------------------------------------------------
# WAV parsing helpers (fixes unknown format: 3)
# -----------------------------------------------------------------------------


def _parse_wav_chunk(chunk_bytes: bytes) -> dict:
    """Parse a minimal WAV header and return audio parameters + raw data.

    Supports:
    - PCM (format code 1)
    - IEEE float (format code 3)  <-- what the server currently emits
    """

    if len(chunk_bytes) < 44:
        raise ValueError("WAV chunk too small to contain a header")

    header = chunk_bytes[:44]
    (
        chunk_id,
        chunk_size,
        fmt,
        subchunk1_id,
        subchunk1_size,
        audio_format,
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        subchunk2_id,
        subchunk2_size,
    ) = struct.unpack("<4sI4s4sIHHIIHH4sI", header)

    if chunk_id != b"RIFF" or fmt != b"WAVE":
        raise ValueError("Invalid WAV header (not RIFF/WAVE)")

    data = chunk_bytes[44:]
    if len(data) == 0:
        raise ValueError("WAV chunk has no data")

    return {
        "audio_format": audio_format,
        "channels": num_channels,
        "sample_rate": sample_rate,
        "bits_per_sample": bits_per_sample,
        "data": data,
    }


# -----------------------------------------------------------------------------
# Audio Player (supports streaming chunks)
# -----------------------------------------------------------------------------


class StreamingAudioPlayer:
    """Plays audio chunks as they arrive (progressive playback)."""

    def __init__(self):
        self.playing = False
        self.stop_flag = False
        self.audio_queue = queue.Queue()
        self.playback_thread: Optional[threading.Thread] = None

    def start_playback(self):
        """Start the playback thread.

        If something is already playing, it is stopped first to avoid overlap.
        """
        # Ensure any previous playback is completely stopped
        self.stop()

        self.playing = True
        self.stop_flag = False
        self.audio_queue = queue.Queue()

        if HAS_PYAUDIO:
            self.playback_thread = threading.Thread(
                target=self._pyaudio_player,
                daemon=True,
            )
        else:
            self.playback_thread = threading.Thread(
                target=self._simpleaudio_player,
                daemon=True,
            )

        self.playback_thread.start()

    def add_chunk(self, wav_bytes: Optional[bytes]):
        """Add an audio chunk to the playback queue.

        Use ``None`` as a sentinel to signal the end of the stream.
        """
        if self.playing:
            self.audio_queue.put(wav_bytes)

    def stop(self):
        """Stop playback cleanly and wait for the playback thread to finish."""
        self.stop_flag = True
        if self.playback_thread and self.playback_thread.is_alive():
            # Signal end of queue so the playback thread can exit its loop.
            self.audio_queue.put(None)
            try:
                self.playback_thread.join(timeout=2.0)
            except RuntimeError:
                # If join is called from the same thread, just skip.
                pass
        self.playback_thread = None
        self.playing = False

    def _pyaudio_player(self):
        """Real-time streaming playback using PyAudio.

        This version supports both PCM (format 1) and IEEE float32 (format 3).
        """
        if not HAS_PYAUDIO:
            return

        p = pyaudio.PyAudio()
        stream = None

        try:
            while not self.stop_flag:
                chunk_bytes = self.audio_queue.get()
                if chunk_bytes is None:
                    break

                try:
                    info = _parse_wav_chunk(chunk_bytes)
                except Exception as exc:
                    print(f"[WARN] Failed to parse WAV chunk: {exc}")
                    continue

                audio_format = info["audio_format"]
                channels = info["channels"]
                sample_rate = info["sample_rate"]
                bits_per_sample = info["bits_per_sample"]
                frames = info["data"]

                # Map WAV format to PyAudio format
                if audio_format == 1:  # PCM
                    sample_width = bits_per_sample // 8
                    pa_format = p.get_format_from_width(sample_width)
                elif audio_format == 3:  # IEEE float
                    pa_format = pyaudio.paFloat32
                else:
                    print(f"[WARN] Unsupported WAV format code: {audio_format}")
                    continue

                if stream is None:
                    stream = p.open(
                        format=pa_format,
                        channels=channels,
                        rate=sample_rate,
                        output=True,
                    )

                stream.write(frames)

        finally:
            if stream:
                stream.stop_stream()
                stream.close()
            p.terminate()
            self.playing = False

    def _simpleaudio_player(self):
        """Sequential playback using simpleaudio (fallback)."""
        if not HAS_SIMPLEAUDIO:
            return

        try:
            while not self.stop_flag:
                chunk_bytes = self.audio_queue.get()
                if chunk_bytes is None:
                    break

                try:
                    info = _parse_wav_chunk(chunk_bytes)
                except Exception as exc:
                    print(f"[WARN] Failed to parse WAV chunk (simpleaudio): {exc}")
                    continue

                frames = info["data"]
                channels = info["channels"]
                sample_rate = info["sample_rate"]
                bits_per_sample = info["bits_per_sample"]

                wave_obj = sa.WaveObject(
                    frames,
                    channels,
                    bits_per_sample // 8,
                    sample_rate,
                )
                play_obj = wave_obj.play()
                play_obj.wait_done()  # Wait for this chunk to finish

        finally:
            self.playing = False


# -----------------------------------------------------------------------------
# TTS Client
# -----------------------------------------------------------------------------


def call_tts_streaming(
    text: str,
    profile: dict,
    chunk_by_sentences: bool = True,
    progress_callback=None,
    cancel_event: Optional[threading.Event] = None,
    response_holder: Optional[dict] = None,
) -> int:
    """Call the streaming TTS endpoint and stream audio chunks as they arrive.

    Args:
        text: Text to synthesize.
        profile: Voice profile dictionary.
        chunk_by_sentences: If True, server uses sentence-based chunking;
            if False, the entire text is generated as a single chunk.
        progress_callback: Optional callback(chunk_num, chunk_bytes).
        cancel_event: If set, streaming will stop as soon as possible.
        response_holder: shared dict to store the requests.Response, so that
            the caller can close it from another thread to cancel more quickly.

    Returns:
        The total number of chunks received.
    """

    if not HAS_REQUESTS:
        raise RuntimeError(
            "The 'requests' library is required for streaming. "
            "Install it with: pip install requests"
        )

    url = SERVER_URL.rstrip("/") + STREAMING_ENDPOINT

    payload = {
        "input": text,
        "voice": profile.get("voice", "neutral"),
        "temperature": profile.get("temperature", 0.7),
        "cfg_weight": profile.get("cfg_weight", 0.4),
        "exaggeration": profile.get("exaggeration", 0.35),
        "speed": profile.get("speed", 1.0),
        "stream": True,
        "chunk_by_sentences": bool(chunk_by_sentences),
    }

    response = None
    try:
        # IMPORTANT CHANGE: no explicit timeout here so long chunks don't hit
        # ReadTimeout while the server is still generating the next chunk.
        response = requests.post(
            url,
            json=payload,
            stream=True,
        )
        response.raise_for_status()

        if response_holder is not None:
            response_holder["response"] = response

        chunk_num = 0
        # chunk_size=None: yield exactly the server-sent chunks, reducing
        # extra splitting/overhead.
        for chunk in response.iter_content(chunk_size=None):
            if cancel_event is not None and cancel_event.is_set():
                # Cancel requested: stop consuming the stream.
                break

            if not chunk:
                continue
            chunk_num += 1
            if progress_callback:
                progress_callback(chunk_num, chunk)

        return chunk_num

    except requests.exceptions.RequestException as e:
        # If we cancelled on purpose, don't treat as an error.
        if cancel_event is not None and cancel_event.is_set():
            return 0
        raise RuntimeError(f"Streaming request failed: {e}") from e

    finally:
        if response is not None:
            try:
                response.close()
            except Exception:
                pass
        if response_holder is not None:
            response_holder["response"] = None


def call_tts_standard(
    text: str,
    profile: dict,
    chunk_by_sentences: bool = True,
) -> bytes:
    """Call the standard (non-streaming) TTS endpoint.

    Fallback for when streaming is not available.
    """

    url = SERVER_URL.rstrip("/") + STANDARD_ENDPOINT

    payload = {
        "input": text,
        "voice": profile.get("voice", "neutral"),
        "temperature": profile.get("temperature", 0.7),
        "cfg_weight": profile.get("cfg_weight", 0.4),
        "exaggeration": profile.get("exaggeration", 0.35),
        "speed": profile.get("speed", 1.0),
        "stream": False,
        "chunk_by_sentences": bool(chunk_by_sentences),
    }

    if HAS_REQUESTS:
        response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.content
    else:
        # urllib fallback
        import urllib.request

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            return resp.read()


# -----------------------------------------------------------------------------
# GUI Application
# -----------------------------------------------------------------------------


class OptimizedVoiceTestApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("VRSecretary TTS - Real-Time Voice Test")
        self.geometry("750x580")
        self.resizable(True, True)

        self.player = StreamingAudioPlayer()
        self.is_generating = False

        # Controls whether we ask the server to chunk by sentences or not.
        self.chunking_enabled = tk.BooleanVar(value=True)

        # For cancellation of the current streaming request
        self.current_cancel_event: Optional[threading.Event] = None
        self.current_response_holder: dict = {}

        self._build_widgets()
        self._check_server_health()

    # ----------------- UI building -----------------

    def _build_widgets(self):
        # Main container
        main = ttk.Frame(self, padding=15)
        main.pack(fill=tk.BOTH, expand=True)

        # Header
        header = ttk.Label(
            main,
            text="🎤 VRSecretary TTS - Real-Time Voice Test",
            font=("Segoe UI", 14, "bold"),
        )
        header.pack(anchor="w", pady=(0, 5))

        # Server info
        server_info = ttk.Label(
            main,
            text=f"Server: {SERVER_URL}",
            foreground="gray",
        )
        server_info.pack(anchor="w")

        # Voice selection frame
        voice_frame = ttk.LabelFrame(main, text="Voice Selection", padding=10)
        voice_frame.pack(fill=tk.X, pady=(10, 0))

        voice_inner = ttk.Frame(voice_frame)
        voice_inner.pack(fill=tk.X)

        ttk.Label(voice_inner, text="Voice Profile:").pack(side=tk.LEFT)

        self.voice_var = tk.StringVar()
        voice_names = list(VOICE_PROFILES.keys())

        self.voice_combo = ttk.Combobox(
            voice_inner,
            textvariable=self.voice_var,
            values=voice_names,
            state="readonly",
            width=40,
        )
        self.voice_combo.pack(side=tk.LEFT, padx=(10, 0), fill=tk.X, expand=True)
        self.voice_combo.set(voice_names[0])
        self.voice_combo.bind("<<ComboboxSelected>>", self._on_voice_changed)

        # Voice description
        self.voice_desc_var = tk.StringVar()
        self.voice_desc_label = ttk.Label(
            voice_frame,
            textvariable=self.voice_desc_var,
            foreground="gray",
            font=("Segoe UI", 9, "italic"),
        )
        self.voice_desc_label.pack(anchor="w", pady=(5, 0))
        self._on_voice_changed()

        # Sample text selector
        sample_frame = ttk.Frame(main)
        sample_frame.pack(fill=tk.X, pady=(10, 5))

        ttk.Label(sample_frame, text="Quick samples:").pack(side=tk.LEFT)

        for sample_name in SAMPLE_TEXTS.keys():
            btn = ttk.Button(
                sample_frame,
                text=sample_name,
                command=lambda name=sample_name: self._load_sample(name),
                width=12,
            )
            btn.pack(side=tk.LEFT, padx=(5, 0))

        # Text input
        text_frame = ttk.LabelFrame(main, text="Text to Synthesize", padding=10)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        # Text box with scrollbar
        text_container = ttk.Frame(text_frame)
        text_container.pack(fill=tk.BOTH, expand=True)

        self.text_box = tk.Text(
            text_container,
            wrap="word",
            font=("Segoe UI", 10),
            height=8,
        )
        scrollbar = ttk.Scrollbar(text_container, command=self.text_box.yview)
        self.text_box.config(yscrollcommand=scrollbar.set)

        self.text_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.text_box.insert("1.0", SAMPLE_TEXTS["Greeting"])

        # Chunking toggle frame
        chunk_frame = ttk.Frame(main)
        chunk_frame.pack(fill=tk.X, pady=(5, 0))

        self.chunk_check = ttk.Checkbutton(
            chunk_frame,
            text="Enable sentence-based chunking (streamed)",
            variable=self.chunking_enabled,
        )
        self.chunk_check.pack(side=tk.LEFT)

        chunk_hint = ttk.Label(
            chunk_frame,
            text="Uncheck to send full text as a single chunk",
            foreground="gray",
            font=("Segoe UI", 8, "italic"),
        )
        chunk_hint.pack(side=tk.LEFT, padx=(5, 0))

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            main,
            variable=self.progress_var,
            mode="indeterminate",
        )
        self.progress_bar.pack(fill=tk.X, pady=(10, 5))

        # Status and controls
        bottom_frame = ttk.Frame(main)
        bottom_frame.pack(fill=tk.X, pady=(5, 0))

        # Status
        status_frame = ttk.Frame(bottom_frame)
        status_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(
            status_frame,
            textvariable=self.status_var,
            font=("Segoe UI", 9),
        )
        self.status_label.pack(side=tk.LEFT)

        # Buttons
        button_frame = ttk.Frame(bottom_frame)
        button_frame.pack(side=tk.RIGHT)

        self.stop_button = ttk.Button(
            button_frame,
            text="⏹ Stop",
            command=self._on_stop,
            state=tk.DISABLED,
            width=10,
        )
        self.stop_button.pack(side=tk.LEFT, padx=(0, 5))

        self.speak_button = ttk.Button(
            button_frame,
            text="🎙 Speak",
            command=self._on_speak,
            width=12,
        )
        self.speak_button.pack(side=tk.LEFT)

    # ----------------- UI callbacks -----------------

    def _on_voice_changed(self, event=None):
        """Update voice description when selection changes."""
        voice_name = self.voice_var.get()
        profile = VOICE_PROFILES.get(voice_name, {})
        desc = profile.get("description", "No description available")
        self.voice_desc_var.set(f"ℹ {desc}")

    def _load_sample(self, sample_name: str):
        """Load a sample text into the text box."""
        text = SAMPLE_TEXTS.get(sample_name, "")
        self.text_box.delete("1.0", "end")
        self.text_box.insert("1.0", text)

    def _check_server_health(self):
        """Check if the server is reachable."""

        def check():
            try:
                health_url = SERVER_URL.rstrip("/") + "/health"
                if HAS_REQUESTS:
                    response = requests.get(health_url, timeout=5)
                    data = response.json()
                else:
                    import urllib.request

                    with urllib.request.urlopen(health_url, timeout=5) as resp:
                        data = json.loads(resp.read())

                status = data.get("status", "unknown")
                device = data.get("device", "unknown")

                msg = f"✓ Server connected ({device})"
                if status != "ready":
                    msg = "⚠ Server initializing..."

                self.after(0, lambda: self.status_var.set(msg))

            except Exception as e:
                self.after(0, lambda: self.status_var.set(f"❌ Server offline: {e}"))

        threading.Thread(target=check, daemon=True).start()

    # ----------------- cancellation helpers -----------------

    def _cancel_current_generation(self):
        """Cancel any ongoing streaming + playback."""
        # Signal cancellation to the worker
        if self.current_cancel_event is not None:
            self.current_cancel_event.set()

        # Close HTTP response if we have it (forces iter_content to error/stop)
        resp = self.current_response_holder.get("response") if self.current_response_holder else None
        if resp is not None:
            try:
                resp.close()
            except Exception:
                pass

        # Stop audio playback
        self.player.stop()

    # ----------------- speak / stop logic -----------------

    def _on_speak(self):
        """Generate and play speech."""
        text = self.text_box.get("1.0", "end").strip()
        if not text:
            messagebox.showwarning("No Text", "Please enter some text to synthesize.")
            return

        voice_name = self.voice_var.get()
        profile = VOICE_PROFILES.get(voice_name, {})

        # If there's already a generation running, cancel it first to avoid overlap.
        if self.is_generating:
            self._cancel_current_generation()

        self.is_generating = True
        self.speak_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.progress_bar.start(10)

        # Start streaming playback for the new request
        self.player.start_playback()

        chunk_by_sentences = bool(self.chunking_enabled.get())

        # Set up new cancellation primitives for this request
        cancel_event = threading.Event()
        self.current_cancel_event = cancel_event
        self.current_response_holder = {}

        threading.Thread(
            target=self._worker_speak,
            args=(text, profile, voice_name, chunk_by_sentences, cancel_event, self.current_response_holder),
            daemon=True,
        ).start()

    def _worker_speak(
        self,
        text: str,
        profile: dict,
        voice_name: str,
        chunk_by_sentences: bool,
        cancel_event: threading.Event,
        response_holder: dict,
    ):
        """Background worker for TTS generation and streaming."""
        try:
            mode_label = "chunked" if chunk_by_sentences else "single-chunk"
            self.after(
                0,
                lambda: self.status_var.set(f"🎵 Generating {voice_name} ({mode_label})..."),
            )

            def on_chunk(chunk_num, chunk_bytes):
                # If cancelled mid-stream, don't enqueue more audio.
                if cancel_event.is_set():
                    return
                self.player.add_chunk(chunk_bytes)
                self.after(
                    0,
                    lambda: self.status_var.set(
                        f"🎵 Playing chunk {chunk_num} ({mode_label})..."
                    ),
                )

            # Stream generation (returns total chunk count, but we also track via callback)
            total_chunks = call_tts_streaming(
                text,
                profile,
                chunk_by_sentences=chunk_by_sentences,
                progress_callback=on_chunk,
                cancel_event=cancel_event,
                response_holder=response_holder,
            )

            # If we were cancelled, just exit quietly (UI already updated in _on_stop).
            if cancel_event.is_set():
                return

            # Signal playback completion for this stream
            self.player.add_chunk(None)

            self.after(0, self._on_speak_complete, total_chunks, voice_name, chunk_by_sentences)

        except Exception as e:
            # If cancelled, swallow errors from forced close.
            if cancel_event.is_set():
                return
            self.after(0, self._on_speak_error, str(e))

    def _on_speak_complete(self, chunk_count: int, voice_name: str, chunk_by_sentences: bool):
        """Called when generation completes successfully."""
        self.is_generating = False
        self.current_cancel_event = None
        self.current_response_holder = {}

        self.speak_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.progress_bar.stop()
        mode_label = "chunked" if chunk_by_sentences else "single-chunk"
        self.status_var.set(
            f"✓ Completed ({chunk_count} chunks with {voice_name}, mode={mode_label})"
        )

    def _on_speak_error(self, error_msg: str):
        """Called when generation fails."""
        self.is_generating = False
        self.current_cancel_event = None
        self.current_response_holder = {}

        self.speak_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.progress_bar.stop()
        self.player.stop()
        self.status_var.set("❌ Error occurred")
        messagebox.showerror("TTS Error", f"Failed to generate speech:\n\n{error_msg}")

    def _on_stop(self):
        """Stop current generation and playback."""
        if not self.is_generating:
            # Nothing to stop
            return

        self._cancel_current_generation()
        self.is_generating = False
        self.current_cancel_event = None
        self.current_response_holder = {}

        self.speak_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.progress_bar.stop()
        self.status_var.set("⏹ Stopped")


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


def main():
    """Run the application."""
    # Check dependencies
    missing = []
    if not HAS_REQUESTS:
        missing.append("requests")
    if not HAS_SIMPLEAUDIO and not HAS_PYAUDIO:
        missing.append("simpleaudio or pyaudio")

    if missing:
        print("\n⚠ WARNING: Missing optional dependencies:")
        for pkg in missing:
            print(f"  - {pkg}")
        print("\nInstall with: pip install " + " ".join(missing))
        print("\nThe app will work with limited functionality.\n")

    app = OptimizedVoiceTestApp()
    app.mainloop()


if __name__ == "__main__":
    main()
