"""RFC 5545 calendar event with the confirmed ceremony time."""

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
    start = datetime.fromisoformat(wedding["date"])
    day = start.date()
    end = start.replace(hour=0, minute=0, second=0) + timedelta(days=1)
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
        f"DTSTART:{start.astimezone(UTC):%Y%m%dT%H%M%SZ}",
        f"DTEND:{end.astimezone(UTC):%Y%m%dT%H%M%SZ}",
        f"SUMMARY:{escape_text(names)}",
        f"LOCATION:{escape_text(wedding['venue'] + ', ' + wedding['address'])}",
        f"DESCRIPTION:{escape_text(wedding['confirmationEmail']['calendarDescription'])}",
        f"URL:{site_url.rstrip('/')}/",
        "TRANSP:OPAQUE",
        "STATUS:CONFIRMED",
        "SEQUENCE:1",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(fold_line(line) for line in lines) + "\r\n"
