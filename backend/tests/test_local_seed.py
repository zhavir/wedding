import asyncio
from unittest.mock import AsyncMock, MagicMock

from app.manage import seed_local


def test_fresh_demo_invitations_use_english(monkeypatch):
    """Demo browser flows must not inherit the Italian admin creation default."""
    db = AsyncMock()
    db.get.return_value = None
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=db)
    context.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr("app.manage.sessions", lambda: lambda: context)
    monkeypatch.setattr("app.manage.settings", lambda: MagicMock(dsql_host="", cookie_secure=False))
    create = AsyncMock()
    monkeypatch.setattr("app.manage.create_invitation", create)

    asyncio.run(seed_local())

    assert create.await_count == 2
    assert {call.kwargs["token"] for call in create.await_args_list} == {
        "DEMO-LOVE-2027",
        "DEMO-ADMIN-2027",
    }
    assert all(call.args[1].language == "en" for call in create.await_args_list)
    db.commit.assert_awaited_once()
