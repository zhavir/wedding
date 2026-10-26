# Transactional email with Resend

Production sends invitations, recovery/+1 emails, RSVP confirmations (including the `.ics` calendar), and organiser notifications through Resend's HTTPS API. Templates remain in this repository and the admin interface; no Resend template IDs are needed. The app stores the provider message ID where supported. `sent` means provider acceptance, not inbox delivery. There are no delivery webhooks in this application; use the Resend dashboard to inspect delivery, bounce and complaint events.

## DNS values stored as AWS-backed SST secrets

For `saraandreawedding.online`, set `SITE_DOMAIN` to that domain in the GitHub `production` environment. Store the record values using SST's interactive prompts in an authenticated operator terminal:

```sh
npx sst secret set ResendDkim --stage production-dns
npx sst secret set ResendRsend --stage production-dns
npx sst secret set ResendSend --stage production-dns
```

| SST secret | Record name relative to `SITE_DOMAIN` | Type |
| --- | --- | --- |
| `ResendDkim` | `resend._domainkey` | TXT |
| `ResendRsend` | `rsend` | CNAME |
| `ResendSend` | `send` | CNAME |

Paste the raw, single-line DKIM value without surrounding quotes, and the exact target hostname for each CNAME. SST splits long DKIM values into DNS strings automatically. Route 53 uses a TTL of 300 seconds for all three records (there is no `Auto` TTL setting).

