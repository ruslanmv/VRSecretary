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

# IMPORTANT: Import the multilingual version
from chatterbox.mtl_tts import ChatterboxMultilingualTTS


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

logger = logging.getLogger("vr_chatterbox_server_multilingual")

# Supported languages (23 total)
SUPPORTED_LANGUAGES = {
    "ar": "Arabic",
    "da": "Danish",
    "de": "German",
    "el": "Greek",
    "en": "English",
    "es": "Spanish",
    "fi": "Finnish",
    "fr": "French",
    "he": "Hebrew",
    "hi": "Hindi",
    "it": "Italian",
    "ja": "Japanese",
    "ko": "Korean",
    "ms": "Malay",
    "nl": "Dutch",
    "no": "Norwegian",
    "pl": "Polish",
    "pt": "Portuguese",
    "ru": "Russian",
    "sv": "Swedish",
    "sw": "Swahili",
    "tr": "Turkish",
    "zh": "Chinese",
}

# Project base / voices dir
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICES_DIR = os.path.join(BASE_DIR, "voices")

# Performance tuning
MAX_WORKERS = int(os.getenv("CHATTERBOX_MAX_WORKERS", "3"))
FAST_MODE = os.getenv("CHATTERBOX_FAST_MODE", "true").lower() == "true"
DEFAULT_CHUNK_SIZE = int(os.getenv("CHATTERBOX_CHUNK_SIZE", "15"))
FAST_CHUNK_SIZE = int(os.getenv("CHATTERBOX_FAST_CHUNK_SIZE", "10"))
CHUNK_SIZE = FAST_CHUNK_SIZE if FAST_MODE else DEFAULT_CHUNK_SIZE
CHUNK_PARALLELISM = max(
    1,
    min(int(os.getenv("CHATTERBOX_CHUNK_PARALLELISM", "2")), MAX_WORKERS),
)
WARMUP_ENABLED = os.getenv("CHATTERBOX_SKIP_WARMUP", "false").lower() != "true"

# Chunking behaviour tuning:
# - LONG_TEXT_WORD_THRESHOLD: minimum approximate word count before we apply
#   sentence-based chunking when the client has not requested a specific
#   max_chunk_words. Short / medium texts are kept as ONE chunk so that
#   the original text is not implicitly "broken up".
# - MIN_EFFECTIVE_CHUNK_WORDS: when the client does not override
#   max_chunk_words, we use at least this many "words" as the target
#   per chunk so that each chunk feels like a natural paragraph / group
#   of sentences rather than tiny sentence fragments.
LONG_TEXT_WORD_THRESHOLD = int(os.getenv("CHATTERBOX_LONG_TEXT_WORD_THRESHOLD", "150"))
MIN_EFFECTIVE_CHUNK_WORDS = int(os.getenv("CHATTERBOX_MIN_CHUNK_WORDS", "60"))

# Voice fine-tuning
FEMALE_EXAGGERATION_BASE = float(os.getenv("CHATTERBOX_FEMALE_EXAGGERATION", "0.45"))
MALE_EXAGGERATION_BASE = float(os.getenv("CHATTERBOX_MALE_EXAGGERATION", "0.30"))

# Sentence splitting: split on these punctuation marks when followed by
# whitespace. We only ever cut chunks on these boundaries so sentences
# themselves are never broken.
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
LanguageCode = Literal[
    "ar", "da", "de", "el", "en", "es", "fi", "fr", "he", "hi",
    "it", "ja", "ko", "ms", "nl", "no", "pl", "pt", "ru", "sv",
    "sw", "tr", "zh",
]


