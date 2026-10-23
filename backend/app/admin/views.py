import asyncio
import secrets
from pathlib import Path

from fastapi import HTTPException
from jinja2 import ChoiceLoader, PackageLoader, PrefixLoader
from markupsafe import Markup
from pydantic import ValidationError
from sqladmin import Admin, ModelView, action, expose
from sqladmin.filters import AllUniqueStringValuesFilter, BooleanFilter
from sqlalchemy import func, select, update
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse
from wtforms import BooleanField, Form, IntegerField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Email, NumberRange, Optional

from app.admin.auth import AdminAuth
from app.admin.mfa import MfaView
from app.core.config import settings
from app.core.security import cipher
from app.db.models import (
    ConfirmationEmail,
    Invitation,
    InvitationMessage,
    Photo,
    RSVPGuest,
    RSVPNotification,
    RSVPResponse,
    WitnessResponse,
)
from app.db.session import sessions
from app.schemas import InvitationCreate
from app.services.access import ensure_access
from app.services.email import render_email, send_invitation
from app.services.invitations import create_invitation, invitation_link
from app.services.messages import invitation_message, validate_message


class InvitationForm(Form):
    name = StringField("Name", validators=[DataRequired()])
    email = StringField(
        "Email",
        validators=[Optional(), Email()],
        description="Optional: leave blank to share the personal link yourself.",
    )
    max_guests = IntegerField("Reserved places", default=2, validators=[NumberRange(min=1, max=12)])
    language = SelectField(
        "Email language", choices=[("en", "English"), ("it", "Italiano")], default="en"
    )
    is_witness = BooleanField("Witness", default=False)
    active = BooleanField("Active", default=True)


class InvitationNamesMixin(ModelView):
    async def get_list_value(self, obj, prop, request=None):
        value, formatted = await super().get_list_value(obj, prop, request)
        if prop in {"invitation_id", "owner", "parent_invitation_id"} and value:
            async with sessions()() as db:
                person = await db.get(Invitation, value)
                if person:
                    formatted = person.name
        return value, formatted

    async def get_detail_value(self, obj, prop, request=None):
        value, formatted = await super().get_detail_value(obj, prop, request)
        if prop in {"invitation_id", "owner", "parent_invitation_id"} and value:
            async with sessions()() as db:
                person = await db.get(Invitation, value)
                if person:
                    formatted = person.name
        return value, formatted


