import base64
import io
import json
from email.message import Message
from http.client import IncompleteRead
from unittest.mock import MagicMock
from urllib.error import HTTPError, URLError

import pytest
from app.core.config import settings
from app.services import mail_transport
from app.services.confirmations import calendar_attachment


@pytest.fixture(autouse=True)
def resend(monkeypatch):
    monkeypatch.setenv("INVITE_ENCRYPTION_KEY", "unused-for-transport")
    monkeypatch.setenv("EMAIL_PROVIDER", "resend")
    monkeypatch.setenv("RESEND_API_KEY", "private-test-key")
    monkeypatch.setenv("EMAIL_FROM", "wedding@example.com")
    settings.cache_clear()
    yield
    settings.cache_clear()


MESSAGE = {"subject": "Invito à Sara", "html": "<p>Private invitation</p>", "text": "Hello"}


@pytest.mark.parametrize("language", [None, "en", "it"])
def test_resend_payload_and_calendar_bytes(monkeypatch, language):
    requests = []

    def send(request, timeout):
        requests.append(request)
        assert timeout == 15
        return io.BytesIO(b'{"id":"resend-message-id"}')

    monkeypatch.setattr(mail_transport, "urlopen", send)
    attachment = calendar_attachment(language) if language else None
    result = mail_transport.send_message("guest@example.net", MESSAGE, attachment=attachment)
    assert result == {"MessageId": "resend-message-id"}
    (request,) = requests
    assert request.full_url == "https://api.resend.com/emails"
    assert request.method == "POST"
    assert request.get_header("Authorization") == "Bearer private-test-key"
    payload = json.loads(request.data)
    assert payload["from"] == "wedding@example.com"
    assert payload["to"] == ["guest@example.net"]
    assert all(payload[key] == value for key, value in MESSAGE.items())
    if attachment:
        assert base64.b64decode(payload["attachments"][0]["content"]) == attachment
        assert payload["attachments"][0]["filename"].endswith(".ics")
    else:
        assert "attachments" not in payload


@pytest.mark.parametrize("status", [400, 401, 403, 422, 429, 500, 503])
def test_resend_error_classification_and_no_retry(monkeypatch, status):
    send = MagicMock(
        side_effect=HTTPError(
            "https://api.resend.com/emails",
            status,
            "private-message",
            Message(),
            io.BytesIO(b"private-response-body"),
        )
    )
    monkeypatch.setattr(mail_transport, "urlopen", send)
    error = mail_transport.EmailRejected if status < 500 else mail_transport.EmailUncertain
    with pytest.raises(error) as exc:
        mail_transport.send_message("guest@example.net", MESSAGE)
    assert "private" not in str(exc.value)
    send.assert_called_once()


@pytest.mark.parametrize("response", [b"{}", b"[]", b'{"id":null}', b"not-json"])
def test_ambiguous_success_is_uncertain(monkeypatch, response):
    send = MagicMock(return_value=io.BytesIO(response))
    monkeypatch.setattr(mail_transport, "urlopen", send)
    with pytest.raises(mail_transport.EmailUncertain):
        mail_transport.send_message("guest@example.net", MESSAGE)
    send.assert_called_once()


@pytest.mark.parametrize(
    "error", [TimeoutError(), URLError("private-network-error"), IncompleteRead(b"partial")]
)
def test_network_failure_is_uncertain(monkeypatch, error):
    send = MagicMock(side_effect=error)
    monkeypatch.setattr(mail_transport, "urlopen", send)
    with pytest.raises(mail_transport.EmailUncertain):
        mail_transport.send_message("guest@example.net", MESSAGE)
    send.assert_called_once()


def test_missing_key_does_not_call_provider(monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY")
    send = MagicMock()
    monkeypatch.setattr(mail_transport, "urlopen", send)
    with pytest.raises(mail_transport.EmailRejected, match="not configured"):
        mail_transport.send_message("guest@example.net", MESSAGE)
    send.assert_not_called()


def test_local_ses_requires_explicit_endpoint(monkeypatch):
    from app.services.aws import ses

    monkeypatch.setenv("EMAIL_PROVIDER", "ses-local")
    monkeypatch.delenv("AWS_ENDPOINT_URL", raising=False)
    ses.cache_clear()
    with pytest.raises(ValueError, match="local emulator endpoint"):
        ses()
    ses.cache_clear()