These secrets belong to **`production-dns`**, while `ResendApiKey` belongs to **`production`**. SST stores secrets encrypted in AWS and propagates secret marking into deployment state. Values are not committed, added to stack outputs, or passed to the application. DNS values become publicly queryable once published; secret storage protects their configuration, not DNS visibility. See [SST secrets](https://sst.dev/docs/component/secret/).

Run **Release to AWS → setup-dns** after setting or rotating these secrets. Missing secrets fail the DNS deployment; the ordinary `deploy` operation does not update this separate DNS stage. If the same records were previously created manually, import them into the DNS stage before deploying instead of creating duplicates or overwriting them blindly. The workflow retains its existing output masking. Finally, verify the domain in Resend; SST does not perform that provider-side step.

## Production migration: required operator steps

Complete these steps before deploying this change to the existing site. Keep the existing SST stages, domain, database, invitation encryption key and administrator password.

1. **Create a Resend account/team.** Enable account MFA and review the account's sending limits/approval requirements in its dashboard. Choose a plan with enough capacity for invitations, recovery messages, confirmations and notifications. Do not assume domain verification alone removes account limits.
2. **Add your sending domain in Resend → Domains.** To retain `wedding@example.com`, verify `example.com`. Alternatively verify a dedicated subdomain such as `mail.example.com` and use `wedding@mail.example.com`. The sender must match the verified domain. Use your own domain, not the development `resend.dev` sender. See [verified domains](https://resend.com/docs/dashboard/domains/introduction).
3. **Publish the Resend records through SST.** Set the three DNS secrets described below, then run **Release to AWS → setup-dns**. The protected `production-dns` stage creates the DKIM TXT at `resend._domainkey` and CNAMEs at `rsend` and `send` in the existing public hosted zone for `SITE_DOMAIN`. Use the exact values from your Resend domain screen. After DNS propagation, return to Resend → Domains and verify the domain. Keep existing website/certificate records, mailbox MX records and the managed `_dmarc` policy. See [verified domains](https://resend.com/docs/dashboard/domains/introduction).
4. **Keep receiving mail working.** This integration sends mail only; it does not create a mailbox or forwarding. `EMAIL_FROM` also supplies the public contact address and email-template contact link. Choose a sender whose replies you can receive, or arrange mailbox forwarding separately. Leave open/click tracking disabled for invitation emails containing private sign-in links.
5. **Create a dedicated API key** in Resend → API Keys with **Sending access**, restricted to the selected domain. Save it in your password manager. See [API key permissions](https://resend.com/docs/dashboard/api-keys/introduction).
6. **Store the key in SST**, from an authorised operator terminal in this checkout, using the same AWS account/profile and `eu-central-1` region as production:

   ```sh
   export AWS_PROFILE=wedding-admin
   export AWS_REGION=eu-central-1
   aws sts get-caller-identity
   npx sst secret set ResendApiKey --stage production
   ```

   Check the account ID, then paste the Resend key at the prompt. Do not pass it as a command-line argument, put it in frontend variables, commit it, or print it in CI. This is a new secret; do not regenerate `InviteEncryptionKey` or `AdminPassword`. SST passes it to the backend Lambda as `RESEND_API_KEY`. Setting a secret does not update the running function until deployment.
7. **Update GitHub → Settings → Environments → production → Environment secrets.** Set `EMAIL_FROM` to the verified sender (a bare email address). Set `RSVP_NOTIFICATION_EMAIL` to the monitored organiser inbox, or leave it empty to disable those notifications. Existing deployment/host secrets remain required. Delete the obsolete `SES_IDENTITY_ARN` secret if present. `ResendApiKey` belongs in SST, not GitHub. SST explicitly sets `EMAIL_PROVIDER=resend` for the API; it supplies no local AWS endpoint or dummy credentials.
8. **Deploy using the normal release workflow.** Merge the reviewed changes, then run **Release AWS → deploy** from `main`, with the existing confirmation. Do not rerun initial DNS setup or reset the database for this migration. Deployment removes SES sending permissions from the runtime role and SES review permissions/calls from bootstrap. The existing SES identity/DKIM/DNS resources remain managed in the protected DNS stage to avoid deleting deployed resources; they are unused by the production application. Do not manually remove SST-managed resources during this cutover.
9. **Verify real delivery before inviting guests.** Create a guest using an inbox you control, preview and explicitly send the invitation. Check the Resend dashboard and inbox/spam folder, open the private link, accept the RSVP, verify the confirmation and open its calendar attachment. Verify organiser notification delivery with `RSVP_NOTIFICATION_EMAIL` set, and test email recovery and the +1 flow. Check both template languages if you use both. Do not bulk-send until this succeeds.

## Delivery failures and key rotation

The persisted states below apply to invitations, RSVP confirmations and organiser notifications. Recovery requests keep their generic response even when delivery fails; they do not create a delivery-status record. Use Resend logs to investigate those sends.

- Missing key or an HTTP 4xx rejection: persisted as `failed`. Check the configured key/domain/sender, recipient, account status and Resend logs. HTTP 429 means rate/quota limits: reduce the batch size and wait for capacity before an explicit retry. The app does not automatically retry rejected messages.
- Timeout, connection error, HTTP 5xx or an invalid success response: persisted as `unknown`. Resend may already have accepted the email. Inspect its dashboard by recipient/time before deciding whether to resend. The app intentionally does not automatically retry uncertain sends. Invitations already marked `sent`, `sending` or `unknown` are not claimed again by normal invitation sending.
- Interrupted processes may leave `sending` records; inspect provider history before operator recovery. Do not blindly reset delivery statuses or resend a whole batch.
- To rotate a key: create a new domain-scoped sending key, set `ResendApiKey` with the same command, redeploy, verify a test delivery, then revoke the old key in Resend. Never revoke the active key before replacement is deployed.

See the [send API](https://resend.com/docs/api-reference/emails/send-email) and [API errors](https://resend.com/docs/api-reference/errors). Local tests cannot establish production domain verification, account approval, quotas or inbox delivery.

## Local Docker: simulated email, no Resend account required

`docker compose up --build -d --wait` sets `EMAIL_PROVIDER=ses-local` and points it at Floci. Email remains captured by the fake AWS SES service and **never reaches a real inbox**. No Resend key is passed to Docker. S3 also remains on Floci. Existing integration/browser tests and the SES simulator's message inspection continue to work. `EMAIL_FROM=wedding@example.com` is fine locally; set `RSVP_NOTIFICATION_EMAIL=hosts@example.com` in your local `.env` to exercise notification capture. Restart/recreate the API after changing that setting.

The backend defaults to Resend outside Compose. Standalone local runs must explicitly set `EMAIL_PROVIDER=ses-local` and `AWS_ENDPOINT_URL` to the emulator. The SES client refuses to initialise without an emulator endpoint; there is no production SES fallback.

Run local validation with:

```sh
docker compose --profile test run --build --rm unit
docker compose --profile test run --build --rm integration
```

Resend HTTP payloads, attachments and failure handling are also tested with mocked HTTP responses; no test calls the real Resend service.

## Admin workflow

- **Guests**: create the guest name, optional email and audience, then select guests and choose **Create invitations**. In **Invitations**, set reserved places and **Email language** (English or Italiano).
- Email unknown: leave it blank, save, open **View → Show personal link and short code**, and copy the link into your own message. This is a private invitation token, not an S3 download URL. Creating/viewing it sends no mail. Deactivation revokes access.
- Email known: **Preview invitation email** uses the selected language. Select records and choose **Send invitation**, review, then confirm. Records without an email are skipped. Previously sent messages are not automatically resent.
- The guest's name and email prefill their first RSVP. Existing saved answers take precedence. Consent must still be checked explicitly.
- **Invitations** holds attendance, contact email, response message, dietary details, consent and response timestamp. Alembic manages the schema.

## RSVP notifications

Set `RSVP_NOTIFICATION_EMAIL` to the destination mailbox. A new or changed RSVP sends a notification for both acceptance and decline; replaying an identical response does not send another email. The response is committed before sending. If email fails, the guest's reply remains saved.

Notifications include the invitation name, yes/no answer, guest count and an admin link. Dietary details remain in the protected admin interface. The internal notification table retains pending/sending/sent/failed/unknown delivery state and error codes. Blank notification configuration disables delivery. Changes made while disabled are not emailed retroactively.

Notifications are awaited by the API, not dispatched through an untracked background task. If a process stops mid-delivery, a record can remain pending/sending. There is no automatic retry worker; inspect Resend before manually retrying uncertain deliveries to avoid duplicates.

## Inspecting delivery state

Open the invitation detail page and inspect **email_error**. Rejections record a safe HTTP status, not the provider response body. Use the Resend dashboard for details; see the failure-handling section above. `skipped` means no email, an inactive invitation, or an invitation already sent/sending/uncertain.

## Witnesses and acceptance confirmations

Select **Witness** as the guest audience. The selected language is used for a dedicated witness email and the guest sees a witness-role confirmation in the RSVP form. Saved witness answers appear on the invitation.

After accepting, the guest receives a thank-you email and `andrea-sara-wedding.ics`, with the confirmed ceremony start at 16:30 Europe/Rome and midnight finish. It uses the same event UID as the public calendar download. Edit calendar event details in `frontend/static/calendar/wedding-{en,it}.ics` and confirmation wording in `backend/app/services/email_content.py`. Resend receives the calendar as a Base64 attachment. Delivery states remain in the internal confirmation-email table.

Identical replies and dietary/message edits do not resend the confirmation. A new acceptance after declining, or an accepted reply using a different email, sends a new confirmation. Saving the RSVP succeeds even when mail delivery fails. The UI locks a saved form until a full page reload, including navigation away and back.

Invitation links authenticate the guest and open the landing page at the top. Gallery links authenticate at `/gallery#invite=…`, then replace the token fragment with `#upload` and scroll to the upload section.

## Current template and delivery model

The admin menu exposes **Invitation Email Template** with language, audience and mutable text. `invitation_en.html` and `invitation_it.html` are the code-owned Jinja layouts; shared stationery and static labels also live in code (`email_base.html`, `services/email_content.py`). The legacy `email_copy` table is removed by migration 0004. Template edits apply to subsequent previews and sends.

A +1 requires a unique email and is automatically created/reused, activated and sent after the parent's RSVP commits. `RSVP_NOTIFICATION_EMAIL` receives the response notification. Reactivation reuses an already sent invitation without resending. Provider delivery outcomes remain persisted; local mocked tests do not verify delivery to a real inbox.

### Language, participants and shared assets

Set Italian or English on the **Guest** record. Invitations, previews, recovery emails,
confirmations and the guest's initial website language use that preference. Migration
`0006_guest_language` preserves existing invitation languages and moves them to guests.

Invitation wording uses the number of reserved places; confirmation and RSVP wording
use the participating party size. Invitation Email Template has separate singular and
plural message fields. An empty plural field uses the standard plural invitation.
Witness acceptance remains a personal role; confirmation emails use the same template
for all audiences.

The website's `/monogram.svg` is the source of the email's `/monogram.png`. To regenerate
the email-compatible raster after changing the logo:

```sh
convert -background none -density 288 frontend/static/monogram.svg -resize 360x360 frontend/static/monogram.png
```

The two static files in `frontend/static/calendar/wedding-{en,it}.ics` are the only calendar
content. The website downloads them directly without an API. The backend image copies
these exact files into its email package for confirmation attachments. Migration
`0007_static_calendar` removes the redundant stored calendar payload from confirmation
emails; their delivery records remain in use.
Keep the event UID shared across languages; there are no guest-specific calendar fields
or database-managed calendar translations.
