# 🎙️ Fis-Fis

**Speak Banglish. Get a clean note.**

Bolo-Log turns short spoken **Banglish** (Bengali mixed with English) into a tidy text note. No typing, no keyboard switching.

| You say | You get |
|---|---|
| "akash er sathe meeting ache bikal 4 tay" | `Meeting with Akash - 4:00 PM` |
| "rickshaw te dici 50tk khabar khaichi 50 tk" | `rickshaw - 50`<br>`khabar - 50`<br>`total - 100` |

---

## How it works

```
Browser mic  ->  FastAPI backend  ->  Speech understanding  ->  Clean note
(MediaRecorder)   (PyAV: 16 kHz mono)   Gemini  OR  Whisper+LLM   (JSON -> text)
```

1. The browser records audio with the **MediaRecorder API** and sends it to the backend.
2. The backend (**FastAPI**) decodes it with **PyAV** and converts it to **16 kHz mono WAV**.
3. Two interchangeable speech backends (set with `STT_BACKEND`):
   - **`gemini` (default):** one multimodal LLM call handles listening, Banglish transliteration, and formatting.
   - **`whisper` (open-source, CPU):** `faster-whisper` (CTranslate2, int8) transcribes, then an LLM call formats the note.
4. A system prompt with few-shot examples forces strict JSON output, which is parsed defensively with fallbacks.
5. Rules built into the prompt: Bengali time words map to AM/PM, and expenses become `item - amount` with a computed total.

## Tech stack

- **Backend:** Python, FastAPI, uvicorn, httpx, PyAV
- **Speech:** Gemini 3.5 Flash (default), OpenAI Whisper via faster-whisper (optional)
- **Frontend:** single `index.html`, vanilla JavaScript, no build step
- **Config:** environment variables (no secrets in code)
- **Hosting:** Render free web service (HTTPS is required for browser mic access)

---

## Quick start (local)

**Requirements:** Python 3.10+ and a Google AI Studio API key (free at [aistudio.google.com](https://aistudio.google.com)).

```bash
git clone https://github.com/smdanial/fisfis.git
cd fisfis/bolo-log

# 1. Create a virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Add your settings
cp .env.example .env
# Open .env and paste your key after LLM_API_KEY=

# 3. Run the app
uvicorn backend.main:app --reload --port 7860
```

Open **http://localhost:7860**, allow the microphone, click the mic, speak one or two short sentences, then click it again to stop.

### Environment variables (`.env`)

| Variable | Example | Purpose |
|---|---|---|
| `STT_BACKEND` | `gemini` | `gemini` (default) or `whisper` |
| `LLM_API_KEY` | `your key` | Google AI Studio API key |
| `LLM_MODEL` | `gemini-3.5-flash` | Model used for audio and formatting |
| `LLM_BASE_URL` | `https://generativelanguage.googleapis.com/v1beta/openai` | OpenAI-compatible endpoint |
| `WHISPER_MODEL` | `small` | Only used when `STT_BACKEND=whisper` |

> Never commit `.env`. It is already listed in `.gitignore`.

### Optional: run the open-source Whisper backend

```bash
python backend/preload_model.py        # downloads the Whisper model (~460 MB)
# then set STT_BACKEND=whisper in .env, or pick "whisper" in the page dropdown
```

Runs on a normal CPU laptop, no GPU needed. Accuracy on real Banglish is weaker than Gemini, which is why Gemini is the default.

---

## Deploy (Render, free tier)

> Requires `render.yaml` and `requirements-deploy.txt` in the repo (the deploy-prep step).

1. Push the repo to GitHub.
2. On [render.com](https://render.com): **New → Web Service**, connect the repo, choose the **Free** instance.
3. Build command: `pip install -r requirements-deploy.txt`
4. Start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables: `STT_BACKEND=gemini`, `LLM_MODEL=gemini-3.5-flash`, `LLM_BASE_URL`, and `LLM_API_KEY` (set in the dashboard, never in code).
6. Open the generated `onrender.com` URL.

The free tier sleeps after 15 minutes without traffic and takes about a minute to wake, so open the URL before a demo. The 512 MB free instance is too small for Whisper, so deploy in `gemini` mode.

---

## API

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/transcribe` | Multipart `audio` (optional form field `backend`). Returns `{"transcript", "result", "warning"?}` |
| `GET` | `/health` | Health check |

## Project structure

```
bolo-log/
├── backend/
│   ├── main.py            # FastAPI routes
│   ├── stt.py             # audio decoding + speech backends
│   ├── llm.py             # prompts, LLM calls, JSON parsing
│   └── preload_model.py   # optional Whisper model download
├── frontend/index.html    # mic UI
├── requirements.txt
├── .env.example
└── Dockerfile
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `404 Not Found` from the LLM | The model name is retired. Check `LLM_MODEL` against the current Gemini model list. |
| Warning about missing key | `LLM_API_KEY` is empty in `.env`. Save the file and restart the server. |
| Mic button does nothing | Use `localhost` or an `https://` URL, and allow mic permission in the browser. |
| Garbled text with `whisper` | Whisper `small` struggles with Banglish. Switch to `gemini`, or try `WHISPER_MODEL=medium`. |

## Limitations and roadmap

- Built for **short, 1-2 sentence** inputs, not long dictation.
- The default backend needs internet and an API key.
- Next: fine-tune Whisper on Banglish data, add more note types (reminders, orders), and explore on-device inference (Cactus).

## License

See [LICENSE](LICENSE).

---

Built at a hackathon by [@smdanial](https://github.com/smdanial).
