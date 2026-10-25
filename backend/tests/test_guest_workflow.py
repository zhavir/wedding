# ruff: noqa: F811
"""Regressions for guest identity, +1 lifecycle and private gallery selection."""

import re

from app.core.config import settings
from app.db.models import Guest, Invitation, Photo, PhotoGuest, RSVPNotification
from app.db.session import sessions
from sqlalchemy import select
from test_api import admin_login, aws, body, client, login  # noqa: F401


def test_existing_email_reuses_identity_and_notifies_admin(client, aws, monkeypatch):
    monkeypatch.setattr(settings(), "rsvp_notification_email", "hosts@example.com")
    login(client, "ADMIN-CODE-123")
    existing = client.post(
        "/api/admin/invitations",
        json={"invitations": [{"name": "Existing Alex", "email": "alex@example.com"}]},
    ).json()["items"][0]
    login(client)
    parent = client.get("/api/session").json()["id"]
    party = body(
        email="GUEST@example.com",
        guests=[{"name": "Guest"}, {"name": "Alex", "email": "ALEX@example.com"}],
    )
    assert client.put("/api/rsvp", json=party).status_code == 200

    async def inspect():
        async with sessions()() as db:
            rows = list(
                await db.scalars(
                    select(Invitation).where(
                        Invitation.guest.has(Guest.email == "alex@example.com")
                    )
                )
            )
            assert len(rows) == 1
            child = rows[0]
            assert child.id == existing["id"] and child.parent_invitation_id == parent
            assert child.active and child.guest.audience == "+1"
            assert child.guest.name == "Existing Alex"
            assert child.email_status == "sent"
            notifications = list(await db.scalars(select(RSVPNotification)))
            assert len(notifications) == 1 and notifications[0].status == "sent"
            return child.guest_id

    guest_id = client.portal.call(inspect)
    sent = aws[1].send_email.call_count
    assert client.put("/api/rsvp", json=party).status_code == 200
    assert aws[1].send_email.call_count == sent
    assert client.put("/api/rsvp", json=body()).status_code == 200
    assert client.put("/api/rsvp", json=party).status_code == 200

    async def reactivated():
        async with sessions()() as db:
            child = await db.get(Invitation, existing["id"])
            assert child is not None
            assert child.active and child.guest_id == guest_id
            assert len(list(await db.scalars(select(Guest).where(Guest.id == guest_id)))) == 1

    client.portal.call(reactivated)
    admin_login(client)
    details = client.get(f"/api/admin/invitation/details/{parent}")
    assert details.status_code == 200 and "Party response details" in details.text


def test_carousel_and_gallery_enforce_multiple_guest_targets(client, aws):
    assert client.get("/api/photos/carousel").status_code == 401
    login(client)
    identity = client.get("/api/session").json()["id"]

    async def seed():
        async with sessions()() as db:
            invite = await db.get(Invitation, identity)
            host = await db.scalar(select(Invitation).where(Invitation.is_admin.is_(True)))
            assert invite is not None and host is not None
            for i in range(28):
                db.add(
                    Photo(
                        id=f"{i:032x}",
                        owner=identity,
                        size=100,
                        content_type="image/jpeg",
                        caption="A memory",
                        status="complete",
                        carousel_visible=True,
                        gallery_visible=True,
                        expires=0,
                    )
                )
            db.add_all(
                [
                    PhotoGuest(
                        photo_id="00000000000000000000000000000000", guest_id=invite.guest_id
                    ),
                    PhotoGuest(photo_id="00000000000000000000000000000000", guest_id=host.guest_id),
                    PhotoGuest(photo_id="00000000000000000000000000000001", guest_id=host.guest_id),
                ]
            )
            await db.commit()

    client.portal.call(seed)
    items = client.get("/api/photos/carousel").json()["items"]
    assert len(items) == 27 and "00000000000000000000000000000000" in {i["id"] for i in items}
    assert "00000000000000000000000000000001" not in {i["id"] for i in items}
    result = client.get("/api/photos?limit=24").json()
    all_items = (
        result["items"] + client.get(f"/api/photos?cursor={result['cursor']}").json()["items"]
    )
    assert len(all_items) == 27 and "00000000000000000000000000000001" not in {
        i["id"] for i in all_items
    }
    login(client, "ADMIN-CODE-123")
    assert len(client.get("/api/photos/carousel").json()["items"]) == 28


