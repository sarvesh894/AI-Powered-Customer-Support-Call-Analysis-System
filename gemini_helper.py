import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

DEFAULT_MODELS = (
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-3.0-flash",
    "gemini-2.0-flash",
)

_MODEL_CACHE = {"ts": 0.0, "models": list(DEFAULT_MODELS)}

def load_env_file():
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and not os.environ.get(k):
            os.environ[k] = v

def get_api_key() -> str:
    load_env_file()
    api_key = (
        os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or ""
    ).strip()
    if api_key:
        return api_key

    try:
        import streamlit as st

        return str(
            st.secrets.get("GEMINI_API_KEY")
            or st.secrets.get("GOOGLE_API_KEY")
            or ""
        ).strip()
    except FileNotFoundError:
        return ""

def _mime_for_audio(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac",
    }.get(ext, "audio/mpeg")

def _parse_json_loose(txt: str) -> dict:
    cleaned = txt.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    try:
        data = json.loads(cleaned)
        return data if isinstance(data, dict) else {}
    except Exception:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                data = json.loads(cleaned[start:end + 1])
                return data if isinstance(data, dict) else {}
            except Exception:
                pass
    return {"transcript": cleaned} if cleaned else {}

def _candidate_models(client) -> list:
    now = time.time()
    if now - _MODEL_CACHE["ts"] < 600 and _MODEL_CACHE["models"]:
        return _MODEL_CACHE["models"]

    ordered = list(DEFAULT_MODELS)
    try:
        for m in client.models.list():
            name = getattr(m, "name", "") or ""
            short = name.replace("models/", "").strip()
            if short and "flash" in short and short not in ordered:
                ordered.append(short)
    except Exception:
        pass

    _MODEL_CACHE["ts"] = now
    _MODEL_CACHE["models"] = ordered
    return ordered

def test_gemini_connection() -> dict:
    api_key = get_api_key()
    if not api_key:
        return {
            "ok": False,
            "sdk": None,
            "model": None,
            "message": "GEMINI_API_KEY or GOOGLE_API_KEY was not found in environment, .env, or Streamlit secrets.",
        }

    last_err = ""
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        for model_name in _candidate_models(client):
            try:
                resp = client.models.generate_content(
                    model=model_name,
                    contents="Reply with OK only.",
                )
                txt = (getattr(resp, "text", "") or "").strip()
                if txt:
                    _MODEL_CACHE["models"] = [model_name] + [m for m in _candidate_models(client) if m != model_name]
                    return {
                        "ok": True,
                        "sdk": "google-genai",
                        "model": model_name,
                        "message": f"Connected via google-genai ({model_name}): {txt[:60]}",
                    }
            except Exception as e:
                last_err = str(e)
                continue
    except ImportError:
        last_err = "google-genai package is not installed"
    except Exception as e:
        return {"ok": False, "sdk": "google-genai", "model": None, "message": f"google-genai error: {e}"}

    try:
        import google.generativeai as genai_legacy
        genai_legacy.configure(api_key=api_key)
        for model_name in DEFAULT_MODELS:
            try:
                m = genai_legacy.GenerativeModel(model_name)
                resp = m.generate_content("Reply with OK only.")
                txt = (getattr(resp, "text", "") or "").strip()
                if txt:
                    return {
                        "ok": True,
                        "sdk": "google-generativeai",
                        "model": model_name,
                        "message": f"Connected via google-generativeai ({model_name}): {txt[:60]}",
                    }
            except Exception as e:
                last_err = str(e)
                continue
    except ImportError:
        pass
    except Exception as e:
        return {"ok": False, "sdk": "google-generativeai", "model": None, "message": f"google-generativeai error: {e}"}

    return {
        "ok": False,
        "sdk": None,
        "model": None,
        "message": f"Model request failed: {last_err[:220]}",
    }

def transcribe_and_analyze_audio_with_gemini(audio_path: Path) -> dict:
    api_key = get_api_key()
    if not api_key:
        return {"ok": False, "error": "Missing GEMINI_API_KEY / GOOGLE_API_KEY"}

    prompt = (
        "Carefully listen to this customer support call recording (in Hindi, Hinglish, or English). "
        "Provide a complete, thorough, speaker-labeled transcript without omitting details or cutting off early. "
        "Return ONLY valid JSON with these exact keys:\n"
        "{\n"
        '  "transcript": "Complete speaker-labeled verbatim transcript (Customer / Agent) preserving original spoken language",\n'
        '  "language": "Hindi | Hinglish | English",\n'
        '  "topic": "billing_or_payment | delivery_or_order_status | login_or_account_access | general_support",\n'
        '  "sentiment": "frustrated | confused | neutral | satisfied",\n'
        '  "resolution": "resolved | partly_resolved | unresolved",\n'
        '  "summary": "Detailed, clear summary of the conversation, issue context, and outcome",\n'
        '  "customer_query": "Complete description of what the customer asked or reported",\n'
        '  "rep_performance": {"clarity": 4.0, "helpfulness": 4.0, "empathy": 4.0, "summary": "Detailed evaluation of representative tone, accuracy, and helpfulness"},\n'
        '  "key_problems": [{"category": "issue", "description": "Specific problem observed in the call"}],\n'
        '  "improvement_suggestions": ["Specific actionable improvement 1", "Specific actionable improvement 2", "Specific actionable improvement 3"],\n'
        '  "recurring_pattern": "Pattern or trend across support operations"\n'
        "}"
    )

    raw_bytes = audio_path.read_bytes()
    mime = _mime_for_audio(audio_path)

    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
        for model_name in _candidate_models(client):
            try:
                resp = client.models.generate_content(
                    model=model_name,
                    contents=[
                        types.Part.from_bytes(data=raw_bytes, mime_type=mime),
                        prompt,
                    ],
                )
                txt = (getattr(resp, "text", "") or "").strip()
                parsed = _parse_json_loose(txt)
                if parsed.get("transcript"):
                    parsed["_model"] = model_name
                    parsed["ok"] = True
                    return parsed
            except Exception:
                continue
    except Exception:
        pass

    return {"ok": False, "error": "Gemini audio call did not return a transcript."}
