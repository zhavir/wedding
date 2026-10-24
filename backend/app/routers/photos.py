import asyncio
import time
import uuid

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import exists, or_, select, update

from app.core.config import settings
from app.core.security import DB, Guest
from app.db.models import Invitation, Photo, PhotoGuest
from app.schemas import FinishUpload, Upload
from app.services.aws import s3
from app.services.photos import media_key, photo_preview, photo_view, process_photo
from app.services.uploads import finish_targets, part_url, start_target

router = APIRouter(prefix="/photos")


@router.post("/upload")
async def begin_upload(body: Upload, invite: Guest, db: DB):
    if body.motion_size and (
        body.content_type.startswith("video/") or not body.motion_content_type
    ):
        raise HTTPException(422, "A Live Photo needs one still image and its paired video.")
    if body.content_type.startswith("image/") and body.size > settings().max_upload_bytes:
        raise HTTPException(413, "This photo is too large.")
    updated = await db.scalar(
        update(Invitation)
        .where(Invitation.id == invite.id, Invitation.uploads < settings().max_uploads_per_invite)
        .values(uploads=Invitation.uploads + 1)
        .returning(Invitation.id)
    )
    if not updated:
        raise HTTPException(
            429, "Your invitation's upload allowance is full. Please contact the couple."
        )
    photo = Photo(
        id=uuid.uuid7().hex,
        owner=invite.id,
        storage_prefix=f"{invite.id}/",
        uploader_name=invite.name,
        original_filename=body.filename,
        uploaded_at=int(time.time()),
        size=body.size,
        motion_size=body.motion_size,
        motion_content_type=body.motion_content_type,
        gallery_visible=False,
        content_type=body.content_type,
        caption=body.caption,
        status="pending",
        expires=int(time.time()) + 86400,
    )
    db.add(photo)
    await db.commit()
    post = await asyncio.to_thread(start_target, photo, False)
    motion = await asyncio.to_thread(start_target, photo, True) if body.motion_size else None
    await db.commit()
    return {"id": photo.id, "upload": post, "motion_upload": motion}


@router.get("/{photo_id}/parts/{number}")
async def upload_part(photo_id: str, number: int, invite: Guest, db: DB, motion: bool = False):
    photo = await db.get(Photo, photo_id)
    if not photo or photo.owner != invite.id:
        raise HTTPException(404, "Upload not found.")
    if photo.status != "pending" or photo.expires < time.time():
        raise HTTPException(410, "Upload expired. Please upload again.")
    return {"url": await asyncio.to_thread(part_url, photo, number, motion)}


@router.post("/{photo_id}/complete")
async def complete(photo_id: str, invite: Guest, db: DB, body: FinishUpload | None = None):
    photo = await db.get(Photo, photo_id)
    if not photo or photo.owner != invite.id:
        raise HTTPException(404, "Upload not found.")
    if photo.status == "complete":
        return {"id": photo_id}
    if photo.expires < time.time():
        raise HTTPException(410, "Upload expired. Please upload again.")
    await asyncio.to_thread(finish_targets, photo, body or FinishUpload())
    await db.commit()
    await asyncio.to_thread(process_photo, photo)
    photo.status = "complete"
    photo.completed_at = int(time.time())
    await db.commit()
    await asyncio.to_thread(
        s3().delete_object, Bucket=settings().bucket_name, Key=media_key(photo, "pending")
    )
    if photo.motion_size:
        await asyncio.to_thread(
            s3().delete_object,
            Bucket=settings().bucket_name,
            Key=media_key(photo, "pending", "-motion"),
        )
    return {"id": photo_id}


def visible_to(invite: Invitation):
    targeted = exists().where(PhotoGuest.photo_id == Photo.id)
    allowed = exists().where(
        PhotoGuest.photo_id == Photo.id, PhotoGuest.guest_id == invite.guest_id
    )
    return or_(~targeted, allowed)


@router.get("/random")
@router.get("/carousel")
async def carousel_photos(invite: Guest, db: DB):
    """Return every eligible signed preview in one authenticated request."""
    rows = list(
        await db.scalars(
            select(Photo)
            .where(
                Photo.status == "complete",
                Photo.carousel_visible.is_(True),
                Photo.content_type.like("image/%"),
                visible_to(invite),
            )
            .order_by(Photo.id)
        )
    )
    items = await asyncio.gather(*(asyncio.to_thread(photo_preview, row) for row in rows))
    return {"items": items}


@router.get("")
async def gallery(
    invite: Guest, db: DB, cursor: str | None = None, limit: int = Query(12, ge=1, le=24)
):
    query = (
        select(Photo)
        .where(Photo.status == "complete", Photo.gallery_visible.is_(True), visible_to(invite))
        .order_by(Photo.id.desc())
        .limit(limit + 1)
    )
    if cursor:
        if len(cursor) != 32 or any(c not in "0123456789abcdef" for c in cursor):
            raise HTTPException(400, "Invalid gallery cursor.")
        query = query.where(Photo.id < cursor)
    rows = list((await db.scalars(query)).all())
    items = await asyncio.gather(*(asyncio.to_thread(photo_view, row) for row in rows[:limit]))
    return {"items": items, "cursor": rows[limit - 1].id if len(rows) > limit else None}
