"""RFC 5545 all-day save-the-date: no unconfirmed ceremony time is invented."""

import hashlib
from datetime import UTC, datetime, timedelta


def escape_text(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\n", "\\n")
        .replace(";", "\\;")
        .replace(",", "\\,")
    )


def fold_line(line: str) -> str:
    # Count UTF-8 octets, and never split a multibyte character.
    parts: list[str] = []
    current = ""
    for char in line:
        if len((current + char).encode("utf-8")) > 75:
            parts.append(current)
            current = " "
        current += char
    parts.append(current)
    return "\r\n".join(parts)


def wedding_calendar(wedding: dict, site_url: str) -> str:
    day = datetime.fromisoformat(wedding["date"]).date()
    names = " & ".join(wedding["names"])
    # The same UID across languages and recipients avoids duplicate calendar events.
    identity = hashlib.sha256(f"{names}:{day}".encode()).hexdigest()[:32]
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Andrea and Sara//Wedding//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{identity}@wedding",
        f"DTSTAMP:{datetime.now(UTC):%Y%m%dT%H%M%SZ}",
        f"DTSTART;VALUE=DATE:{day:%Y%m%d}",
        f"DTEND;VALUE=DATE:{day + timedelta(days=1):%Y%m%d}",
        f"SUMMARY:{escape_text(names)}",
        f"LOCATION:{escape_text(wedding['venue'] + ', ' + wedding['address'])}",
        f"DESCRIPTION:{escape_text(wedding['confirmationEmail']['calendarDescription'])}",
        f"URL:{site_url.rstrip('/')}/",
        "TRANSP:OPAQUE",
        "STATUS:CONFIRMED",
        "SEQUENCE:0",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(fold_line(line) for line in lines) + "\r\n"
