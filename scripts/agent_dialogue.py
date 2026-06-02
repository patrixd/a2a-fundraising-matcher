#!/usr/bin/env python3
"""Standalone agent dialogue simulator (stdin JSON → stdout JSON)."""
import json
import sys


def main():
    data = json.loads(sys.stdin.read())
    founder = data["founder"]
    vc = data["vc"]
    fa = data.get("founder_agent_md", "")
    va = data.get("vc_agent_md", "")

    f_agent = fa.split("\n")[0].replace("#", "").strip() if fa else "Founder Agent"
    v_agent = va.split("\n")[0].replace("#", "").strip() if va else "VC Agent"

    company = founder.get("company") or "the startup"
    sector = founder.get("sector") or "tech"
    stage = founder.get("stage") or "seed"
    thesis = vc.get("thesis") or "innovative software"
    check = vc.get("check_size") or "$1M"

    lines = [
        (f_agent or "Founder Agent", f"Representing {company} — {founder.get('headline', 'building in ' + sector)}. Raising {stage}."),
        (v_agent or "VC Agent", f"Our fund focuses on {thesis}. We write {check} checks. What's your wedge?"),
        (f_agent or "Founder Agent", (founder.get("bio") or "Clear product-market fit signals.")[:300]),
        (v_agent or "VC Agent", f"Interesting. {sector} at {stage} is in our sweet spot. I'd flag this for a partner meeting."),
        ("Match Engine", "Negotiation complete. Alignment on stage, sector, and thesis."),
    ]

    score = 72
    if founder.get("sector") and vc.get("thesis"):
        if founder["sector"].lower() in vc["thesis"].lower() or vc["thesis"].lower() in founder["sector"].lower():
            score = 88
    if founder.get("stage") and "seed" in (founder.get("stage") or "").lower():
        score = min(score + 5, 95)

    out = {
        "score": score,
        "verdict": "Match recommended" if score >= 75 else "Exploratory fit",
        "transcript": [{"speaker": s, "message": m} for s, m in lines],
        "highlights": [
            f"{company} ↔ {vc.get('company', vc.get('name', 'Fund'))}",
            f"Stage: {stage} | Check: {check}",
            "Agent dialogue completed via subprocess",
        ],
    }
    print(json.dumps(out))


if __name__ == "__main__":
    main()