class InvitationAdmin(InvitationNamesMixin, model=Invitation):
    async def get_detail_value(self, obj, prop, request=None):
        if prop == "id" and not obj.encrypted_token:
            async with sessions()() as db:
                await ensure_access(db, obj.id)
                row = await db.get(Invitation, obj.id)
                assert row is not None
                obj.encrypted_token = row.encrypted_token
                await db.commit()
        return await super().get_detail_value(obj, prop, request)

    name = "Invitation"
    name_plural = "Invitations"
    icon = "fa-solid fa-envelope"
    can_delete = False
    can_export = False
    column_list = [
        Invitation.name,
        Invitation.email,
        Invitation.language,
        Invitation.is_witness,
        Invitation.max_guests,
        Invitation.active,
        Invitation.email_status,
    ]
    column_searchable_list = [Invitation.name, Invitation.email]
    column_sortable_list = [Invitation.name, Invitation.email, Invitation.created_at]
    column_default_sort = (Invitation.created_at, True)
    column_details_list = [
        Invitation.name,
        Invitation.email,
        Invitation.language,
        Invitation.is_witness,
        Invitation.max_guests,
        Invitation.id,
        Invitation.active,
        Invitation.email_status,
        Invitation.email_error,
        Invitation.has_rsvp,
        Invitation.parent_invitation_id,
    ]
    column_labels = {
        Invitation.max_guests: "Reserved places",
        Invitation.language: "Email language",
        Invitation.is_witness: "Witness",
        Invitation.id: "Personal invitation link",
        Invitation.has_rsvp: "RSVP response",
        Invitation.parent_invitation_id: "Invited by",
    }
    column_formatters_detail = {Invitation.id: lambda model, attr: invitation_link(model)}
    form = InvitationForm

    def list_query(self, request):
        return super().list_query(request).where(Invitation.is_admin.is_(False))

    def count_query(self, request):
        return super().count_query(request).where(Invitation.is_admin.is_(False))

    def details_query(self, request):
        return super().details_query(request).where(Invitation.is_admin.is_(False))

    def form_edit_query(self, request):
        return super().form_edit_query(request).where(Invitation.is_admin.is_(False))

    @staticmethod
    def validated(data: dict) -> InvitationCreate:
        try:
            return InvitationCreate.model_validate(
                {
                    **{k: data[k] for k in ("name", "max_guests")},
                    "email": data.get("email") or None,
                    "language": data.get("language", "en"),
                    "is_witness": bool(data.get("is_witness", False)),
                }
            )
        except ValidationError as exc:
            raise ValueError(
                "Enter a name, valid email address and between 1 and 12 reserved places."
            ) from exc

    async def insert_model(self, request: Request, data: dict):
        async with sessions()() as db:
            invite = await create_invitation(db, self.validated(data))
            invite.active = bool(data.get("active"))
            await db.commit()
            return invite

    async def update_model(self, request: Request, pk: str, data: dict):
        values = self.validated(data)
        async with sessions()() as db:
            invite = await db.get(Invitation, pk)
            if not invite or invite.is_admin:
                raise ValueError("Invitation not found.")
            if (
                str(values.email) if values.email else ""
            ) != invite.email and invite.email_status not in {"draft", "failed"}:
                raise ValueError("Create a new invitation when changing a recipient after sending.")
            invite.language = values.language
            invite.is_witness = values.is_witness
            invite.name, invite.email, invite.max_guests = (
                values.name,
                str(values.email) if values.email else "",
                values.max_guests,
            )
            invite.active = bool(data.get("active"))
            await db.commit()
            return invite

    @action(name="send-invitations", label="Send selected invitations")
    async def review_send(self, request: Request):
        ids = list(dict.fromkeys(request.query_params.get("pks", "").split(",")))
        if not ids or not ids[0] or len(ids) > 25:
            raise HTTPException(400, "Select between 1 and 25 invitations.")
        async with sessions()() as db:
            invites = list(
                await db.scalars(
                    select(Invitation).where(Invitation.id.in_(ids), Invitation.is_admin.is_(False))
                )
            )
        if len(invites) != len(ids):
            raise HTTPException(400, "Invalid invitation selection.")
        request.session["send_ids"] = ids
        request.session["send_csrf"] = secrets.token_urlsafe(32)
        return await self.templates.TemplateResponse(
            request,
            "admin/send.html",
            {"invites": invites, "csrf": request.session["send_csrf"], "results": None},
        )

    @expose("/send-confirm", methods=["POST"])
    async def send_confirm(self, request: Request):
        form = await request.form()
        token = request.session.pop("send_csrf", "")
        ids = request.session.pop("send_ids", [])
        if (
            not token
            or not secrets.compare_digest(str(form.get("csrf", "")), token)
            or not 1 <= len(ids) <= 25
        ):
            raise HTTPException(403, "Review the invitations again before sending.")
        semaphore = asyncio.Semaphore(4)

        async def send(invitation_id):
            async with semaphore:
                return await send_invitation(invitation_id)

        results = await asyncio.gather(*(send(invitation_id) for invitation_id in ids))
        return await self.templates.TemplateResponse(
            request, "admin/send.html", {"invites": [], "csrf": "", "results": results}
        )

    @action(name="personal-link", label="Show personal link and short code", add_in_list=False)
    async def personal_link(self, request: Request):
        async with sessions()() as db:
            invite = await db.get(Invitation, request.query_params.get("pks", ""))
            if not invite or invite.is_admin:
                raise HTTPException(404, "Invitation not found.")
            access = await ensure_access(db, invite.id)
            await db.commit()
            return await self.templates.TemplateResponse(
                request,
                "admin/link.html",
                {
                    "invite": invite,
                    "link": invitation_link(invite),
                    "code": cipher().decrypt(access.encrypted_code.encode()).decode(),
                },
            )

    @action(name="preview-email", label="Preview invitation email", add_in_list=False)
    async def preview_email(self, request: Request):
        async with sessions()() as db:
            invite = await db.get(Invitation, request.query_params.get("pks", ""))
            if not invite or invite.is_admin:
                raise HTTPException(404, "Invitation not found.")
            access = await ensure_access(db, invite.id)
            selected_message = await invitation_message(db, invite)
            await db.commit()
            code = cipher().decrypt(access.encrypted_code.encode()).decode()
            # Email HTML is autoescaped by Jinja; render it without enabling scripts.
            return HTMLResponse(
                render_email(invite, code, message_template=selected_message)["html"],
                headers={
                    "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; img-src https: data:; sandbox allow-popups"
                },
            )


