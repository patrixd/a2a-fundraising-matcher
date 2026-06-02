import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "platform.db"


def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema():
    """Run migrations; safe to call before any write."""
    conn = get_db()
    _migrate_schema(conn)
    conn.commit()
    conn.close()


def init_db():
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('founder', 'vc')),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        -- Founder: startup facts + what they want from investors
        CREATE TABLE IF NOT EXISTS founder_profiles (
            user_id INTEGER PRIMARY KEY,
            company_name TEXT,
            one_liner TEXT,
            problem_solution TEXT,
            traction TEXT,
            stage TEXT,
            sector TEXT,
            geography TEXT,
            raising_amount TEXT,
            use_of_funds TEXT,
            team_background TEXT,
            looking_for_investor TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        -- VC: fund facts + what they look for in deals
        CREATE TABLE IF NOT EXISTS vc_profiles (
            user_id INTEGER PRIMARY KEY,
            fund_name TEXT,
            your_title TEXT,
            investment_thesis TEXT,
            sectors TEXT,
            stages TEXT,
            check_size TEXT,
            geography TEXT,
            notable_investments TEXT,
            looking_for_founders TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS agent_md (
            user_id INTEGER PRIMARY KEY,
            content TEXT NOT NULL DEFAULT '',
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS availability_slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            slot_date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            founder_id INTEGER NOT NULL,
            vc_id INTEGER NOT NULL,
            score INTEGER,
            verdict TEXT,
            transcript TEXT,
            meeting_start TEXT,
            meeting_end TEXT,
            meeting_title TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (founder_id) REFERENCES users(id),
            FOREIGN KEY (vc_id) REFERENCES users(id)
        );
        """
    )
    _migrate_schema(conn)
    _migrate_legacy_profiles(conn)
    conn.commit()
    conn.close()


def _table_columns(conn, table: str) -> set:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _add_column_if_missing(conn, table: str, column: str, definition: str):
    if table not in {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}:
        return
    if column not in _table_columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _migrate_schema(conn):
    """Add columns introduced after first deploy (SQLite has no IF NOT EXISTS for columns)."""
    for table, column, definition in (
        ("agent_md", "updated_at", "TEXT DEFAULT CURRENT_TIMESTAMP"),
        ("founder_profiles", "updated_at", "TEXT DEFAULT CURRENT_TIMESTAMP"),
        ("vc_profiles", "updated_at", "TEXT DEFAULT CURRENT_TIMESTAMP"),
        ("founder_profiles", "geography", "TEXT"),
        ("founder_profiles", "raising_amount", "TEXT"),
        ("founder_profiles", "use_of_funds", "TEXT"),
        ("founder_profiles", "team_background", "TEXT"),
        ("founder_profiles", "looking_for_investor", "TEXT"),
        ("founder_profiles", "problem_solution", "TEXT"),
        ("vc_profiles", "your_title", "TEXT"),
        ("vc_profiles", "notable_investments", "TEXT"),
        ("vc_profiles", "looking_for_founders", "TEXT"),
        ("matches", "meeting_start", "TEXT"),
        ("matches", "meeting_end", "TEXT"),
        ("matches", "meeting_title", "TEXT"),
    ):
        _add_column_if_missing(conn, table, column, definition)


def _migrate_legacy_profiles(conn):
    """One-time import from old generic profiles table if present."""
    if not conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='profiles'"
    ).fetchone():
        return

    rows = conn.execute("SELECT * FROM profiles").fetchall()
    for row in rows:
        row = dict(row)
        uid = row["user_id"]
        user = conn.execute("SELECT role FROM users WHERE id = ?", (uid,)).fetchone()
        if not user:
            continue
        if user["role"] == "founder":
            conn.execute(
                """
                INSERT INTO founder_profiles (
                    user_id, company_name, one_liner, problem_solution, traction,
                    stage, sector, looking_for_investor
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO NOTHING
                """,
                (
                    uid,
                    row.get("company"),
                    row.get("headline"),
                    row.get("bio"),
                    row.get("bio"),
                    row.get("stage"),
                    row.get("sector"),
                    "",
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO vc_profiles (
                    user_id, fund_name, investment_thesis, check_size,
                    sectors, looking_for_founders
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO NOTHING
                """,
                (
                    uid,
                    row.get("company"),
                    row.get("thesis") or row.get("headline"),
                    row.get("check_size"),
                    row.get("sector") or "",
                    row.get("bio") or "",
                ),
            )


def get_agent_md(user_id: int) -> str:
    ensure_schema()
    conn = get_db()
    row = conn.execute(
        "SELECT content FROM agent_md WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return row["content"] if row else ""


def save_agent_md(user_id: int, content: str):
    ensure_schema()
    conn = get_db()
    conn.execute(
        """
        INSERT INTO agent_md (user_id, content)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET content=excluded.content
        """,
        (user_id, content),
    )
    conn.commit()
    conn.close()
