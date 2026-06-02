"""User availability slots and overlap detection for intro meetings."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from database import ensure_schema, get_db

SLOT_FMT = "%Y-%m-%d"
TIME_FMT = "%H:%M"


def normalize_time(value: str) -> str:
    """Accept HH:MM or HH:MM:SS from DB / browsers; store as HH:MM."""
    value = (value or "").strip()
    if not value:
        return ""
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(value, fmt).strftime(TIME_FMT)
        except ValueError:
            continue
    return value


def normalize_slot(slot: Dict) -> Dict:
    return {
        "slot_date": (slot.get("slot_date") or "").strip(),
        "start_time": normalize_time(slot.get("start_time", "")),
        "end_time": normalize_time(slot.get("end_time", "")),
    }


def list_slots(user_id: int) -> List[Dict]:
    ensure_schema()
    conn = get_db()
    rows = conn.execute(
        """
        SELECT id, slot_date, start_time, end_time
        FROM availability_slots
        WHERE user_id = ?
        ORDER BY slot_date, start_time
        """,
        (user_id,),
    ).fetchall()
    conn.close()
    return [normalize_slot(dict(r)) for r in rows]


def replace_slots(user_id: int, slots: List[Dict]):
    """Replace all slots for user. Each slot: {slot_date, start_time, end_time}."""
    ensure_schema()
    conn = get_db()
    conn.execute("DELETE FROM availability_slots WHERE user_id = ?", (user_id,))
    for raw in slots:
        s = normalize_slot(raw)
        if not s["slot_date"] or not s["start_time"] or not s["end_time"]:
            continue
        if s["start_time"] >= s["end_time"]:
            continue
        conn.execute(
            """
            INSERT INTO availability_slots (user_id, slot_date, start_time, end_time)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, s["slot_date"], s["start_time"], s["end_time"]),
        )
    conn.commit()
    conn.close()


def parse_slot_range(slot: Dict) -> Tuple[datetime, datetime]:
    s = normalize_slot(slot)
    start = datetime.strptime(f"{s['slot_date']} {s['start_time']}", f"{SLOT_FMT} {TIME_FMT}")
    end = datetime.strptime(f"{s['slot_date']} {s['end_time']}", f"{SLOT_FMT} {TIME_FMT}")
    return start, end


def slots_overlap(a: Dict, b: Dict) -> Optional[Tuple[datetime, datetime]]:
    a0, a1 = parse_slot_range(a)
    b0, b1 = parse_slot_range(b)
    start = max(a0, b0)
    end = min(a1, b1)
    if start < end:
        return start, end
    return None


def find_meeting_slot(founder_id: int, vc_id: int) -> Optional[Dict]:
    """
    Pick the first overlapping window between founder and VC availability.
    Falls back to a suggested slot 3 business days out if no overlap.
    """
    f_slots = list_slots(founder_id)
    v_slots = list_slots(vc_id)

    best = None
    for fs in f_slots:
        for vs in v_slots:
            overlap = slots_overlap(fs, vs)
            if not overlap:
                continue
            start, end = overlap
            # Prefer 30-min intro if overlap is longer
            if (end - start) > timedelta(minutes=30):
                end = start + timedelta(minutes=30)
            candidate = {"start": start, "end": end}
            if best is None or start < best["start"]:
                best = candidate

    if best:
        return _slot_dict(best["start"], best["end"])

    # Suggest default: next weekday 2pm, 30 min
    if f_slots:
        start, _ = parse_slot_range(f_slots[0])
        end = start + timedelta(minutes=30)
        return _slot_dict(start, end)

    now = datetime.now().replace(hour=14, minute=0, second=0, microsecond=0)
    while now.weekday() >= 5:
        now += timedelta(days=1)
    now += timedelta(days=3)
    return _slot_dict(now, now + timedelta(minutes=30))


def _slot_dict(start: datetime, end: datetime) -> Dict:
    return {
        "meeting_start": start.isoformat(),
        "meeting_end": end.isoformat(),
        "display_date": f"{start.strftime('%A, %B')} {start.day}, {start.year}",
        "display_time": (
            f"{start.strftime('%I:%M %p').lstrip('0')} – "
            f"{end.strftime('%I:%M %p').lstrip('0')}"
        ),
        "slot_date": start.strftime(SLOT_FMT),
        "start_time": start.strftime(TIME_FMT),
        "end_time": end.strftime(TIME_FMT),
    }


def parse_slots_from_form(form) -> List[Dict]:
    """Parse availability_slots[] JSON or parallel form fields."""
    raw = form.get("availability_json", "").strip()
    if raw:
        import json

        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return [normalize_slot(s) for s in data if isinstance(s, dict)]
        except json.JSONDecodeError:
            pass

    dates = form.getlist("slot_date")
    starts = form.getlist("slot_start")
    ends = form.getlist("slot_end")
    out = []
    for d, s, e in zip(dates, starts, ends):
        slot = normalize_slot({"slot_date": d, "start_time": s, "end_time": e})
        if slot["slot_date"] and slot["start_time"] and slot["end_time"]:
            out.append(slot)
    return out
