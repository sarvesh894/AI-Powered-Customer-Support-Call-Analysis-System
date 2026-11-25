import os
from pathlib import Path

BASE = Path(__file__).parent
INBOX = BASE / "inbox"            # yahan call recordings daalo
REPORTS = BASE / "reports"        # per-call reports yahan banengi
TRANSCRIPTS = BASE / "transcripts"  # sirf REDACTED transcripts save hote hain
DB_PATH = BASE / "calls.db"

MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")  # Hindi/Hinglish ke liye "small" ya "medium" try karo

POLL_SECONDS = 10
MAX_RETRIES = 3                   # failed call kitni baar retry hogi
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}
TEXT_EXT = {".txt"}               # testing ke liye: ready transcript bhi chalega

MIN_TRANSCRIPT_WORDS = 30         # isse chhota => audio incomplete/unclear
MIN_ASR_CONFIDENCE = 0.45         # speech-to-text confidence isse kam => human review

# Fixed topic list taaki alag-alag calls ko gin sako (dashboard ke liye zaroori)
TOPICS = [
    "billing_or_payment",
    "refund_or_cancellation",
    "login_or_account_access",
    "product_feature_howto",
    "delivery_or_order_status",
    "technical_issue",
    "complaint_about_service",
    "other",
]

PROBLEM_CATEGORIES = [
    "unclear_explanation",
    "incorrect_or_unsupported_info",
    "delay",
    "repeated_explanation",
    "poor_empathy",
    "missed_resolution",
    "process_gap",
    "other",
]
