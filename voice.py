import sys

from faster_whisper import WhisperModel

WHISPER_MODEL_SIZE = "tiny"   # "tiny" uses the least memory; "base" / "small" are more accurate
LANGUAGE = "en"               # fixed language: skips the language-detection step
CPU_THREADS = 2               # fewer threads = less working memory

_model = None   # loaded the first time it's needed, then reused


def get_model():
    """Load the speech recognition model once and keep it in memory."""
    global _model
    if _model is None:
        _model = WhisperModel(
            WHISPER_MODEL_SIZE, device="cpu", compute_type="int8", cpu_threads=CPU_THREADS
        )
    return _model


def transcribe(audio_path):
    """Turn a recording into text. Returns (text, language)."""
    segments, info = get_model().transcribe(audio_path, beam_size=1, language=LANGUAGE)
    text = " ".join(segment.text.strip() for segment in segments)
    return text, info.language


if __name__ == "__main__":
    text, language = transcribe(sys.argv[1])
    print("Language:", language)
    print("Text:    ", text)