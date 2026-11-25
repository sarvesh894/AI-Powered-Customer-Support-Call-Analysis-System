# AI-Powered Customer Support Call Analysis Agent - Architecture & Design

## 1. System Overview & Two-Agent Workflow
- **Agent 1 (Call Tracking & Collection Agent):** Monitors the designated inbox/ directory for new call recordings/transcripts, avoids duplicate re-processing via tracking/database state, records processing status (pending, done, needs_review, failed), and dispatches jobs to Agent 2.
- **Agent 2 (AI Call Analysis Agent):** Converts audio to text (transcribe.py), masks sensitive personal information (pii.py), runs structured call analysis (analysis_agent.py using gemini-3.8-flash with a safe 503 / offline fallback), verifies quotes against the transcript to reduce hallucinations, computes recurring patterns across calls, and writes structured Markdown reports to reports/.

## 2. Key Engineering Considerations
- **Multiple Recordings & Duplicate Prevention:** Tracks processed files and call records in calls.db (sqlite3) so previously analysed calls are not repeatedly processed.
- **Unclear, Short, or Incomplete Recordings:** Checks transcript length (MIN_TRANSCRIPT_WORDS) and ASR confidence (MIN_ASR_CONFIDENCE) before LLM analysis, routing short or noisy inputs to needs_review with a clear reason.
- **Anti-Hallucination & Evidence Verification:** Enforces structured JSON output and verifies quoted evidence against the normalized transcript (verify_evidence), dropping unverified quotes and flagging high drop ratios for review.
- **Resilience Under High Demand (503 UNAVAILABLE):** Uses retry backoff and a deterministic fallback analyzer (_fallback_analysis, marked as fallback_503) so reporting and dashboard visibility never block during cloud demand spikes.
- **Privacy & PII Protection:** Redacts personal data (pii.py) prior to persisting transcripts or generating outputs.

## 3. Deliverables & Future Enhancements
- **Deliverables:** Working Python + Streamlit prototype (main.py, analysis_agent.py, dashboard.py, insights.py, db.py, pii.py, transcribe.py), structured .md call reports in reports/, and this architecture guide.
- **Suggested Future Features:**
  1. Automatic background re-analysis queue for fallback_503 calls once cloud capacity normalizes.
  2. Speaker diarization (Customer vs. Support Rep separation) and SLA/escalation alert rules.
  3. Exportable weekly manager summary reports (PDF/CSV) and trend comparisons across time windows.
