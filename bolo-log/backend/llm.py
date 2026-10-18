"""Voice-to-note LLM step: ONE call to an OpenAI-compatible endpoint.

Turns (a) Banglish audio (base64 wav) or (b) a Banglish transcript into
{"transcript": "...", "result": "..."} via SYSTEM_PROMPT. Never crashes the
app: failures raise and the caller warns.
"""
import base64
import json
import os
import re

import httpx

DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"

SYSTEM_PROMPT = """You turn short spoken Banglish (Bengali mixed with English, possibly Bengali script) into a clean, short note.
Input is only 1-2 sentences. Return ONLY JSON: {"transcript": "...", "result": "..."}.
- transcript: exactly what was said, written in romanized Banglish (Latin letters), English words kept as-is.
- result: the final note, plain text, no markdown, no explanation. Use \\n for new lines.
Rules for result:
1. Schedule, meeting, reminder: one line like "Meeting with Akash - 4:00 PM". Capitalize names. Use 12-hour time with AM/PM. Time words: shokal/shokale = AM, dupur = noon (12:00 PM), bikal/bikele = PM, shondha/rat = PM.
2. Money or expenses: one line per item as "item - amount" (plain numbers, "tk" and "taka" removed). If there are 2 or more items, add a final line "total - N". Compute N yourself by adding the amounts, even if the speaker said a total.
3. Anything else: one short clean line summarizing what was said, in the speaker's own words, lightly corrected.
Examples:
"akash er sathe meeting ache bikal 4 tay" -> "Meeting with Akash - 4:00 PM"
"rickshaw te dici 50tk khabar khaichi 50 tk total 100" -> "rickshaw - 50\\nkhabar - 50\\ntotal - 100"
"""


def is_configured() -> bool:
    return bool(os.environ.get("LLM_API_KEY") and os.environ.get("LLM_MODEL"))


def _base_url() -> str:
    return (os.environ.get("LLM_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")


def _headers() -> dict:
    return {"Authorization": f"Bearer {os.environ['LLM_API_KEY']}"}


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    return m.group(1).strip() if m else text


def _parse(content: str) -> dict:
    data = json.loads(_strip_code_fences(content))
    if not isinstance(data, dict):
        raise ValueError("model did not return a JSON object")
    return {
        "transcript": str(data.get("transcript") or "").strip(),
        "result": str(data.get("result") or "").strip(),
    }


def _chat_url() -> str:
    return f"{_base_url()}/chat/completions"


def _openai_compatible_body(wav: bytes | None, transcript: str | None) -> dict:
    parts = [
        {
            "type": "text",
            "text": "Turn this short Banglish speech into a clean note, per the rules.",
        }
    ]
    if wav is not None:
        parts.append(
            {
                "type": "input_audio",
                "input_audio": {
                    "data": base64.b64encode(wav).decode("ascii"),
                    "format": "wav",
                },
            }
        )
    else:
        parts[0] = {"type": "text", "text": transcript}
    return {
        "model": os.environ["LLM_MODEL"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": parts},
        ],
        "temperature": 0,
    }


def _call_native_gemini(audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
    """Fallback: Gemini generateContent with inline_data (key in a header only,
    never in the URL, so failure messages/log lines cannot leak the key)."""
    key = os.environ["LLM_API_KEY"]
    model = os.environ["LLM_MODEL"]
    # Derive the native endpoint from the compatible one (or default).
    native = (_base_url().split("/openai")[0] + "/v1beta") if "/openai" in _base_url() else _base_url()
    url = f"{native}/models/{model}:generateContent"
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": "Turn this short Banglish speech into a clean note, per the rules."},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": base64.b64encode(audio_bytes).decode("ascii"),
                        }
                    },
                ],
            }
        ],
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "generationConfig": {"temperature": 0},
    }
    headers = {"x-goog-api-key": key, "content-type": "application/json"}
    with httpx.Client(timeout=90) as client:
        resp = client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError):
        raise ValueError(f"unexpected native response shape: {list(data)}")


def format_notes(wav: bytes | None = None, transcript: str | None = None) -> dict:
    """One LLM call. Prefer the OpenAI-compatible endpoint with input_audio
    (base64 16kHz mono wav); on any failure there, fall back to the native
    Gemini generateContent endpoint with inline_data. Both raise on failure.
    """
    if not is_configured():
        raise RuntimeError("LLM not configured (LLM_API_KEY/LLM_MODEL missing)")

    content: str
    audio_ok = wav is not None
    try:
        with httpx.Client(timeout=90) as client:
            resp = client.post(_chat_url(), json=_openai_compatible_body(wav, transcript), headers=_headers())
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
        if wav is None:
            return _parse(content)
    except Exception:
        if wav is None:
            raise
        # audio input rejected by the compatible endpoint -> native fallback
        if audio_ok:
            content = _call_native_gemini(wav, "audio/wav")
    return _parse(content)
