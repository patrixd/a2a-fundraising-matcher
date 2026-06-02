"""ICS and calendar links for match intro meetings."""
from datetime import datetime
from urllib.parse import quote


def _ics_dt(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%S")


def build_ics(
    title: str,
    start_iso: str,
    end_iso: str,
    description: str = "",
    location: str = "Video call (link TBD)",
) -> str:
    start = datetime.fromisoformat(start_iso)
    end = datetime.fromisoformat(end_iso)
    desc = description.replace("\n", "\\n").replace(",", "\\,")
    return "\r\n".join(
        [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//AgentMatch//Hackathon//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            "BEGIN:VEVENT",
            f"UID:agentmatch-{start.timestamp()}@agentmatch.local",
            f"DTSTAMP:{_ics_dt(datetime.now())}",
            f"DTSTART:{_ics_dt(start)}",
            f"DTEND:{_ics_dt(end)}",
            f"SUMMARY:{title}",
            f"DESCRIPTION:{desc}",
            f"LOCATION:{location}",
            "END:VEVENT",
            "END:VCALENDAR",
        ]
    )


def google_calendar_url(title: str, start_iso: str, end_iso: str, details: str = "") -> str:
    start = datetime.fromisoformat(start_iso)
    end = datetime.fromisoformat(end_iso)
    dates = f"{_ics_dt(start)}/{_ics_dt(end)}"
    params = (
        f"action=TEMPLATE&text={quote(title)}"
        f"&dates={dates}"
        f"&details={quote(details)}"
        "&location=Video+call"
    )
    return f"https://calendar.google.com/calendar/render?{params}"
