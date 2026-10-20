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

## Create and send invitations

1. Open **Invitations → New Invitation**. Enter the guest/group name, email and reserved places (1–12). Keep **Active** checked and save. This creates the private link without sending email.
2. Open the record’s details to copy its **Personal invitation link**, inspect its RSVP, or select **Preview invitation email**.
3. In the list, select one or more invitations (up to 25) and choose **Actions → Send selected invitations**.
4. Review the recipients, then press **Confirm and send emails**. This is the step that sends email.
5. Review the result. Only active `draft` or `failed` entries are eligible. `sent`, `sending`, or `unknown` deliveries are not automatically resent. If a delivery is uncertain, check SES before intervening.

Uncheck **Active** to revoke an invitation and block its guest sessions. After sending, changing a recipient’s email requires a new invitation. Use **Media moderation** to review uploaded photos/videos and approve publication. Originals remain private in S3. See [media moderation](MEDIA.md).

## AWS / production credentials

Use the same CLI against the production database from an authorised operator environment, with the production application configuration and IAM database access. Run the database migrations first so `admin_users` exists. Use the runtime configuration’s `DSQL_HOST`, `DB_USER`, `AWS_REGION`, `SITE_URL` and `INVITE_ENCRYPTION_KEY`. Never use local test AWS keys or the local encryption key in production.

```sh
uv run --package wedding-api python -m app.manage admin-user --username andrea
```

Production must use HTTPS with `COOKIE_SECURE=true`. The admin cookie is HttpOnly, SameSite=Strict and scoped to `/api/admin`; guest sessions use a separate cookie. The reverse proxy/CDN must route **all `/api/*` paths**, including SQLAdmin assets and forms, to FastAPI. Form submissions require the website’s configured Origin. Guest tokens cannot create or sign into admin accounts.

Docker browser tests provision an independent, random `browser-test-admin` account in the local database. Its password is shared only through a Docker test volume, never a hard-coded default or a committed file.

## Guest links, short codes and recovery

Creating an invitation generates its private link and a short code. **Preview invitation email** shows both without sending anything. The email includes a separate gallery link; either link establishes the same guest session used for RSVP and uploads. Share these credentials only with the intended guest.

Guests without a session can paste the short code on the RSVP form or `/gallery`. **Lost your code?** emails a replacement to the address saved on the invitation. It never creates an invitation for an unknown address. Replacements expire after 15 minutes if unused, and replace the previous link/code only when redeemed. A replacement request has a five-minute cooldown; mail delivery failures do not invalidate the previous invitation.

After updating the application, run `docker compose up --build -d --wait` so the initializer creates the invitation-access and login-throttle tables. Production migrations must also run before deploying this version. Deactivating an invitation blocks its codes, links and existing sessions.

## Optional email, language and responses

The invitation email is optional. Choose **Email language** when creating/editing a record. After saving, open **View → Show personal link and short code** to copy an invitation without sending an email. Email preview and sending use the selected language. An invitation without an email address is skipped by bulk sending.

The admin includes **RSVP responses**, **Attending guests** and **RSVP notifications**. Responses are stored in structured SQL tables. Alembic manages schema migrations. See [email setup](EMAIL.md) for real AWS SES delivery and the notification destination setting.

## Witnesses, messages and publication

Set **Witness** for a witness invitation; the invitation email and RSVP form then ask them to accept that role. The guest confirmation includes a save-the-date calendar attachment after an accepted RSVP.

Use **Invitation messages** to edit the English/Italian wording pool. Separate guest and witness messages are randomly selected and saved for each invitation, so its preview and sent message match. See [migration and message details](MIGRATIONS.md).

Use **Media moderation** to review photos, videos and Live Photos. Uploads are hidden until you check **Published** and save. **Review selected media** displays private previews and originals before approval. Uncheck **Published** to remove an item from future gallery requests. See [media instructions](MEDIA.md).

## Authenticator two-factor authentication

After creating credentials with the existing `admin-user` CLI, sign in at `/api/admin/` with username and password. First login opens a private QR enrollment page. Scan it using Google Authenticator or another TOTP authenticator, then enter its six-digit code. Enrollment must finish before any admin data becomes accessible. Subsequent logins require the password and current authenticator code. Codes cannot be reused; wait for the next code when signing in again immediately. Keep the server and phone clocks synchronized.

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

Changing an additional attendee's email, removing them, or declining the holder's RSVP deactivates the old additional invitation and revokes its sessions. An additional guest who declines their own invitation also loses access. Re-adding a removed guest creates a new invitation; the old link remains expired. Existing uploaded media is retained for moderation. Unchanged RSVP retries do not create duplicate invitations or send duplicate emails. Failed email deliveries remain visible and can be resent from Invitations.

## Faster media moderation

Media moderation displays uploader names and supports searching and filtering by uploader. Open a record's details to see its image or video immediately. Select multiple rows and choose **Approve selected media** to publish completed uploads together; incomplete uploads are never approved. Originals remain unchanged.

## Andrea and Sara's gallery access

Migration `0006_wedding_hosts` creates ordinary guest invitations for Andrea Aramini (`andrea.aramini.lavoro@gmail.com`) and Sara Donciglio (`donciglio.sa@gmail.com`). These accounts can upload media and do not grant administrator privileges. No email is sent by the migration. In Invitations, open their entry and generate a personal link, or send their invitation after configuring SES. Credentials are generated securely on first use, with the application's encryption key.
