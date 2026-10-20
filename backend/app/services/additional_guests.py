"""Additional guests own separate, revocable invitations and upload access."""

from sqlalchemy import select, update

from app.db.models import Invitation, Session
from app.schemas import RSVP, InvitationCreate
from app.services.invitations import create_invitation


async def sync_additional_guests(db, parent: Invitation, body: RSVP) -> list[str]:
    children = list(
        (
            await db.scalars(select(Invitation).where(Invitation.parent_invitation_id == parent.id))
        ).all()
    )
    desired = (
        {str(person.email).casefold(): person for person in body.guests[1:]}
        if body.attending
        else {}
    )
    pending = []
    for child in children:
        person = desired.pop(child.email.casefold(), None) if child.active else None
        if person is None and child.active:
            child.active = False
            await db.execute(
                update(Session).where(Session.invitation_id == child.id).values(active=False)
            )
        elif person:
            child.name = person.name
            if child.email_status in {"draft", "failed"}:
                pending.append(child.id)
    for person in desired.values():
        child = await create_invitation(
            db,
            InvitationCreate(
                name=person.name,
                email=person.email,
                language="it" if parent.language == "it" else "en",
                max_guests=1,
            ),
        )
        child.parent_invitation_id = parent.id
        pending.append(child.id)
    if parent.parent_invitation_id and not body.attending:
        parent.active = False
        await db.execute(
            update(Session).where(Session.invitation_id == parent.id).values(active=False)
        )
    return pending