def test_admin_bulk_create_activate_and_send_excludes_inactive(client, aws):
    admin_login(client)
    for name in ("First", "Second"):
        response = client.post(
            "/api/admin/guest/create", data={"name": name, "audience": "guest", "save": "Save"}
        )
        assert response.status_code == 200

    async def ids():
        async with sessions()() as db:
            return list(
                await db.scalars(select(Guest.id).where(Guest.name.in_(["First", "Second"])))
            )

    selected = ",".join(client.portal.call(ids))
    for _ in range(2):
        assert (
            client.get(f"/api/admin/guest/action/create-invitations?pks={selected}").status_code
            == 200
        )

    async def prepare():
        async with sessions()() as db:
            invites = list(
                await db.scalars(
                    select(Invitation)
                    .where(Invitation.guest_id.in_(selected.split(",")))
                    .order_by(Invitation.name)
                )
            )
            assert len(invites) == 2
            for i, invite in enumerate(invites):
                invite.guest.email = f"bulk-{i}@example.com"
                invite.active = i == 0
            await db.commit()
            return [invite.id for invite in invites]

    invites = client.portal.call(prepare)
    query = ",".join(invites)
    review = client.get(f"/api/admin/invitation/action/send-invitations?pks={query}")
    assert "bulk-0@example.com" in review.text and "bulk-1@example.com" not in review.text
    match = re.search(r'name="csrf" value="([^"]+)"', review.text)
    assert match is not None
    token = match.group(1)
    assert (
        client.post("/api/admin/invitation/send-confirm", data={"csrf": token}).status_code == 200
    )
    assert aws[1].send_email.call_count == 1
    assert (
        client.get(f"/api/admin/invitation/action/activate-invitations?pks={query}").status_code
        == 200
    )

    async def activated():
        async with sessions()() as db:
            assert all(
                row.active
                for row in await db.scalars(select(Invitation).where(Invitation.id.in_(invites)))
            )

    client.portal.call(activated)


def test_duplicate_invitation_email_is_rejected(client):
    login(client, "ADMIN-CODE-123")
    result = client.post(
        "/api/admin/invitations",
        json={"invitations": [{"name": "Duplicate", "email": "GUEST@example.com"}]},
    )
    assert result.status_code == 409


def test_gallery_guest_selector_updates_and_clears_targets(client):
    async def seed():
        async with sessions()() as db:
            guest = await db.scalar(select(Guest).where(Guest.name == "Guest"))
            db.add(
                Photo(
                    id="targeted-photo",
                    owner="guest",
                    size=100,
                    content_type="image/jpeg",
                    caption="Private",
                    status="complete",
                    expires=0,
                )
            )
            await db.commit()
            assert guest is not None
            return guest.id

    guest_id = client.portal.call(seed)
    admin_login(client)
    url = "/api/admin/photo/edit/targeted-photo"
    form = client.get(url)
    assert form.status_code == 200 and "Visible to guests" in form.text
    assert 'type="checkbox" name="guests"' in form.text
    for field in ("gallery_visible", "carousel_visible"):
        tag = re.search(r'<input[^>]*name="' + field + r'"[^>]*>', form.text)
        assert (
            tag and 'type="checkbox"' in tag.group() and 'class="form-check-input"' in tag.group()
        )
    detail = client.get("/api/admin/photo/details/targeted-photo")
    assert detail.status_code == 200 and "Save visibility" in detail.text
    data = {
        "caption": "Private",
        "gallery_visible": "y",
        "carousel_visible": "y",
        "guests": guest_id,
        "save": "Save",
    }
    response = client.post(url, data=data)
    assert response.status_code == 200

    async def targets():
        async with sessions()() as db:
            return list(
                await db.scalars(
                    select(PhotoGuest.guest_id).where(PhotoGuest.photo_id == "targeted-photo")
                )
            )

    assert client.portal.call(targets) == [guest_id]
    del data["guests"]
    assert client.post(url, data=data).status_code == 200
    assert client.portal.call(targets) == []
    del data["gallery_visible"]
    del data["carousel_visible"]
    assert client.post(url, data=data).status_code == 200

    async def flags():
        async with sessions()() as db:
            photo = await db.get(Photo, "targeted-photo")
            assert photo is not None
            return photo.gallery_visible, photo.carousel_visible

    assert client.portal.call(flags) == (False, False)
    assert client.get("/api/admin/photo/action/show-carousel?pks=targeted-photo").status_code == 200
    assert client.portal.call(flags) == (False, True)
    assert client.get("/api/admin/photo/action/approve-media?pks=targeted-photo").status_code == 200
    assert client.portal.call(flags) == (True, True)


