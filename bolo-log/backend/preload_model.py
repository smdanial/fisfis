"""Download the Whisper model once at startup/build so the first request isn't slow."""
import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from faster_whisper import WhisperModel

model_name = os.environ.get("WHISPER_MODEL", "small")
print(f"Downloading/loading Whisper model: {model_name} (cpu, int8) ...")
WhisperModel(model_name, device="cpu", compute_type="int8")
print(f"Model '{model_name}' ready.")
