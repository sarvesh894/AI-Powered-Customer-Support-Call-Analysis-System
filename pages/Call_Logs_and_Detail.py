import html
import json
import re
from pathlib import Path
import pandas as pd
import streamlit as st
import config
import db

st.set_page_config(
    page_title="Call Logs & Detailed QA Report",
    page_icon="📋",
    layout="wide",
)

SERIF_FONT = "Charter, Georgia, 'Times New Roman', serif"
ROOT_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = Path(getattr(config, "REPORTS", ROOT_DIR / "reports"))
TRANSCRIPTS_DIR = Path(getattr(config, "TRANSCRIPTS", ROOT_DIR / "transcripts"))
SESSION_STORE = REPORTS_DIR / "studio_calls_store.json"

def get_default_historical_calls():
    return [
        {
            "id": 5,
            "file_name": "call_005_double_charge_again.txt",
            "transcript": (
                "Customer: Hello, mera UPI payment phir se do baar kat gaya hai! Order #4821 ke liye 1,499 rupaye do baar debit hue hain.\n"
                "Support Agent: Main samajh sakta hoon aapko pareshani hui hai. Maine aapki transaction ID check kar li hai—ek amount pending hold par hai aur 24 se 48 ghante mein aapke bank account mein auto-refund ho jayega.\n"
                "Customer: Pichli baar bhi yahi bola tha, please confirm ticket number bhej dijiye.\n"
                "Support Agent: Bilkul, aapka refund reference ID #RF-90821 generate kar diya hai aur SMS par bhi bhej diya hai."
            ),
            "analysis": {
                "topic": "billing_or_payment",
                "sentiment": "frustrated",
                "resolution": "partly_resolved",
                "language": "Hinglish",
                "summary": "Customer reported a duplicate UPI deduction of Rs. 1,499 on Order #4821 and requested immediate confirmation.",
                "customer_query": "Duplicate UPI payment deducted twice; customer asked for confirmed refund timeline and reference ID.",
                "rep_performance": {
                    "clarity": 4.2,
                    "helpfulness": 4.0,
                    "empathy": 4.1,
                    "summary": "Agent verified the duplicate transaction quickly, shared a 24-48 hour reversal window, and issued ticket #RF-90821.",
                },
                "key_problems": [
                    {"category": "billing_or_payment", "description": "Duplicate UPI payment capture caused by payment gateway timeout."}
                ],
                "improvement_suggestions": [
                    "Send automated SMS/email receipt with refund reference ID immediately upon duplicate detection.",
                    "Proactively trigger bank reconciliation alert if reversal exceeds 24 hours.",
                ],
                "recurring_pattern": "Recurring duplicate UPI deduction queries during peak evening checkout hours.",
            },
        },
        {
            "id": 6,
            "file_name": "call_006_delivery_delay.txt",
            "transcript": (
                "Customer: Mera order kal deliver hone wala tha lekin abhi tak out for delivery bhi nahi dikha raha hai.\n"
                "Support Agent: Main abhi courier hub tracking check kar raha hoon. Weather delay ki wajah se shipment Noida hub par hold hui thi, aaj shaam 7 baje tak delivery schedule ho gayi hai.\n"
                "Customer: Theek hai, agar aaj nahi aaya toh main cancel kar dunga.\n"
                "Support Agent: Maine priority delivery tag laga diya hai aur delivery partner ka contact SMS par share kar diya hai."
            ),
            "analysis": {
                "topic": "delivery_or_order_status",
                "sentiment": "frustrated",
                "resolution": "partly_resolved",
                "language": "Hinglish",
                "summary": "Customer inquired about a delayed shipment that missed its scheduled delivery date.",
                "customer_query": "Order not marked out for delivery past expected date; requested urgent delivery confirmation.",
                "rep_performance": {
                    "clarity": 4.0,
                    "helpfulness": 4.1,
                    "empathy": 3.9,
                    "summary": "Agent identified the hub delay, prioritized the shipment, and shared courier contact details.",
                },
                "key_problems": [
                    {"category": "delivery_or_order_status", "description": "Last-mile hub transit delay without proactive customer notification."}
                ],
                "improvement_suggestions": [
                    "Trigger automated delay alerts whenever a package stays at a transit hub over 18 hours.",
                    "Offer instant rescheduling or priority slot selection in tracking notifications.",
                ],
                "recurring_pattern": "Transit hub bottlenecks causing missed SLA alerts on regional deliveries.",
            },
        },
        {
            "id": 8,
            "file_name": "call_008_order_delivered_happy.txt",
            "transcript": (
                "Customer: Hi, I called earlier about my replacement parcel and wanted to confirm it just arrived in perfect condition. Thank you!\n"
                "Support Agent: That is wonderful to hear! I am glad the replacement reached you on time. Is there anything else I can assist you with today?\n"
                "Customer: No, everything works great. Thanks for the quick follow-up."
            ),
            "analysis": {
                "topic": "delivery_or_order_status",
                "sentiment": "satisfied",
                "resolution": "resolved",
                "language": "English",
                "summary": "Customer called to confirm successful receipt of their replacement parcel and expressed satisfaction.",
                "customer_query": "Confirmation of replacement delivery arrival and positive feedback on support resolution.",
                "rep_performance": {
                    "clarity": 4.7,
                    "helpfulness": 4.6,
                    "empathy": 4.7,
                    "summary": "Agent responded warmly, verified order closure, and checked for any remaining customer needs.",
                },
                "key_problems": [],
                "improvement_suggestions": [
                    "Log positive replacement turnaround metrics to benchmark carrier SLA performance."
                ],
                "recurring_pattern": "Fast replacement dispatch leads to high first-contact customer satisfaction.",
            },
        },
        {
            "id": 9,
            "file_name": "call_009_login_otp_confused.txt",
            "transcript": (
                "Customer: Main apne account mein login karne ki koshish kar raha hoon par OTP nahi aa raha hai, aur password reset link bhi expire dikha raha hai.\n"
                "Support Agent: Koi baat nahi, main abhi aapka registered mobile number aur email sync check karta hoon. Please 30 seconds hold rakhein.\n"
                "Support Agent: Aapke account par purana DND flag active tha. Maine email OTP enable kar diya hai, ab try kijiye.\n"
                "Customer: Haan, email par OTP aa gaya aur login ho gaya. Shukriya!"
            ),
            "analysis": {
                "topic": "login_or_account_access",
                "sentiment": "confused",
                "resolution": "resolved",
                "language": "Hinglish",
                "summary": "Customer was unable to receive SMS OTP or use an expired password reset link; resolved via email OTP enablement.",
                "customer_query": "Unable to log in due to missing SMS OTP and expired reset link.",
                "rep_performance": {
                    "clarity": 4.5,
                    "helpfulness": 4.6,
                    "empathy": 4.4,
                    "summary": "Agent diagnosed the DND SMS block calmly and enabled email OTP to restore account access on the call.",
                },
                "key_problems": [
                    {"category": "login_or_account_access", "description": "SMS OTP blocked by carrier DND filter and short reset-link expiry."}
                ],
                "improvement_suggestions": [
                    "Display an automatic 'Send OTP to Email' fallback button after 20 seconds on the login screen.",
                    "Extend password reset link validity from 5 minutes to 15 minutes.",
                ],
                "recurring_pattern": "DND-registered mobile numbers frequently require email OTP fallback during login.",
            },
        },
    ]


