import html
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

[data-testid="stIconMaterial"], [data-testid="stSidebarCollapseButton"] *, [data-testid="stSidebarExpandButton"] *, .material-symbols-rounded, .material-icons { font-family: 'Material Symbols Rounded', 'Material Icons' !important; }
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

[data-testid="stIconMaterial"], [data-testid="stSidebarCollapseButton"] *, [data-testid="stSidebarExpandButton"] *, .material-symbols-rounded, .material-icons { font-family: 'Material Symbols Rounded', 'Material Icons' !important; }
</style>

<div class="page-banner">
  <div class="page-pill">Filter &bull; Search Transcripts &bull; Deep QA Inspector</div>
  <div class="page-h1">Call Logs &amp; Detailed QA Explorer</div>
  <div class="page-sub">Filter calls by topic, sentiment, or resolution, search inside transcripts, and inspect full structured QA reports.</div>
</div>
""", unsafe_allow_html=True)

raw_done = db.done_calls() or []
rows = []
for c in raw_done:
    a = c.get("analysis") or {}
    rp = a.get("rep_performance") or {}
    fname = c.get("file_name", "")
    tr_text = load_transcript_for_file(fname)
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

if not rows:
    st.info("No analysed call logs found in the database.")
    st.stop()

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