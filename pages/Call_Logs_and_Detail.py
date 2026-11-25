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

st.markdown("""
st.markdown("""<style>[data-testid="stIconMaterial"],[data-testid="stSidebarCollapseButton"] *,[data-testid="stSidebarExpandButton"] *,.material-symbols-rounded,.material-icons{font-family:'Material Symbols Rounded','Material Icons' !important;}</style>""", unsafe_allow_html=True)
