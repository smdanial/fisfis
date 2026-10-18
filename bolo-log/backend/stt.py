"""Whisper STT (optional backend) + PyAV audio conversion helpers.

The model is loaded lazily ONCE and cached as a module-global. Audio bytes are
decoded by faster-whisper's bundled PyAV — no system ffmpeg required.
"""
import io
import os

import av

# Compatibility shim: newer PyAV (>=15) removed the `metadata_errors` kwarg of
# av.open that faster-whisper still passes. Drop it if unsupported.
_orig_av_open = av.open


def _av_open_compat(*args, **kwargs):
    kwargs.pop("metadata_errors", None)
    return _orig_av_open(*args, **kwargs)


av.open = _av_open_compat

from faster_whisper import WhisperModel

_model_name = os.environ.get("WHISPER_MODEL", "small")
_model: WhisperModel | None = None


def _resolve_model(model_name: str) -> str:
    """Prefer a complete local copy in ./models/<name> over a (possibly stalled) hub download."""
    local = os.path.join("models", model_name)
    if os.path.isfile(os.path.join(local, "model.bin")):
        return local
    return model_name


def get_model() -> WhisperModel | None:
    """Load the model once, lazily. Returns None if loading fails."""
    global _model
    if _model is None:
        try:
            _model = WhisperModel(_resolve_model(_model_name), device="cpu", compute_type="int8")
        except Exception as e:
            print(f"[bolo-log] WARNING: whisper model load failed: {e}")
    return _model


def transcribe_bytes(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    """Transcribe raw audio bytes (webm/ogg/wav/mp3 ok) to text.

    Raises on decode failure or if no model could be loaded.
    """
    model = get_model()
    if model is None:
        raise RuntimeError("whisper model could not be loaded (check logs)")
    segments, _info = model.transcribe(
        io.BytesIO(audio_bytes),
        language="bn",
        condition_on_previous_text=False,
        temperature=[0.0, 0.2, 0.4],
        no_speech_threshold=0.6,
        vad_filter=True,
    )
    text = " ".join(s.text.strip() for s in segments).strip()
    if not text:
        raise ValueError("no speech detected in the audio")
    return text


def to_16k_wav(audio_bytes: bytes) -> bytes:
    """Decode any container (webm/ogg/wav/mp3) to 16kHz mono PCM wav bytes.

    Raises on decode failure so the caller can warn cleanly.
    """
    src = av.open(io.BytesIO(audio_bytes))
    out = io.BytesIO()
    try:
        stream = src.streams.audio[0]
        resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
        with av.open(out, "w", "wav") as dst:
            ostream = dst.add_stream("pcm_s16le", rate=16000, layout="mono")
            for frame in src.decode(stream):
                for rframe in resampler.resample(frame):
                    for packet in ostream.encode(rframe):
                        dst.mux(packet)
            for packet in ostream.encode(None):
                dst.mux(packet)
    finally:
        src.close()
    return out.getvalue()


def wav_properties(wav_bytes: bytes) -> dict:
    """Read back a wav produced by to_16k_wav (used in tests)."""
    with av.open(io.BytesIO(wav_bytes)) as c:
        s = c.streams.audio[0]
        return {
            "rate": s.rate,
            "channels": s.channels,
            "codec": s.codec_context.name,
            "duration": float(c.duration or 0) / av.time_base if c.duration else 0.0,
        }
