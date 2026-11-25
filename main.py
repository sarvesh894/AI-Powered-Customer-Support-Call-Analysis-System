import argparse
import json
import time
import db
import tracking_agent
import insights
from config import INBOX, REPORTS, TRANSCRIPTS, POLL_SECONDS


def main():
    ap = argparse.ArgumentParser(description="AI Customer Support Call Analysis")
    ap.add_argument("cmd", choices=["run", "once", "insights", "status"],
                    help="run=hamesha chalta rahe | once=ek baar | insights=cross-call report | status=sab calls ka status")
    args = ap.parse_args()
    for d in (INBOX, REPORTS, TRANSCRIPTS):
        d.mkdir(exist_ok=True)
    db.init()

    if args.cmd == "once":
        tracking_agent.run_once()
    elif args.cmd == "run":
        print(f"Inbox watch ho raha hai ({POLL_SECONDS}s). Band karne ke liye Ctrl+C")
        while True:
            tracking_agent.run_once()
            time.sleep(POLL_SECONDS)
    elif args.cmd == "insights":
        out = insights.generate_top_areas()
        if out["areas"]:
            insights.write_summary_md(out)
        print(json.dumps(out, indent=1, ensure_ascii=False))
    elif args.cmd == "status":
        for r in db.all_calls():
            print(f"#{r['id']:<3} {r['status']:<13} tries={r['attempts']} {r['file_name']} {r['reason'] or ''}")


if __name__ == "__main__":
    main()
