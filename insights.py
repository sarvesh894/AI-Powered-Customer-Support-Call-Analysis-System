"""Multiple calls ko jod ke trends nikaalta hai.
Numbers = code se (exact). Top-5 improvement areas = LLM se, lekin sirf in numbers/problems par based."""
import json
from collections import Counter, defaultdict
import anthropic
import db
from config import MODEL, REPORTS

client = anthropic.Anthropic(max_retries=3)


def compute_stats():
    calls = db.done_calls()
    n = len(calls)
    if n == 0:
        return {"total_calls": 0}
    topics, sent, res, cats = Counter(), Counter(), Counter(), Counter()
    topic_bad = defaultdict(lambda: [0, 0])      # topic -> [dissatisfied, total]
    topic_unres = defaultdict(lambda: [0, 0])    # topic -> [not resolved, total]
    topic_cat = Counter()
    scores = {"clarity": 0, "helpfulness": 0, "empathy": 0}
    for c in calls:
        a = c["analysis"]
        t = a["topic"]
        topics[t] += 1
        sent[a["sentiment"]] += 1
        res[a["resolution"]] += 1
        topic_bad[t][1] += 1
        topic_bad[t][0] += a["sentiment"] in ("frustrated", "confused")
        topic_unres[t][1] += 1
        topic_unres[t][0] += a["resolution"] in ("unresolved", "partly_resolved")
        for p in a["key_problems"]:
            cats[p["category"]] += 1
            topic_cat[(t, p["category"])] += 1
        for k in scores:
            scores[k] += a["rep_performance"][k]
    return {
        "total_calls": n,
        "topics": dict(topics.most_common()),
        "sentiment": dict(sent),
        "resolution": dict(res),
        "first_call_resolution_pct": round(100 * res["resolved"] / n, 1),
        "dissatisfaction_pct_by_topic": {t: round(100 * v[0] / v[1], 1) for t, v in topic_bad.items()},
        "not_fully_resolved_pct_by_topic": {t: round(100 * v[0] / v[1], 1) for t, v in topic_unres.items()},
        "rep_problem_categories": dict(cats.most_common()),
        "topic_problem_pairs": [{"topic": t, "problem": c, "count": k} for (t, c), k in topic_cat.most_common(8)],
        "avg_rep_scores": {k: round(v / n, 2) for k, v in scores.items()},
    }


TOP5_TOOL = {
    "name": "submit_top_areas",
    "description": "Submit top improvement areas for the support team.",
    "input_schema": {"type": "object", "properties": {"areas": {"type": "array", "maxItems": 5, "items": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "why_it_matters": {"type": "string", "description": "Use numbers from the data"},
            "evidence_call_ids": {"type": "array", "items": {"type": "integer"}},
            "recommended_action": {"type": "string"},
            "owner": {"type": "string", "enum": ["support_training", "product", "process", "knowledge_base"]},
        },
        "required": ["title", "why_it_matters", "evidence_call_ids", "recommended_action", "owner"]}}},
        "required": ["areas"]},
}


def generate_top_areas():
    stats = compute_stats()
    calls = db.done_calls()
    if len(calls) < 3:
        return {"note": "Kam se kam 3 analysed calls chahiye", "areas": []}
    compact = [{"call_id": c["id"], "topic": c["analysis"]["topic"],
                "sentiment": c["analysis"]["sentiment"], "resolution": c["analysis"]["resolution"],
                "problems": [f"{p['category']}: {p['issue']}" for p in c["analysis"]["key_problems"]],
                "suggestions": c["analysis"]["improvement_suggestions"]} for c in calls]
    prompt = ("You are advising a customer support manager. Based ONLY on the statistics and per-call "
              "findings below, give the top (up to 5) improvement areas, ranked by impact. Cite call ids "
              "as evidence. Do not invent numbers.\n\nSTATS:\n" + json.dumps(stats, indent=1) +
              "\n\nCALLS:\n" + json.dumps(compact, indent=1))
    resp = client.messages.create(model=MODEL, max_tokens=2500, tools=[TOP5_TOOL],
                                  tool_choice={"type": "tool", "name": "submit_top_areas"},
                                  messages=[{"role": "user", "content": prompt}])
    areas = next(b.input["areas"] for b in resp.content if b.type == "tool_use")
    valid = {c["id"] for c in calls}
    for a in areas:  # galat call id hata do
        a["evidence_call_ids"] = [i for i in a["evidence_call_ids"] if i in valid]
    out = {"stats": stats, "areas": areas}
    (REPORTS / "top_areas.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


def write_summary_md(out):
    s = out["stats"]
    L = ["# Support Insights Report", "",
         f"- Calls analysed: **{s['total_calls']}**",
         f"- First-call resolution: **{s['first_call_resolution_pct']}%**",
         f"- Sentiment: {s['sentiment']}", f"- Top topics: {s['topics']}",
         f"- Dissatisfaction % by topic: {s['dissatisfaction_pct_by_topic']}",
         f"- Rep problem categories: {s['rep_problem_categories']}", "", "## Top improvement areas"]
    for i, a in enumerate(out["areas"], 1):
        L += [f"### {i}. {a['title']}  ({a['owner']})", a["why_it_matters"],
              f"**Action:** {a['recommended_action']}", f"*Evidence calls: {a['evidence_call_ids']}*", ""]
    (REPORTS / "insights_report.md").write_text("\n".join(L), encoding="utf-8")
