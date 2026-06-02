"""Load/save role-specific profiles and build matcher payloads."""

from typing import Dict, List, Optional

from database import ensure_schema, get_db

FOUNDER_REQUIRED = ("company_name", "one_liner", "stage", "sector")
VC_REQUIRED = ("fund_name", "investment_thesis", "check_size", "stages")


def get_role_profile(user_id: int, role: str) -> Optional[Dict]:
    conn = get_db()
    if role == "founder":
        row = conn.execute(
            "SELECT * FROM founder_profiles WHERE user_id = ?", (user_id,)
        ).fetchone()
    else:
        row = conn.execute("SELECT * FROM vc_profiles WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def save_founder_profile(user_id: int, data: dict):
    ensure_schema()
    conn = get_db()
    conn.execute(
        """
        INSERT INTO founder_profiles (
            user_id, company_name, one_liner, problem_solution, traction,
            stage, sector, geography, raising_amount, use_of_funds,
            team_background, looking_for_investor
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            company_name=excluded.company_name,
            one_liner=excluded.one_liner,
            problem_solution=excluded.problem_solution,
            traction=excluded.traction,
            stage=excluded.stage,
            sector=excluded.sector,
            geography=excluded.geography,
            raising_amount=excluded.raising_amount,
            use_of_funds=excluded.use_of_funds,
            team_background=excluded.team_background,
            looking_for_investor=excluded.looking_for_investor
        """,
        (
            user_id,
            data.get("company_name", ""),
            data.get("one_liner", ""),
            data.get("problem_solution", ""),
            data.get("traction", ""),
            data.get("stage", ""),
            data.get("sector", ""),
            data.get("geography", ""),
            data.get("raising_amount", ""),
            data.get("use_of_funds", ""),
            data.get("team_background", ""),
            data.get("looking_for_investor", ""),
        ),
    )
    conn.commit()
    conn.close()


def save_vc_profile(user_id: int, data: dict):
    ensure_schema()
    conn = get_db()
    conn.execute(
        """
        INSERT INTO vc_profiles (
            user_id, fund_name, your_title, investment_thesis, sectors,
            stages, check_size, geography, notable_investments,
            looking_for_founders
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            fund_name=excluded.fund_name,
            your_title=excluded.your_title,
            investment_thesis=excluded.investment_thesis,
            sectors=excluded.sectors,
            stages=excluded.stages,
            check_size=excluded.check_size,
            geography=excluded.geography,
            notable_investments=excluded.notable_investments,
            looking_for_founders=excluded.looking_for_founders
        """,
        (
            user_id,
            data.get("fund_name", ""),
            data.get("your_title", ""),
            data.get("investment_thesis", ""),
            data.get("sectors", ""),
            data.get("stages", ""),
            data.get("check_size", ""),
            data.get("geography", ""),
            data.get("notable_investments", ""),
            data.get("looking_for_founders", ""),
        ),
    )
    conn.commit()
    conn.close()


def profile_is_complete(user_id: int, role: str) -> bool:
    p = get_role_profile(user_id, role)
    if not p:
        return False
    required = FOUNDER_REQUIRED if role == "founder" else VC_REQUIRED
    return all((p.get(k) or "").strip() for k in required)


def to_match_payload(user: dict, profile: Optional[Dict]) -> dict:
    """Normalize DB row for matcher subprocess (keeps legacy keys)."""
    if not profile:
        return {"name": user["name"]}
    if user["role"] == "founder":
        return {
            "name": user["name"],
            "company": profile.get("company_name"),
            "headline": profile.get("one_liner"),
            "bio": profile.get("traction") or profile.get("problem_solution"),
            "problem_solution": profile.get("problem_solution"),
            "traction": profile.get("traction"),
            "stage": profile.get("stage"),
            "sector": profile.get("sector"),
            "geography": profile.get("geography"),
            "raising_amount": profile.get("raising_amount"),
            "looking_for": profile.get("looking_for_investor"),
        }
    return {
        "name": user["name"],
        "company": profile.get("fund_name"),
        "headline": profile.get("investment_thesis"),
        "thesis": profile.get("investment_thesis"),
        "sectors": profile.get("sectors"),
        "sector": profile.get("sectors"),
        "stage": profile.get("stages"),
        "check_size": profile.get("check_size"),
        "geography": profile.get("geography"),
        "looking_for": profile.get("looking_for_founders"),
    }


def list_counterparts(role: str) -> List[Dict]:
    """Founders see VCs and vice versa, with summary fields for dashboard."""
    conn = get_db()
    other = "vc" if role == "founder" else "founder"
    if other == "vc":
        rows = conn.execute(
            """
            SELECT u.id, u.name, p.fund_name AS company, p.investment_thesis AS headline
            FROM users u
            LEFT JOIN vc_profiles p ON p.user_id = u.id
            WHERE u.role = 'vc'
            ORDER BY u.id DESC
            """
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT u.id, u.name, p.company_name AS company, p.one_liner AS headline
            FROM users u
            LEFT JOIN founder_profiles p ON p.user_id = u.id
            WHERE u.role = 'founder'
            ORDER BY u.id DESC
            """
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
