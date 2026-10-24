"""Public save-the-date download, shared with the confirmation email attachment."""

from typing import Literal

from fastapi import APIRouter
from fastapi.responses import Response

from app.core.config import settings
from app.services.calendar import wedding_calendar
from app.services.email import content

router = APIRouter()


@router.get("/calendar.ics")
async def calendar_download(locale: Literal["en", "it"] = "en") -> Response:
    return Response(
        wedding_calendar(await content(locale), settings().site_url),
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="andrea-sara-wedding.ics"'},
    )
