# Wedding administration

The administration interface is **SQLAdmin**, mounted inside FastAPI at `/api/admin/`. It provides searchable, sortable invitation records, create/edit forms, record details, email previews and a send action. `/admin` redirects there for convenience.

## Create your credentials locally

Start the application and let the database bootstrap finish:

```sh
docker compose up --build -d --wait
```

Create your own account from the terminal:

```sh
docker compose exec api python -m app.manage admin-user --username andrea
```

Enter a password of at least 14 characters, then confirm it. The prompt hides your password. Open **http://localhost:5173/api/admin/** and sign in with username `andrea` and the password you chose. You can create a separate `sara` account using the same command with `--username sara`.

There is **no default administrator password**. The old `DEMO-ADMIN-2027` invitation link does not authenticate SQLAdmin. Guest email links still work for guest RSVP and photo access.

Run the same `admin-user` command again to reset a password. A reset invalidates that account’s existing admin sessions and clears a failed-login lockout. Admin sessions expire after eight hours; signing out invalidates the account’s sessions on other devices too. Five failed password attempts lock an account for 15 minutes.

For automated provisioning, `--password-stdin` reads one line from stdin. Supply it from a secret manager; do not put passwords in command arguments, source control, or workflow logs.

## Guests and invitations

The menu contains **Guests**, **Invitations**, **Gallery**, and **Invitation Email Template**. Authentication and delivery records remain internal.

1. In **Guests**, enter a name (the only required input) and choose Guest, Witness, Groom, Bride, or +1. Guest is the default audience.
2. Select guests and choose **Create invitations**. Repeating this action reuses their existing invitations. Each guest has one personal invitation.
3. In **Invitations**, optionally add an email, select English/Italian, set reserved places, and keep **Active** enabled. Email addresses are unique and matched case-insensitively; empty addresses are allowed.
4. Open details for the personal link, **Show personal link and short code**, **Preview invitation email**, or **Send invitation**.
5. Select up to 25 invitations and choose **Send invitation**, then confirm the recipients. Inactive invitations are excluded; entries without an email and sent/sending/unknown deliveries are skipped. **Activate invitations** enables selected records without sending email.

Filters cover answered/unanswered, accepted/declined, active/inactive, and email status. Attendance, dietary details, witness acceptance and the response message belong to the invitation. An unanswered invitation has no attendance value.

Deactivating an invitation blocks its link and sessions. Changing its email resets delivery status to draft; it does not send automatically.

## Gallery

Gallery and carousel visibility are independent. **Make visible in gallery** publishes completed uploads; **Make visible in carousel** publishes completed still photos to the landing carousel. Open a record to preview it and edit the **Visible in gallery** and **Visible in carousel** checkboxes, then **Save visibility**. Uncheck either checkbox to hide the item from that feed. The list shows one uploader and an upload date/time in UTC.

**Visible to guests** is a list of individual checkboxes. Check or uncheck any guest and save; no modifier keys are needed. Leave it empty for all authenticated guests; otherwise only the selected guests receive this media in gallery and carousel API responses. The carousel fetches every eligible still-photo preview in one authenticated request. Videos stay in the gallery.

## AWS / production credentials

SST creates the initial production account from the GitHub `ADMIN_USERNAME` secret and SST `AdminPassword` secret during deployment; MFA enrollment happens at first login. Redeployments preserve existing accounts. For intentional recovery only, use the same CLI against the production database from an authorised operator environment, with the production application configuration and IAM database access. Run the database migrations first so `admin_users` exists. Use the production `DSQL_HOST`, `AWS_REGION`, `SITE_URL` and `INVITE_ENCRYPTION_KEY`, with `DB_USER=admin` and an operator role authorized for `dsql:DbConnectAdmin`. Never use local test AWS keys or the local encryption key in production.

```sh
uv run --package wedding-api python -m app.manage admin-user --username andrea
```

Production must use HTTPS with `COOKIE_SECURE=true`. The admin cookie is HttpOnly, SameSite=Strict and scoped to `/api/admin`; guest sessions use a separate cookie. The reverse proxy/CDN must route **all `/api/*` paths**, including SQLAdmin assets and forms, to FastAPI. Form submissions require the website’s configured Origin. Guest tokens cannot create or sign into admin accounts.

Docker browser tests provision an independent, random `browser-test-admin` account in the local database. Its password is shared only through a Docker test volume, never a hard-coded default or a committed file.

## Guest links, short codes and recovery

Creating an invitation generates its private link and a short code. **Preview invitation email** shows both without sending anything. The email includes a separate gallery link; either link establishes the same guest session used for RSVP and uploads. Share these credentials only with the intended guest.

Guests without a session can paste the short code on the RSVP form or `/gallery`. **Lost your code?** emails a replacement to the address saved on the invitation. It never creates an invitation for an unknown address. Replacements expire after 15 minutes if unused, and replace the previous link/code only when redeemed. A replacement request has a five-minute cooldown; mail delivery failures do not invalidate the previous invitation.

After updating the application, run `docker compose up --build -d --wait` so the initializer creates the invitation-access and login-throttle tables. Production migrations must also run before deploying this version. Deactivating an invitation blocks its codes, links and existing sessions.

