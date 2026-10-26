"""Resend in production; explicit SES emulator transport for local development."""

import base64
import json
from email.message import EmailMessage
from email.policy import SMTP
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings
from app.services.aws import ses


class EmailRejected(Exception):
    """The provider explicitly rejected the message."""


class EmailUncertain(Exception):
    """The provider may have accepted the message; do not automatically retry."""


def send_message(
    recipient: str, message: dict[str, str], *, attachment: bytes | None = None
) -> dict[str, str]:
    cfg = settings()
    if cfg.email_provider == "ses-local":
        return send_local(recipient, message, attachment)
    if not cfg.resend_api_key or not cfg.resend_api_key.get_secret_value().strip():
        raise EmailRejected("RESEND_API_KEY is not configured")
    payload = {
        "from": cfg.email_from,
        "to": [recipient],
        "subject": message["subject"],
        "html": message["html"],
        "text": message["text"],
    }
    if attachment is not None:
        payload["attachments"] = [
            {
                "filename": "andrea-sara-wedding.ics",
                "content": base64.b64encode(attachment).decode("ascii"),
                "content_type": "text/calendar; charset=UTF-8; method=PUBLISH",
            }
        ]
    request = Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {cfg.resend_api_key.get_secret_value()}",
            "Content-Type": "application/json",
            "User-Agent": "wedding-api/1.0",
        },
        method="POST",
    )
    try:
        # No automatic retries: a timeout can occur after acceptance.
        with urlopen(request, timeout=15) as response:
            result = json.load(response)
        message_id = result.get("id") if isinstance(result, dict) else None
        if not isinstance(message_id, str) or not message_id:
            raise EmailUncertain("Resend did not return a message ID")
        return {"MessageId": message_id}
    except HTTPError as exc:
        # Do not store response bodies: they may contain private message content.
        if 400 <= exc.code < 500:
            raise EmailRejected(f"Resend rejected email (HTTP {exc.code})") from None
        raise EmailUncertain("Resend returned an ambiguous server response") from None
    except (URLError, OSError, HTTPException, ValueError) as exc:
        raise EmailUncertain("Resend delivery could not be confirmed") from exc


def send_local(recipient: str, message: dict[str, str], attachment: bytes | None) -> dict[str, str]:
    try:
        client = ses()
        if attachment is None:
            result = client.send_email(
                Source=settings().email_from,
                Destination={"ToAddresses": [recipient]},
                Message={
                    "Subject": {"Data": message["subject"], "Charset": "UTF-8"},
                    "Body": {
                        "Html": {"Data": message["html"], "Charset": "UTF-8"},
                        "Text": {"Data": message["text"], "Charset": "UTF-8"},
                    },
                },
            )
            return {"MessageId": result["MessageId"]}
        mime = EmailMessage(policy=SMTP)
        mime["From"] = settings().email_from
        mime["To"] = recipient
        mime["Subject"] = message["subject"]
        mime.set_content(message["text"])
        mime.add_alternative(message["html"], subtype="html")
        mime.add_attachment(
            attachment,
            maintype="text",
            subtype="calendar",
            filename="andrea-sara-wedding.ics",
            params={"charset": "UTF-8", "method": "PUBLISH"},
        )
        result = client.send_raw_email(
            Source=settings().email_from,
            Destinations=[recipient],
            RawMessage={"Data": mime.as_bytes()},
        )
        return {"MessageId": result["MessageId"]}
    except ClientError as exc:
        raise EmailRejected(
            str(exc.response.get("Error", {}).get("Code", "Email rejected"))
        ) from None
    except BotoCoreError as exc:
        raise EmailUncertain("Local delivery could not be confirmed") from exc
