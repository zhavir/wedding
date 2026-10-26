# ruff: noqa: F811
import re
from html import unescape

import pytest
from app.db.models import (
    ConfirmationEmail,
    Guest,
    Invitation,
    InvitationAccess,
    InvitationLink,
    InvitationMessage,
    Photo,
    PhotoGuest,
    RSVPNotification,
    Session,
)
from app.db.session import sessions
from app.schemas import InvitationCreate
from app.services.invitations import create_invitation
from sqlalchemy import select
from test_api import admin_login, aws, client  # noqa: F401


async def seed_tree():
    async with sessions()() as db:
        parent = await create_invitation(db, InvitationCreate(name="Delete parent"))
        child = await create_invitation(db, InvitationCreate(name="Delete child"))
        child.parent_invitation_id = parent.id
        db.add(Session(token_hash="delete-session", invitation_id=child.id))
        db.add(
            Photo(
                id="cascade-photo",
                owner=child.id,
                size=100,
                content_type="image/jpeg",
                caption="Cascade",
                expires=0,
                status="complete",
                storage_prefix=f"{child.id}/",
            )
        )
        db.add(PhotoGuest(photo_id="cascade-photo", guest_id=parent.guest_id))
        db.add(
            RSVPNotification(
                id="delete-notification",
                invitation_id=parent.id,
                recipient="test@example.com",
                subject="Test",
                body="Test",
                created_at=1,
            )
        )
        db.add(
            ConfirmationEmail(
                id="delete-confirmation",
                invitation_id=child.id,
                recipient="test@example.com",
                subject="Test",
                text_body="Test",
                html_body="Test",
                created_at=1,
            )
        )
        await db.commit()
        return parent.id, child.id, parent.guest_id, child.guest_id


def test_invitation_delete_cascades_and_then_guest_can_be_deleted(client, aws):
    parent, child, parent_guest, child_guest = client.portal.call(seed_tree)
    assert (
        client.delete(
            f"/api/admin/invitation/delete?pks={parent}", follow_redirects=False
        ).status_code
        != 200
    )
    aws[0].delete_object.assert_not_called()
    admin_login(client)
    assert client.delete(f"/api/admin/guest/delete?pks={parent_guest}").status_code == 403
    response = client.delete(f"/api/admin/invitation/delete?pks={parent}")
    assert response.status_code == 200 and "error=" not in response.text

    async def verify():
        async with sessions()() as db:
            assert await db.get(Invitation, parent) is None
            assert await db.get(Invitation, child) is None
            assert await db.get(Photo, "cascade-photo") is None
            assert await db.get(PhotoGuest, ("cascade-photo", parent_guest)) is None
            for model in (
                InvitationAccess,
                InvitationLink,
                Session,
                RSVPNotification,
                ConfirmationEmail,
            ):
                assert not list(
                    await db.scalars(select(model).where(model.invitation_id.in_([parent, child])))
                )
            assert await db.get(Guest, child_guest) is not None
            assert await db.get(Guest, parent_guest) is not None

    client.portal.call(verify)
    assert aws[0].delete_object.call_count == 5
    response = client.delete(f"/api/admin/guest/delete?pks={parent_guest},{child_guest}")
    assert response.status_code == 200 and "error=" not in response.text


def test_invitation_delete_storage_failure_preserves_tree(client, aws):
    parent, child, _, _ = client.portal.call(seed_tree)
    admin_login(client)
    aws[0].delete_object.side_effect = RuntimeError("Storage unavailable")
    response = client.delete(f"/api/admin/invitation/delete?pks={parent}")
    assert "error=" in response.text

    async def verify():
        async with sessions()() as db:
            for pk in (parent, child):
                assert await db.get(Invitation, pk) is not None
                assert await db.get(InvitationAccess, pk) is not None
            assert await db.get(Photo, "cascade-photo") is not None
            assert await db.get(Session, "delete-session") is not None

    client.portal.call(verify)


def test_guest_delete_blocks_uploads_and_cleans_viewer_assignments(client):
    async def seed():
        async with sessions()() as db:
            db.add_all([Guest(id="uploader", name="Uploader"), Guest(id="viewer", name="Viewer")])
            db.add(
                Photo(
                    id="owned-photo",
                    owner="uploader",
                    size=100,
                    content_type="image/jpeg",
                    caption="Keep",
                    expires=0,
                )
            )
            db.add(PhotoGuest(photo_id="owned-photo", guest_id="viewer"))
            await db.commit()

    client.portal.call(seed)
    admin_login(client)
    assert client.delete("/api/admin/guest/delete?pks=uploader").status_code == 403
    response = client.delete("/api/admin/guest/delete?pks=viewer")
    assert "error=" not in response.text

    async def verify():
        async with sessions()() as db:
            assert await db.get(Guest, "viewer") is None
            assert await db.get(PhotoGuest, ("owned-photo", "viewer")) is None
            assert await db.get(Photo, "owned-photo") is not None

    client.portal.call(verify)


def test_admin_invitation_cannot_be_deleted(client):
    async def find():
        async with sessions()() as db:
            return await db.scalar(select(Invitation.id).where(Invitation.is_admin.is_(True)))

    pk = client.portal.call(find)
    admin_login(client)
    assert client.delete(f"/api/admin/invitation/delete?pks={pk}").status_code == 403


@pytest.mark.parametrize("identity", ["guest", "invitation", "photo", "invitation-message"])
@pytest.mark.parametrize("screen", ["details", "edit"])
def test_entry_navigation_round_trip_and_boundaries(client, identity, screen):
    async def seed():
        async with sessions()() as db:
            for index in range(3):
                if identity in {"guest", "invitation"}:
                    await create_invitation(db, InvitationCreate(name=f"Navigation {index}"))
                elif identity == "photo":
                    db.add(
                        Photo(
                            id=f"navigation-{index}",
                            owner="guest",
                            size=10,
                            content_type="image/jpeg",
                            caption=f"Navigation {index}",
                            expires=0,
                        )
                    )
                else:
                    db.add(
                        InvitationMessage(
                            id=f"navigation-{index}",
                            language="en",
                            audience="guest",
                            text=f"Navigation {index}",
                        )
                    )
            await db.commit()
            model = {
                "guest": Guest,
                "invitation": Invitation,
                "photo": Photo,
                "invitation-message": InvitationMessage,
            }[identity]
            return (await db.scalars(select(model.id).order_by(model.id))).first()

    first = client.portal.call(seed)
    admin_login(client)
    response = client.get(f"/api/admin/{identity}/{screen}/{first}")
    assert response.status_code == 200, response.text
    assert 'aria-label="Entry navigation"' in response.text
    # Find an enabled neighbor, then follow its inverse back to the original entry.
    links = re.findall(r'href="([^"]+)" rel="(prev|next)"', response.text)
    assert links
    target, direction = links[0]
    neighbor = client.get(unescape(target))
    assert neighbor.status_code == 200, neighbor.text
    reverse = "next" if direction == "prev" else "prev"
    back = re.search(rf'href="([^"]+)" rel="{reverse}"', neighbor.text)
    assert back and unescape(back[1]).endswith(f"/{screen}/{first}")
    if identity == "guest":
        assert '<button class="btn" disabled>← Previous entry</button>' in response.text