class UploaderFilter(AllUniqueStringValuesFilter):
    async def lookups(self, request, model, run_query):
        rows = await run_query(
            select(Photo.owner, func.coalesce(Invitation.name, Photo.uploader_name))
            .outerjoin(Invitation, Invitation.id == Photo.owner)
            .distinct()
        )
        return [("__all", "All"), *[(row[0], row[1] or "Deleted guest") for row in rows]]


class PhotoAdmin(InvitationNamesMixin, model=Photo):
    name_plural = "Media moderation"
    can_create = False
    can_edit = True
    form_columns = [Photo.published, Photo.caption]
    column_details_list = [
        Photo.id,
        Photo.caption,
        Photo.status,
        Photo.published,
        Photo.owner,
        Photo.uploader_name,
        Photo.original_filename,
        Photo.uploaded_at,
        Photo.completed_at,
        Photo.width,
        Photo.height,
        Photo.duration_ms,
        Photo.codec,
        Photo.sha256,
        Photo.content_type,
        Photo.size,
        Photo.motion_size,
        Photo.motion_content_type,
    ]
    column_filters = [
        BooleanFilter(Photo.published),
        AllUniqueStringValuesFilter(Photo.status),
        UploaderFilter(Photo.owner, title="Uploader", parameter_name="uploader"),
    ]
    column_labels = {
        Photo.owner: "Uploaded by",
        Photo.uploader_name: "Uploader",
        Photo.id: "Media preview",
    }

    async def get_detail_value(self, obj, prop, request=None):
        value, formatted = await super().get_detail_value(obj, prop, request)
        if prop == "id" and obj.status == "complete":
            from app.services.photos import photo_view

            view = await asyncio.to_thread(photo_view, obj)
            formatted = Markup(
                '<img src="{}" alt="Uploaded media preview" style="max-width:100%;max-height:65vh">'
            ).format(view["preview"])
            if view["kind"] != "photo":
                formatted += Markup(
                    '<video controls playsinline preload="metadata" src="{}" style="max-width:100%;max-height:65vh"></video>'
                ).format(view["motion"] or view["original"])
        return value, formatted

    @action(
        name="approve-media",
        label="Approve selected media",
        confirmation_message="Publish all selected completed uploads?",
    )
    async def approve_media(self, request):
        ids = request.query_params.get("pks", "").split(",")[:100]
        async with sessions()() as db:
            await db.execute(
                update(Photo)
                .where(Photo.id.in_(ids), Photo.status == "complete")
                .values(published=True)
            )
            await db.commit()
        return RedirectResponse(request.url_for("admin:list", identity="photo"), status_code=303)

    async def on_model_change(self, data, model, is_created, request):
        if data.get("published") and model.status != "complete":
            raise ValueError("Only successfully processed media can be published.")

    @action(name="review-media", label="Review selected media")
    async def review_media(self, request):
        from html import escape

        from app.services.photos import photo_view

        ids = request.query_params.get("pks", "").split(",")[:25]
        async with sessions()() as db:
            rows = list(
                await db.scalars(select(Photo).where(Photo.id.in_(ids), Photo.status == "complete"))
            )
        views = await asyncio.gather(*(asyncio.to_thread(photo_view, row) for row in rows))
        cards = []
        for row, view in zip(rows, views, strict=True):
            video = (
                f'<video controls playsinline preload="none" src="{escape(view["motion"] or view["original"])}"></video>'
                if view["kind"] != "photo"
                else ""
            )
            cards.append(
                f'<article><h2>{escape(row.caption)}</h2><img src="{escape(view["preview"])}" alt="Media preview">{video}<p><a href="{escape(view["original"])}">Download original</a></p><a href="/api/admin/photo/edit/{row.id}">Approve or unpublish</a></article>'
            )
        return HTMLResponse(
            '<html lang="en"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Review media</title><style>body{font:18px Arial;max-width:900px;margin:auto;padding:20px}img,video{max-width:100%;max-height:60vh}article{padding:20px;border-bottom:1px solid #ccc}</style><h1>Review uploaded media</h1><p>Media stays private until Published is checked and saved.</p>'
            + "".join(cards)
            + "</html>"
        )

    can_delete = False
    can_export = False
    column_list = [
        Photo.id,
        Photo.owner,
        Photo.caption,
        Photo.status,
        Photo.published,
        Photo.content_type,
        Photo.size,
    ]
    column_searchable_list = [Photo.caption, Photo.uploader_name, Photo.original_filename]


