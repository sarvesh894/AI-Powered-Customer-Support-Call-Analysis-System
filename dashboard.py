import html
import re
import pandas as pd
import streamlit as st
import db
from config import REPORTS

st.set_page_config(page_title="Call Intelligence Studio", page_icon="📞", layout="wide")

SERIF_FONT = "Charter, Georgia, 'Times New Roman', serif"

def lbl(v):
    s = "" if v is None else str(v).strip()
    return "Backup Mode" if s.startswith("fallback_") else (s.replace("_", " ").title() or "General")

def build_readable_reports(call_row: dict, md_fallback: str = ""):
    call_obj = call_row.get("raw") or {}
    a = call_obj.get("analysis") or {}
    rp = a.get("rep_performance") or {}
    probs = a.get("key_problems") or []
    imps = a.get("improvement_suggestions") or []

    cid = call_row.get("id", "")
    fname = call_row.get("file_name", "")
    topic = call_row.get("Topic", "General")
    sentiment = call_row.get("Sentiment", "Unclear")
    resolution = call_row.get("Resolution", "Unclear")
    clarity = f"{call_row.get('Clarity', 0):.1f} / 5.0"
    helpful = f"{call_row.get('Helpfulness', 0):.1f} / 5.0"
    empathy = f"{call_row.get('Empathy', 0):.1f} / 5.0"

    summary = a.get("summary") or "No summary recorded."
    query = a.get("customer_query") or "No customer query recorded."
    rep_note = rp.get("summary") or rp.get("feedback") or "No detailed representative note recorded."
    recurring = a.get("recurring_pattern") or "No recurring pattern flagged."

    prob_lines_txt = [f"  - {lbl(p.get('category', 'issue'))}: {p.get('description', '')}" for p in probs] or ["  - None recorded"]
    imp_lines_txt = [f"  - {s}" for s in imps] or ["  - None recorded"]

    plain_txt = "\n".join([
        "============================================================",
        f"CUSTOMER SUPPORT CALL ANALYSIS REPORT — CALL #{cid}",
        "============================================================",
        f"Recording File : {fname}",
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
        "============================================================",
    ])

    prob_li_html = "".join(
        f"<li><strong>{html.escape(lbl(p.get('category', 'issue')))}:</strong> {html.escape(str(p.get('description', '')))}</li>"
        for p in probs
    ) or "<li>None recorded</li>"

    imp_li_html = "".join(
        f"<li>{html.escape(str(s))}</li>"
        for s in imps
    ) or "<li>None recorded</li>"

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Call Report #{html.escape(str(cid))} — {html.escape(str(fname))}</title>
<style>
  body {{
    font-family: Charter, Georgia, 'Times New Roman', serif;
    background: #f8fafc;
    color: #0f172a;
    margin: 0;
    padding: 32px;
    line-height: 1.6;
  }}
  .sheet {{
    max-width: 860px;
    margin: 0 auto;
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 12px;
    padding: 32px 36px;
    box-shadow: 0 4px 18px rgba(15, 23, 42, 0.06);
  }}
  .top-tag {{
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #1d4ed8;
  }}
  h1 {{ margin: 6px 0 4px 0; font-size: 24px; color: #0f172a; }}
  .sub {{ color: #475569; font-size: 14px; margin-bottom: 20px; }}
  .grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 22px;
  }}
  .kpi {{
    background: #f1f5f9;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 10px 12px;
  }}
  .kpi .k {{ font-size: 11px; text-transform: uppercase; color: #475569; font-weight: 700; }}
  .kpi .v {{ font-size: 16px; font-weight: 700; color: #0f172a; margin-top: 3px; }}
  h2 {{
    font-size: 16px;
    color: #1e3a8a;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 4px;
    margin-top: 20px;
  }}
  p, li {{ font-size: 15px; color: #1e293b; }}
  @media print {{
    body {{ background: #ffffff; padding: 0; }}
    .sheet {{ border: none; box-shadow: none; }}
  }}
</style>
</head>
<body>
  <div class="sheet">
    <div class="top-tag">Customer Support Call Analysis Report</div>
    <h1>Call #{html.escape(str(cid))} — {html.escape(str(fname))}</h1>
    <div class="sub">Structured QA &amp; Improvement Summary (Press Ctrl+P in browser to save as PDF)</div>
    <div class="grid">
      <div class="kpi"><div class="k">Topic</div><div class="v">{html.escape(str(topic))}</div></div>
      <div class="kpi"><div class="k">Sentiment</div><div class="v">{html.escape(str(sentiment))}</div></div>
      <div class="kpi"><div class="k">Resolution</div><div class="v">{html.escape(str(resolution))}</div></div>
      <div class="kpi"><div class="k">Clarity / Empathy</div><div class="v">{clarity} | {empathy}</div></div>
    </div>
    <h2>1. Call Summary</h2>
    <p>{html.escape(str(summary))}</p>
    <h2>2. Customer Query</h2>
    <p>{html.escape(str(query))}</p>
    <h2>3. Support Representative Performance</h2>
    <p>{html.escape(str(rep_note))}</p>
    <h2>4. Key Problems</h2>
    <ul>{prob_li_html}</ul>
    <h2>5. Improvement Suggestions</h2>
    <ul>{imp_li_html}</ul>
    <h2>6. Recurring Patterns</h2>
    <p>{html.escape(str(recurring))}</p>
  </div>
</body>
</html>"""
    return html_doc, plain_txt

st.markdown(f"""
<style>
header[data-testid="stHeader"] {{ height: 2.3rem; background: transparent; }}
.stApp, .stApp p, .stApp div, .stApp label, .stApp span, .stApp li {{
  font-family: {SERIF_FONT};
}}
[data-testid="stIconMaterial"],
[data-testid="stSidebarCollapseButton"] *,
[data-testid="stSidebarExpandButton"] *,
.material-symbols-rounded,
.material-icons {{
  font-family: 'Material Symbols Rounded', 'Material Icons' !important;
}}
.stApp {{ background-color: #0b1120; color: #e2e8f0; }}
.block-container {{ padding-top: 3.2rem; padding-bottom: 2.4rem; max-width: 1320px; }}

.hero-box {{
  background: linear-gradient(135deg, #111827 0%, #1e293b 65%, #0f172a 100%);
  border: 1px solid #334155;
  border-radius: 16px;
  padding: 20px 24px;
  margin-bottom: 14px;
}}
.hero-tag {{
  display: inline-block;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #7dd3fc;
  background: rgba(14, 165, 233, 0.16);
  border: 1px solid rgba(125, 211, 252, 0.45);
  border-radius: 999px;
  padding: 4px 12px;
  margin-bottom: 8px;
}}
.hero-h1 {{ font-size: 1.65rem; font-weight: 700; color: #f8fafc; margin: 0; }}
.hero-p {{ font-size: 0.94rem; color: #cbd5e1; margin-top: 6px; }}

.m-card, .detail-box {{
  background: #111827;
  border: 1px solid #334155;
  border-radius: 14px;
  padding: 15px 17px;
  margin-bottom: 8px;
}}
.m-lbl {{ font-size: 0.76rem; font-weight: 700; text-transform: uppercase; color: #94a3b8; letter-spacing: 0.04em; }}
.m-val {{ font-size: 1.55rem; font-weight: 700; color: #f8fafc; margin-top: 4px; }}
.m-sub {{ font-size: 0.8rem; font-weight: 700; color: #38bdf8; margin-top: 4px; }}
.m-help {{ font-size: 0.82rem; color: #cbd5e1; margin-top: 4px; line-height: 1.4; }}

.live-banner {{
  background: #0f172a;
  border: 1px solid #38bdf8;
  border-radius: 12px;
  padding: 11px 16px;
  margin: 10px 0 14px 0;
  color: #f8fafc;
  font-size: 0.94rem;
}}
.sec-hdr {{
  background: #111827;
  border-left: 4px solid #38bdf8;
  border-radius: 10px;
  padding: 10px 16px;
  margin: 16px 0 12px 0;
  font-weight: 700;
  font-size: 1.02rem;
  color: #f8fafc;
}}

div.stButton > button, div.stDownloadButton > button {{
  background-color: #1d4ed8 !important;
  color: #ffffff !important;
  border: 1px solid #60a5fa !important;
  border-radius: 10px !important;
  font-weight: 700 !important;
  font-size: 0.9rem !important;
  padding: 0.55rem 0.9rem !important;
}}
div.stButton > button:hover, div.stDownloadButton > button:hover {{
  background-color: #2563eb !important;
  border-color: #93c5fd !important;
  color: #ffffff !important;
}}

.log-table-wrap {{
  overflow-x: auto;
  border: 1px solid #334155;
  border-radius: 12px;
  background: #111827;
  margin-bottom: 14px;
}}
table.call-log-tbl {{
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
  color: #f1f5f9;
}}
table.call-log-tbl thead th {{
  background: #1e293b;
  color: #7dd3fc;
  font-weight: 700;
  text-align: left;
  padding: 11px 14px;
  border-bottom: 2px solid #38bdf8;
  white-space: nowrap;
}}
table.call-log-tbl tbody td {{
  padding: 10px 14px;
  border-bottom: 1px solid #1e293b;
  color: #e2e8f0;
  vertical-align: middle;
}}
table.call-log-tbl tbody tr:hover {{
  background: #172554;
}}
.badge {{
  display: inline-block;
  padding: 2px 9px;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 700;
}}
.b-frust {{ background: rgba(239, 68, 68, 0.2); color: #fca5a5; border: 1px solid rgba(248, 113, 113, 0.5); }}
.b-unres {{ background: rgba(245, 158, 11, 0.2); color: #fcd34d; border: 1px solid rgba(251, 191, 36, 0.5); }}
.b-res {{ background: rgba(16, 185, 129, 0.2); color: #6ee7b7; border: 1px solid rgba(52, 211, 153, 0.5); }}
.b-topic {{ background: rgba(56, 189, 248, 0.16); color: #7dd3fc; border: 1px solid rgba(56, 189, 248, 0.4); }}
</style>
<div class="hero-box">
  <div class="hero-tag">Step 2 • Readable Formatted Reports (HTML &amp; Clean Text)</div>
  <div class="hero-h1">Customer Support Call Intelligence Studio</div>
  <div class="hero-p">Ab report download karne par browser mein direct readable formatted report (.html) aur clean plain-text (.txt) milega.</div>
</div>
""", unsafe_allow_html=True)

if hasattr(db, "init_db"):
    db.init_db()

raw_done = db.done_calls() or []
rows = []
for c in raw_done:
    a = c.get("analysis") or {}
    rp = a.get("rep_performance") or {}
    rows.append({
        "id": c.get("id"),
        "file_name": c.get("file_name", ""),
        "Topic": lbl(a.get("topic", "unclear")),
        "Sentiment": lbl(a.get("sentiment", "unclear")),
        "Resolution": lbl(a.get("resolution", "unclear")),
        "r_raw": str(a.get("resolution", "unclear")).lower(),
        "s_raw": str(a.get("sentiment", "unclear")).lower(),
        "Clarity": float(rp.get("clarity", 0) or 0),
        "Helpfulness": float(rp.get("helpfulness", 0) or 0),
        "Empathy": float(rp.get("empathy", 0) or 0),
        "raw": c,
    })

df = pd.DataFrame(rows)

if "mode_filter" not in st.session_state:
    st.session_state["mode_filter"] = "ALL"
if "click_count" not in st.session_state:
    st.session_state["click_count"] = 0

def set_mode(new_mode):
    st.session_state["mode_filter"] = new_mode
    st.session_state["click_count"] = st.session_state.get("click_count", 0) + 1

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown('<div class="m-card"><div class="m-sub">ACTION 1 • ALL CALLS</div><div class="m-val">All Calls</div><div class="m-help">Sabhi analysed calls ka full view.</div></div>', unsafe_allow_html=True)
    st.button("Show All Calls", key="btn_all", use_container_width=True, on_click=set_mode, args=("ALL",))
with c2:
    st.markdown('<div class="m-card"><div class="m-sub">ACTION 2 • FRUSTRATED</div><div class="m-val">Frustrated</div><div class="m-help">Frustrated ya confused calls filter karein.</div></div>', unsafe_allow_html=True)
    st.button("Filter Frustrated", key="btn_frust", use_container_width=True, on_click=set_mode, args=("FRUSTRATED",))
with c3:
    st.markdown('<div class="m-card"><div class="m-sub">ACTION 3 • UNRESOLVED</div><div class="m-val">Unresolved</div><div class="m-help">Jo calls abhi solve nahi hui hain.</div></div>', unsafe_allow_html=True)
    st.button("Filter Unresolved", key="btn_unres", use_container_width=True, on_click=set_mode, args=("UNRESOLVED",))
with c4:
    st.markdown('<div class="m-card"><div class="m-sub">ACTION 4 • TOP TOPIC</div><div class="m-val">Billing Focus</div><div class="m-help">Billing / Payment calls dekhein.</div></div>', unsafe_allow_html=True)
    st.button("Filter Billing", key="btn_bill", use_container_width=True, on_click=set_mode, args=("BILLING",))

mode = st.session_state["mode_filter"]
clicks = st.session_state["click_count"]

if df.empty:
    fdf = df.copy()
elif mode == "FRUSTRATED":
    fdf = df[df["s_raw"].isin(["frustrated", "confused"])].copy()
elif mode == "UNRESOLVED":
    fdf = df[df["r_raw"] != "resolved"].copy()
elif mode == "BILLING":
    fdf = df[df["Topic"].str.contains("Billing", case=False, na=False)].copy()
else:
    fdf = df.copy()

st.markdown(
    f'<div class="live-banner"><b>Live Button Status:</b> Active Mode = <b>{mode}</b> | '
    f'Matched Calls = <b>{len(fdf)}</b> of <b>{len(df)}</b> | Button Clicks Registered = <b>{clicks}</b></div>',
    unsafe_allow_html=True,
)

tot = len(fdf)
res_n = int(fdf["r_raw"].eq("resolved").sum()) if tot else 0
res_p = (res_n / tot * 100) if tot else 0.0
cl_a = float(fdf["Clarity"].mean()) if tot else 0.0
em_a = float(fdf["Empathy"].mean()) if tot else 0.0
attn_n = int(fdf["s_raw"].isin(["frustrated", "confused"]).sum()) if tot else 0
unres_n = tot - res_n

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(
        f'<div class="m-card"><div class="m-lbl">Analysed Calls</div><div class="m-val">{tot} Calls</div>'
        f'<div class="m-sub">{attn_n} need attention</div>'
        f'<div class="m-help">Frustrated/confused calls ko priority review ke liye filter karein.</div></div>',
        unsafe_allow_html=True,
    )
    st.button(f"Review {attn_n} Attention Calls", key="k_attn", use_container_width=True, on_click=set_mode, args=("FRUSTRATED",))
with k2:
    st.markdown(
        f'<div class="m-card"><div class="m-lbl">First-Call Resolution</div><div class="m-val">{res_p:.0f}%</div>'
        f'<div class="m-sub">{res_n} of {tot} resolved ({unres_n} open)</div>'
        f'<div class="m-help">Unresolved calls dekh kar repeat follow-up ghatayein.</div></div>',
        unsafe_allow_html=True,
    )
    st.button(f"Inspect {unres_n} Unresolved", key="k_unres", use_container_width=True, on_click=set_mode, args=("UNRESOLVED",))
with k3:
    cl_status = "Target >= 4.0 (Needs Coaching)" if cl_a < 4.0 else "Target Met (>= 4.0)"
    st.markdown(
        f'<div class="m-card"><div class="m-lbl">Avg Clarity</div><div class="m-val">{cl_a:.1f} / 5.0</div>'
        f'<div class="m-sub">{cl_status}</div>'
        f'<div class="m-help">Unclear explanations kam karke clarity badhayein.</div></div>',
        unsafe_allow_html=True,
    )
    st.button("Reset to All Calls", key="k_cl_reset", use_container_width=True, on_click=set_mode, args=("ALL",))
with k4:
    em_status = "Target >= 4.0 (Tone Check)" if em_a < 4.0 else "Target Met (>= 4.0)"
    st.markdown(
        f'<div class="m-card"><div class="m-lbl">Avg Empathy</div><div class="m-val">{em_a:.1f} / 5.0</div>'
        f'<div class="m-sub">{em_status}</div>'
        f'<div class="m-help">Billing/sensitive cases par supportive tone check karein.</div></div>',
        unsafe_allow_html=True,
    )
    st.button("Focus Billing Cases", key="k_em_bill", use_container_width=True, on_click=set_mode, args=("BILLING",))

st.markdown('<div class="sec-hdr">Step 2 • Styled Call Logs Table &amp; Readable Report Download</div>', unsafe_allow_html=True)

if fdf.empty:
    st.info("Is filter mein koi call match nahi hui. **Show All Calls** dabayein.")
else:
    tbl_rows_html = []
    for _, r in fdf.iterrows():
        s_cls = "b-frust" if r["s_raw"] in ("frustrated", "confused") else "b-topic"
        r_cls = "b-res" if r["r_raw"] == "resolved" else "b-unres"
        tbl_rows_html.append(
            f"<tr>"
            f"<td><b>#{r['id']}</b></td>"
            f"<td>{r['file_name']}</td>"
            f"<td><span class='badge b-topic'>{r['Topic']}</span></td>"
            f"<td><span class='badge {s_cls}'>{r['Sentiment']}</span></td>"
            f"<td><span class='badge {r_cls}'>{r['Resolution']}</span></td>"
            f"<td>{r['Clarity']:.1f} / 5</td>"
            f"<td>{r['Helpfulness']:.1f} / 5</td>"
            f"<td>{r['Empathy']:.1f} / 5</td>"
            f"</tr>"
        )
    tbl_html = (
        "<div class='log-table-wrap'><table class='call-log-tbl'>"
        "<thead><tr>"
        "<th>Call ID</th><th>Recording / File</th><th>Topic</th><th>Sentiment</th>"
        "<th>Resolution</th><th>Clarity</th><th>Helpfulness</th><th>Empathy</th>"
        "</tr></thead><tbody>"
        + "".join(tbl_rows_html)
        + "</tbody></table></div>"
    )
    st.markdown(tbl_html, unsafe_allow_html=True)

    f_records = fdf.to_dict("records")
    chosen = st.selectbox(
        "Select a Call Log to Inspect Full Analysis",
        f_records,
        format_func=lambda r: f"Call #{r['id']} — {r['file_name']} ({r['Topic']} | {r['Sentiment']} | {r['Resolution']})",
    )

    call_obj = chosen["raw"]
    analysis = call_obj.get("analysis") or {}
    rep = analysis.get("rep_performance") or {}

    st.markdown('<div class="detail-box">', unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Topic", chosen["Topic"])
    m2.metric("Sentiment", chosen["Sentiment"])
    m3.metric("Resolution", chosen["Resolution"])
    m4.metric("Clarity / Empathy", f"{chosen['Clarity']:.1f} / {chosen['Empathy']:.1f}")

    if analysis.get("summary"):
        st.markdown(f"**Call Summary:** {analysis['summary']}")
    if analysis.get("customer_query"):
        st.markdown(f"**Customer Query:** {analysis['customer_query']}")
    if rep.get("summary") or rep.get("feedback"):
        st.markdown(f"**Support Representative Performance:** {rep.get('summary') or rep.get('feedback')}")

    probs = analysis.get("key_problems") or []
    if probs:
        st.markdown("**Key Problems:**")
        for p in probs:
            st.markdown(f"- **{lbl(p.get('category', 'issue'))}:** {p.get('description', '')}")

    imps = analysis.get("improvement_suggestions") or []
    if imps:
        st.markdown("**Improvement Suggestions:**")
        for s in imps:
            st.markdown(f"- {s}")

    if analysis.get("recurring_pattern"):
        st.markdown(f"**Recurring Patterns:** {analysis['recurring_pattern']}")

    html_rep, txt_rep = build_readable_reports(chosen)
    md_path = REPORTS / f"call_{chosen['id']}.md"
    md_content = md_path.read_text(encoding="utf-8") if md_path.exists() else txt_rep

    dl1, dl2, dl3 = st.columns(3)
    with dl1:
        st.download_button(
            "📄 Download Formatted Report (.html)",
            data=html_rep,
            file_name=f"call_{chosen['id']}_report.html",
            mime="text/html",
            use_container_width=True,
            key=f"dl_html_{chosen['id']}",
        )
    with dl2:
        st.download_button(
            "📝 Download Clean Text Report (.txt)",
            data=txt_rep,
            file_name=f"call_{chosen['id']}_report.txt",
            mime="text/plain",
            use_container_width=True,
            key=f"dl_txt_{chosen['id']}",
        )
    with dl3:
        st.download_button(
            "⬇️ Download Raw Markdown (.md)",
            data=md_content,
            file_name=f"call_{chosen['id']}_report.md",
            mime="text/markdown",
            use_container_width=True,
            key=f"dl_md_{chosen['id']}",
        )
    st.markdown('</div>', unsafe_allow_html=True)