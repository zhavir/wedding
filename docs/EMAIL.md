# Invitation emails and RSVP notifications

## Local simulation versus real delivery

Normal `docker compose up` uses Floci. It simulates SES and **does not deliver to real inboxes**. A `sent` status means the configured SES service accepted the message; it does not prove inbox delivery. Creating an invitation never sends it automatically.

For production on `example.com`, the [SST DNS setup operation](PUBLISH.md) creates the domain identity and verification/DKIM/DMARC records automatically. Delegate the domain and wait for verification; the application deployment then requests SES production access automatically. The manual identity instructions below are for alternate senders or standalone email testing.

## Set up Amazon SES

1. Choose an AWS Region (the examples use `eu-central-1`) and open Amazon SES in that Region.
2. Under **Verified identities**, create a domain identity for a domain you control. Add the DNS records SES gives you, including DKIM, and wait for verification. Alternatively verify an individual sender address by following its verification email. Set `EMAIL_FROM` to an address covered by this identity.
3. While SES is in the sandbox, verify **every recipient**, including the RSVP notification mailbox, or use SES's mailbox simulator for testing. Request production access in SES Account dashboard before inviting unverified guests. Verification and sandbox status are Region-specific.
4. Grant the application role only the sending permission it needs. Replace the placeholders below with your account, Region, verified identity and actual sender. Never attach administrator permissions just to send mail.
5. Configure the application, deploy/restart it, create one invitation, preview it, then explicitly send it to a verified mailbox you control. Check the result and inbox/spam folder before bulk sending. The sandbox permits only one message per second; test individual messages there and check your production sending quota before using concurrent bulk delivery. SES acceptance is not delivery confirmation; use SES delivery/bounce events for production monitoring.

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["ses:SendEmail", "ses:SendRawEmail"],
    "Resource": "arn:aws:ses:eu-central-1:123456789012:identity/example.org",
    "Condition": {"StringEquals": {"ses:FromAddress": "wedding@example.org"}}
  }]
}
```

Production runtime configuration:

```dotenv
AWS_REGION=eu-central-1
SES_REGION=eu-central-1
EMAIL_FROM=wedding@example.org
RSVP_NOTIFICATION_EMAIL=hosts@example.org
SITE_URL=https://your-wedding-domain.example
COOKIE_SECURE=true
```

In AWS, omit `AWS_ENDPOINT_URL`, `SES_ENDPOINT_URL`, `SES_PROFILE`, and local dummy access keys. Use the application's IAM role for credentials. Keep the database, encryption key and other application settings configured as documented elsewhere. The SST configuration includes scoped SES and DSQL permissions; follow [deployment setup](DEPLOYMENT.md) before releasing. Verify actual AWS delivery after deployment and before inviting guests.

## Deliver real email while keeping local SQL and S3

Use a dedicated AWS profile with the sending policy above; short-lived AWS IAM Identity Center credentials are preferable to static keys. Configure it with `aws configure sso --profile wedding-mail`, then sign in on the host with `aws sso login --profile wedding-mail`. If you use IAM access keys instead, configure the dedicated, restricted identity with `aws configure --profile wedding-mail`. Verify the selected identity with `aws sts get-caller-identity --profile wedding-mail`. Never commit AWS credentials.

Create a local, uncommitted `.env`:

```dotenv
EMAIL_FROM=wedding@example.org
RSVP_NOTIFICATION_EMAIL=hosts@example.org
```

Create `/tmp/wedding-real-mail.yaml` (Linux/macOS example):

```yaml
services:
  api:
    environment:
      SES_PROFILE: wedding-mail
      SES_REGION: eu-central-1
      SES_ENDPOINT_URL: https://email.eu-central-1.amazonaws.com
    volumes:
      - ${HOME}/.aws:/root/.aws:ro
