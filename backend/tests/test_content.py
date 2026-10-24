# ruff: noqa: F811
"""The two applications own their copy; emails retain links and escaped data."""

from types import SimpleNamespace

import pytest
from app.services.email import content, templates
from test_api import client  # noqa: F401, F811 - reuse the migrated database fixture


def keys(value, prefix=""):
    return {
        f"{prefix}{key}.{nested}" if isinstance(item, dict) else f"{prefix}{key}"
        for key, item in value.items()
        for nested in (keys(item) if isinstance(item, dict) else [""])
    }


def test_admin_email_copy_has_complete_matching_sections(client):
    locales = [client.portal.call(content, lang) for lang in ("en", "it")]
    assert keys(locales[0]) == keys(locales[1])
    for locale in locales:
        assert all(
            locale[name] for name in ("email", "witnessEmail", "confirmationEmail", "labels")
        )
        assert "story" not in locale
        assert locale["names"] == ["Andrea", "Sara"]


def test_admin_copy_edits_survive_migration_and_are_used_immediately(client):
    from app.db.models import InvitationMessage
    from app.db.session import sessions
    from app.manage import migrate
    from sqlalchemy import select

    async def edit():
        async with sessions()() as db:
            row = await db.scalar(
                select(InvitationMessage)
                .where(InvitationMessage.language == "it")
                .order_by(InvitationMessage.id)
            )
            assert row is not None
            row.text = "Il nostro invito aggiornato"
            await db.commit()
        await migrate()
        async with sessions()() as db:
            return await db.scalar(
                select(InvitationMessage.text)
                .where(InvitationMessage.language == "it")
                .order_by(InvitationMessage.id)
            )

    assert client.portal.call(edit) == "Il nostro invito aggiornato"


@pytest.mark.parametrize("language", ["en", "it"])
def test_email_stationery_preserves_private_links_and_escapes_names(language, client):
    wedding = client.portal.call(content, language)
    assert "story" not in wedding
    guest = SimpleNamespace(name='<img src=x onerror="bad">')
    html = templates.get_template(f"invitation_{language}.html").render(
        w=wedding,
        guest=guest,
        language=language,
        link="https://example.test/#invite=private-token",
        short_code="DEMO-LOVE-2027",
    )
    assert "&lt;img" in html
    assert "<img src=x" not in html
    assert "https://example.test/#invite=private-token" in html
    assert "https://example.test/gallery#invite=private-token" in html
    assert "DEMO-LOVE-2027" in html
    assert wedding["labels"]["codeHelp"] in html
    copy = wedding["confirmationEmail"]
    confirmation = templates.get_template("confirmation.html").render(
        w=wedding,
        guest=guest,
        language=language,
        copy=copy,
        intro=copy["intro"],
        site_url="https://example.test/",
    )
    assert copy["calendarHelp"] in confirmation
    assert 'href="https://example.test/"' in confirmation
    assert "&lt;img" in confirmation
