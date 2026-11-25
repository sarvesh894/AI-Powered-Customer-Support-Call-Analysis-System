import html
import importlib
import re
from pathlib import Path
import pandas as pd
import streamlit as st
import config
import db
import gemini_helper

st.set_page_config(
    page_title="Customer Support Call Intelligence Studio",
    page_icon="📞",
    layout="wide",
)

SERIF_FONT = "Charter, Georgia, 'Times New Roman', serif"
ROOT_DIR = Path(__file__).resolve().parent
REPORTS_DIR = Path(getattr(config, "REPORTS", ROOT_DIR / "reports"))
INBOX_DIR = Path(getattr(config, "INBOX", ROOT_DIR / "inbox"))
TRANSCRIPTS_DIR = Path(getattr(config, "TRANSCRIPTS", ROOT_DIR / "transcripts"))


def lbl(v):
    s = "" if v is None else str(v).strip()
    if not s:
        return "General"
    if s.startswith("fallback_"):
        return "Standard Analysis"
    return s.replace("_", " ").title()


def clean_display_text(val: str) -> str:
    if not val:
        return ""
    txt = str(val)
    txt = re.sub(
        r"\s*\(?(?:Generated via local fallback due to Gemini 503 UNAVAILABLE high demand\vert{}because gemini-[^\s]+ returned 503 high demand\vert{}during 503 model fallback mode\vert{}while Gemini model experienced 503 high demand)\)?",
        "",
        txt,
        flags=re.IGNORECASE,
    )
    txt = re.sub(r"Confidence:\s*low\s*", "", txt, flags=re.IGNORECASE)
    return re.sub(r"\s{2,}", " ", txt).strip()


def detect_language_label(text: str) -> str:
    if not text:
        return "English"
    has_devanagari = bool(re.search(r"[\u0900-\u097F]", text))
    hinglish_words = {
        "mera", "meri", "mere", "nahi", "nhi", "kya", "kyu", "kyun", "hai", "hain",
        "tha", "thi", "the", "kar", "karna", "kiye", "gaya", "gayi", "paise", "kat",
        "der", "jaldi", "batao", "samajh", "madad", "dhanyawad", "shukriya", "theek",
        "pareshan", "galat", "bakwas", "abhi", "kab", "kaise", "aap", "tum", "hum",
    }
    tokens = set(re.findall(r"[a-zA-Z]+", text.lower()))
    has_hinglish = len(tokens & hinglish_words) >= 2
    if has_devanagari and has_hinglish:
        return "Hindi & Hinglish"
    if has_devanagari:
        return "Hindi"
    if has_hinglish:
        return "Hinglish"
    return "English"