```

Then start the stack using both files:

```sh
docker compose -f compose.yaml -f /tmp/wedding-real-mail.yaml up --build -d --wait
```

Only the API's SES client uses real AWS; SQL and S3 still use the normal local services. Sending from the admin or submitting an RSVP **will now send real email**. Choose test recipients you control. Windows users should put the override in a local file and mount their AWS configuration directory at `/root/.aws:ro`.

To return to simulated mail, recreate the API using only `compose.yaml`:

```sh
docker compose -f compose.yaml up -d --force-recreate api
```

## Admin workflow

- **Guests**: create the guest name, optional email and audience, then select guests and choose **Create invitations**. In **Invitations**, set reserved places and **Email language** (English or Italiano).
- Email unknown: leave it blank, save, open **View → Show personal link and short code**, and copy the link into your own message. This is a private invitation token, not an S3 download URL. Creating/viewing it sends no mail. Deactivation revokes access.
- Email known: **Preview invitation email** uses the selected language. Select records and choose **Send invitation**, review, then confirm. Records without an email are skipped. Previously sent messages are not automatically resent.
- The guest's name and email prefill their first RSVP. Existing saved answers take precedence. Consent must still be checked explicitly.
- **Invitations** holds attendance, contact email, response message, dietary details, consent and response timestamp. Alembic manages the schema.

## RSVP notifications

Set `RSVP_NOTIFICATION_EMAIL` to the destination mailbox. A new or changed RSVP sends a notification for both acceptance and decline; replaying an identical response does not send another email. The response is committed before sending. If email fails, the guest's reply remains saved.

Notifications include the invitation name, yes/no answer, guest count and an admin link. Dietary details remain in the protected admin interface. The internal notification table retains pending/sending/sent/failed/unknown delivery state and error codes. Blank notification configuration disables delivery. Changes made while disabled are not emailed retroactively.

Notifications are awaited by the API, not dispatched through an untracked background task. If a process stops mid-delivery, a record can remain pending/sending. There is no automatic retry worker; inspect SES before manually retrying uncertain deliveries to avoid duplicates.

## Troubleshooting

Open the invitation's detail page and inspect **email_error**; sending results also show the provider's error text.

- `MessageRejected`: check sender verification, recipient verification while in the sandbox, Region, and the complete error message.
- `AccessDenied`: check the application's IAM sending policy and identity ARN.
- Credential/profile errors: refresh the selected AWS profile or check the deployed execution role. Local `test` credentials cannot send through real SES.
- `unknown`: delivery may already have been accepted; inspect SES before resending.
- `skipped`: no email, inactive invitation, or an invitation already sent/sending/uncertain.

AWS references: [verified identities](https://docs.aws.amazon.com/ses/latest/dg/verify-addresses-and-domains.html), [creating identities](https://docs.aws.amazon.com/ses/latest/dg/creating-identities.html), [production access](https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html), [IAM sending policies](https://docs.aws.amazon.com/ses/latest/dg/control-user-access.html).

## Witnesses and acceptance confirmations

Select **Witness** as the guest audience. The selected language is used for a dedicated witness email and the guest sees a witness-role confirmation in the RSVP form. Saved witness answers appear on the invitation.

After accepting, the guest receives a thank-you email and `andrea-sara-wedding.ics`, with the confirmed ceremony start at 16:30 Europe/Rome and midnight finish. It uses the same event UID as the public calendar download. Edit calendar event details in `frontend/static/calendar/wedding-{en,it}.ics` and confirmation wording in `backend/app/services/email_content.py`. `ses:SendRawEmail` is required for attachments. Delivery states remain in the internal confirmation-email table.

Identical replies and dietary/message edits do not resend the confirmation. A new acceptance after declining, or an accepted reply using a different email, sends a new confirmation. Saving the RSVP succeeds even when mail delivery fails. The UI locks a saved form until a full page reload, including navigation away and back.

## Automatic production-access request

The application SST deployment checks the SES account in Frankfurt and submits a production-access request once the sender identity is verified. It uses the site URL, `TRANSACTIONAL` mail type, English, and `WEDDING_GROOM_EMAIL` as the contact inbox. Approved/pending requests are skipped; denied reviews are reported without resubmission. The release job shows a non-sensitive status message. AWS approval remains asynchronous, and sandbox limits continue until approval. See [deployment setup](DEPLOYMENT.md#ses-production-access). Review bounce/complaint feedback and any follow-up questions from AWS before sending invitations.

Invitation links authenticate the guest and open the landing page at the top. Gallery links authenticate at `/gallery#invite=…`, then replace the token fragment with `#upload` and scroll to the upload section.

## Current template and delivery model

The admin menu exposes **Invitation Email Template** with language, audience and mutable text. `invitation_en.html` and `invitation_it.html` are the code-owned Jinja layouts; shared stationery and static labels also live in code (`email_base.html`, `services/email_content.py`). The legacy `email_copy` table is removed by migration 0004. Template edits apply to subsequent previews and sends.

A +1 requires a unique email and is automatically created/reused, activated and sent after the parent's RSVP commits. `RSVP_NOTIFICATION_EMAIL` receives the response notification. Reactivation reuses an already sent invitation without resending. SES delivery outcomes remain persisted; local mocked tests do not verify delivery to a real inbox.

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