class SpeechRequest(BaseModel):
    """Request schema for multilingual TTS generation."""

    input: str = Field(..., description="Text to synthesize.", min_length=1, max_length=5000)

    # Language selection
    language: LanguageCode = Field(
        "en",
        description="Language code for synthesis (ISO 639-1 format).",
    )

    voice: VoiceType = Field(
        "neutral",
        description="Voice profile: 'female', 'male', or 'neutral' (no cloning).",
    )
    temperature: float = Field(0.7, ge=0.1, le=1.5, description="Sampling temperature.")
    cfg_weight: float = Field(0.4, ge=0.0, le=1.0, description="Guidance weight.")
    exaggeration: float = Field(0.3, ge=0.0, le=1.0, description="Expressiveness level.")
    speed: float = Field(1.0, ge=0.5, le=2.0, description="Speech speed multiplier.")
    stream: bool = Field(True, description="Enable streaming.")
    chunk_by_sentences: bool = Field(
        True,
        description=(
            "If True and the text is long, split by full sentences for streaming. "
            "If False, the entire input is always treated as a single chunk even "
            "in streaming mode."
        ),
    )
    max_chunk_words: Optional[int] = Field(
        None,
        ge=5,
        le=2000,
        description=(
            "Approximate maximum words per chunk when chunking is enabled. "
            "If omitted, a conservative default is used and chunking is only "
            "applied for long texts."
        ),
    )
    max_chunk_sentences: Optional[int] = Field(
        None,
        ge=1,
        le=200,
        description=(
            "Maximum number of sentences per chunk when chunking is enabled. "
            "Ignored if chunk_by_sentences is False."
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
    supported_languages: dict[str, str]


class LanguagesResponse(BaseModel):
    """Response listing all supported languages."""

    languages: dict[str, str]
    count: int


# -----------------------------------------------------------------------------
# Voice Profile Manager (Multilingual)
# -----------------------------------------------------------------------------


class VoiceProfileManager:
    """Manages pre-loaded voice profiles with language awareness."""

    def __init__(self, model: ChatterboxMultilingualTTS):
        self.model = model

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
                    prep_exaggeration = (
                        FEMALE_EXAGGERATION_BASE if voice_type == "female" else MALE_EXAGGERATION_BASE
                    )
                    self.model.prepare_conditionals(path, exaggeration=prep_exaggeration)
                    self.prepared[voice_type] = True
                    logger.info("✓ %s voice profile loaded", voice_type.capitalize())
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
# Multilingual TTS Service
# -----------------------------------------------------------------------------


class ChatterboxServiceMultilingual:
    """High-performance multilingual TTS service with streaming.

    Chunking semantics:

    - Non-streaming requests (stream=False) never chunk; the full input text
      is synthesized as a single audio file.

    - When stream=True and chunk_by_sentences=False, the full input text is
      still treated as a single chunk. This guarantees that explicitly
      disabling chunking will never split or reformat the text.

    - When stream=True and chunk_by_sentences=True, sentence-aware chunking
      is applied *only* for long texts (or when the client explicitly sets
      max_chunk_words). Chunk boundaries are placed only at natural sentence
      ends (periods, question marks, exclamation marks, including Chinese
      equivalents) and the original text inside each chunk is preserved
      byte-for-byte: no stripping or re-joining that could "destroy" the text.
    """

    def __init__(self, device: str):
        self.device = device
        self._model: Optional[ChatterboxMultilingualTTS] = None
        self._voice_manager: Optional[VoiceProfileManager] = None
        self._executor = ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="tts-worker")
        self._active_requests = 0
        self._lock = threading.Lock()
        self._gen_lock = threading.Lock()
        self._initialized = False

    def initialize(self) -> None:
        """Initialize multilingual model and voice profiles."""
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return

            logger.info("🚀 Initializing ChatterboxMultilingualTTS on %s...", self.device)
            start = time.time()

            # Load MULTILINGUAL model
            self._model = ChatterboxMultilingualTTS.from_pretrained(device=self.device)

            if hasattr(self._model, "eval"):
                self._model.eval()

            torch.set_grad_enabled(False)

            # Load voice profiles
            self._voice_manager = VoiceProfileManager(self._model)
            self._voice_manager.load_all()

            # Warmup
            if WARMUP_ENABLED:
                logger.info("Warming up multilingual model...")
                try:
                    ctx = torch.inference_mode() if hasattr(torch, "inference_mode") else torch.no_grad()
                    with ctx:
                        # Test with English
                        _ = self._model.generate(
                            "Initialization test.",
                            language_id="en",
                            temperature=0.6,
                            cfg_weight=0.35,
                            exaggeration=0.25,
                        )
                    logger.info("✓ Warmup completed")
                except Exception as exc:
                    logger.warning("Warmup failed (non-critical): %s", exc)

            self._initialized = True
            elapsed = time.time() - start
            logger.info("✓ ChatterboxMultilingualTTS ready in %.2f seconds", elapsed)
            logger.info("📚 Supported languages: %d", len(SUPPORTED_LANGUAGES))

    def shutdown(self) -> None:
        """Cleanly shutdown internal resources."""
        logger.info("🛑 Shutting down TTS executor...")
        self._executor.shutdown(wait=True, cancel_futures=True)
        logger.info("🛑 TTS executor shutdown complete.")

    @property
    def model(self) -> ChatterboxMultilingualTTS:
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

    @staticmethod
    def _approx_word_count(text: str) -> int:
        """Approximate a 'word' count for chunking decisions.

        For space-separated languages this is just len(text.split()).
        For scripts without spaces (e.g. Chinese, Japanese), fall back to
        a rough character-based heuristic so that long texts can still be
        considered "long" for chunking purposes.
        """
        basic = len(text.split())
        if basic > 0:
            return basic
        # Rough heuristic: ~4 characters per "word-like" unit
        return max(1, len(text) // 4)

    def _split_into_sentences(self, text: str) -> list[tuple[int, int]]:
        """Return sentence spans as (start, end) indices into `text`.

        We split only on end-of-sentence punctuation (. ! ? and their
        CJK equivalents) when followed by whitespace. The returned spans
        are *slices* of the original string; if you concatenate all of
        them in order, you recover the original text exactly.

        This guarantees that we never modify or "destroy" the input text
        during chunking – we only decide where to cut it.
        """
        if not text:
            return []

        spans: list[tuple[int, int]] = []
        last_idx = 0

        for match in SENTENCE_SPLIT_PATTERN.finditer(text):
            # Sentence goes from last_idx up to the whitespace that starts
            # after the end-of-sentence punctuation.
            end_idx = match.start()
            if end_idx > last_idx:
                spans.append((last_idx, end_idx))
                last_idx = end_idx

        if last_idx < len(text):
            spans.append((last_idx, len(text)))

        return spans

    def _chunk_text(
        self,
        text: str,
        word_target: int,
        max_sentences: Optional[int] = None,
    ) -> list[str]:
        """Split text into streaming chunks without altering the content.

        IMPORTANT:
        - We never split *inside* a sentence.
        - Each chunk is a direct substring of `text` (no stripping, no
          re-joining). Concatenating all chunks reproduces the original
          string byte-for-byte.
        - A chunk can contain one paragraph with many sentences, or even
          multiple paragraphs; chunk boundaries are there only to keep
          latency reasonable, not to change semantics.
        """
        spans = self._split_into_sentences(text)
        if not spans:
            return [text]

        chunks: list[str] = []

        current_start: Optional[int] = None
        current_word_count = 0
        current_sentence_count = 0

        def flush(end_index: int) -> None:
            nonlocal current_start, current_word_count, current_sentence_count
            if current_start is not None and end_index > current_start:
                chunks.append(text[current_start:end_index])
            current_start = None
            current_word_count = 0
            current_sentence_count = 0

        for s_start, s_end in spans:
            sent_text = text[s_start:s_end]
            sent_words = self._approx_word_count(sent_text)

            if current_sentence_count == 0:
                # Start a new chunk at this sentence
                current_start = s_start

            new_word_count = current_word_count + sent_words
            new_sentence_count = current_sentence_count + 1

            # If we already have some sentences in the current chunk and adding
            # this one would exceed our targets, flush the current chunk and
            # start a new one from this sentence.
            if current_sentence_count > 0 and (
                new_word_count > word_target
                or (max_sentences is not None and new_sentence_count > max_sentences)
            ):
                flush(s_start)
                current_start = s_start
                current_word_count = sent_words
                current_sentence_count = 1
            else:
                current_word_count = new_word_count
                current_sentence_count = new_sentence_count

        # Flush the final chunk.
        if current_sentence_count > 0:
            last_end = spans[-1][1]
            flush(last_end)

        return chunks or [text]

    def _apply_voice_shaping(self, voice: VoiceType, exaggeration: float) -> float:
        """Ensure minimum exaggeration per voice."""
        if voice == "female":
            return max(exaggeration, FEMALE_EXAGGERATION_BASE)
        if voice == "male":
            return max(exaggeration, MALE_EXAGGERATION_BASE)
        return exaggeration

    def _generate_chunk(
        self,
        text: str,
        language: str,
        voice: VoiceType,
        temperature: float,
        cfg_weight: float,
        exaggeration: float,
    ) -> torch.Tensor:
        """Generate audio for a single text chunk with language support."""
        audio_prompt = self.voice_manager.get_voice_path(voice)
        exaggeration = self._apply_voice_shaping(voice, exaggeration)

        ctx = torch.inference_mode() if hasattr(torch, "inference_mode") else torch.no_grad()
        with self._gen_lock:
            with ctx:
                # IMPORTANT: Pass language_id parameter
                wav = self.model.generate(
                    text,
                    language_id=language,
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
        language: str,
        voice: VoiceType,
        temperature: float,
        cfg_weight: float,
        exaggeration: float,
        speed: float,
    ) -> bytes:
        """Generate and encode a chunk with language support."""
        chunk_start = time.time()
        wav = self._generate_chunk(text, language, voice, temperature, cfg_weight, exaggeration)

        buf = BytesIO()
        wav_cpu = wav.detach().cpu()

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
            "Chunk %d/%d [%s] generated in %.3f seconds (%d bytes)",
            chunk_index + 1,
            total_chunks,
            language,
            elapsed,
            len(chunk_bytes),
        )

        return chunk_bytes

    async def synthesize_streaming(
        self,
        req: SpeechRequest,
    ) -> AsyncIterator[bytes]:
        """Generate audio chunks with language support.

        Behaviour summary:

        - If req.chunk_by_sentences is False, the full input is treated as a
          single chunk even in streaming mode: the text is never split.

        - If req.chunk_by_sentences is True, we apply sentence-aware chunking
          *only* when the text is long enough to justify it (or when the
          client explicitly sets max_chunk_words). This keeps short inputs
          as one natural chunk, so users do not "feel" that chunking exists.
        """
        self._active_requests += 1
        try:
            if req.chunk_by_sentences:
                total_words = self._approx_word_count(req.input)

                if req.max_chunk_words is not None:
                    # Client explicitly opted into a specific chunk size.
                    base_target = req.max_chunk_words
                    effective_target = base_target
                    should_chunk = total_words > base_target
                else:
                    # Default behaviour: only chunk truly long texts.
                    base_target = CHUNK_SIZE
                    effective_target = max(base_target, MIN_EFFECTIVE_CHUNK_WORDS)
                    should_chunk = total_words > LONG_TEXT_WORD_THRESHOLD

                if should_chunk:
                    word_target = effective_target
                    max_sentences = req.max_chunk_sentences
                    chunks = self._chunk_text(
                        req.input,
                        word_target=word_target,
                        max_sentences=max_sentences,
                    )
                else:
                    # Treat entire text as a single chunk; no splitting, no
                    # modification. This guarantees that "normal" sized texts
                    # are never implicitly chunked.
                    chunks = [req.input]
                    word_target = total_words
                    max_sentences = None
            else:
                # Explicit opt-out: never chunk, regardless of length.
                chunks = [req.input]
                total_words = self._approx_word_count(req.input)
                word_target = total_words
                max_sentences = None

            num_chunks = len(chunks)

            logger.info(
                "Streaming TTS: %d chunk(s), lang=%s, voice=%s, temp=%.2f, chunk_by_sentences=%s, target_words=%s, max_sentences=%s",
                num_chunks,
                req.language,
                req.voice,
                req.temperature,
                req.chunk_by_sentences,
                word_target,
                max_sentences,
            )

            loop = asyncio.get_event_loop()

            for idx, chunk_text in enumerate(chunks):
                chunk_bytes = await loop.run_in_executor(
                    self._executor,
                    self._generate_and_encode_chunk,
                    idx,
                    num_chunks,
                    chunk_text,
                    req.language,  # Pass language
                    req.voice,
                    req.temperature,
                    req.cfg_weight,
                    req.exaggeration,
                    req.speed,
                )
                yield chunk_bytes

        except Exception as exc:
            logger.exception("Streaming TTS error")
            raise HTTPException(status_code=500, detail=f"TTS failed: {exc}") from exc
        finally:
            self._active_requests -= 1

    async def synthesize(self, req: SpeechRequest) -> bytes:
        """Generate complete audio (non-streaming).

        Non-streaming synthesis always uses the full input text as a
        single chunk; chunk_by_sentences, max_chunk_words and related
        options are ignored here by design.
        """
        self._active_requests += 1
        try:
            logger.info(
                "Non-streaming TTS: text_len=%d, lang=%s, voice=%s",
                len(req.input),
                req.language,
                req.voice,
            )

            loop = asyncio.get_event_loop()
            wav_bytes = await loop.run_in_executor(
                self._executor,
                self._generate_and_encode_chunk,
                0,
                1,
                req.input,
                req.language,  # Pass language
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
            "supported_languages": len(SUPPORTED_LANGUAGES),
        }


# -----------------------------------------------------------------------------
# FastAPI Application
# -----------------------------------------------------------------------------


def create_app(device: str) -> FastAPI:
    """Create multilingual FastAPI application."""
    app = FastAPI(
        title="VRSecretary Chatterbox TTS - Multilingual",
        version="2.1.0",
        description="High-performance streaming TTS supporting 23 languages",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    service = ChatterboxServiceMultilingual(device=device)
    app.state.tts_service = service

    @app.on_event("startup")
    async def startup() -> None:
        logger.info("🚀 Starting up multilingual TTS server...")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, service.initialize)
        logger.info("✓ Server ready for requests in %d languages", len(SUPPORTED_LANGUAGES))

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        logger.info("🛶 FastAPI shutdown received, cleaning up TTS service...")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, service.shutdown)

    @app.get("/health", response_model=HealthResponse)
    async def health():
        """Health check with language support info."""
        svc: ChatterboxServiceMultilingual = app.state.tts_service
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
            supported_languages=SUPPORTED_LANGUAGES,
        )

    @app.get("/languages", response_model=LanguagesResponse)
    async def get_languages():
        """Get list of all supported languages."""
        return LanguagesResponse(
            languages=SUPPORTED_LANGUAGES,
            count=len(SUPPORTED_LANGUAGES),
        )

    @app.post("/v1/audio/speech/stream")
    async def v1_audio_speech_stream(request: SpeechRequest):
        """Streaming TTS endpoint with multilingual support."""
        svc: ChatterboxServiceMultilingual = app.state.tts_service

        async def audio_generator():
            async for chunk in svc.synthesize_streaming(request):
                yield chunk

        return StreamingResponse(
            audio_generator(),
            media_type="audio/wav",
            headers={
                "X-Voice-Type": request.voice,
                "X-Language": request.language,
                "X-Streaming": "true",
            },
        )

    @app.post("/v1/audio/speech")
    async def v1_audio_speech(request: SpeechRequest):
        """Standard TTS endpoint with multilingual support."""
        svc: ChatterboxServiceMultilingual = app.state.tts_service

        if request.stream:
            return await v1_audio_speech_stream(request)

        wav_bytes = await svc.synthesize(request)
        return StreamingResponse(
            BytesIO(wav_bytes),
            media_type="audio/wav",
            headers={
                "X-Voice-Type": request.voice,
                "X-Language": request.language,
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
        description="Multilingual Chatterbox TTS Server (23 languages)",
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
    logger.info("🎤 Starting multilingual TTS server on %s:%d", args.host, args.port)
    logger.info("💬 Device: %s | Languages: %d", device, len(SUPPORTED_LANGUAGES))
    logger.info("📚 Supported: " + ", ".join(SUPPORTED_LANGUAGES.keys()))

    global app
    if device != _device_for_app:
        app = create_app(device)

    import uvicorn

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
