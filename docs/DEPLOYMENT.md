# AWS deployment with SST

The product is already released in production. Preserve the existing SST stages, database, buckets and invitation encryption key when updating it. Local tests and infrastructure type checks do not prove an AWS deployment or Resend delivery. Releases deploy directly to production. Verify real email delivery, database access, admin login and media moderation after deployment and before inviting guests.

## Infrastructure

SST provisions a single CloudFront origin for the static SvelteKit site and `/api` routes through API Gateway to the FastAPI Lambda container. Cookies and Origin headers reach the API; API responses use `Cache-Control: no-store`. The app restores only the configured canonical site host for admin redirects. Originals, motion components and WebP previews stay in a private S3 bucket. Pending uploads expire after one day.

Aurora DSQL is the serverless SQL database, with no always-running PostgreSQL server, VPC or NAT gateway. The region is `eu-central-1`. It is selected to meet the SQLAlchemy requirement with usage-based billing; free allowances are not a guarantee of a zero bill. S3 storage/requests, downloads, Resend, CloudFront, API Gateway, Lambda, ECR and logs can incur charges. Set an AWS Budget; see https://aws.amazon.com/rds/aurora/dsql/pricing/ for current database allowances. Production resources are retained/protected from accidental removal.

The Lambda runtime role has:

- `dsql:DbConnect` only for its database, mapped to `wedding_app`. SQL deletion grants cover guests, invitations, photos, targeting links, invitation messages, invitation access/links/sessions, and notification/confirmation records for admin cascade deletion. Administrator accounts cannot be deleted by the runtime role. No schema administration is granted.
- Object access and deletion only within its bucket's `pending/`, `originals/` and `previews/` prefixes.
- No SES sending permissions. Transactional email uses a domain-scoped Resend API key supplied by the SST `ResendApiKey` secret.
- Log writes only to its own log group, retained seven days.

Migrations and admin-account provisioning run in a private SST-managed bootstrap Lambda with `dsql:DbConnectAdmin`, scoped to this database. It has no public route or function URL. Only that function receives the initial admin password; the public API keeps its restricted role. Guest invitation tokens never grant SQLAdmin access.

## Wedding-period warm-up

The production SST stack includes an EventBridge Scheduler ping every five minutes
from **19 May 2027 at 23:45** until **4 June 2027 at 00:00**, Italy time
(`Europe/Rome`). The UTC boundaries are explicit in `sst.config.ts`; update them
there if the wedding dates change. Deploying the stack installs the schedule, but
it only invokes the API within that window.

The scheduler invokes the shared admin/gallery Lambda directly with an HTTP API
event for `GET /api/health`. Its dedicated role can invoke only that function and
can be assumed only by Scheduler for this account and schedule group. The health
endpoint executes `SELECT 1` using the application's existing SQLAlchemy pool,
then returns the connection to the pool for reuse. Database failures return a
failure response rather than reporting healthy. Lambda Web Adapter also uses
this endpoint for startup readiness.

This is best-effort warming, not provisioned concurrency: AWS can replace an
environment or start additional ones during traffic bursts, and database
connections can expire. The pings incur Lambda and database usage during the
window. Scheduler delivery retries are disabled; the next periodic ping tries
again. The schedule stops invoking after its end date and remains managed by SST.

After deployment, verify the schedule boundaries and target in EventBridge
Scheduler. During the active window, check Lambda invocations and database health
alongside real admin/gallery response times; local validation does not establish
that production warming is working.

## One-time owner setup

Follow [production updates and initial setup](PUBLISH.md) for registration, GitHub configuration before the first push, AWS OIDC, SST DNS bootstrap, registrar delegation, Resend setup, encryption-key setup and first deployment.

Set `SITE_DOMAIN=example.com` in the GitHub `production` environment. The `setup-dns` operation creates the public hosted zone, secret-backed Resend DKIM/`rsend`/`send` records, and retained SES verification/DKIM/DMARC records in the protected `production-dns` SST stage. After delegation, `deploy` creates the application in the separate protected `production` stage. SST creates a free non-exportable ACM certificate, validation records, CloudFront aliases and the `www` redirect. HTTP redirects to HTTPS. Keep both stages and their resource names stable.

