# Bolo-Log — HANDOVER

## What's built

Minimal voice-to-note demo: mic button → 1–2 sentences of Banglish → short clean note. No storage, no tables, no totals anymore (the entries/store features were removed).

- `backend/main.py` — FastAPI: `/` (frontend), `GET /health`, `POST /api/transcribe` (multipart `audio`, optional form field `backend`). The key is never printed or logged anywhere.
- `backend/stt.py` — PyAV helpers: `to_16k_wav()` decodes webm/ogg/wav/mp3 to 16 kHz mono PCM wav (for gemini mode); whisper transcribe with `language="bn"`, `condition_on_previous_text=False`, `temperature=[0.0,0.2,0.4]`, `no_speech_threshold=0.6`, `vad_filter=True`. Contains two compatibility fixes (PyAV ≥15 `metadata_errors` shim; local `models/<name>` auto-preference).
- `backend/llm.py` — `SYSTEM_PROMPT` constant (time words → AM/PM; item-amount lines; auto-computed "total - N"), plus `format_notes()`: gemini mode sends base64 16 kHz wav in **one** call to the OpenAI-compatible endpoint (`input_audio` part; `Authorization` header only — key never in a URL so errors can't leak it), falls back once to the native `generateContent` endpoint with `inline_data` (`x-goog-api-key` header). Whisper mode sends the transcript as text to the same compatible endpoint. Response strictly parsed to `{"transcript", "result"}` with fence stripping; failures raise for the caller to warn.
- `frontend/index.html` — title, pulsing mic button, "Listening..."/"Thinking..." status, result box (line breaks preserved, large text), grey transcript line, Copy button, backend dropdown (gemini/whisper). Nothing else.
- Helpers kept for testing: `mock_llm.py` (canned OpenAI-compatible server), `make_test_audio.py` + `test_audio.mp3` (Bengali gTTS sample), `download_model.sh`/`download_to.sh` (chunked mirror fallback downloaders).

## How to run

```bash
cd bolo-log
.venv/bin/uvicorn backend.main:app --reload --port 7860
```

Fresh machine: `.venv` + requirements noted in README; put your key in `LLM_API_KEY` in `.env`.

## Env vars

| Var | Default | Meaning |
|---|---|---|
| `STT_BACKEND` | `gemini` | default pipeline; per-request `backend` form field overrides |
| `WHISPER_MODEL` | `small` | whisper-backend only; `./models/<name>` preferred if complete |
| `LLM_API_KEY` | _(blank)_ | API key; leave blank to run transcript-degraded (warning only) |
| `LLM_MODEL` | `gemini-3.5-flash` | model id |
| `LLM_BASE_URL` | Gemini OpenAI-compatible endpoint | override for proxies/mocks |

## What was verified (this environment)

- `POST /api/transcribe` whisper path end-to-end with the real Bengali sample (`test_audio.mp3` → whisper tiny → mocked LLM): `{transcript: "mock transcript romanized", result: "mock note result"}` — and the raw whisper transcript produced from the new whisper params was reasonable romanized Banglish.
- `POST /api/transcribe` gemini path end-to-end (mp3 → real PyAV conversion to 16 kHz mono wav → base64 `input_audio` call → mocked LLM): correct shape, no warning.
- `backend` form field honored; env default (`STT_BACKEND=whisper` in test) honored with no form field.
- `to_16k_wav()` verified: 16 kHz, mono, pcm_s16le, correct duration; garbage input raises (caught → HTTP 200 + warning).
- Defensive parse: plain JSON, fenced JSON (incl. `\n` inside result strings), garbage → raise.
- Failure paths: whisper with dead LLM endpoint → 200 + warning + raw transcript; gemini with dead endpoint (both attempts fail) → 200 + warning; unconfigured key → 200 + warning. Zero crashes in all runs.
- Key-leak check: with a `FAKEKEY-DO-NOT-LOG-123` value configured, grep over uvicorn stdout/stderr logs found 0 occurrences; in code the key is only ever passed as a request header.

## Could NOT be verified

- The **real Gemini API** (no key available): the OpenAI-compatible `input_audio` call and the native `generateContent` fallback were verified against a mockserver — request shapes match the documented APIs, but live behaviour (429s, audio-format rejection, actual note quality) needs a real key + 1 manual mic test.
- The exact note formatting by the model (example transcripts → example notes): rules live in `SYSTEM_PROMPT`, but a real model call is required to prove output quality. The prompt plumbing + parsing are verified.
- The browser mic button (no browser automation here).
- Docker build (no docker daemon in this environment).
- No local TTS (espeak-ng absent); `gTTS` was used to generate the Bengali sample. **text-formatting with the two example transcripts could not be exercised against a real model** — the two examples in `SYSTEM_PROMPT` are consumed by the model itself.

## Known issues

- `models/small` + `models/tiny` in this checkout were fetched via the chunked mirror script (`download_model.sh`) because `huggingface_hub` stalled on this network; `stt.py` prefers them automatically.
- Gemini mode ~ a few seconds per note; whisper mode on this CPU: ~9 s/7 s clip (tiny) or ~50 s (small int8).
- Mic capture requires `https://` or `localhost`.

## Next steps

1. Fill `LLM_API_KEY`, run once with the mic, confirm a real note comes back (and that a Bengali `transcript` still parses).
2. If Gemini rejects the compatible `input_audio` path, check the warning text — the native fallback then takes over automatically; if both fail, the warning names both endpoints only in prose (no key in URLs by design).
3. Optional polish: duration cap on uploads, streaming "Listening..." VU meter, PWA install prompt.
