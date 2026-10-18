# 🎙️ Bolo-Log

Minimal voice-to-note demo: click the mic, say 1–2 sentences in Banglish (Bengali + English), click again, get a short clean note back.

```
"akash er sathe meeting ache bikal 4 tay"        ->  "Meeting with Akash - 4:00 PM"
"rickshaw te dici 50tk khabar khaichi 50 tk total 100"
                                       ->  rickshaw - 50
                                           khabar - 50
                                           total - 100
```

Everything runs on CPU; there are no storage/entries features — one API call, one note.

## How it works

- `STT_BACKEND=gemini` (default): the uploaded audio is converted to 16 kHz mono wav with PyAV and sent in **one** call to Gemini via its OpenAI-compatible endpoint (`input_audio` base64 part); if that is rejected, it retries once with the native `generateContent` endpoint (`inline_data`). The model replies with strict JSON `{"transcript": "...", "result": "..."}` (transcript in romanized Banglish, `result` = the clean note).
- `STT_BACKEND=whisper`: `faster-whisper` transcribes, then the same formatting prompt turns the transcript into the note.
- The form field `backend` (gemini/whisper) overrides the env per request.
- Failures never crash: you get `{transcript, result: "", warning}`.

Both backends use the prompt in `backend/llm.py` (`SYSTEM_PROMPT`, exact rules for time words AM/PM and item-amount lines with auto-computed total).

## Run

```bash
cd bolo-log
.venv/bin/uvicorn backend.main:app --reload --port 7860
```

(venv + models/ already prepared in this checkout; fresh install: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`)

The API key goes into `.env` as `LLM_API_KEY`. It is only read from the environment at request time — it is never printed or logged.

## Env vars

| Var | Default | Meaning |
|---|---|---|
| `STT_BACKEND` | `gemini` | `gemini` or `whisper` (per-request `backend` form field overrides) |
| `WHISPER_MODEL` | `small` | only for the whisper backend; a complete `./models/<name>` is preferred automatically |
| `LLM_API_KEY` | _(blank)_ | Gemini/Gemini-compatible API key |
| `LLM_MODEL` | `gemini-3.5-flash` | model id |
| `LLM_BASE_URL` | `https://generativelanguage.googleapis.com/v1beta/openai` | OpenAI-compatible base; native fallback derives its URL from this |

## Endpoints

- `POST /api/transcribe` — multipart `audio` (webm/ogg/wav/mp3), optional form field `backend` → `{transcript, result, warning?}`
- `GET /health` — `{"ok": true}`

## Notes

- Mic capture needs `localhost` or HTTPS (`cloudflared tunnel --url http://localhost:7860` for a public demo).
- Whisper on this CPU: `small` ≈ real-time-ish per sentence (~50 s/7 s clip on the dev box, `tiny` ≈ 9 s/7 s). The gemini path is much faster end-to-end.
