"""AGENT 2: Call Analysis Agent.
Input : job = {"call_id", "path", "file_name"}   (Agent 1 se aata hai)
Output: {"status": "done"|"needs_review", "reason": str|None, "analysis": dict|None}
Exception raise kare to Agent 1 usse 'failed' mark karke retry karta hai.
"""
import json
import os
import re
import time
from google import genai
from google.genai import types
import db
import pii
from config import (
    TOPICS,
    PROBLEM_CATEGORIES,
    REPORTS,
    TRANSCRIPTS,
    MIN_TRANSCRIPT_WORDS,
    MIN_ASR_CONFIDENCE,
)
from transcribe import transcribe

API_KEY = (
    os.environ.get("GEMINI_API_KEY")
    or os.environ.get("GOOGLE_API_KEY")
    or ""
).strip().strip('"').strip("'")

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
client = genai.Client(api_key=API_KEY) if API_KEY else None

SYSTEM = """You are a senior customer-support quality analyst.
You receive ONE call transcript (may be mixed Hindi/English; speakers may be unlabeled - infer
who is the customer and who is the support representative from context). Write all output in English.

STRICT RULES (to avoid misleading conclusions):
1. Use ONLY what is in the transcript. Never assume facts that are not said.
2. Every quote must be copied VERBATIM from ONE utterance (no timestamps, no speaker labels, no paraphrase).
3. If something cannot be determined, use "unclear" - do not guess.
4. Mark an explanation as incorrect only if it contradicts something else said in the same call
   or is clearly self-inconsistent; otherwise use 'unclear_explanation' or mention uncertainty.
5. Personal data is masked like [PHONE]; ignore it.
6. Be specific and actionable in improvement suggestions (what to say/do differently)."""

ANALYSIS_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "summary": {"type": "STRING", "description": "2-3 sentences: what happened"},
        "customer_query": {"type": "STRING", "description": "Why the customer called"},
        "topic": {"type": "STRING", "enum": TOPICS},
        "sentiment": {
            "type": "STRING",
            "enum": ["satisfied", "neutral", "confused", "frustrated", "unclear"],
        },
        "sentiment_evidence": {
            "type": "STRING",
            "description": "Verbatim customer quote supporting sentiment",
        },
        "resolution": {
            "type": "STRING",
            "enum": ["resolved", "partly_resolved", "unresolved", "unclear"],
        },
        "resolution_evidence": {
            "type": "STRING",
            "description": "Verbatim quote supporting resolution status",
        },
        "rep_performance": {
            "type": "OBJECT",
            "properties": {
                "clarity": {"type": "INTEGER"},
                "helpfulness": {"type": "INTEGER"},
                "empathy": {"type": "INTEGER"},
                "comment": {"type": "STRING"},
            },
            "required": ["clarity", "helpfulness", "empathy", "comment"],
        },
        "key_problems": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "issue": {"type": "STRING"},
                    "category": {"type": "STRING", "enum": PROBLEM_CATEGORIES},
                    "quote": {"type": "STRING", "description": "Verbatim quote as evidence"},
                    "timestamp": {"type": "STRING", "description": "mm:ss if available else empty"},
                },
                "required": ["issue", "category", "quote"],
            },
        },
        "improvement_suggestions": {"type": "ARRAY", "items": {"type": "STRING"}},
        "confidence": {"type": "STRING", "enum": ["high", "medium", "low"]},
        "confidence_reason": {"type": "STRING"},
    },
    "required": [
        "summary",
        "customer_query",
        "topic",
        "sentiment",
        "sentiment_evidence",
        "resolution",
        "resolution_evidence",
        "rep_performance",
        "key_problems",
        "improvement_suggestions",
        "confidence",
        "confidence_reason",
    ],
}


def _norm(s):
    return re.sub(
        r"\s+",
        " ",
        re.sub(r"[^a-z0-9\u0900-\u097f ]+", " ", (s or "").lower()),
    ).strip()


def _quote_ok(quote, norm_transcript):
    q = _norm(quote)
    return len(q) > 0 and q in norm_transcript


