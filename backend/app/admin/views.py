import asyncio
import json
import secrets
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException
from jinja2 import ChoiceLoader, PackageLoader, PrefixLoader
from markupsafe import Markup
from sqladmin import Admin, ModelView, action, expose
from sqladmin.filters import AllUniqueStringValuesFilter, BooleanFilter
from sqlalchemy import func, select, update
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse
from wtforms import BooleanField, Form, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Email, NumberRange, Optional

from app.admin.auth import AdminAuth
from app.admin.mfa import MfaView
from app.core.config import settings
from app.core.security import cipher
from app.db.models import Guest, Invitation, InvitationMessage, Photo
from app.db.session import sessions
from app.schemas import InvitationCreate
from app.services.access import ensure_access
from app.services.confirmations import render_confirmation
from app.services.email import content, render_email, send_invitation
from app.services.invitations import create_invitation, invitation_link
from app.services.messages import invitation_message, validate_message

AUDIENCES = [
    ("guest", "Guest"),
    ("witness", "Witness"),
    ("groom", "Groom"),
    ("bride", "Bride"),
    ("+1", "+1"),
]

DATE_FORMAT = "%Y-%m-%d %H:%M UTC"


class GuestForm(Form):
    name = StringField("Name", validators=[DataRequired()])
    email = StringField("Email", validators=[Optional(), Email()])
    language = SelectField(
        "Language", choices=[("en", "English"), ("it", "Italiano")], default="en"
    )
    audience = SelectField("Audience", choices=AUDIENCES, default="guest")


