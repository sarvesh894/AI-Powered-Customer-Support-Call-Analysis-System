"""Audio -> text. .txt file ho to seedha padh leta hai (testing ke liye)."""
import math
from pathlib import Path
from config import TEXT_EXT, WHISPER_MODEL

_model = None


def _fmt(sec):
    return f"{int(sec // 60):02d}:{int(sec % 60):02d}"


def transcribe(path):
    """Returns (transcript_text, confidence 0-1)."""
    p = Path(path)
    if p.suffix.lower() in TEXT_EXT:
        return p.read_text(encoding="utf-8"), 1.0

    global _model
    if _model is None:
        from faster_whisper import WhisperModel  # lazy import: pehli baar model download hoga
        _model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")

    segments, info = _model.transcribe(str(p), vad_filter=True)
    segs = list(segments)
    if not segs:
        return "", 0.0
    text = "\n".join(f"[{_fmt(s.start)}] {s.text.strip()}" for s in segs)
    conf = sum(math.exp(s.avg_logprob) for s in segs) / len(segs)
    return text, conf