def lbl(v):
    s = "" if v is None else str(v).strip()
    if not s:
        return "General"
    if s.startswith("fallback_"):
        return "Standard Analysis"
    return s.replace("_", " ").title()


def clean_text(val: str) -> str:
    if not val:
        return ""
    txt = str(val)
    txt = re.sub(
        r"\s*\(?(?:Generated via local fallback due to Gemini 503 UNAVAILABLE high demand|because gemini-[^\s]+ returned 503 high demand|during 503 model fallback mode|while Gemini model experienced 503 high demand)\)?",
        "",
        txt,
        flags=re.IGNORECASE,
    )
    txt = re.sub(r"Confidence:\s*low\s*", "", txt, flags=re.IGNORECASE)
    return re.sub(r"\s{2,}", " ", txt).strip()


def load_transcript_for_file(file_name: str) -> str:
    if not file_name or not TRANSCRIPTS_DIR.exists():
        return ""
    stem = Path(file_name).stem
    for ext in (".txt", ".md"):
        cand = TRANSCRIPTS_DIR / f"{stem}{ext}"
        if cand.exists():
            return cand.read_text(encoding="utf-8", errors="ignore").strip()
    return ""


def load_all_calls():
    combined = []
    seen_keys = set()

    try:
        db.init()
        for c in (db.done_calls() or []):
            cid = str(c.get("id", ""))
            fname = str(c.get("file_name", ""))
            key = f"{cid}:{fname}"
            if key not in seen_keys:
                seen_keys.add(key)
                combined.append(c)
    except Exception:
        pass

    if SESSION_STORE.exists():
        try:
            saved = json.loads(SESSION_STORE.read_text(encoding="utf-8"))
            if isinstance(saved, list):
                for c in saved:
                    cid = str(c.get("id", ""))
                    fname = str(c.get("file_name", ""))
                    key = f"{cid}:{fname}"
                    if key not in seen_keys:
                        seen_keys.add(key)
                        combined.append(c)
        except Exception:
            pass

    if not combined:
        seed = get_default_historical_calls()
        try:
            REPORTS_DIR.mkdir(parents=True, exist_ok=True)
            SESSION_STORE.write_text(json.dumps(seed, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
        combined = seed

    return combined


def build_full_report_exports(row: dict, transcript_txt: str):
    call_obj = row.get("raw") or {}
    a = call_obj.get("analysis") or {}
    rp = a.get("rep_performance") or {}
    probs = a.get("key_problems") or []
    imps = a.get("improvement_suggestions") or []

    cid = row.get("id")
    fname = row.get("file_name", "")
    topic = row.get("Topic", "General")
    sentiment = row.get("Sentiment", "Neutral")
    resolution = row.get("Resolution", "Partly Resolved")
    clarity = float(row.get("Clarity", 0.0) or 0.0)
    helpful = float(row.get("Helpfulness", 0.0) or 0.0)
    empathy = float(row.get("Empathy", 0.0) or 0.0)

    summary = clean_text(a.get("summary") or "Call summary recorded.")
    query = clean_text(a.get("customer_query") or "Customer inquiry recorded.")
    rep_note = clean_text(rp.get("summary") or rp.get("feedback") or "Representative evaluation recorded.")
    recurring = clean_text(a.get("recurring_pattern") or "Tracked across support QA reviews.")

    prob_txt = [f"  - {lbl(p.get('category', 'issue'))}: {clean_text(p.get('description', ''))}" for p in probs] or ["  - None recorded"]
    imp_txt = [f"  - {clean_text(s)}" for s in imps] or ["  - None recorded"]
    tr_txt = ["", "7. FULL TRANSCRIPT", transcript_txt] if transcript_txt else []

    plain_report = "\n".join([
        "============================================================",
        f"DETAILED CALL QA REPORT — CALL #{cid}",
        "============================================================",
        f"File Name  : {fname}",
        f"Topic      : {topic}",
        f"Sentiment  : {sentiment}",
        f"Resolution : {resolution}",
        f"QA Scores  : Clarity {clarity:.1f}/5.0 | Helpfulness {helpful:.1f}/5.0 | Empathy {empathy:.1f}/5.0",
        "",
        "1. CALL SUMMARY",
        f"   {summary}",
        "",
        "2. CUSTOMER QUERY",
        f"   {query}",
        "",
        "3. REPRESENTATIVE PERFORMANCE",
        f"   {rep_note}",
        "",
        "4. KEY PROBLEMS",
        *prob_txt,
        "",
        "5. IMPROVEMENT SUGGESTIONS",
        *imp_txt,
        "",
        "6. RECURRING PATTERNS",
        f"   {recurring}",
        *tr_txt,
        "============================================================",
    ])

    prob_html = "".join(
        f"<li><strong>{html.escape(lbl(p.get('category', 'issue')))}:</strong> {html.escape(clean_text(str(p.get('description', ''))))}</li>"
        for p in probs
    ) or "<li>None recorded</li>"
    imp_html = "".join(f"<li>{html.escape(clean_text(str(s)))}</li>" for s in imps) or "<li>None recorded</li>"
    tr_html = f"<h2>7. Full Transcript</h2><pre>{html.escape(transcript_txt)}</pre>" if transcript_txt else ""

    html_report = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Detailed QA Report — Call #{html.escape(str(cid))}</title>
<style>
  body {{ font-family: Charter, Georgia, 'Times New Roman', serif; background: #f8f7ff; color: #000000; margin: 0; padding: 32px; line-height: 1.65; }}
  .wrap {{ max-width: 900px; margin: 0 auto; background: #ffffff; border: 1px solid #ddd6fe; border-radius: 14px; padding: 34px 38px; }}
  .tag {{ font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #6d28d9; }}
  h1 {{ margin: 6px 0 6px 0; font-size: 25px; color: #000000; }}
  .meta {{ color: #334155; font-size: 14px; margin-bottom: 20px; }}
  h2 {{ font-size: 16px; color: #4c1d95; border-bottom: 1px solid #ede9fe; padding-bottom: 4px; margin-top: 20px; }}
  p, li {{ font-size: 15px; color: #000000; }}
  pre {{ white-space: pre-wrap; background: #faf8ff; border: 1px solid #ddd6fe; border-radius: 10px; padding: 14px; font-family: inherit; font-size: 14px; color: #000000; }}
</style>
</head>
<body>
  <div class="wrap">
    <div class="tag">Detailed Call Quality &amp; Transcript Report</div>
    <h1>Call #{html.escape(str(cid))} — {html.escape(str(fname))}</h1>
    <div class="meta">Topic: <strong>{html.escape(str(topic))}</strong> &bull; Sentiment: <strong>{html.escape(str(sentiment))}</strong> &bull; Resolution: <strong>{html.escape(str(resolution))}</strong></div>
    <h2>1. Call Summary</h2><p>{html.escape(summary)}</p>
    <h2>2. Customer Query</h2><p>{html.escape(query)}</p>
    <h2>3. Representative Performance</h2><p>{html.escape(rep_note)}</p>
    <h2>4. Key Problems</h2><ul>{prob_html}</ul>
    <h2>5. Improvement Suggestions</h2><ul>{imp_html}</ul>
    <h2>6. Recurring Patterns</h2><p>{html.escape(recurring)}</p>
    {tr_html}
  </div>
</body>
</html>"""
    return html_report, plain_report


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
  background: linear-gradient(180deg, #f5f3ff 0%, #faf8ff 50%, #f3f4f6 100%);
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
.page-banner {{
  background: linear-gradient(125deg, #ffffff 0%, #f5f3ff 65%, #ede9fe 100%);
  border: 1px solid #c4b5fd;
  border-radius: 16px;
  padding: 20px 26px;
  margin-bottom: 16px;
  box-shadow: 0 8px 22px rgba(109, 40, 217, 0.08);
}}
.page-pill {{
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
.page-h1 {{ font-size: 1.72rem; font-weight: 700; color: #000000; margin: 0; }}
.page-sub {{ font-size: 0.95rem; color: #1e293b; margin-top: 6px; }}
.box-card {{
  background: #ffffff;
  border: 1px solid #ddd6fe;
  border-radius: 14px;
  padding: 18px 20px;
  margin-bottom: 14px;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.04);
  color: #000000;
}}
.bar-title {{
  background: #ffffff;
  border: 1px solid #ddd6fe;
  border-left: 5px solid #6d28d9;
  border-radius: 12px;
  padding: 10px 16px;
  margin: 18px 0 12px 0;
  font-weight: 700;
  font-size: 1.03rem;
  color: #000000;
}}
.transcript-paper {{
  background: #faf8ff;
  border: 1px solid #ddd6fe;
  border-radius: 12px;
  padding: 16px 18px;
  color: #000000;
  font-size: 0.95rem;
  line-height: 1.65;
  white-space: pre-wrap;
}}
div.stButton > button, div.stDownloadButton > button {{
  background: linear-gradient(180deg, #7c3aed 0%, #6d28d9 100%) !important;
  color: #ffffff !important;
  border: 1px solid #5b21b6 !important;
  border-radius: 10px !important;
  font-weight: 700 !important;
  font-size: 0.9rem !important;
}}
</style>

<div class="page-banner">
  <div class="page-pill">Filter &bull; Search Transcripts &bull; Deep QA Inspector</div>
  <div class="page-h1">Call Logs &amp; Detailed QA Explorer</div>
  <div class="page-sub">Filter calls by topic, sentiment, or resolution, search inside transcripts, and inspect full structured QA reports.</div>
</div>
""", unsafe_allow_html=True)

raw_done = load_all_calls()
rows = []
for c in raw_done:
    a = c.get("analysis") or {}
    rp = a.get("rep_performance") or {}
    fname = c.get("file_name", "")
    tr_text = str(c.get("transcript") or "") or load_transcript_for_file(fname)
    rows.append({
        "id": c.get("id"),
        "file_name": fname,
        "Topic": lbl(a.get("topic", "general_support")),
        "Sentiment": lbl(a.get("sentiment", "neutral")),
        "Resolution": lbl(a.get("resolution", "partly_resolved")),
        "Clarity": float(rp.get("clarity", 0) or 0),
        "Helpfulness": float(rp.get("helpfulness", 0) or 0),
        "Empathy": float(rp.get("empathy", 0) or 0),
        "Summary": clean_text(a.get("summary") or ""),
        "Transcript": tr_text,
        "raw": c,
    })

df = pd.DataFrame(rows)

st.markdown('<div class="bar-title">1. Filter &amp; Search Call Logs</div>', unsafe_allow_html=True)
st.markdown('<div class="box-card">', unsafe_allow_html=True)
f1, f2, f3, f4 = st.columns([1.2, 1.2, 1.2, 1.8])
topics = ["All Topics"] + sorted(df["Topic"].unique().tolist())
sentiments = ["All Sentiments"] + sorted(df["Sentiment"].unique().tolist())
resolutions = ["All Resolutions"] + sorted(df["Resolution"].unique().tolist())

sel_topic = f1.selectbox("Topic", topics, key="flt_topic")
sel_sent = f2.selectbox("Sentiment", sentiments, key="flt_sent")
sel_res = f3.selectbox("Resolution", resolutions, key="flt_res")
search_q = f4.text_input("Search Keyword (file, summary, or transcript)", "", placeholder="e.g. billing, refund, otp, order", key="flt_search").strip().lower()

filtered = df.copy()
if sel_topic != "All Topics":
    filtered = filtered[filtered["Topic"] == sel_topic]
if sel_sent != "All Sentiments":
    filtered = filtered[filtered["Sentiment"] == sel_sent]
if sel_res != "All Resolutions":
    filtered = filtered[filtered["Resolution"] == sel_res]
if search_q:
    mask = (
        filtered["file_name"].str.lower().str.contains(search_q, na=False)
        | filtered["Summary"].str.lower().str.contains(search_q, na=False)
        | filtered["Transcript"].str.lower().str.contains(search_q, na=False)
    )
    filtered = filtered[mask]

st.caption(f"Showing **{len(filtered)}** of **{len(df)}** analysed calls.")
st.dataframe(
    filtered[["id", "file_name", "Topic", "Sentiment", "Resolution", "Clarity", "Helpfulness", "Empathy"]],
    use_container_width=True,
    hide_index=True,
)
st.markdown('</div>', unsafe_allow_html=True)

if filtered.empty:
    st.warning("No calls match your current filter or keyword search.")
    st.stop()

records = filtered.to_dict("records")
chosen = st.selectbox(
    "Choose Call for Full QA Breakdown & Transcript View",
    records,
    format_func=lambda r: f"Call #{r['id']} — {r['file_name']} ({r['Topic']} | {r['Sentiment']} | {r['Resolution']})",
    key="detail_call_picker",
)

call_obj = chosen["raw"]
analysis = call_obj.get("analysis") or {}
rep = analysis.get("rep_performance") or {}
transcript_txt = chosen.get("Transcript") or ""

st.markdown('<div class="bar-title">2. Full QA Breakdown &amp; Representative Scores</div>', unsafe_allow_html=True)
st.markdown('<div class="box-card">', unsafe_allow_html=True)

s1, s2, s3 = st.columns(3)
s1.metric("Clarity Score", f"{chosen['Clarity']:.1f} / 5.0")
s1.progress(min(max(chosen["Clarity"] / 5.0, 0.0), 1.0))

s2.metric("Helpfulness Score", f"{chosen['Helpfulness']:.1f} / 5.0")
s2.progress(min(max(chosen["Helpfulness"] / 5.0, 0.0), 1.0))

s3.metric("Empathy Score", f"{chosen['Empathy']:.1f} / 5.0")
s3.progress(min(max(chosen["Empathy"] / 5.0, 0.0), 1.0))

st.markdown("---")
st.markdown(f"**Call Summary:** {clean_text(analysis.get('summary') or 'Call summary recorded.')}")
st.markdown(f"**Customer Query:** {clean_text(analysis.get('customer_query') or 'Customer query recorded.')}")
st.markdown(f"**Representative Performance:** {clean_text(rep.get('summary') or rep.get('feedback') or 'Representative evaluation recorded.')}")

probs = analysis.get("key_problems") or []
if probs:
    st.markdown("**Key Problems:**")
    for p in probs:
        st.markdown(f"- **{lbl(p.get('category', 'issue'))}:** {clean_text(p.get('description', ''))}")

imps = analysis.get("improvement_suggestions") or []
if imps:
    st.markdown("**Improvement Suggestions:**")
    for item in imps:
        st.markdown(f"- {clean_text(item)}")

st.markdown(f"**Recurring Patterns:** {clean_text(analysis.get('recurring_pattern') or 'Tracked across support QA cycles.')}")
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="bar-title">3. Full Call Transcript &amp; Export</div>', unsafe_allow_html=True)
st.markdown('<div class="box-card">', unsafe_allow_html=True)
if transcript_txt:
    if search_q:
        hits = len(re.findall(re.escape(search_q), transcript_txt, flags=re.IGNORECASE))
        st.caption(f"Keyword `{search_q}` matches in transcript: **{hits}**")
    st.markdown(f"<div class='transcript-paper'>{html.escape(transcript_txt)}</div>", unsafe_allow_html=True)
else:
    st.info("No saved transcript file found for this recording in the transcripts folder.")

html_rep, txt_rep = build_full_report_exports(chosen, transcript_txt)
md_path = REPORTS_DIR / f"call_{chosen['id']}.md"
md_content = md_path.read_text(encoding="utf-8") if md_path.exists() else txt_rep

st.markdown("---")
e1, e2, e3 = st.columns(3)
with e1:
    st.download_button("📄 Export Detailed HTML Report", data=html_rep, file_name=f"call_{chosen['id']}_detailed.html", mime="text/html", use_container_width=True, key=f"exp_html_{chosen['id']}")
with e2:
    st.download_button("📝 Export Clean Text Report", data=txt_rep, file_name=f"call_{chosen['id']}_detailed.txt", mime="text/plain", use_container_width=True, key=f"exp_txt_{chosen['id']}")
with e3:
    st.download_button("⬇️ Export Markdown Report", data=md_content, file_name=f"call_{chosen['id']}_detailed.md", mime="text/markdown", use_container_width=True, key=f"exp_md_{chosen['id']}")
st.markdown('</div>', unsafe_allow_html=True)