class GuestAdmin(ModelView, model=Guest):
    name_plural = "Guests"
    icon = "fa-solid fa-users"
    form = GuestForm
    can_delete = can_export = False
    column_list = [Guest.name, Guest.email, Guest.language, Guest.audience]
    column_searchable_list = [Guest.name, Guest.email]
    column_filters = [AllUniqueStringValuesFilter(Guest.audience)]
    column_sortable_list = [Guest.name, Guest.email, Guest.language, Guest.audience]

    async def on_model_change(self, data, model, is_created, request):
        if data["language"] not in {"en", "it"}:
            raise ValueError("Choose a supported language.")
        if data["audience"] not in dict(AUDIENCES):
            raise ValueError("Choose a supported audience.")
        data["email"] = (data.get("email") or "").strip().casefold() or None
        if is_created:
            model.id = uuid.uuid7().hex

    async def update_model(self, request, pk, data):
        async with sessions()() as db:
            guest = await db.get(Guest, pk)
            if guest is None:
                raise ValueError("Guest not found.")
            await self.on_model_change(data, guest, False, request)
            email = data["email"]
            if email and await db.scalar(
                select(Guest.id).where(Guest.email == email, Guest.id != pk)
            ):
                raise ValueError("This email already belongs to another guest.")
            values = {"name": data["name"], "is_witness": data["audience"] == "witness"}
            if guest.email != email:
                values.update(email_status="draft", email_error=None, email_message_id=None)
            guest.language = data["language"]
            guest.name, guest.email, guest.audience = data["name"], email, data["audience"]
            await db.execute(update(Invitation).where(Invitation.guest_id == pk).values(**values))
            await db.commit()
            return guest

    @action(
        name="create-invitations",
        label="Create invitations",
        confirmation_message="Create personal invitations for the selected guests?",
    )
    async def create_invitations(self, request):
        ids = list(dict.fromkeys(request.query_params.get("pks", "").split(",")))
        async with sessions()() as db:
            guests = list(await db.scalars(select(Guest).where(Guest.id.in_(ids))))
            for guest in guests:
                await create_invitation(db, InvitationCreate(name=guest.name), guest=guest)
            await db.commit()
        return RedirectResponse(
            request.url_for("admin:list", identity="invitation"), status_code=303
        )


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
        Invitation.guest,
        Invitation.active,
        Invitation.email_status,
        Invitation.attending,
        Invitation.created_at,
    ]
    column_searchable_list = [Invitation.name]
    column_default_sort = (Invitation.created_at, True)
    column_details_list = [
        Invitation.guest,
        Invitation.id,
        Invitation.active,
        Invitation.email_status,
        Invitation.email_error,
        Invitation.has_rsvp,
        Invitation.parent_invitation_id,
        Invitation.attending,
        Invitation.message,
        Invitation.dietary,
        Invitation.response_email,
        Invitation.response_guests,
        Invitation.witness_acceptance,
        Invitation.updated_at,
    ]
    column_sortable_list = [
        Invitation.guest,
        Invitation.active,
        Invitation.email_status,
        Invitation.attending,
        Invitation.created_at,
    ]
    column_labels = {
        Invitation.guest: "Guest",
        Invitation.attending: "Accepted",
        Invitation.updated_at: "Responded at",
        Invitation.response_guests: "Party response details",
        Invitation.max_guests: "Reserved places",
        Invitation.is_witness: "Witness",
        Invitation.id: "Personal invitation link",
        Invitation.has_rsvp: "RSVP response",
        Invitation.parent_invitation_id: "Invited by",
    }
    column_formatters = {
        Invitation.updated_at: lambda model, attr: datetime.fromtimestamp(
            model.updated_at, UTC
        ).strftime(DATE_FORMAT),
        Invitation.created_at: lambda model, attr: datetime.fromtimestamp(
            model.created_at, UTC
        ).strftime(DATE_FORMAT),
    }
    column_formatters_detail = {
        Invitation.id: lambda model, attr: invitation_link(model),
        Invitation.updated_at: lambda model, attr: (
            datetime.fromtimestamp(model.updated_at, UTC).strftime(DATE_FORMAT)
            if model.updated_at
            else "Not answered"
        ),
        Invitation.created_at: lambda model, attr: datetime.fromtimestamp(
            model.created_at, UTC
        ).strftime(DATE_FORMAT),
        Invitation.response_guests: lambda model, attr: "; ".join(
            person["name"] + (": " + person["dietary"] if person.get("dietary") else "")
            for person in json.loads(model.response_guests or "[]")
        ),
    }
    column_filters = [
        BooleanFilter(Invitation.has_rsvp, title="Has responded"),
        BooleanFilter(Invitation.attending, title="Accepted"),
        BooleanFilter(Invitation.active),
        AllUniqueStringValuesFilter(Invitation.email_status),
    ]
    form_columns = [
        Invitation.guest,
        Invitation.max_guests,
        Invitation.active,
    ]
    form_args = {
        "max_guests": {"default": 2, "validators": [NumberRange(min=1, max=12)]},
    }

    def list_query(self, request):
        return super().list_query(request).where(Invitation.is_admin.is_(False))

    def count_query(self, request):
        return super().count_query(request).where(Invitation.is_admin.is_(False))

    def details_query(self, request):
        return super().details_query(request).where(Invitation.is_admin.is_(False))

    def form_edit_query(self, request):
        return super().form_edit_query(request).where(Invitation.is_admin.is_(False))

    async def insert_model(self, request: Request, data: dict):
        async with sessions()() as db:
            guest = await db.get(Guest, data["guest"])
            if guest is None:
                raise ValueError("Select a guest.")
            if await db.scalar(select(Invitation.id).where(Invitation.guest_id == guest.id)):
                raise ValueError("This guest already has an invitation.")
            invite = await create_invitation(
                db,
                InvitationCreate(
                    name=guest.name,
                    language=guest.language,
                    max_guests=data["max_guests"],
                ),
                guest=guest,
            )
            invite.active = bool(data.get("active"))
            await db.commit()
            return invite

    async def update_model(self, request: Request, pk: str, data: dict):
        async with sessions()() as db:
            invite = await db.get(Invitation, pk)
            if not invite or invite.is_admin:
                raise ValueError("Invitation not found.")
            if data["guest"] != invite.guest_id:
                raise ValueError("An invitation stays linked to its original guest.")
            values = InvitationCreate(
                name=invite.guest.name,
                language=invite.guest.language,
                max_guests=data["max_guests"],
            )
            invite.max_guests = values.max_guests
            invite.active = bool(data.get("active"))
            await db.commit()
            return invite

    @action(
        name="activate-invitations",
        label="Activate invitations",
        confirmation_message="Activate the selected invitations?",
    )
    async def activate_invitations(self, request):
        ids = request.query_params.get("pks", "").split(",")
        async with sessions()() as db:
            await db.execute(
                update(Invitation)
                .where(Invitation.id.in_(ids), Invitation.is_admin.is_(False))
                .values(active=True)
            )
            await db.commit()
        return RedirectResponse(
            request.url_for("admin:list", identity="invitation"), status_code=303
        )

    @action(name="send-invitations", label="Send invitation")
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
        invites = [invite for invite in invites if invite.active]
        request.session["send_ids"] = [invite.id for invite in invites]
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
                render_email(
                    invite,
                    code,
                    message_template=selected_message,
                    wedding=await content(invite.guest.language or "en", db),
                )["html"],
                headers={
                    "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; img-src https: data:; sandbox allow-popups"
                },
            )

    @action(
        name="preview-confirmation-email",
        label="Preview confirmation email",
        add_in_list=False,
    )
    async def preview_confirmation_email(self, request: Request):
        async with sessions()() as db:
            invite = await db.get(Invitation, request.query_params.get("pks", ""))
            if not invite or invite.is_admin:
                raise HTTPException(404, "Invitation not found")
            count = (
                len(json.loads(invite.response_guests or "[]"))
                if invite.attending
                else invite.max_guests
            )
            message = await render_confirmation(invite, count, db)
            return HTMLResponse(
                message["html"],
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


class GuestCheckboxes:
    """A reversible guest selector without modifier keys or Select2 state."""

    def __call__(self, field, **kwargs):
        choices = []
        for index, (value, label, selected, _) in enumerate(field.iter_choices()):
            choices.append(
                Markup(
                    '<label class="guest-choice"><input type="checkbox" name="{}" '
                    'id="{}-{}" value="{}" {}> <span>{}</span></label>'
                ).format(
                    field.name, field.id, index, value, Markup("checked") if selected else "", label
                )
            )
        return Markup('<div class="guest-choices" id="{}">{}</div>').format(
            field.id, Markup("").join(choices)
        )


class PhotoAdmin(InvitationNamesMixin, model=Photo):
    name_plural = "Gallery"
    details_template = "admin/photo_details.html"
    can_create = False
    can_edit = True
    form_columns = [Photo.gallery_visible, Photo.carousel_visible, Photo.caption, Photo.guests]
    form_overrides = {"gallery_visible": BooleanField, "carousel_visible": BooleanField}
    form_widget_args = {
        "gallery_visible": {"class": "form-check-input"},
        "carousel_visible": {"class": "form-check-input"},
    }
    form_args = {
        "guests": {
            "label": "Visible to guests",
            "widget": GuestCheckboxes(),
            "description": "Leave empty for all authenticated guests. Selected guests are the only viewers in both gallery and carousel.",
        },
        "gallery_visible": {
            "label": "Visible in gallery",
            "description": "Show this media in the authenticated gallery.",
        },
        "carousel_visible": {
            "label": "Visible in carousel",
            "description": "Show this photo in the authenticated landing carousel. Videos are excluded.",
        },
    }
    column_details_list = [
        Photo.id,
        Photo.caption,
        Photo.status,
        Photo.owner,
        Photo.original_filename,
        Photo.uploaded_at,
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
        BooleanFilter(Photo.gallery_visible),
        BooleanFilter(Photo.carousel_visible),
        AllUniqueStringValuesFilter(Photo.content_type),
        AllUniqueStringValuesFilter(Photo.status),
        UploaderFilter(Photo.owner, title="Uploader", parameter_name="uploader"),
    ]
    column_sortable_list = [
        Photo.uploaded_at,
        Photo.owner,
        Photo.status,
        Photo.content_type,
        Photo.gallery_visible,
        Photo.carousel_visible,
    ]
    column_default_sort = (Photo.uploaded_at, True)
    column_labels = {
        Photo.owner: "Uploaded by",
        Photo.guests: "Visible to guests",
        Photo.uploaded_at: "Uploaded at",
        Photo.gallery_visible: "Visible in gallery",
        Photo.carousel_visible: "Visible in carousel",
        Photo.id: "Media preview",
    }

    column_formatters = {
        Photo.uploaded_at: lambda model, attr: datetime.fromtimestamp(
            model.uploaded_at, UTC
        ).strftime(DATE_FORMAT)
    }
    column_formatters_detail = column_formatters

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
        label="Make visible in gallery",
        confirmation_message="Make selected completed uploads visible in the gallery?",
    )
    async def approve_media(self, request):
        ids = request.query_params.get("pks", "").split(",")[:100]
        async with sessions()() as db:
            await db.execute(
                update(Photo)
                .where(Photo.id.in_(ids), Photo.status == "complete")
                .values(gallery_visible=True)
            )
            await db.commit()
        return RedirectResponse(request.url_for("admin:list", identity="photo"), status_code=303)

    @action(
        name="show-carousel",
        label="Make visible in carousel",
        confirmation_message="Make selected completed photos visible in the carousel? Videos are excluded.",
    )
    async def show_carousel(self, request):
        ids = request.query_params.get("pks", "").split(",")[:100]
        async with sessions()() as db:
            await db.execute(
                update(Photo)
                .where(
                    Photo.id.in_(ids),
                    Photo.status == "complete",
                    Photo.content_type.like("image/%"),
                )
                .values(carousel_visible=True)
            )
            await db.commit()
        return RedirectResponse(request.url_for("admin:list", identity="photo"), status_code=303)

    async def visibility_form(self, model):
        form = await self.scaffold_form()
        return form(data=await self.get_form_data_for_edit(model))

    async def on_model_change(self, data, model, is_created, request):
        if (
            data.get("gallery_visible") or data.get("carousel_visible")
        ) and model.status != "complete":
            raise ValueError("Only successfully processed media can be made visible.")

    async def on_model_delete(self, model, request):
        from app.services.photos import delete_photo_media

        await asyncio.to_thread(delete_photo_media, model)

    can_delete = True
    can_export = False
    column_list = [
        Photo.uploaded_at,
        Photo.owner,
        Photo.caption,
        Photo.status,
        Photo.gallery_visible,
        Photo.carousel_visible,
        Photo.content_type,
        Photo.size,
    ]
    column_searchable_list = [Photo.caption, Photo.uploader_name, Photo.original_filename]


