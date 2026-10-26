"""Shared stationery, participant grammar and guest-owned language regressions."""

import asyncio
from types import SimpleNamespace

import pytest
from app.db.models import Guest, Invitation
from app.services.confirmations import calendar_attachment
from app.services.email import content, render_email
from app.services.email_content import participant_copy


@pytest.fixture(autouse=True)
def settings_env(monkeypatch):
    from app.core.config import settings

    monkeypatch.setenv("INVITE_ENCRYPTION_KEY", "AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8=")
    settings.cache_clear()
    yield
    settings.cache_clear()


@pytest.mark.parametrize("count", [1, 2])
def test_italian_email_grammar_and_website_identity(count):
    invite = Invitation(name="Alex", guest=Guest(language="it"), max_guests=count, is_witness=False)
    wedding = asyncio.run(content("it"))
    message = render_email(invite, wedding=wedding, link="https://example.test/#invite=private")
    assert ("Sei invitato" if count == 1 else "Siete invitati") in message["subject"]
    assert ("senza di te" if count == 1 else "senza di voi") in message["html"]
    assert "monogram.png" in message["html"]
    assert "#496a55" in message["html"]
    assert "#25352b" not in message["html"]
    assert "https://example.test/#invite=private" in message["html"]


def test_email_defaults_to_italian_when_language_is_missing():
    wedding = asyncio.run(content())
    assert wedding == asyncio.run(content("it"))
    invite = Invitation(name="Alex", guest=Guest(), max_guests=2, is_witness=False)
    message = render_email(invite, wedding=wedding, link="https://example.test/")
    assert "Siete invitati" in message["subject"]
    assert 'lang="it"' in message["html"]
    assert message["text"].startswith("Ciao Alex")


def test_confirmation_same_for_all_roles_and_calendar_same_for_all_guests():
    from app.schemas import RSVP
    from app.services.confirmations import queue_confirmation

    items = []
    db = SimpleNamespace(add=items.append)
    body = RSVP(email="alex@example.com", attending=True, guests=[{"name": "Alex"}], consent=True)
    for witness in (False, True):
        invite = Invitation(id="alex", name="Alex", guest=Guest(language="it"), is_witness=witness)
        asyncio.run(queue_confirmation(db, invite, body))  # ty: ignore[invalid-argument-type]
    assert items[0].html_body == items[1].html_body
    assert items[0].text_body == items[1].text_body
    assert "calendar" not in items[0].__table__.columns
    assert calendar_attachment("en") != calendar_attachment("it")
    assert "calendarDescription" not in asyncio.run(content("it"))["confirmationEmail"]


def test_confirmation_grammar_does_not_mutate_shared_copy():
    wedding = asyncio.run(content("it"))
    assert "insieme a voi" in participant_copy(wedding, "it", 2)["confirmationEmail"]["intro"]
    assert "insieme a te" in wedding["confirmationEmail"]["intro"]


def test_language_belongs_to_guest_table():
    assert "language" in Guest.__table__.columns
    assert "language" not in Invitation.__table__.columns


def test_migration_preserves_guest_language_and_invitation_credentials():
    import importlib
    from unittest.mock import patch

    import sqlalchemy as sa
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    migration = importlib.import_module("app.migrations.versions.0006_guest_language")
    engine = sa.create_engine("sqlite://")
    with engine.connect() as connection:
        connection.exec_driver_sql("CREATE TABLE guests (id TEXT PRIMARY KEY)")
        connection.exec_driver_sql(
            "CREATE TABLE invitations (guest_id TEXT, language TEXT, encrypted_token TEXT)"
        )
        connection.exec_driver_sql("CREATE TABLE invitation_messages (language TEXT, text TEXT)")
        connection.exec_driver_sql("INSERT INTO guests VALUES ('it'), ('en'), ('uninvited')")
        connection.exec_driver_sql(
            "INSERT INTO invitations VALUES ('it', 'it', 'private-it'), ('en', 'en', 'private-en')"
        )
        connection.exec_driver_sql("INSERT INTO invitation_messages VALUES ('en', 'Welcome')")
        connection.commit()
        context = MigrationContext.configure(
            connection, opts={"transactional_ddl": False, "transaction_per_migration": True}
        )
        with (
            context.begin_transaction(_per_migration=True),
            Operations.context(context),
            patch.object(migration.context, "is_offline_mode", return_value=False),
        ):
            migration.upgrade()
            migration.upgrade()
        assert dict(connection.exec_driver_sql("SELECT id, language FROM guests").all()) == {
            "it": "it",
            "en": "en",
            "uninvited": "en",
        }
        assert connection.exec_driver_sql(
            "SELECT encrypted_token FROM invitations ORDER BY guest_id"
        ).scalars().all() == ["private-en", "private-it"]
        assert "language" not in {
            c["name"] for c in sa.inspect(connection).get_columns("invitations")
        }
    engine.dispose()


def test_session_exposes_guest_language_and_actual_participant_count():
    from app.routers.auth import guest_view

    invite = Invitation(
        id="guest",
        name="Alex",
        guest=Guest(language="it"),
        max_guests=3,
        attending=True,
        response_guests='[{"name":"Alex"}]',
    )
    view = guest_view(invite)
    assert view["language"] == "it"
    assert view["participant_count"] == 1
    invite.attending = None
    assert guest_view(invite)["participant_count"] == 3


def test_static_calendar_migration_preserves_pending_email_delivery():
    import importlib
    from unittest.mock import patch

    import sqlalchemy as sa
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    migration = importlib.import_module("app.migrations.versions.0007_static_calendar")
    engine = sa.create_engine("sqlite://")
    with engine.connect() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE confirmation_emails (id TEXT PRIMARY KEY, recipient TEXT, status TEXT, calendar TEXT)"
        )
        connection.exec_driver_sql(
            "INSERT INTO confirmation_emails VALUES ('pending', 'guest@example.test', 'pending', 'old calendar')"
        )
        connection.commit()
        context = MigrationContext.configure(
            connection, opts={"transactional_ddl": False, "transaction_per_migration": True}
        )
        with (
            context.begin_transaction(_per_migration=True),
            Operations.context(context),
            patch.object(migration.context, "is_offline_mode", return_value=False),
        ):
            migration.upgrade()
            migration.upgrade()
        assert connection.exec_driver_sql(
            "SELECT id, recipient, status FROM confirmation_emails"
        ).one() == ("pending", "guest@example.test", "pending")
        assert "calendar" not in {
            c["name"] for c in sa.inspect(connection).get_columns("confirmation_emails")
        }
    engine.dispose()


@pytest.mark.parametrize("language", ["en", "it"])
def test_email_attachment_is_exactly_the_frontend_download(language):
    from pathlib import Path

    frontend = Path(__file__).resolve().parents[2] / "frontend" / "static" / "calendar"
    assert calendar_attachment(language) == (frontend / f"wedding-{language}.ics").read_bytes()


@pytest.mark.parametrize("language", ["en", "it"])
def test_email_contact_uses_ses_sender(monkeypatch, language):
    monkeypatch.setenv("EMAIL_FROM", "wedding@our-domain.test")
    wedding = asyncio.run(content(language))
    invite = Invitation(name="Alex", guest=Guest(language=language), max_guests=1, is_witness=False)
    message = render_email(invite, wedding=wedding, link="https://example.test/#invite=private")
    assert wedding["contactEmail"] == "wedding@our-domain.test"
    assert 'href="mailto:wedding@our-domain.test"' in message["html"]
    assert "hello@example.com" not in message["html"]