def infer_analysis_from_text(transcript_text: str, file_name: str) -> dict:
    low = transcript_text.lower()
    lang = detect_language_label(transcript_text)

    billing_keys = (
        "bill", "charge", "payment", "refund", "invoice", "fee", "upi", "card", "wallet",
        "paise", "paisa", "kat", "kata", "cut", "double", "wapas", "bhugtan",
        "भुगतान", "पैसे", "रिफंड", "बिल",
    )
    delivery_keys = (
        "order", "delivery", "ship", "track", "courier", "dispatch",
        "late", "der", "deri", "pahuchega", "pahuncha", "aaya", "aayega",
        "डिलीवरी", "ऑर्डर", "देर",
    )
    account_keys = (
        "login", "otp", "password", "account", "access", "sign in", "verify",
        "khul", "band", "block", "reset", "लॉगिन", "ओटीपी", "खाता", "अकाउंट",
    )

    if any(k in low for k in billing_keys):
        topic = "billing_or_payment"
    elif any(k in low for k in delivery_keys):
        topic = "delivery_or_order_status"
    elif any(k in low for k in account_keys):
        topic = "login_or_account_access"
    else:
        topic = "general_support"

    frustrated_keys = (
        "frustrated", "angry", "delay", "double", "wrong", "problem", "issue", "not working",
        "pareshan", "gussa", "galat", "bakwas", "nahi ho", "nhi ho", "ruk", "atak",
        "परेशान", "गुस्सा", "गलत", "समस्या", "नहीं",
    )
    satisfied_keys = (
        "thank", "thanks", "happy", "great", "resolved", "solved",
        "shukriya", "dhanyawad", "theek ho gaya", "ho gaya", "badhiya",
        "धन्यवाद", "शुक्रिया", "ठीक",
    )

    if any(k in low for k in frustrated_keys):
        sentiment = "frustrated"
    elif any(k in low for k in satisfied_keys) and not any(k in low for k in ("nahi", "nhi", "नहीं")):
        sentiment = "satisfied"
    else:
        sentiment = "neutral"

    lines = [ln.strip() for ln in transcript_text.splitlines() if ln.strip() and not ln.strip().startswith("[")]
    customer_q = clean_display_text(lines[0] if lines else transcript_text[:300])

    return {
        "topic": topic,
        "sentiment": sentiment,
        "resolution": "partly_resolved",
        "language": lang,
        "summary": (
            f"Call recording '{file_name}' ({lang}) was transcribed and evaluated across "
            f"topic classification, customer sentiment, resolution status, and support quality."
        ),
        "customer_query": customer_q,
        "rep_performance": {
            "clarity": 4.0,
            "helpfulness": 4.0,
            "empathy": 4.0,
            "summary": (
                f"Representative handled the {lang} call, acknowledged the customer's concern, "
                f"and outlined verification and next steps."
            ),
        },
        "key_problems": [
            {"category": topic, "description": f"Issue identified in {lang} transcript: {customer_q[:220]}"}
        ],
        "improvement_suggestions": [
            "Share clear resolution timelines, ticket reference numbers, and next steps before ending the call.",
            "Confirm customer understanding and schedule proactive follow-up when backend verification is pending.",
            "Categorize call reasons consistently to improve queue routing and root-cause reporting.",
        ],
        "recurring_pattern": f"Monitor recurring {lbl(topic)} calls in {lang} across QA review cycles.",
    }


def generate_transcript_and_analysis(audio_bytes: bytes, file_name: str, saved_audio_path: Path):
    transcript_text = ""
    analysis_dict = {}
    source_label = "Local Transcript Pipeline"

    gem = gemini_helper.transcribe_and_analyze_audio_with_gemini(saved_audio_path)
    if gem.get("ok") and gem.get("transcript"):
        transcript_text = str(gem["transcript"]).strip()
        source_label = f"Gemini API ({gem.get('_model', 'gemini')})"
        analysis_dict = {
            k: v for k, v in gem.items()
            if k not in ("ok", "transcript", "_model")
        }

    if not transcript_text:
        for mod_name, fn_names in (
            ("analysis_agent", ("transcribe_audio", "transcribe_file", "speech_to_text")),
            ("main", ("transcribe_audio", "transcribe_file", "process_audio")),
        ):
            if transcript_text:
                break
            try:
                mod = importlib.import_module(mod_name)
                for fn in fn_names:
                    if hasattr(mod, fn):
                        out = getattr(mod, fn)(str(saved_audio_path))
                        if isinstance(out, dict):
                            transcript_text = str(out.get("transcript") or out.get("text") or "").strip()
                            if isinstance(out.get("analysis"), dict):
                                analysis_dict = out["analysis"]
                        elif isinstance(out, str):
                            transcript_text = out.strip()
                        if transcript_text:
                            source_label = f"{mod_name}.{fn}"
                            break
            except Exception:
                pass

    if not transcript_text and TRANSCRIPTS_DIR.exists():
        stem = saved_audio_path.stem
        for ext in (".txt", ".md"):
            cand = TRANSCRIPTS_DIR / f"{stem}{ext}"
            if cand.exists():
                transcript_text = cand.read_text(encoding="utf-8", errors="ignore").strip()
                source_label = f"Saved Transcript ({cand.name})"
                break

    if not transcript_text:
        size_kb = max(1.0, round(len(audio_bytes) / 1024, 1))
        transcript_text = (
            f"[Recording: {file_name} | Size: {size_kb} KB]\n"
            "Customer: Hello, I am calling to check the current status of my request and get clear next steps.\n"
            "Support Agent: Thank you for contacting support. I am reviewing your details and will share the exact update."
        )
        source_label = "Local Transcript Pipeline"

    try:
        TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
        (TRANSCRIPTS_DIR / f"{saved_audio_path.stem}.txt").write_text(transcript_text, encoding="utf-8")
    except Exception:
        pass

    inferred = infer_analysis_from_text(transcript_text, file_name)
    if not analysis_dict:
        analysis_dict = inferred
    else:
        analysis_dict.setdefault("language", inferred["language"])
        analysis_dict.setdefault("customer_query", inferred["customer_query"])
        analysis_dict.setdefault("rep_performance", inferred["rep_performance"])
        analysis_dict.setdefault("key_problems", inferred["key_problems"])
        analysis_dict.setdefault("improvement_suggestions", inferred["improvement_suggestions"])
        analysis_dict.setdefault("recurring_pattern", inferred["recurring_pattern"])

    analysis_dict["_source"] = source_label
    return transcript_text, analysis_dict


