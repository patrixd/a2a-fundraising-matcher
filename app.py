import json
from functools import wraps

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from database import get_db, init_db
from matcher import run_match
from profiles import (
    get_role_profile,
    list_counterparts,
    profile_is_complete,
    save_founder_profile,
    save_vc_profile,
    to_match_payload,
)

app = Flask(__name__)
app.secret_key = "hackathon-mock-secret-change-in-prod"


def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("index"))
        return f(*args, **kwargs)

    return wrapped


def current_user():
    if "user_id" not in session:
        return None
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_agent_md(user_id):
    conn = get_db()
    row = conn.execute("SELECT content FROM agent_md WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return row["content"] if row else ""


def save_agent_md(user_id, content):
    conn = get_db()
    conn.execute(
        """
        INSERT INTO agent_md (user_id, content, updated_at)
        VALUES (?, ?, datetime('now'))
        ON CONFLICT(user_id) DO UPDATE SET
            content=excluded.content,
            updated_at=datetime('now')
        """,
        (user_id, content),
    )
    conn.commit()
    conn.close()


def setup_is_complete(user):
    return profile_is_complete(user["id"], user["role"]) and bool(get_agent_md(user["id"]).strip())


def dashboard_route(user):
    return "founder_dashboard" if user["role"] == "founder" else "vc_dashboard"


@app.before_request
def setup_db():
    init_db()


@app.route("/")
def index():
    if session.get("user_id"):
        user = current_user()
        if not setup_is_complete(user):
            return redirect(url_for("setup"))
        return redirect(url_for(dashboard_route(user)))
    return render_template("index.html")


@app.route("/login", methods=["POST"])
def login():
    name = (request.form.get("name") or "Demo User").strip()
    role = request.form.get("role", "founder")
    if role not in ("founder", "vc"):
        role = "founder"

    conn = get_db()
    cur = conn.execute("INSERT INTO users (name, role) VALUES (?, ?)", (name, role))
    user_id = cur.lastrowid
    conn.commit()
    conn.close()

    session["user_id"] = user_id
    session["role"] = role
    flash(f"Welcome, {name}! Set up your profile and agent.", "success")
    return redirect(url_for("setup"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/setup", methods=["GET", "POST"])
@login_required
def setup():
    user = current_user()
    profile = get_role_profile(user["id"], user["role"]) or {}
    agent_content = get_agent_md(user["id"]) or default_agent_md(user)

    if request.method == "POST":
        if user["role"] == "founder":
            save_founder_profile(
                user["id"],
                {
                    "company_name": request.form.get("company_name", "").strip(),
                    "one_liner": request.form.get("one_liner", "").strip(),
                    "problem_solution": request.form.get("problem_solution", "").strip(),
                    "traction": request.form.get("traction", "").strip(),
                    "stage": request.form.get("stage", "").strip(),
                    "sector": request.form.get("sector", "").strip(),
                    "geography": request.form.get("geography", "").strip(),
                    "raising_amount": request.form.get("raising_amount", "").strip(),
                    "use_of_funds": request.form.get("use_of_funds", "").strip(),
                    "team_background": request.form.get("team_background", "").strip(),
                    "looking_for_investor": request.form.get("looking_for_investor", "").strip(),
                },
            )
        else:
            save_vc_profile(
                user["id"],
                {
                    "fund_name": request.form.get("fund_name", "").strip(),
                    "your_title": request.form.get("your_title", "").strip(),
                    "investment_thesis": request.form.get("investment_thesis", "").strip(),
                    "sectors": request.form.get("sectors", "").strip(),
                    "stages": request.form.get("stages", "").strip(),
                    "check_size": request.form.get("check_size", "").strip(),
                    "geography": request.form.get("geography", "").strip(),
                    "notable_investments": request.form.get("notable_investments", "").strip(),
                    "looking_for_founders": request.form.get("looking_for_founders", "").strip(),
                },
            )

        agent_body = request.form.get("agent_content", "").strip()
        if agent_body:
            save_agent_md(user["id"], agent_body)

        flash("Saved to SQLite.", "success")

        if setup_is_complete(user):
            return redirect(url_for(dashboard_route(user)))
        flash("Fill required fields (*) and AGENTS.md to continue.", "error")
        profile = get_role_profile(user["id"], user["role"]) or {}
        agent_content = get_agent_md(user["id"]) or agent_body

    return render_template(
        "setup.html",
        user=user,
        profile=profile,
        agent_content=agent_content,
        profile_complete=profile_is_complete(user["id"], user["role"]),
        agent_complete=bool(get_agent_md(user["id"]).strip()),
    )


@app.route("/profile")
@login_required
def edit_profile_redirect():
    return redirect(url_for("setup"))


@app.route("/agent")
@login_required
def edit_agent_redirect():
    return redirect(url_for("setup"))


def _require_setup(user):
    if not setup_is_complete(user):
        flash("Complete your setup first.", "error")
        return redirect(url_for("setup"))
    return None


@app.route("/founder")
@login_required
def founder_dashboard():
    user = current_user()
    if user["role"] != "founder":
        return redirect(url_for("vc_dashboard"))
    guard = _require_setup(user)
    if guard:
        return guard

    profile = get_role_profile(user["id"], "founder")
    agent = get_agent_md(user["id"])
    conn = get_db()
    matches = conn.execute(
        "SELECT m.*, u.name AS vc_name FROM matches m "
        "JOIN users u ON u.id = m.vc_id WHERE m.founder_id = ? ORDER BY m.id DESC",
        (user["id"],),
    ).fetchall()
    conn.close()

    return render_template(
        "dashboard.html",
        user=user,
        profile=profile,
        agent_md=agent,
        counterparts=list_counterparts("founder"),
        matches=[dict(m) for m in matches],
        role_label="Founder",
    )


@app.route("/vc")
@login_required
def vc_dashboard():
    user = current_user()
    if user["role"] != "vc":
        return redirect(url_for("founder_dashboard"))
    guard = _require_setup(user)
    if guard:
        return guard

    profile = get_role_profile(user["id"], "vc")
    agent = get_agent_md(user["id"])
    conn = get_db()
    matches = conn.execute(
        "SELECT m.*, u.name AS founder_name FROM matches m "
        "JOIN users u ON u.id = m.founder_id WHERE m.vc_id = ? ORDER BY m.id DESC",
        (user["id"],),
    ).fetchall()
    conn.close()

    return render_template(
        "dashboard.html",
        user=user,
        profile=profile,
        agent_md=agent,
        counterparts=list_counterparts("vc"),
        matches=[dict(m) for m in matches],
        role_label="VC",
    )


def default_agent_md(user):
    if user["role"] == "founder":
        return """# Founder Agent

## What I'm looking for
- Seed investors with B2B SaaS experience
- Hands-on help with enterprise GTM

## What you should do
- Represent our startup accurately using profile data
- Only recommend intros when stage, sector, and check size align
- Be direct, data-driven, and protect founder calendar time
"""
    return """# VC Agent

## What I'm looking for
- Seed–Series A founders with clear wedge and early traction
- Teams that can articulate unit economics

## What you should do
- Screen for thesis fit before recommending partner time
- Ask sharp questions on moat, market size, and retention
- Decline politely when out of mandate; escalate strong fits
"""


@app.route("/match/<int:other_id>", methods=["POST"])
@login_required
def trigger_match(other_id):
    user = current_user()
    guard = _require_setup(user)
    if guard:
        return guard

    conn = get_db()
    other = conn.execute("SELECT * FROM users WHERE id = ?", (other_id,)).fetchone()
    if not other:
        conn.close()
        flash("User not found.", "error")
        return redirect(request.referrer or url_for("index"))

    other = dict(other)
    if user["role"] == other["role"]:
        conn.close()
        flash("Can only match Founder ↔ VC.", "error")
        return redirect(request.referrer or url_for("index"))

    founder_id = user["id"] if user["role"] == "founder" else other_id
    vc_id = other_id if user["role"] == "founder" else user["id"]

    f_user = dict(conn.execute("SELECT * FROM users WHERE id = ?", (founder_id,)).fetchone())
    v_user = dict(conn.execute("SELECT * FROM users WHERE id = ?", (vc_id,)).fetchone())
    f_prof = get_role_profile(founder_id, "founder")
    v_prof = get_role_profile(vc_id, "vc")
    f_agent = get_agent_md(founder_id)
    v_agent = get_agent_md(vc_id)

    if not f_prof or not v_prof:
        conn.close()
        flash("Both sides need a completed profile.", "error")
        return redirect(request.referrer or url_for(dashboard_route(user)))

    founder = to_match_payload(f_user, f_prof)
    vc = to_match_payload(v_user, v_prof)
    result = run_match(founder, vc, f_agent, v_agent)

    conn.execute(
        """
        INSERT INTO matches (founder_id, vc_id, score, verdict, transcript)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            founder_id,
            vc_id,
            result.get("score", 0),
            result.get("verdict", ""),
            json.dumps(result),
        ),
    )
    match_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()

    return redirect(url_for("show_match", match_id=match_id))


@app.route("/matches/<int:match_id>")
@login_required
def show_match(match_id):
    conn = get_db()
    m = conn.execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()
    if not m:
        conn.close()
        flash("Match not found.", "error")
        return redirect(url_for("index"))
    m = dict(m)
    founder = dict(conn.execute("SELECT * FROM users WHERE id = ?", (m["founder_id"],)).fetchone())
    vc = dict(conn.execute("SELECT * FROM users WHERE id = ?", (m["vc_id"],)).fetchone())
    conn.close()

    data = json.loads(m["transcript"])
    user = current_user()
    back = url_for(dashboard_route(user)) if user else url_for("index")

    return render_template(
        "match.html",
        match=m,
        founder=founder,
        vc=vc,
        result=data,
        transcript=data.get("transcript", []),
        highlights=data.get("highlights", []),
        back_url=back,
    )


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5050)