def verify_evidence(a, transcript):
    """Hallucination guard: jo quote transcript mein nahi mila, usse hata do."""
    nt = _norm(transcript)
    total = dropped = 0
    for key in ("sentiment_evidence", "resolution_evidence"):
        total += 1
        if not _quote_ok(a.get(key), nt):
            a[key] = "(quote could not be verified - removed)"
            dropped += 1
    kept = []
    for p in a.get("key_problems", []):
        total += 1
        if _quote_ok(p.get("quote"), nt):
            kept.append(p)
        else:
            dropped += 1
    a["key_problems"] = kept
    return a, dropped, total


def _fallback_analysis(transcript):
    """Gemini 503 high demand ke dauran pipeline na ruke isliye safe local extraction."""
    lines = [ln.strip() for ln in (transcript or "").splitlines() if ln.strip()]
    first_line = lines[0] if lines else "Transcript available"
    sample_quote = first_line[:140]
    low = (transcript or "").lower()

    topic = TOPICS[0] if TOPICS else "general_support"
    for t in TOPICS:
        token = t.replace("_", " ").split()[0]
        if token and token in low:
            topic = t
            break

    sentiment = "neutral"
    if any(w in low for w in ["angry", "frustrat", "late", "delay", "worst", "problem", "issue", "nahi mila", "der"]):
        sentiment = "frustrated"
    elif any(w in low for w in ["thank", "great", "good", "helpful", "resolved", "shukriya", "theek"]):
        sentiment = "satisfied"

    cat = PROBLEM_CATEGORIES[0] if PROBLEM_CATEGORIES else "other"
    for c in PROBLEM_CATEGORIES:
        token = c.replace("_", " ").split()[0]
        if token and token in low:
            cat = c
            break

    return {
        "summary": (
            f"Automated fallback summary generated because {MODEL} returned 503 high demand. "
            f"Transcript excerpt reviewed: {sample_quote}"
        ),
        "customer_query": sample_quote,
        "topic": topic,
        "sentiment": sentiment,
        "sentiment_evidence": sample_quote,
        "resolution": "unclear",
        "resolution_evidence": sample_quote,
        "rep_performance": {
            "clarity": 3,
            "helpfulness": 3,
            "empathy": 3,
            "comment": "Fallback evaluation generated while Gemini model experienced 503 high demand.",
        },
        "key_problems": [
            {
                "issue": "Issue detected in transcript during 503 model fallback mode.",
                "category": cat,
                "quote": sample_quote,
                "timestamp": "",
            }
        ],
        "improvement_suggestions": [
            "Provide clear status updates and realistic timelines to the customer.",
            "Re-run LLM analysis once Gemini 503 high demand subsides.",
        ],
        "confidence": "low",
        "confidence_reason": "Generated via local fallback due to Gemini 503 UNAVAILABLE high demand",
        "_mode": "fallback_503",
    }


def call_llm(transcript):
    if not client:
        return _fallback_analysis(transcript)
    last_err = None
    for attempt in range(2):
        try:
            resp = client.models.generate_content(
                model=MODEL,
                contents=f"Transcript:\n\n{transcript}",
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM,
                    response_mime_type="application/json",
                    response_schema=ANALYSIS_SCHEMA,
                    temperature=0.2,
                ),
            )
            if not resp.text:
                raise RuntimeError("Model ne structured output nahi diya")
            data = json.loads(resp.text)
            data["_mode"] = "llm"
            return data
        except Exception as exc:
            last_err = exc
            if "503" in str(exc) or "UNAVAILABLE" in str(exc):
                time.sleep(2 * (attempt + 1))
                continue
            raise
    if last_err and ("503" in str(last_err) or "UNAVAILABLE" in str(last_err)):
        return _fallback_analysis(transcript)
    raise last_err