## Responses and +1 invitations

Every additional guest must supply a distinct valid email. The RSVP transaction creates their Guest and active Invitation, or reuses an existing invitation by email. Existing Guest audience changes to +1; witness/bride/groom roles remain intact. The child invitation links to its inviter. Draft/failed emails send automatically after commit, and the configured `RSVP_NOTIFICATION_EMAIL` recipient receives the RSVP notification. Repeated identical responses do not send duplicate notifications.

Removing a +1 or declining the parent's attendance deactivates the linked invitation and revokes its sessions. Re-adding that email reactivates the same invitation and link; old revoked sessions remain revoked. Sent invitations are not sent again. Each invitation stores its own response. Confirmation emails with calendar attachments and durable notification delivery state remain internal.

## Invitation Email Template

Edit language, audience and templated text here. Allowed placeholders are `{name}`, `{couple}`, `{date}`, and `{venue}`; values are HTML-escaped. The first active template by ID for the invitation's language/audience is used consistently for previews and sends; edits take effect immediately. Initial Italian/English +1 templates are seeded by migration `0004_guests_and_invitations`.

The Italian/English Jinja layouts, shared stationery and static event labels live in code. There is no section-by-section copy table. Mutable invitation wording lives in the database.

## Authenticator two-factor authentication

After SST creates the account (or after local creation with the `admin-user` CLI), sign in at `/api/admin/` with username and password. First login opens a private QR enrollment page. Scan it using Google Authenticator or another TOTP authenticator, then enter its six-digit code. Enrollment must finish before any admin data becomes accessible. Subsequent logins require the password and current authenticator code. Codes cannot be reused; wait for the next code when signing in again immediately. Keep the server and phone clocks synchronized.

Secrets are encrypted in the database using the application encryption key. The QR is generated locally and never sent to an external QR service. Pending enrollment expires after five minutes; failed codes are rate limited.

For a lost phone, a trusted operator can reset the password and MFA using:

```sh
docker compose run --rm api python -m app.manage admin-user --username YOUR_USERNAME --password-stdin --reset-mfa
```

Supply a new password on standard input. This revokes existing sessions and requires QR enrollment on the next login. Keep this operator access restricted; there is no public MFA reset endpoint.

## Responses and upload records

RSVP data is stored in response, guest and witness tables; there is no duplicate JSON response column. Email is required when responding. After saving, guests see a confirmation and an **Edit your preferences** button. A restored session keeps the form collapsed; entering a short code explicitly opens the existing response for editing. Email links open directly at the RSVP section.

Media moderation shows upload ownership, filename, timestamps and validated media metadata. New images, videos and paired Live Photos remain unpublished until an administrator approves them.

The legacy invitation-token administration API and `create-admin` token command are restricted to local test mode. With secure cookies or DSQL enabled they are rejected, so an old invitation token cannot bypass production two-factor authentication. Use `admin-user` and SQLAdmin for production administration.

## Additional guests

The first attendee is the invitation holder. Every additional attendee must have a distinct valid email address. Saving an accepted RSVP creates a separate invitation for each additional guest, in the holder's language, and sends their personal link and short code, including gallery/upload access. These invitations allow one attendee each. Admin invitation details show **Invited by** using the original holder's name.

Changing an additional attendee's email, removing them, or declining the holder's RSVP deactivates the old additional invitation and revokes its sessions. An additional guest who declines their own invitation keeps access to revise the response. Re-adding a removed guest reactivates the same invitation and link; previously revoked sessions stay revoked. An already sent invitation is not sent again. Existing email matches reuse the guest and invitation; an ordinary guest becomes audience +1. Existing uploaded media is retained for moderation. Unchanged RSVP retries do not create duplicate invitations or send duplicate emails. Failed email deliveries remain visible and can be resent from Invitations.

## Faster media moderation

Media moderation displays uploader names and supports searching and filtering by uploader. Open a record's details to see its image or video immediately. Select multiple rows and choose **Make visible in gallery** to publish completed uploads together; incomplete uploads are never approved. Originals remain unchanged.

## Andrea and Sara's gallery access

Migration `0001_initial` creates two ordinary guest invitations using `WEDDING_GROOM_NAME`, `WEDDING_GROOM_EMAIL`, `WEDDING_BRIDE_NAME`, and `WEDDING_BRIDE_EMAIL`. Supply these through production environment secrets in GitHub; local runs default to fictional example addresses. Migration does not send email or grant administrator privileges. In Invitations, open each entry and generate its personal link, or send its invitation after configuring SES. Credentials are generated securely on first use with the application's encryption key. Already migrated databases retain their existing records; changing these secrets does not update existing invitations. Edit those through the administrator interface.

## Email copy and private photo feeds

**Invitation Email Template** edits invitation wording by language and audience. Italian and English Jinja layouts and shared email labels live in the codebase; the former section-copy table has been removed. Preview and delivery use the same active template. Gallery and carousel visibility are independent: use **Visible in gallery** and **Visible in carousel**. Both feeds require authentication, and either, both or neither flag may be enabled. Existing gallery approvals are preserved; the new carousel flag defaults to off. Originals remain invitation-only, with temporary signed S3 links.
