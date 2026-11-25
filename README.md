# AI-Powered Customer Support Call Analysis Agent

An end-to-end Python and Streamlit prototype that monitors customer support call recordings/transcripts, analyzes conversations through a two-agent pipeline, generates structured Markdown call reports, and visualizes operational insights on an interactive dashboard.

## 1. Two-Agent Architecture & Workflow
- Agent 1 - Call Tracking & Collection (tracking_agent.py, main.py, db.py): Watches the inbox/ directory for new recordings/transcripts, tracks processing state (pending, done, needs_review, failed) in calls.db (SQLite) to prevent duplicate processing, and dispatches jobs to Agent 2.
- Agent 2 - AI Call Analysis (transcribe.py, pii.py, analysis_agent.py): Converts audio to text, masks personal data (pii.py), extracts structured call analysis (summary, customer_query, topic, sentiment, resolution, rep_performance, key_problems, improvement_suggestions, recurring_patterns), verifies quotes against the transcript to reduce hallucinations, and writes reports to reports/.

## 2. Technologies & Models Used
- Language & Runtime: Python (venv), sqlite3, pandas.
- AI / LLM Layer: google-genai SDK targeting gemini-3.8-flash (configurable via GEMINI_MODEL), paired with retry handling and a local fallback analyzer (fallback_503) so cloud 503 UNAVAILABLE high-demand spikes or missing keys never block reporting or demos.
- Dashboard & Insights: Streamlit (dashboard.py) and insights.py.

## 3. Setup & How to Run
- Install: `python -m venv venv` then activate it and run `pip install -r requirements.txt`.
- Configure the Gemini API key as the `GEMINI_API_KEY` environment variable.
- Process calls and view the dashboard: `python main.py once`, `python main.py status`, or `streamlit run dashboard.py`.

## 4. Sample Output & Documentation
- Individual call reports are generated under `reports/`; the database, uploads, transcripts, and reports are local runtime data and are not committed.
- Detailed design considerations (duplicate control, short/unclear audio routing, anti-hallucination verification, PII protection, and future roadmap) are documented in [ARCHITECTURE.md](ARCHITECTURE.md).

## 5. Deploy on Streamlit Community Cloud
1. Push this repository to GitHub and create a Streamlit Community Cloud app using `dashboard.py` as the entry point.
2. Select Python 3.12 in the app's advanced settings.
3. Add `GEMINI_API_KEY` in the app's **Secrets** settings (do not commit `.env` or `secrets.toml`).
4. The app uses local SQLite and local folders for its runtime data. On hosted instances, that data may not persist across restarts; use persistent storage before relying on it for production customer call data.

## Project Requirements
See the [system requirements document](https://github.com/user-attachments/files/35422092/AI-Powered.Customer.Support.Call.Analysis.System.SRS.pdf).