class MessageForm(Form):
    language = SelectField(
        "Language", choices=[("en", "English"), ("it", "Italiano")], default="en"
    )
    audience = SelectField("Invitation type", choices=AUDIENCES)
    text = TextAreaField(
        "Message",
        validators=[DataRequired()],
        description="Plain text. Optional placeholders: {name}, {couple}, {date}, {venue}.",
    )
    plural_text = TextAreaField(
        "Message for multiple participants",
        description="Optional. Uses the standard plural invitation when empty. Same placeholders as above.",
    )
    active = BooleanField("Active", default=True)


class MessageAdmin(ModelView, model=InvitationMessage):
    name = "Invitation Email Template"
    name_plural = "Invitation Email Template"
    form = MessageForm
    can_export = False
    column_list = [
        InvitationMessage.language,
        InvitationMessage.audience,
        InvitationMessage.text,
        InvitationMessage.active,
    ]
    column_searchable_list = [InvitationMessage.text]
    column_sortable_list = [
        InvitationMessage.language,
        InvitationMessage.audience,
        InvitationMessage.active,
    ]

    async def on_model_change(self, data, model, is_created, request):
        import uuid

        data["text"] = validate_message(data["text"])
        data["plural_text"] = (
            validate_message(data["plural_text"]) if data.get("plural_text") else ""
        )
        if data["language"] not in {"en", "it"} or data["audience"] not in dict(AUDIENCES):
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
    admin.add_view(GuestAdmin)
    admin.add_view(InvitationAdmin)
    admin.add_view(MfaView)
    admin.add_view(PhotoAdmin)
    admin.add_view(MessageAdmin)
    return admin