`EMAIL_FROM` must be on a Resend-verified domain. Set the three DNS-stage secrets and run `setup-dns`, then configure the SST `ResendApiKey` secret before deploying; follow the [production email migration checklist](EMAIL.md). `EMAIL_FROM` also supplies the contact address in backend email templates and the frontend footer (`PUBLIC_CONTACT_EMAIL`). Mailbox hosting/forwarding is separate. The DNS stage retains its legacy SES records to preserve existing managed resources, but neither the runtime nor bootstrap uses SES.

## Release

For deployment choose **Release to AWS → Run workflow**, select `main`, operation `deploy`, and type `deploy`. The workflow checks the owner identity, runs the full CI workflow by default, then enters the protected environment before obtaining AWS credentials. For release troubleshooting, select **Skip the entire verification job for release troubleshooting** (`skip_verify`). This skips the entire reusable CI workflow for that release. Owner/branch authorization, release configuration validation, environment protection, deployment, database migrations, and deployed-route checks still run. Pull requests and pushes to `main` continue to run all checks. It builds/pushes the Lambda image and deploys SST. SST invokes the private bootstrap Lambda to run Alembic, grant the runtime SQL role, and create the administrator if missing before updating the API Lambda. Bootstrap failures fail deployment. The workflow then checks deployed API/admin routes. Initialization reruns on every deploy, so partially completed initialization can be retried. Keep deployments serialized (the release workflow already does this).

Approve the production environment review when prompted. Pushing code alone never deploys. For a local infrastructure preview (requires configured AWS credentials and the same domain/email variables):

```sh
npx sst diff --stage production
```

The repository can be checked without AWS access using `npx sst install && npx tsc -p tsconfig.infra.json`; this is a type check, not an AWS plan. Do not run `sst remove` against production. Take backups before future schema changes; code rollback does not automatically roll back migrations.

## First administrator

Before deployment, set `ADMIN_USERNAME` in the GitHub **production environment secrets**, using 3–100 letters, digits, or `_.@+-`. Usernames are normalized to lowercase. For local SST deploy/diff, export the same value as an environment variable.

Set the separate SST password secret once using an authorized operator terminal:

```sh
npx sst secret set AdminPassword --stage production
```

Enter a password of 14–1024 characters at the prompt; save it in your password manager. Do not pass it as a command-line argument or put it in GitHub secrets. `InviteEncryptionKey` remains a separate, stable SST secret.

SST creates the account only when that username is absent. Sign in at `https://your-site/admin` and complete the existing MFA enrollment prompt. Redeployments preserve existing passwords, MFA enrollment, sessions, account status and lockouts. Changing `AdminPassword` does not reset an existing account; changing `ADMIN_USERNAME` creates another account without deleting the old one. Use the existing `app.manage admin-user` operator command only for an intentional credential reset/recovery.

## Resend production email

Follow [the email setup guide](EMAIL.md) for domain verification, Route 53 records, the domain-scoped sending API key, `ResendApiKey`, cutover validation and rotation. Bootstrap only initialises the database and administrator; it does not contact Resend or request SES production access. A successful release does not establish real email delivery.

Before authorizing a release, set `STAGE=production`, `AWS_ACCOUNT_ID`, `AWS_DEPLOY_ROLE_ARN`, `SITE_DOMAIN`, `ADMIN_USERNAME`, `EMAIL_FROM`, `WEDDING_GROOM_NAME`, `WEDDING_GROOM_EMAIL`, `WEDDING_BRIDE_NAME`, and `WEDDING_BRIDE_EMAIL` in your local environment (optionally set `RSVP_NOTIFICATION_EMAIL` for response notifications), then run:

```sh
node scripts/validate_release_config.mjs
```

This check validates required values and account/region consistency without contacting AWS or printing configured values. The release workflow runs it before requesting AWS credentials. It does not verify Resend domain/key status, IAM permissions, SST secrets, or deployed behavior; those require the explicitly approved production deployment. Configure the same values as secrets in the GitHub `production` environment (the workflow supplies `STAGE` automatically).
