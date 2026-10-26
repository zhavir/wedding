import asyncio

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    ConfirmationEmail,
    Invitation,
    InvitationAccess,
    InvitationLink,
    Photo,
    PhotoGuest,
    RSVPNotification,
    Session,
)
from app.services.photos import delete_photo_media


async def guest_has_dependents(db: AsyncSession, guest_id: str) -> bool:
    if await db.scalar(select(Invitation.id).where(Invitation.guest_id == guest_id).limit(1)):
        return True
    return bool(await db.scalar(select(Photo.id).where(Photo.owner == guest_id).limit(1)))


async def delete_invitation_dependents(db: AsyncSession, invitation: Invitation) -> None:
    """Remove the invitation tree and its private data in the caller's transaction."""
    if invitation.is_admin:
        raise ValueError("Administrator invitations cannot be deleted.")
    ids = {invitation.id}
    pending = [invitation.id]
    while pending:
        children = list(
            await db.scalars(select(Invitation).where(Invitation.parent_invitation_id.in_(pending)))
        )
        if any(child.is_admin for child in children):
            raise ValueError("Administrator invitations cannot be deleted.")
        pending = [child.id for child in children if child.id not in ids]
        ids.update(pending)

    photos = list(await db.scalars(select(Photo).where(Photo.owner.in_(ids))))
    # Keep database records if storage cleanup fails, so deletion can be retried.
    for photo in photos:
        await asyncio.to_thread(delete_photo_media, photo)
    for photo in photos:
        await db.delete(photo)
    for model in (InvitationAccess, InvitationLink, Session, RSVPNotification, ConfirmationEmail):
        await db.execute(delete(model).where(model.invitation_id.in_(ids)))
    await db.execute(delete(Invitation).where(Invitation.id.in_(ids - {invitation.id})))


async def delete_guest_dependents(db: AsyncSession, guest_id: str) -> None:
    if await guest_has_dependents(db, guest_id):
        raise ValueError("Delete this guest's invitations and gallery uploads first.")
    await db.execute(delete(PhotoGuest).where(PhotoGuest.guest_id == guest_id))
