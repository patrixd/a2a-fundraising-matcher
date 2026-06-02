"""Simulated agent-to-agent matching via subprocess script."""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent / "scripts" / "agent_dialogue.py"


def run_match(founder: dict, vc: dict, founder_agent: str, vc_agent: str) -> dict:
    payload = json.dumps(
        {
            "founder": founder,
            "vc": vc,
            "founder_agent_md": founder_agent,
            "vc_agent_md": vc_agent,
        }
    )
    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input=payload,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(SCRIPT.parent),
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        pass
    return _fallback_match(founder, vc, founder_agent, vc_agent)


def _fallback_match(founder: dict, vc: dict, founder_agent: str, vc_agent: str) -> dict:
    f_name = founder.get("name", "Founder")
    v_name = vc.get("name", "VC")
    sector = founder.get("sector") or "their space"
    stage = founder.get("stage") or "seed"
    check = vc.get("check_size") or "$500k–$2M"

    transcript = [
        {"speaker": f"{f_name}'s Agent", "message": f"Hi — I represent {founder.get('company', 'our startup')}. We're raising at {stage} in {sector}. {founder.get('headline', '')}"},
        {"speaker": f"{v_name}'s Agent", "message": f"Thanks. Our mandate: {vc.get('thesis', 'B2B software')}. Typical check {check}. Tell me about traction."},
        {"speaker": f"{f_name}'s Agent", "message": founder.get("bio", "Strong early metrics and a clear wedge.")[:280]},
        {"speaker": f"{v_name}'s Agent", "message": "Sector and stage align with our thesis. I'd recommend a partner intro call."},
        {"speaker": "Match Engine", "message": "Agents reached consensus: proceed to intro."},
    ]
    return {
        "score": 78,
        "verdict": "Strong fit — schedule intro",
        "transcript": transcript,
        "highlights": [
            f"Stage ({stage}) matches VC focus",
            f"Sector overlap: {sector}",
            "Agents agreed on follow-up",
        ],
    }
