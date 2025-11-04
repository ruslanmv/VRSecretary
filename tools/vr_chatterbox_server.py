"""
vr_chatterbox_server_optimized.py
=================================

Fast, robust Chatterbox TTS server for real-time chatbot applications.

Key features
------------
1. Faster inference:
   - Uses `torch.inference_mode()` (or `no_grad()` fallback) around generation.
   - Supports small sentence-based chunks so first audio arrives earlier for long inputs.

2. Clearer female / male voice identity:
   - Uses a slightly higher exaggeration for the pre-loaded female profile.
   - Enforces a per-voice minimum exaggeration when generating.

3. Natural sentence-level streaming:
   - Long text is split ONLY at sentence boundaries (never in the middle of a sentence).
   - Each audio chunk corresponds to one or more complete sentences.

4. Robust streaming (no stuck last chunk):
   - Chunks for a single request are generated SEQUENTIALLY (per-request), to
     avoid thread-safety issues in the TTS model.
   - The TTS model call is protected by a lock so only one thread calls
     `model.generate` at a time.
   - Streaming still yields each chunk as soon as it’s ready, so the client can
     play chunk 1 while chunk 2 is being generated.

5. Default voice files:
   - Uses `voices/female.wav` and `voices/male.wav` by default.
   - Still allows overriding via `CHATTERBOX_FEMALE_VOICE` / `CHATTERBOX_MALE_VOICE`.

6. Per-request control of chunking:
   - Field `chunk_by_sentences: bool = True` in `SpeechRequest`.
   - If `chunk_by_sentences=False`, the WHOLE input is treated as ONE big chunk
     (even for streaming) – no sentence splitting is applied at all.
   - New fields `max_chunk_words` and `max_chunk_sentences` let the client
     control how big each sentence-based chunk can be.

7. Clean shutdown:
   - On FastAPI shutdown, the ThreadPoolExecutor is shut down cleanly to avoid
     lingering threads and `_python_exit` errors.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from typing import AsyncIterator, Literal, Optional

import torch
import torchaudio as ta
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from chatterbox.tts import ChatterboxTTS


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

logger = logging.getLogger("vr_chatterbox_server")

# Project base / voices dir (so we can default to voices/female.wav, voices/male.wav)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICES_DIR = os.path.join(BASE_DIR, "voices")

# Performance tuning
MAX_WORKERS = int(os.getenv("CHATTERBOX_MAX_WORKERS", "3"))

# Fast mode: smaller chunks so the first audio arrives earlier on long texts.
FAST_MODE = os.getenv("CHATTERBOX_FAST_MODE", "true").lower() == "true"
DEFAULT_CHUNK_SIZE = int(os.getenv("CHATTERBOX_CHUNK_SIZE", "15"))
FAST_CHUNK_SIZE = int(os.getenv("CHATTERBOX_FAST_CHUNK_SIZE", "10"))
CHUNK_SIZE = FAST_CHUNK_SIZE if FAST_MODE else DEFAULT_CHUNK_SIZE

# We keep this config for future tuning / logging, but chunk generation is now
# sequential per request to keep the model stable.
CHUNK_PARALLELISM = max(
    1,
    min(int(os.getenv("CHATTERBOX_CHUNK_PARALLELISM", "2")), MAX_WORKERS),
)

WARMUP_ENABLED = os.getenv("CHATTERBOX_SKIP_WARMUP", "false").lower() != "true"

# Voice fine-tuning: make female voice more clearly distinct/expressive.
FEMALE_EXAGGERATION_BASE = float(os.getenv("CHATTERBOX_FEMALE_EXAGGERATION", "0.45"))
MALE_EXAGGERATION_BASE = float(os.getenv("CHATTERBOX_MALE_EXAGGERATION", "0.30"))

# Sentence splitting: split on these punctuation marks.
SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[\.!?。！？])\s+")


def configure_logging(level: str = "INFO") -> None:
    level = level.upper()
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        level=getattr(logging, level, logging.INFO),
    )
    logger.setLevel(getattr(logging, level, logging.INFO))


def detect_device(explicit: Optional[str] = None) -> str:
    """Auto-detect best available device."""
    if explicit:
        return explicit
    env_dev = os.getenv("CHATTERBOX_DEVICE")
    if env_dev:
        return env_dev
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


# -----------------------------------------------------------------------------
# Request/Response Models
# -----------------------------------------------------------------------------

VoiceType = Literal["female", "male", "neutral"]


class SpeechRequest(BaseModel):
    """Request schema for TTS generation."""

    input: str = Field(..., description="Text to synthesize.", min_length=1, max_length=5000)
    voice: VoiceType = Field(
        "neutral",
        description="Voice profile: 'female', 'male', or 'neutral' (no cloning).",
    )
    temperature: float = Field(0.7, ge=0.1, le=1.5, description="Sampling temperature (lower=faster).")
    cfg_weight: float = Field(0.4, ge=0.0, le=1.0, description="Guidance weight.")
    exaggeration: float = Field(0.3, ge=0.0, le=1.0, description="Expressiveness level.")
    speed: float = Field(1.0, ge=0.5, le=2.0, description="Speech speed multiplier.")
    stream: bool = Field(
        True,
        description="Enable streaming (recommended for real-time).",
    )
    chunk_by_sentences: bool = Field(
        True,
        description=(
            "If True, split long text into sentence-based chunks for streaming. "
            "If False, treat the whole input as a single chunk even for streaming."
        ),
    )
    max_chunk_words: Optional[int] = Field(
        None,
        ge=5,
        le=2000,
        description=(
            "Override default chunk size (approximate words per chunk) when "
            "chunk_by_sentences=True. Ignored if chunk_by_sentences=False."
        ),
    )
    max_chunk_sentences: Optional[int] = Field(
        None,
        ge=1,
        le=200,
        description=(
            "Maximum number of sentences per chunk when chunk_by_sentences=True. "
            "If set, a new chunk will be started once this limit is reached, even "
            "if the word count is still below max_chunk_words. Ignored if "
            "chunk_by_sentences=False."
        ),
    )


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    device: str
    model_ready: bool
    voices_loaded: dict[str, bool]
    active_requests: int


# -----------------------------------------------------------------------------
# Voice Profile Manager
# -----------------------------------------------------------------------------


class VoiceProfileManager:
    """Manages pre-loaded voice profiles for instant switching."""

    def __init__(self, model: ChatterboxTTS):
        self.model = model

        # Default to voices/female.wav and voices/male.wav in the project root.
        default_female = os.path.join(VOICES_DIR, "female.wav")
        default_male = os.path.join(VOICES_DIR, "male.wav")

        self.profiles: dict[str, Optional[str]] = {
            "female": os.getenv("CHATTERBOX_FEMALE_VOICE", default_female),
            "male": os.getenv("CHATTERBOX_MALE_VOICE", default_male),
        }
        self.prepared: dict[str, bool] = {}
        self._lock = threading.Lock()

    def load_all(self) -> None:
        """Pre-load all available voice profiles."""
        for voice_type, path in self.profiles.items():
            if path:
                path = os.path.abspath(path)
                self.profiles[voice_type] = path

            if path and os.path.exists(path):
                try:
                    logger.info("Loading %s voice profile from: %s", voice_type, path)
                    # Give the female profile a slightly higher exaggeration to
                    # make it more clearly distinct.
                    prep_exaggeration = (
                        FEMALE_EXAGGERATION_BASE if voice_type == "female" else MALE_EXAGGERATION_BASE
                    )
                    self.model.prepare_conditionals(path, exaggeration=prep_exaggeration)
                    self.prepared[voice_type] = True
                    logger.info("\u2713 %s voice profile loaded", voice_type.capitalize())
                except Exception as exc:
                    logger.warning("Failed to load %s voice: %s", voice_type, exc)
                    self.prepared[voice_type] = False
            else:
                self.prepared[voice_type] = False
                logger.warning(
                    "%s voice path not found or not set: %s",
                    voice_type.capitalize(),
                    path,
                )

    def get_voice_path(self, voice: VoiceType) -> Optional[str]:
        """Get the path for a specific voice type."""
        if voice == "neutral":
            return None
        return self.profiles.get(voice)

    def is_loaded(self, voice: VoiceType) -> bool:
        """Check if a voice profile is loaded."""
        if voice == "neutral":
            return True
        return self.prepared.get(voice, False)


# -----------------------------------------------------------------------------
# Optimized TTS Service
# -----------------------------------------------------------------------------


class ChatterboxServiceOptimized:
    """High-performance TTS service with streaming and voice caching.

    IMPORTANT FOR STABILITY:
    - `model.generate(...)` is guarded by a lock so that only one thread
      uses the TTS model at a time. This avoids internal state corruption
      and "endless sampling" on later chunks.
    - For each request, chunks are generated SEQUENTIALLY. Streaming still
      ensures the client can start playing the first chunk as soon as it
      is ready.
    """

    def __init__(self, device: str):
        self.device = device
        self._model: Optional[ChatterboxTTS] = None
        self._voice_manager: Optional[VoiceProfileManager] = None
        self._executor = ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="tts-worker")
        self._active_requests = 0
        self._lock = threading.Lock()          # protects initialization
        self._gen_lock = threading.Lock()      # protects model.generate
        self._initialized = False

    def initialize(self) -> None:
        """Initialize model and voice profiles."""
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return

            logger.info("\ud83d\ude80 Initializing ChatterboxTTS on %s...", self.device)
            start = time.time()

            # Load model
            self._model = ChatterboxTTS.from_pretrained(device=self.device)

            # Optimize for inference
            if hasattr(self._model, "eval"):
                self._model.eval()

            # Disable gradients globally for inference (kept for safety; actual
            # calls also use inference_mode/no_grad).
            torch.set_grad_enabled(False)

            # Load voice profiles
            self._voice_manager = VoiceProfileManager(self._model)
            self._voice_manager.load_all()

            # Warmup: generate dummy audio to compile/cache operations
            if WARMUP_ENABLED:
                logger.info("Warming up model with dummy generation...")
                try:
                    ctx = torch.inference_mode() if hasattr(torch, "inference_mode") else torch.no_grad()
                    with ctx:
                        _ = self._model.generate(
                            "Initialization test.",
                            temperature=0.6,
                            cfg_weight=0.35,
                            exaggeration=0.25,
                        )
                    logger.info("\u2713 Warmup completed")
                except Exception as exc:
                    logger.warning("Warmup failed (non-critical): %s", exc)

            self._initialized = True
            elapsed = time.time() - start
            logger.info("\u2713 ChatterboxTTS ready in %.2f seconds", elapsed)

    def shutdown(self) -> None:
        """Cleanly shutdown internal resources (executor, etc.)."""
        logger.info("\ud83d\uded1 Shutting down TTS executor...")
        self._executor.shutdown(wait=True, cancel_futures=True)
        logger.info("\ud83d\uded1 TTS executor shutdown complete.")

    @property
    def model(self) -> ChatterboxTTS:
        if not self._initialized or self._model is None:
            self.initialize()
        assert self._model is not None
        return self._model

    @property
    def voice_manager(self) -> VoiceProfileManager:
        if not self._initialized or self._voice_manager is None:
            self.initialize()
        assert self._voice_manager is not None
        return self._voice_manager

    # ---------- Sentence-aware chunking ----------

    def _split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences using punctuation (.?! …) as boundaries.

        The punctuation is preserved at the end of each sentence.
        """
        text = text.strip()
        if not text:
            return []

        # Split on punctuation followed by whitespace.
        parts = SENTENCE_SPLIT_PATTERN.split(text)
        sentences: list[str] = []

        for part in parts:
            s = part.strip()
            if s:
                sentences.append(s)

        # Fallback: if regex failed to split, return the whole text as one.
        return sentences or [text]

    def _chunk_text(
        self,
        text: str,
        word_target: int = CHUNK_SIZE,
        max_sentences: Optional[int] = None,
    ) -> list[str]:
        """Split text into chunks for streaming generation.

        IMPORTANT: We never split inside a sentence. We:
        - First split text into full sentences.
        - Then group consecutive sentences into chunks whose total word count
          is approximately <= `word_target`.
        - If a single sentence is longer than `word_target`, we keep it as its
          own chunk (no splitting inside it).
        - If `max_sentences` is provided, we also start a new chunk when the
          sentence count in the current chunk would exceed that limit.
        """
        sentences = self._split_into_sentences(text)
        if not sentences:
            return [text]

        chunks: list[str] = []
        current_sentences: list[str] = []
        current_words = 0

        for sent in sentences:
            sent_words = len(sent.split())

            if not current_sentences:
                # Start a new chunk with this sentence.
                current_sentences = [sent]
                current_words = sent_words
                continue

            new_words = current_words + sent_words
            new_sentence_count = len(current_sentences) + 1

            # If adding this sentence would exceed our word or sentence target,
            # flush the current chunk and start a new one.
            if new_words > word_target or (
                max_sentences is not None and new_sentence_count > max_sentences
            ):
                chunks.append(" ".join(current_sentences))
                current_sentences = [sent]
                current_words = sent_words
            else:
                current_sentences.append(sent)
                current_words = new_words

        if current_sentences:
            chunks.append(" ".join(current_sentences))

        return chunks if chunks else [text]

    # ---------- end of sentence-aware chunking ----------

    def _apply_voice_shaping(self, voice: VoiceType, exaggeration: float) -> float:
        """Ensure a minimum exaggeration per voice to keep identity clear."""
        if voice == "female":
            return max(exaggeration, FEMALE_EXAGGERATION_BASE)
        if voice == "male":
            return max(exaggeration, MALE_EXAGGERATION_BASE)
        return exaggeration

    def _generate_chunk(
        self,
        text: str,
        voice: VoiceType,
        temperature: float,
        cfg_weight: float,
        exaggeration: float,
    ) -> torch.Tensor:
        """Generate audio for a single text chunk.

        Wrapped in an inference-mode context for faster, gradient-free
        execution.

        IMPORTANT: `model.generate` is guarded by `_gen_lock` to avoid
        concurrent access, which can cause the model to get stuck on
        later chunks (endless sampling).
        """
        audio_prompt = self.voice_manager.get_voice_path(voice)

        # Enforce voice-specific minimum exaggeration to help make the female
        # voice sound more distinctly female, and male more distinctly male.
        exaggeration = self._apply_voice_shaping(voice, exaggeration)

        ctx = torch.inference_mode() if hasattr(torch, "inference_mode") else torch.no_grad()
        with self._gen_lock:
            with ctx:
                wav = self.model.generate(
                    text,
                    repetition_penalty=1.05,  # slightly lower for speed vs strictness
                    min_p=0.08,               # a bit more aggressive pruning
                    top_p=0.9,                # slightly tighter nucleus sampling
                    audio_prompt_path=audio_prompt,
                    exaggeration=exaggeration,
                    cfg_weight=cfg_weight,
                    temperature=temperature,
                )
        return wav

    def _generate_and_encode_chunk(
        self,
        chunk_index: int,
        total_chunks: int,
        text: str,
        voice: VoiceType,
        temperature: float,
        cfg_weight: float,
        exaggeration: float,
        speed: float,
    ) -> bytes:
        """Generate a chunk and return encoded WAV bytes.

        This runs inside the ThreadPoolExecutor. It does TTS generation and
        WAV encoding in one go, and logs timing info for debugging.
        """
        chunk_start = time.time()
        wav = self._generate_chunk(text, voice, temperature, cfg_weight, exaggeration)

        buf = BytesIO()
        wav_cpu = wav.detach().cpu()

        # Apply speed adjustment if needed (post-resample)
        if speed != 1.0:
            wav_cpu = ta.functional.resample(
                wav_cpu,
                orig_freq=int(self.model.sr),
                new_freq=int(self.model.sr * speed),
            )

        ta.save(buf, wav_cpu, self.model.sr, format="wav")
        buf.seek(0)

        chunk_bytes = buf.read()
        elapsed = time.time() - chunk_start
        logger.debug(
            "Chunk %d/%d generated in %.3f seconds (%d bytes)",
            chunk_index + 1,
            total_chunks,
            elapsed,
            len(chunk_bytes),
        )

        return chunk_bytes

    async def synthesize_streaming(
        self,
        req: SpeechRequest,
    ) -> AsyncIterator[bytes]:
        """Generate audio chunks as an async iterator for streaming response.

        - For each request, chunks are generated SEQUENTIALLY to keep the
          model stable and avoid stuck chunks.
        - As soon as a chunk is ready, it is yielded to the client, so playback
          can start while the next chunk is being generated.
        - If `req.chunk_by_sentences` is False, the entire input is treated as
          a SINGLE chunk even in streaming mode (no sentence splitting).
        - `req.max_chunk_words` and `req.max_chunk_sentences` allow the client
          to tune how large chunks are, which can help the TTS model reliably
          hit EOS instead of drifting into very long generations.
        """
        self._active_requests += 1
        try:
            if req.chunk_by_sentences:
                word_target = req.max_chunk_words or CHUNK_SIZE
                max_sentences = req.max_chunk_sentences
                chunks = self._chunk_text(req.input, word_target=word_target, max_sentences=max_sentences)
            else:
                # IMPORTANT: when chunking is disabled, use the FULL text
                # as a single chunk. Nothing is split.
                chunks = [req.input]
                word_target = len(req.input.split())
                max_sentences = None

            num_chunks = len(chunks)

            logger.info(
                "Streaming TTS: %d chunk(s), voice=%s, temp=%.2f, chunk_by_sentences=%s, "
                "word_target=%s, max_sentences=%s",
                num_chunks,
                req.voice,
                req.temperature,
                req.chunk_by_sentences,
                word_target,
                max_sentences,
            )

            loop = asyncio.get_event_loop()

            # Generate chunks sequentially for this request.
            for idx, chunk_text in enumerate(chunks):
                chunk_bytes = await loop.run_in_executor(
                    self._executor,
                    self._generate_and_encode_chunk,
                    idx,
                    num_chunks,
                    chunk_text,
                    req.voice,
                    req.temperature,
                    req.cfg_weight,
                    req.exaggeration,
                    req.speed,
                )
                # As soon as we yield here, the client can start playing
                # this chunk while the next one is being generated.
                yield chunk_bytes

        except Exception as exc:
            logger.exception("Streaming TTS error")
            raise HTTPException(status_code=500, detail=f"TTS failed: {exc}") from exc
        finally:
            self._active_requests -= 1

    async def synthesize(self, req: SpeechRequest) -> bytes:
        """Generate complete audio (non-streaming mode)."""
        self._active_requests += 1
        try:
            logger.info(
                "Non-streaming TTS: text_len=%d, voice=%s",
                len(req.input),
                req.voice,
            )

            loop = asyncio.get_event_loop()
            wav_bytes = await loop.run_in_executor(
                self._executor,
                self._generate_and_encode_chunk,
                0,
                1,
                req.input,  # ALWAYS full text in non-streaming mode
                req.voice,
                req.temperature,
                req.cfg_weight,
                req.exaggeration,
                req.speed,
            )

            return wav_bytes

        except Exception as exc:
            logger.exception("TTS error")
            raise HTTPException(status_code=500, detail=f"TTS failed: {exc}") from exc
        finally:
            self._active_requests -= 1

    def get_stats(self) -> dict:
        """Get service statistics."""
        return {
            "active_requests": self._active_requests,
            "max_workers": MAX_WORKERS,
            "device": self.device,
        }