class ResponseAdmin(InvitationNamesMixin, model=RSVPResponse):
    name_plural = "RSVP responses"
    can_create = can_edit = can_delete = can_export = False
    column_list = [
        RSVPResponse.invitation_id,
        RSVPResponse.email,
        RSVPResponse.attending,
        RSVPResponse.updated_at,
    ]
    column_details_list = [
        RSVPResponse.invitation_id,
        RSVPResponse.email,
        RSVPResponse.attending,
        RSVPResponse.message,
        RSVPResponse.consent,
        RSVPResponse.updated_at,
    ]
    column_searchable_list = [RSVPResponse.email]


class GuestAdmin(InvitationNamesMixin, model=RSVPGuest):
    name_plural = "Attending guests"
    can_create = can_edit = can_delete = can_export = False
    column_list = [RSVPGuest.invitation_id, RSVPGuest.name, RSVPGuest.dietary]
    column_searchable_list = [RSVPGuest.name]

    def list_query(self, request):
        return super().list_query(request).where(RSVPGuest.active.is_(True))

    def count_query(self, request):
        return super().count_query(request).where(RSVPGuest.active.is_(True))


class NotificationAdmin(InvitationNamesMixin, model=RSVPNotification):
    name_plural = "RSVP notifications"
    can_create = can_edit = can_delete = can_export = False
    column_list = [
        RSVPNotification.invitation_id,
        RSVPNotification.recipient,
        RSVPNotification.status,
        RSVPNotification.error,
        RSVPNotification.created_at,
    ]


class WitnessAdmin(InvitationNamesMixin, model=WitnessResponse):
    name_plural = "Witness responses"
    can_create = can_edit = can_delete = can_export = False
    column_list = [WitnessResponse.invitation_id, WitnessResponse.accepted]


class ConfirmationAdmin(InvitationNamesMixin, model=ConfirmationEmail):
    name_plural = "Guest confirmation emails"
    can_create = can_edit = can_delete = can_export = False
    column_list = [
        ConfirmationEmail.invitation_id,
        ConfirmationEmail.recipient,
        ConfirmationEmail.status,
        ConfirmationEmail.error,
        ConfirmationEmail.created_at,
    ]


class MessageForm(Form):
    language = SelectField("Language", choices=[("en", "English"), ("it", "Italiano")])
    audience = SelectField("Invitation type", choices=[("guest", "Guest"), ("witness", "Witness")])
    text = TextAreaField(
        "Message",
        validators=[DataRequired()],
        description="Plain text. Optional placeholders: {name}, {couple}, {date}, {venue}.",
    )
    active = BooleanField("Active", default=True)


class MessageAdmin(ModelView, model=InvitationMessage):
    name_plural = "Invitation messages"
    form = MessageForm
    can_export = False
    column_list = [
        InvitationMessage.language,
        InvitationMessage.audience,
        InvitationMessage.text,
        InvitationMessage.active,
    ]
    column_searchable_list = [InvitationMessage.text]

    async def on_model_change(self, data, model, is_created, request):
        import uuid

        data["text"] = validate_message(data["text"])
        if data["language"] not in {"en", "it"} or data["audience"] not in {"guest", "witness"}:
            raise ValueError("Choose a supported language and invitation type.")
        if is_created:
            model.id = uuid.uuid7().hex


def setup_admin(app) -> Admin:
    cfg = settings()
    # Tests can start the same FastAPI instance with a fresh database.
    app.router.routes[:] = [
        route for route in app.router.routes if getattr(route, "path", "") != "/api/admin"
    ]
    auth = AdminAuth(
        secret_key=cfg.invite_encryption_key + ":admin-session",
        session_cookie="wedding_admin",
        max_age=8 * 3600,
        same_site="strict",
        https_only=cfg.cookie_secure,
        path="/api/admin",
    )
    admin = Admin(
        app,
        session_maker=sessions(),
        base_url="/api/admin",
        title="Andrea & Sara · Wedding administration",
        templates_dir=str(Path(__file__).parents[1] / "templates"),
        authentication_backend=auth,
    )
    assert admin.templates.env.loader is not None
    admin.templates.env.loader = ChoiceLoader(
        [
            admin.templates.env.loader,
            PrefixLoader({"upstream": PackageLoader("sqladmin", "templates")}),
        ]
    )
    admin.add_view(InvitationAdmin)
    admin.add_view(MfaView)
    admin.add_view(PhotoAdmin)
    admin.add_view(ResponseAdmin)
    admin.add_view(GuestAdmin)
    admin.add_view(NotificationAdmin)
    admin.add_view(WitnessAdmin)
    admin.add_view(ConfirmationAdmin)
    admin.add_view(MessageAdmin)
    return admin