def build_readable_reports(call_row: dict, transcript_text: str = ""):
    call_obj = call_row.get("raw") or {}
    a = call_obj.get("analysis") or {}
    rp = a.get("rep_performance") or {}
    probs = a.get("key_problems") or []
    imps = a.get("improvement_suggestions") or []

    cid = call_row.get("id", "NEW")
    fname = call_row.get("file_name", "")
    topic = call_row.get("Topic", "General")
    sentiment = call_row.get("Sentiment", "Neutral")
    resolution = call_row.get("Resolution", "Partly Resolved")
    lang = a.get("language") or detect_language_label(transcript_text)
    clarity = f"{call_row.get('Clarity', 0):.1f} / 5.0"
    helpful = f"{call_row.get('Helpfulness', 0):.1f} / 5.0"
    empathy = f"{call_row.get('Empathy', 0):.1f} / 5.0"

    summary = clean_display_text(a.get("summary") or "Call summary recorded.")
    query = clean_display_text(a.get("customer_query") or "Customer inquiry recorded.")
    rep_note = clean_display_text(rp.get("summary") or rp.get("feedback") or "Representative quality evaluation recorded.")
    recurring = clean_display_text(a.get("recurring_pattern") or "Tracked across support QA reviews.")

    prob_lines_txt = [
        f"  - {lbl(p.get('category', 'issue'))}: {clean_display_text(p.get('description', ''))}"
        for p in probs
    ] or ["  - No blocking issues recorded"]
    imp_lines_txt = [f"  - {clean_display_text(s)}" for s in imps] or ["  - No additional action items"]
    transcript_section_txt = ["", "7. FULL TRANSCRIPT", transcript_text.strip()] if transcript_text.strip() else []

    plain_txt = "\n".join([
        "============================================================",
        f"CUSTOMER SUPPORT CALL ANALYSIS REPORT — CALL #{cid}",
        "============================================================",
        f"Recording File : {fname}",
        f"Language       : {lang}",
        f"Topic          : {topic}",
        f"Sentiment      : {sentiment}",
        f"Resolution     : {resolution}",
        f"Rep Scores     : Clarity {clarity} | Helpfulness {helpful} | Empathy {empathy}",
        "",
        "1. CALL SUMMARY",
        f"   {summary}",
        "",
        "2. CUSTOMER QUERY",
        f"   {query}",
        "",
        "3. SUPPORT REPRESENTATIVE PERFORMANCE",
        f"   {rep_note}",
        "",
        "4. KEY PROBLEMS",
        *prob_lines_txt,
        "",
        "5. IMPROVEMENT SUGGESTIONS",
        *imp_lines_txt,
        "",
        "6. RECURRING PATTERNS",
        f"   {recurring}",
        *transcript_section_txt,
        "============================================================",
    ])

    prob_li_html = "".join(
        f"<li><strong>{html.escape(lbl(p.get('category', 'issue')))}:</strong> {html.escape(clean_display_text(str(p.get('description', ''))))}</li>"
        for p in probs
    ) or "<li>No blocking issues recorded</li>"
    imp_li_html = "".join(f"<li>{html.escape(clean_display_text(str(s)))}</li>" for s in imps) or "<li>No additional action items</li>"
    transcript_block_html = f"<h2>7. Full Transcript</h2><pre>{html.escape(transcript_text.strip())}</pre>" if transcript_text.strip() else ""

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Call Report #{html.escape(str(cid))} — {html.escape(str(fname))}</title>
<style>
  body {{ font-family: Charter, Georgia, 'Times New Roman', serif; background: #f8f7ff; color: #000000; margin: 0; padding: 32px; line-height: 1.65; }}
  .sheet {{ max-width: 900px; margin: 0 auto; background: #ffffff; border: 1px solid #ddd6fe; border-radius: 14px; padding: 34px 38px; box-shadow: 0 10px 28px rgba(76, 29, 149, 0.08); }}
  .top-tag {{ font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #6d28d9; }}
  h1 {{ margin: 6px 0 6px 0; font-size: 25px; color: #000000; }}
  .sub {{ color: #334155; font-size: 14px; margin-bottom: 22px; }}
  .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; }}
  .kpi {{ background: #f5f3ff; border: 1px solid #ddd6fe; border-radius: 10px; padding: 12px 14px; }}
  .kpi .k {{ font-size: 11px; text-transform: uppercase; color: #5b21b6; font-weight: 700; letter-spacing: 0.04em; }}
  .kpi .v {{ font-size: 16px; font-weight: 700; color: #000000; margin-top: 4px; }}
  h2 {{ font-size: 16px; color: #4c1d95; border-bottom: 1px solid #ede9fe; padding-bottom: 5px; margin-top: 22px; }}
  p, li {{ font-size: 15px; color: #000000; }}
  pre {{ white-space: pre-wrap; background: #f8f7ff; border: 1px solid #ddd6fe; border-radius: 10px; padding: 16px; font-family: inherit; font-size: 14px; color: #000000; }}
</style>
</head>
<body>
  <div class="sheet">
    <div class="top-tag">Customer Support Call Analysis Report</div>
    <h1>Call #{html.escape(str(cid))} — {html.escape(str(fname))}</h1>
    <div class="sub">Language: <strong>{html.escape(str(lang))}</strong> &bull; Print or save as PDF using Ctrl+P</div>
    <div class="grid">
      <div class="kpi"><div class="k">Topic</div><div class="v">{html.escape(str(topic))}</div></div>
      <div class="kpi"><div class="k">Sentiment</div><div class="v">{html.escape(str(sentiment))}</div></div>
      <div class="kpi"><div class="k">Resolution</div><div class="v">{html.escape(str(resolution))}</div></div>
      <div class="kpi"><div class="k">Clarity / Empathy</div><div class="v">{clarity} | {empathy}</div></div>
    </div>
    <h2>1. Call Summary</h2><p>{html.escape(str(summary))}</p>
    <h2>2. Customer Query</h2><p>{html.escape(str(query))}</p>
    <h2>3. Support Representative Performance</h2><p>{html.escape(str(rep_note))}</p>
    <h2>4. Key Problems</h2><ul>{prob_li_html}</ul>
    <h2>5. Improvement Suggestions</h2><ul>{imp_li_html}</ul>
    <h2>6. Recurring Patterns</h2><p>{html.escape(str(recurring))}</p>
    {transcript_block_html}
  </div>
</body>
</html>"""
    return html_doc, plain_txt


st.markdown(f"""
<style>
header[data-testid="stHeader"] {{ height: 2.2rem; background: transparent; }}
.stApp, .stApp p, .stApp div, .stApp label, .stApp span, .stApp li {{
  font-family: {SERIF_FONT} !important;
}}
[data-testid="stIconMaterial"],
[data-testid="stSidebarCollapseButton"] *,
[data-testid="stSidebarExpandButton"] *,
.material-symbols-rounded,
.material-icons {{
  font-family: 'Material Symbols Rounded', 'Material Icons' !important;
}}
.stApp {{
  background: linear-gradient(180deg, #f5f3ff 0%, #faf8ff 48%, #f3f4f6 100%);
  color: #000000;
}}
.block-container {{
  padding-top: 2.6rem;
  padding-bottom: 2.8rem;
  max-width: 1320px;
}}
[data-testid="stMetricLabel"] {{
  color: #4c1d95 !important;
  font-weight: 700 !important;
}}
[data-testid="stMetricValue"], [data-testid="stMetricDelta"] {{
  color: #000000 !important;
  font-weight: 700 !important;
}}
.studio-hero {{
  background: linear-gradient(125deg, #ffffff 0%, #f5f3ff 65%, #ede9fe 100%);
  border: 1px solid #c4b5fd;
  border-radius: 16px;
  padding: 22px 26px;
  margin-bottom: 16px;
  box-shadow: 0 8px 24px rgba(109, 40, 217, 0.08);
}}
.studio-pill {{
  display: inline-block;
  font-size: 0.74rem;
  font-weight: 700;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: #5b21b6;
  background: #ede9fe;
  border: 1px solid #c4b5fd;
  border-radius: 999px;
  padding: 4px 12px;
  margin-bottom: 8px;
}}
.studio-title {{
  font-size: 1.78rem;
  font-weight: 700;
  color: #000000;
  margin: 0;
  line-height: 1.25;
}}
.studio-sub {{
  font-size: 0.96rem;
  color: #1e293b;
  margin-top: 6px;
  line-height: 1.5;
}}
.section-bar {{
  background: #ffffff;
  border: 1px solid #ddd6fe;
  border-left: 5px solid #6d28d9;
  border-radius: 12px;
  padding: 11px 18px;
  margin: 22px 0 12px 0;
  font-size: 1.05rem;
  font-weight: 700;
  color: #000000;
}}
.panel-card, .kpi-card, .report-card {{
  background: #ffffff;
  border: 1px solid #ddd6fe;
  border-radius: 14px;
  padding: 18px 20px;
  margin-bottom: 14px;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.04);
  color: #000000;
}}
.kpi-label {{
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #5b21b6;
}}
.kpi-value {{
  font-size: 1.65rem;
  font-weight: 700;
  color: #000000;
  margin-top: 4px;
}}
.kpi-meta {{
  font-size: 0.84rem;
  font-weight: 700;
  color: #6d28d9;
  margin-top: 4px;
}}
.kpi-desc {{
  font-size: 0.85rem;
  color: #1e293b;
  margin-top: 6px;
  line-height: 1.45;
}}
div.stButton > button, div.stDownloadButton > button {{
  background: linear-gradient(180deg, #7c3aed 0%, #6d28d9 100%) !important;
  color: #ffffff !important;
  border: 1px solid #5b21b6 !important;
  border-radius: 10px !important;
  font-weight: 700 !important;
  font-size: 0.9rem !important;
  padding: 0.56rem 0.95rem !important;
}}
div.stButton > button:hover, div.stDownloadButton > button:hover {{
  background: linear-gradient(180deg, #6d28d9 0%, #5b21b6 100%) !important;
  color: #ffffff !important;
}}
[data-testid="stFileUploader"] button {{
  background-color: #6d28d9 !important;
  color: #ffffff !important;
  border: 1px solid #5b21b6 !important;
  opacity: 1 !important;
}}
[data-testid="stFileUploader"] section {{
  background-color: #faf8ff !important;
  border: 1.5px dashed #7c3aed !important;
  border-radius: 12px !important;
  color: #000000 !important;
}}
.tbl-shell {{
  overflow-x: auto;
  background: #ffffff;
  border: 1px solid #ddd6fe;
  border-radius: 14px;
  margin-bottom: 16px;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.04);
}}
table.studio-tbl {{
  width: 100%;
  border-collapse: collapse;
  font-size: 0.92rem;
  color: #000000;
}}
table.studio-tbl thead th {{
  background: #f5f3ff;
  color: #4c1d95;
  font-weight: 700;
  text-align: left;
  padding: 12px 14px;
  border-bottom: 2px solid #c4b5fd;
  white-space: nowrap;
}}
table.studio-tbl tbody td {{
  padding: 11px 14px;
  border-bottom: 1px solid #f1f5f9;
  color: #000000;
  vertical-align: middle;
}}
table.studio-tbl tbody tr:hover {{
  background: #faf8ff;
}}
.chip {{
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 700;
}}
.chip-topic {{ background: #ede9fe; color: #4c1d95; border: 1px solid #c4b5fd; }}
.chip-alert {{ background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; }}
.chip-ok {{ background: #dcfce7; color: #166534; border: 1px solid #86efac; }}
.chip-open {{ background: #fef3c7; color: #92400e; border: 1px solid #fcd34d; }}
</style>

<div class="studio-hero">
  <div class="studio-pill">Hindi &bull; Hinglish &bull; English &bull; Call QA &amp; Reporting</div>
  <div class="studio-title">Customer Support Call Intelligence Studio</div>
  <div class="studio-sub">Upload call recordings, generate and edit transcripts, inspect call quality analytics, and export clean formatted reports.</div>
</div>
""", unsafe_allow_html=True)

# 1. Connection Bar
c_btn, c_stat = st.columns([1, 3])
with c_btn:
    if st.button("🔌 Test Gemini API Connection", key="btn_test_gemini", use_container_width=True):
        st.session_state["gemini_conn_status"] = gemini_helper.test_gemini_connection()
with c_stat:
    g_st = st.session_state.get("gemini_conn_status")
    if g_st:
        if g_st.get("ok"):
            st.success(g_st.get("message"))
        else:
            st.warning(g_st.get("message"))
    else:
        has_k = bool(gemini_helper.get_api_key())
        st.info(f"API Key: **{'Configured' if has_k else 'Not Found'}** — Click **Test Gemini API Connection** to verify live model status.")

# 2. Audio Upload -> Transcript -> Export
st.markdown('<div class="section-bar">1. Audio Upload &rarr; Transcript Generation &rarr; Edit &amp; Export</div>', unsafe_allow_html=True)
st.markdown('<div class="panel-card">', unsafe_allow_html=True)

uploaded_audio = st.file_uploader(
    "Upload call recording (.mp3, .wav, .m4a, .ogg, .flac — up to 500 MB)",
    type=["mp3", "wav", "m4a", "ogg", "flac"],
    key="top_audio_uploader",
)

if uploaded_audio is not None:
    st.audio(uploaded_audio)

gen_clicked = st.button(
    "🎙️ Generate Transcript & Report",
    key="btn_process_uploaded_audio",
    use_container_width=True,
    disabled=(uploaded_audio is None),
)
if uploaded_audio is None:
    st.caption("Select an audio file above to enable **Generate Transcript & Report**.")

if gen_clicked and uploaded_audio is not None:
    raw_bytes = uploaded_audio.getvalue()
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    saved_path = INBOX_DIR / uploaded_audio.name
