"""Bolo-Log backend: minimal voice-to-note (speech -> Banglish transcript + clean note)."""
import os

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse

try:  # load local .env if present (optional dependency)
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from . import llm, stt

app = FastAPI(title="Bolo-Log")

_FRONTEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "index.html")


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/")
def index():
    with open(_FRONTEND, encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.post("/api/transcribe")
async def transcribe(audio: UploadFile = File(...), backend: str = Form(None)):
    data = await audio.read()

    # The API key is only read from the environment inside llm.py and is never
    # printed or logged anywhere in this codebase.
    resp: dict = {"transcript": "", "result": "", "warning": None}

    if not data:
        resp["warning"] = "Empty audio upload."
        return resp

    chosen = (backend or os.environ.get("STT_BACKEND") or "gemini").lower()
    if chosen not in ("gemini", "whisper"):
        resp["warning"] = f"Unknown backend '{chosen}' (use gemini or whisper)."
        return resp

    try:
        if chosen == "whisper":
            raw = stt.transcribe_bytes(data, audio.filename or "audio.wav")
        else:
            raw = stt.to_16k_wav(data)
    except Exception as e:
        resp["warning"] = f"Audio processing failed ({chosen}): {e}"
        return resp

    if not llm.is_configured():
        resp["warning"] = "LLM not configured (LLM_API_KEY/LLM_MODEL missing)."
        if chosen == "whisper":
            resp["transcript"] = raw  # at least show what was heard
        return resp

    try:
        if chosen == "whisper":
            out = llm.format_notes(transcript=raw)
        else:
            out = llm.format_notes(wav=raw)
        resp["transcript"] = out["transcript"]
        resp["result"] = out["result"]
    except Exception as e:
        resp["warning"] = f"LLM step failed ({chosen}): {e}"
        if chosen == "whisper":
            resp["transcript"] = raw

    return {k: v for k, v in resp.items() if v is not None}