def test_guest_name_is_only_required_input(client):
    admin_login(client)
    response = client.post("/api/admin/guest/create", data={"name": "Name only", "save": "Save"})
    assert response.status_code == 200

    async def guest():
        async with sessions()() as db:
            person = await db.scalar(select(Guest).where(Guest.name == "Name only"))
            assert person and person.audience == "guest"

    client.portal.call(guest)


def test_guest_owns_email_and_email_edits_reset_delivery(client):
    admin_login(client)

    async def identity():
        async with sessions()() as db:
            invite = await db.scalar(select(Invitation).where(Invitation.name == "Guest"))
            assert invite is not None
            invite.email_status = "sent"
            await db.commit()
            return invite.id, invite.guest_id

    invitation_id, guest_id = client.portal.call(identity)
    form = client.get(f"/api/admin/invitation/edit/{invitation_id}")
    assert 'name="email"' not in form.text
    result = client.post(
        f"/api/admin/guest/edit/{guest_id}",
        data={"name": "Guest", "email": "NEW@example.com", "audience": "guest", "save": "Save"},
    )
    assert result.status_code == 200

    async def inspect():
        async with sessions()() as db:
            invite = await db.get(Invitation, invitation_id)
            assert invite is not None
            assert invite.guest.email == "new@example.com"
            assert invite.email_status == "draft"
            assert "email" not in Invitation.__table__.columns

    client.portal.call(inspect)
    duplicate = client.post(
        "/api/admin/guest/create",
        data={
            "name": "Another guest",
            "email": "NEW@example.com",
            "audience": "guest",
            "save": "Save",
        },
    )
    assert duplicate.status_code == 400


def test_plus_one_reuses_guest_email_before_an_invitation_exists(client, aws):
    admin_login(client)
    assert (
        client.post(
            "/api/admin/guest/create",
            data={
                "name": "Existing identity",
                "email": "friend@example.com",
                "audience": "guest",
                "save": "Save",
            },
        ).status_code
        == 200
    )
    login(client)
    assert (
        client.put(
            "/api/rsvp",
            json=body(
                guests=[{"name": "Guest"}, {"name": "Friend", "email": "FRIEND@example.com"}]
            ),
        ).status_code
        == 200
    )

    async def inspect():
        async with sessions()() as db:
            people = list(
                await db.scalars(select(Guest).where(Guest.email == "friend@example.com"))
            )
            assert len(people) == 1
            assert people[0].name == "Existing identity" and people[0].audience == "+1"
            invitations = list(
                await db.scalars(select(Invitation).where(Invitation.guest_id == people[0].id))
            )
            assert len(invitations) == 1 and invitations[0].active
            assert invitations[0].email_status == "sent"

    client.portal.call(inspect)
