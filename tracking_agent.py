"""AGENT 1: Call Tracking & Collection Agent.
- inbox folder ko dekhta hai
- file ka SHA256 nikaal ke duplicate pehchanta hai (naam badalne se bhi nahi bachega)
- adhoori (abhi upload ho rahi) file skip karta hai
- har nayi call Agent 2 ko bhejta hai aur status DB mein likhta hai
"""
import hashlib
import time
import traceback
import db
import analysis_agent
from config import INBOX, AUDIO_EXT, TEXT_EXT


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_stable(path):
    """Size 1 sec mein badal rahi hai => file abhi copy ho rahi hai."""
    s1 = path.stat().st_size
    time.sleep(1)
    return s1 == path.stat().st_size and s1 > 0


def scan_inbox():
    new = 0
    for p in sorted(INBOX.iterdir()):
        if p.suffix.lower() not in (AUDIO_EXT | TEXT_EXT) or not p.is_file():
            continue
        if not _is_stable(p):
            print(f"[agent1] skip (abhi upload ho rahi): {p.name}")
            continue
        call_id = db.register_call(_sha256(p), p.name, p)
        if call_id:
            print(f"[agent1] nayi call mili: {p.name} -> id {call_id}")
            new += 1
    return new


def process_pending():
    for row in db.get_work():
        cid = row["id"]
        print(f"[agent1] call {cid} ({row['file_name']}) -> Agent 2")
        db.set_status(cid, "processing")
        try:
            result = analysis_agent.analyze_call(
                {"call_id": cid, "path": row["file_path"], "file_name": row["file_name"]})
            db.set_status(cid, result["status"], result["reason"], result["analysis"])
            print(f"[agent1] call {cid}: {result['status']} {result['reason'] or ''}")
        except Exception as e:
            traceback.print_exc()
            db.set_status(cid, "failed", f"{type(e).__name__}: {e}")
            print(f"[agent1] call {cid}: FAILED (retry hoga)")


def run_once():
    scan_inbox()
    process_pending()
