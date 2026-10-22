"""The two applications own their copy; emails retain links and escaped data."""

import json
from importlib.resources import files
from types import SimpleNamespace

import pytest
from app.services.email import content, templates


def keys(value, prefix=""):
    return {
        f"{prefix}{key}.{nested}" if isinstance(item, dict) else f"{prefix}{key}"
        for key, item in value.items()
        for nested in (keys(item) if isinstance(item, dict) else [""])
    }


def test_backend_locales_have_matching_complete_keys():
    locales = [
        json.loads(files("app").joinpath(f"locales/{lang}.json").read_text())
        for lang in ("en", "it")
    ]
    assert keys(locales[0]) == keys(locales[1])
    for locale in locales:
        assert all(
            locale[name] for name in ("email", "witnessEmail", "confirmationEmail", "labels")
        )
        assert "story" not in locale
        assert locale["names"] == ["Andrea", "Sara"]


@pytest.mark.parametrize("language", ["en", "it"])
def test_email_stationery_preserves_private_links_and_escapes_names(language):
    wedding = content(language)
    assert "story" not in wedding
    guest = SimpleNamespace(name='<img src=x onerror="bad">')
    html = templates.get_template("invitation.html").render(
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
