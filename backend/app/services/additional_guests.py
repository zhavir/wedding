"""Reconcile +1 invitations by unique email in the parent's RSVP transaction."""

from fastapi import HTTPException
from sqlalchemy import select, update

from app.db.models import Guest, Invitation, Session
from app.schemas import RSVP, InvitationCreate
from app.services.invitations import create_invitation


async def sync_additional_guests(db, parent: Invitation, body: RSVP) -> list[str]:
    children = list(
        await db.scalars(select(Invitation).where(Invitation.parent_invitation_id == parent.id))
    )
    desired = (
        {str(person.email).casefold(): person for person in body.guests[1:] if person.email}
        if body.attending
        else {}
    )
    for child in children:
        if child.guest.email in desired or not child.active:
            continue
        child.active = False
        await db.execute(
            update(Session).where(Session.invitation_id == child.id).values(active=False)
        )

    # Never let a guest turn their own invitation or an ancestor into their +1.
    ancestors = {parent.id}
    ancestor = parent
    while ancestor.parent_invitation_id:
        if ancestor.parent_invitation_id in ancestors:
            break
        ancestors.add(ancestor.parent_invitation_id)
        ancestor = await db.get(Invitation, ancestor.parent_invitation_id)
        if ancestor is None:
            break

    pending = []
    for email, person in desired.items():
        child = await db.scalar(
            select(Invitation).where(Invitation.guest.has(Guest.email == email))
        )
        if child and (child.id in ancestors or child.is_admin):
            raise HTTPException(422, "An additional guest must have their own email address.")
        if child is None:
            child = await create_invitation(
                db,
                InvitationCreate(
                    name=person.name,
                    email=person.email,
                    language="it" if parent.guest.language == "it" else "en",
                    max_guests=1,
                ),
            )
        if child.guest.audience == "guest":
            child.guest.audience = "+1"
        child.parent_invitation_id = parent.id
        child.active = True
        # Keep an existing guest's identity and response. Re-enabling a sent invitation
        # reuses the same link without sending another copy or reviving old sessions.
        if child.email_status in {"draft", "failed"}:
            pending.append(child.id)
    return pending
