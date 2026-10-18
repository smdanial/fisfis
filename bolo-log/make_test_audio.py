"""Generates a Bengali speech mp3 for testing /api/transcribe (demo helper)."""
import sys

text = "আজকে রিকশায় আশি টাকা লেগেসে, লাঞ্চে একশো পঞ্চাশ টাকা খরচ করলাম।"
out = sys.argv[1] if len(sys.argv) > 1 else "test_audio.mp3"
try:
    from gtts import gTTS
except ImportError:
    sys.exit("run: pip install gtts")

tts = gTTS(text, lang="bn")
tts.save(out)
print("saved", out)
