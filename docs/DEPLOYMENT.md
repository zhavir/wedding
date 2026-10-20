# AWS deployment with SST

No production deployment has been performed. Local tests and infrastructure type checks do not prove an AWS deployment or SES delivery. Releases deploy directly to production. Verify real email delivery, database access, admin login and media moderation after deployment and before inviting guests.

## Infrastructure

SST provisions a single CloudFront origin for the static SvelteKit site and `/api` routes through API Gateway to the FastAPI Lambda container. Cookies and Origin headers reach the API; API responses use `Cache-Control: no-store`. The app restores only the configured canonical site host for admin redirects. Originals, motion components and WebP previews stay in a private S3 bucket. Pending uploads expire after one day.

Aurora DSQL is the serverless SQL database, with no always-running PostgreSQL server, VPC or NAT gateway. The region is `eu-central-1`. It is selected to meet the SQLAlchemy requirement with usage-based billing; free allowances are not a guarantee of a zero bill. S3 storage/requests, downloads, SES, CloudFront, API Gateway, Lambda, ECR and logs can incur charges. Set an AWS Budget; see https://aws.amazon.com/rds/aurora/dsql/pricing/ for current database allowances. Production resources are retained/protected from accidental removal.

The Lambda runtime role has:

- `dsql:DbConnect` only for its database, mapped to `wedding_app`. SQL grants allow reads/inserts/updates and deletion of editable invitation messages. No schema administration is granted.
- Object access only to its bucket's `pending/`, `originals/` and `previews/` prefixes; deletion only in `pending/`.
- `ses:SendEmail` and `ses:SendRawEmail` only for the configured identity ARN, restricted by `ses:FromAddress`.
- Log writes only to its own log group, retained seven days.

Migrations and admin-account provisioning use a separate trusted operator/deployment role with `dsql:DbConnectAdmin`. Guest invitation tokens never grant SQLAdmin access.

## One-time owner setup

Follow [the complete first-publication guide](PUBLISH.md) for registration, GitHub configuration before the first push, AWS OIDC, SST DNS bootstrap, registrar delegation, SES approval, encryption-key setup and first deployment.

Set `SITE_DOMAIN=example.com` in the GitHub `production` environment. The `setup-dns` operation creates the public hosted zone and SES verification/DKIM/DMARC records in the protected `production-dns` SST stage. After delegation, `deploy` creates the application in the separate protected `production` stage. SST creates a free non-exportable ACM certificate, validation records, CloudFront aliases and the `www` redirect. HTTP redirects to HTTPS. Keep both stages and their resource names stable.

`EMAIL_FROM` must belong to this domain unless you explicitly set `SES_IDENTITY_ARN` for a different verified sender. No SES ARN variable is needed for the managed domain identity. The runtime role retains its scoped SES permissions. Mailbox hosting and SES production-access approval are separate from DNS setup.

## Release

For deployment choose **Release to AWS → Run workflow**, select `main`, operation `deploy`, and type `deploy`. The workflow checks the owner identity, runs the full CI workflow, then enters the protected environment before obtaining AWS credentials. It builds/pushes the Lambda image, deploys SST, runs Alembic and grants the runtime SQL role, then checks the deployed API/admin routes. There can be a short period before first-run migrations complete during which database routes are unavailable.

Approve the production environment review when prompted. Pushing code alone never deploys. For a local infrastructure preview (requires configured AWS credentials and the same domain/email variables):

```sh
npx sst diff --stage production
```

The repository can be checked without AWS access using `npx sst install && npx tsc -p tsconfig.infra.json`; this is a type check, not an AWS plan. Do not run `sst remove` against production. Take backups before future schema changes; code rollback does not automatically roll back migrations.

## First administrator

After deployment, get `databaseHost` from `.sst/outputs.json`. Use an authorized operator role and the production encryption key/site URL:

```sh
export AWS_REGION=eu-central-1
export DSQL_HOST='your-cluster.dsql.eu-central-1.on.aws'
export DB_USER=admin
# Set INVITE_ENCRYPTION_KEY and SITE_URL securely in this terminal.
uv run --frozen --package wedding-api python -m app.manage admin-user --username andrea
```

The command prompts for a password of at least 14 characters. Sign in at `https://your-site/admin`. It is safe to rerun to reset credentials; never put the password in shell arguments. Verify actual inbox receipt, a saved RSVP, admin media approval, and the original-byte download before inviting guests.

## Offline release configuration check

Before authorizing a release, set `STAGE=production`, `AWS_ACCOUNT_ID`, `AWS_DEPLOY_ROLE_ARN`, `SITE_DOMAIN`, and `EMAIL_FROM` in your local environment (optionally set `SES_IDENTITY_ARN` to override the managed identity, and `RSVP_NOTIFICATION_EMAIL` for response notifications), then run:

```sh
node scripts/validate_release_config.mjs
```

This check validates required values and account/region consistency without contacting AWS or printing configured values. The release workflow runs it before requesting AWS credentials. It does not verify SES identity status, IAM permissions, SST secrets, or deployed behavior; those require the explicitly approved production deployment. Configure the same values in the GitHub `production` environment (the workflow supplies `STAGE` automatically).