def recurring_patterns(call_id, topic, problems):
    """Code se nikala gaya (LLM se nahi) -> isliye bharosemand."""
    others = [c for c in db.done_calls() if c["id"] != call_id]
    same = [c["analysis"] for c in others if c["analysis"].get("topic") == topic]
    mine = {p["category"] for p in problems}
    shared = {}
    for cat in mine:
        n = sum(
            1
            for a in same
            if any(p.get("category") == cat for p in a.get("key_problems", []))
        )
        if n:
            shared[cat] = n
    return {
        "other_calls_analysed": len(others),
        "same_topic_calls": len(same),
        "same_problem_in_other_calls": shared,
    }


def write_report(call_id, file_name, a):
    rp = a["rep_performance"]
    rec = a["recurring_patterns"]
    lines = [
        f"# Call Report #{call_id} - {file_name}",
        "",
        f"**Confidence:** {a['confidence']} ({a['confidence_reason']})",
        "",
        "## Call summary",
        a["summary"],
        "",
        "## Customer query",
        a["customer_query"],
        f"*Topic: {a['topic']}*",
        "",
        "## Customer sentiment",
        f"**{a['sentiment']}**  \nEvidence: \"{a['sentiment_evidence']}\"",
        "",
        "## Issue resolution",
        f"**{a['resolution']}**  \nEvidence: \"{a['resolution_evidence']}\"",
        "",
        "## Support representative performance",
        f"Clarity {rp['clarity']}/5 | Helpfulness {rp['helpfulness']}/5 | Empathy {rp['empathy']}/5",
        "",
        rp["comment"],
        "",
        "## Key problems",
    ]
    if a["key_problems"]:
        for p in a["key_problems"]:
            ts = f" [{p['timestamp']}]" if p.get("timestamp") else ""
            lines.append(f"- **{p['category']}**{ts}: {p['issue']}  \n  > \"{p['quote']}\"")
    else:
        lines.append("- No verified problems found.")

    lines += ["", "## Improvement suggestions"] + [
        f"- {s}" for s in a["improvement_suggestions"]
    ]
    lines += [
        "",
        "## Recurring patterns",
        f"- {rec['same_topic_calls']} other call(s) on topic '{a['topic']}' (out of {rec['other_calls_analysed']} analysed before this).",
        f"- Same problem type seen in other calls: {rec['same_problem_in_other_calls'] or 'none yet'}",
    ]
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / f"call_{call_id}.md").write_text("\n".join(lines), encoding="utf-8")


def analyze_call(job):
    call_id = job["call_id"]
    text, asr_conf = transcribe(job["path"])
    words = len(text.split())

    # Unclear / incomplete recording => LLM ko mat bhejo, human review ko bhejo
    if words < MIN_TRANSCRIPT_WORDS:
        return {
            "status": "needs_review",
            "analysis": None,
            "reason": f"Transcript bahut chhota ({words} words) - audio incomplete/silent ho sakta hai",
        }
    if asr_conf < MIN_ASR_CONFIDENCE:
        return {
            "status": "needs_review",
            "analysis": None,
            "reason": f"Speech-to-text confidence kam ({asr_conf:.2f}) - audio unclear hai",
        }

    clean = pii.redact(text)  # privacy: raw text kabhi save/send nahi hota
    TRANSCRIPTS.mkdir(parents=True, exist_ok=True)
    (TRANSCRIPTS / f"call_{call_id}.txt").write_text(clean, encoding="utf-8")

    a = call_llm(clean)
    mode = a.pop("_mode", "llm")
    a, dropped, total = verify_evidence(a, clean)
    a["recurring_patterns"] = recurring_patterns(call_id, a["topic"], a["key_problems"])
    a["meta"] = {
        "asr_confidence": round(asr_conf, 2),
        "unverified_quotes_removed": dropped,
        "model": MODEL,
        "mode": mode,
    }

    status, reason = "done", None
    if mode == "fallback_503":
        status, reason = "needs_review", "Gemini 503 high demand fallback se report bani (baad mein LLM se re-run karein)"
    elif a["confidence"] == "low":
        status, reason = "needs_review", "Model ko apne analysis pe low confidence hai"
    elif total and dropped / total >= 0.5:
        status, reason = "needs_review", f"{dropped}/{total} quotes verify nahi hue"

    write_report(call_id, job["file_name"], a)
    return {"status": status, "reason": reason, "analysis": a}