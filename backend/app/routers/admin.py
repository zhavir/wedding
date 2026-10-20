import asyncio

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.core.security import DB, Admin, cipher
from app.db.models import Invitation
from app.schemas import InvitationBatch, SendBatch
from app.services.access import ensure_access
from app.services.email import render_email, send_invitation
from app.services.invitations import create_invitation, invitation_view
from app.services.messages import invitation_message
from app.services.rsvps import read_response

router = APIRouter(prefix="/admin")


@router.get("/invitations")
async def list_invitations(
    admin: Admin, db: DB, cursor: str | None = None, limit: int = Query(50, ge=1, le=100)
):
    query = (
        select(Invitation)
        .where(Invitation.is_admin.is_(False))
        .order_by(Invitation.id.desc())
        .limit(limit + 1)
    )
    if cursor:
        query = query.where(Invitation.id < cursor)
    rows = list((await db.scalars(query)).all())
    for row in rows[:limit]:
        if not row.encrypted_token:
            await ensure_access(db, row.id)
    await db.commit()
    return {
        "items": [invitation_view(row) for row in rows[:limit]],
        "cursor": rows[limit - 1].id if len(rows) > limit else None,
    }


@router.post("/invitations", status_code=201)
async def generate(body: InvitationBatch, admin: Admin, db: DB):
    rows = [await create_invitation(db, item) for item in body.invitations]
    await db.commit()
    return {"items": [invitation_view(row) for row in rows]}


@router.post("/invitations/send")
async def bulk_send(body: SendBatch, admin: Admin):
    semaphore = asyncio.Semaphore(4)

    async def send_one(invitation_id: str):
        async with semaphore:
            return await send_invitation(invitation_id)

    return {"results": await asyncio.gather(*(send_one(i) for i in dict.fromkeys(body.ids)))}


@router.get("/invitations/{invitation_id}/preview")
async def preview(invitation_id: str, admin: Admin, db: DB):
    invite = await db.get(Invitation, invitation_id)
    if not invite or invite.is_admin:
        raise HTTPException(404, "Invitation not found.")
    access = await ensure_access(db, invite.id)
    selected_message = await invitation_message(db, invite)
    await db.commit()
    return render_email(
        invite,
        cipher().decrypt(access.encrypted_code.encode()).decode(),
        message_template=selected_message,
    )


@router.post("/invitations/{invitation_id}/revoke")
async def revoke(invitation_id: str, admin: Admin, db: DB):
    invite = await db.get(Invitation, invitation_id)
    if not invite or invite.is_admin:
        raise HTTPException(404, "Invitation not found.")
    invite.active = False
    await db.commit()
    return {"revoked": True}


@router.get("/rsvps")
async def export(admin: Admin, db: DB):
    rows = (await db.scalars(select(Invitation).where(Invitation.has_rsvp.is_(True)))).all()
    return {"items": [{"name": row.name, "rsvp": await read_response(db, row.id)} for row in rows]}