# -----------------------------------------------------------------------------
# FastAPI Application
# -----------------------------------------------------------------------------


def create_app(device: str) -> FastAPI:
    """Create optimized FastAPI application."""
    app = FastAPI(
        title="VRSecretary Chatterbox TTS - Optimized",
        version="2.0.0",
        description="High-performance streaming TTS for real-time chatbots",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    service = ChatterboxServiceOptimized(device=device)
    app.state.tts_service = service

    @app.on_event("startup")
    async def startup() -> None:
        logger.info("\ud83d\ude80 Starting up TTS server...")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, service.initialize)
        logger.info("\u2713 Server ready for requests")

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        logger.info("\ud83d\uded6 FastAPI shutdown received, cleaning up TTS service...")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, service.shutdown)

    @app.get("/health", response_model=HealthResponse)
    async def health():
        """Health check with detailed status."""
        svc: ChatterboxServiceOptimized = app.state.tts_service
        vm = svc.voice_manager if svc._initialized else None

        return HealthResponse(
            status="ready" if svc._initialized else "initializing",
            device=svc.device,
            model_ready=svc._initialized,
            voices_loaded={
                "female": vm.is_loaded("female") if vm else False,
                "male": vm.is_loaded("male") if vm else False,
            },
            active_requests=svc._active_requests,
        )

    @app.post("/v1/audio/speech/stream")
    async def v1_audio_speech_stream(request: SpeechRequest):
        """Streaming TTS endpoint - sends audio chunks as they're generated."""
        svc: ChatterboxServiceOptimized = app.state.tts_service

        async def audio_generator():
            async for chunk in svc.synthesize_streaming(request):
                yield chunk

        return StreamingResponse(
            audio_generator(),
            media_type="audio/wav",
            headers={
                "X-Voice-Type": request.voice,
                "X-Streaming": "true",
            },
        )

    @app.post("/v1/audio/speech")
    async def v1_audio_speech(request: SpeechRequest):
        """Standard TTS endpoint - returns complete audio file."""
        svc: ChatterboxServiceOptimized = app.state.tts_service

        if request.stream:
            # Redirect to streaming if requested
            return await v1_audio_speech_stream(request)

        wav_bytes = await svc.synthesize(request)
        return StreamingResponse(
            BytesIO(wav_bytes),
            media_type="audio/wav",
            headers={
                "X-Voice-Type": request.voice,
                "X-Streaming": "false",
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(error="http_error", detail=str(exc.detail)).dict(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error")
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(error="internal_error", detail="Server error").dict(),
        )

    return app


_device_for_app = detect_device()
app = create_app(_device_for_app)


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Optimized Chatterbox TTS Server",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--host", default=os.getenv("VRCB_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("VRCB_PORT", "4123")))
    parser.add_argument("--device", default=None, help="Force device (cuda/cpu/mps)")
    parser.add_argument("--workers", type=int, default=1, help="Uvicorn workers")
    parser.add_argument(
        "--log-level",
        default=os.getenv("VRCB_LOG_LEVEL", "info"),
        choices=["debug", "info", "warning", "error"],
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_logging(args.log_level)

    device = detect_device(args.device)
    logger.info("\ud83c\udfa4 Starting optimized TTS server on %s:%d", args.host, args.port)
    logger.info("\ud83d\udcca Device: %s | Max workers: %d", device, MAX_WORKERS)
    logger.info(
        "\u2699 FAST_MODE=%s | CHUNK_SIZE=%d | CHUNK_PARALLELISM=%d",
        FAST_MODE,
        CHUNK_SIZE,
        CHUNK_PARALLELISM,
    )

    global app
    if device != _device_for_app:
        app = create_app(device)

    import uvicorn

    # Use h11 to avoid Windows httptools issues.
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level=args.log_level.lower(),
        workers=args.workers,
        http="h11",
    )


if __name__ == "__main__":
    main()
