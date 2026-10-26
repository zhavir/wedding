# Production updates and initial setup

The website is already released in production. The first-publication instructions below are reference material for a separate, new installation, not steps to repeat on the live site.

## Updating the existing production site

For the SES-to-Resend change, first complete [the production email migration checklist](EMAIL.md). It adds the new SST `ResendApiKey` secret and sender DNS verification; do not recreate the existing application secrets.

1. For website photos, follow [the exact S3 filenames and destinations](ASSETS.md). S3-backed editorial pictures do not need an application release. Bundled pictures, translations, styling and code do.
2. Validate changes locally using the commands in [README](../README.md). Review pending migrations and the deployment diff against the existing production stage. Preserve the deployed migration history; never stamp, reset or recreate a production database to resolve an upgrade error.
3. Preserve `SITE_DOMAIN`, the existing `production` and `production-dns` stages, `InviteEncryptionKey`, administrator credentials, and bucket identities. Do not rerun initial secret creation, registrar delegation or repository creation for an ordinary update.
4. Merge reviewed changes through the existing repository process, then run **Release to AWS → deploy** from `main` with the workflow's confirmation. The existing release workflow applies migrations. Do not run a production deployment merely to preview local changes.
5. Verify the published page, guest sign-in, RSVP saving and notifications, both Gallery checkboxes and guest targeting, plus upload/download and email delivery using accounts you control. Check that existing invitation links still work.

For an interrupted migration or duplicate-email failure, follow [migration recovery](MIGRATIONS.md). Choose which existing invitation owns a conflicting email; do not silently merge guests or reset live data. A code rollback does not reverse a forward-only database migration.

## Initial setup reference


All `example.com` addresses in this guide are placeholders. Store deployment identifiers, domains, sender addresses and host details under **GitHub Settings → Environments → production → Environment secrets**. The workflow uses `${{ secrets.SITE_DOMAIN }}` and the other secrets below. GitHub Variables are not automatically masked. Public DNS and the published website remain discoverable.

Only for a new installation: follow the remaining sections in order, starting with an empty repository and the intended AWS account. Domain names are case-insensitive; `EXAMPLE.COM` is normalized to `example.com`.

## 1. Register the domain and prepare AWS

1. Buy/register `example.com` with your chosen registrar, if you have not already. Compare **renewal** prices, not just first-year offers. Domain registration is separate from hosting. SST does not purchase the domain or change registrar account settings.
2. Enable MFA on the AWS root user and your administrator. Use your existing administrator/service identity for initial setup and local operator commands. Do not copy its access keys into GitHub.
3. In AWS Billing, create a monthly cost budget with email alerts, for example $5 and $10 thresholds. Alerts do not cap spending.
4. Use **Europe (Frankfurt), `eu-central-1`** for the application. Resend sending is configured separately. SST automatically creates CloudFront certificates in **US East (N. Virginia), `us-east-1`**, as CloudFront requires.
5. Do not manually create a Route 53 hosted zone, certificate, S3 website, database, or Lambda. SST creates these. If your registrar is Route 53 and it created a zone during registration, remove that *unused* zone before bootstrap (only if it has no services/records you need). Never delete an active zone. An existing active zone needs a deliberate import/migration before following this fresh-account guide.

## 2. Configure GitHub before the first push

The checked-in release workflow currently supports a **personally owned repository**: only `github.repository_owner` can dispatch a release, from `main`. Organization-owned repositories need an explicit authorized-actor policy adjustment first.

1. Open repository **Settings → Actions → General**. Enable Actions and permit the actions used by the workflows. Keep default workflow token permissions **Read repository contents and packages**; leave permission to create/approve pull requests disabled.
2. Open **Settings → Environments → New environment**, create `production`. Under deployment branches/tags, select a rule for branch `main` only. If GitHub requires the branch to exist first, finish this restriction immediately after the first push, before running a release. For a single maintainer, do not enable a required-reviewer policy that prevents you approving your own deployment. Manual dispatch still requires typing `deploy`.
3. Under **Settings → Secrets and variables → Actions → Secrets**, add repository secret `GH_TOKEN`: a fine-grained PAT for this repository with **Administration: read/write** and Metadata read. This is only for ruleset synchronization; it is not an AWS credential.
4. Under the adjacent **Variables** tab, add repository variable `RELEASE_APP_ID`: the numeric App ID of your authorized release GitHub App (not its installation ID). If you have no such app, create one under your GitHub developer settings, restrict installation to your account and install it on this repository. No App private key is used by the current workflows; this ID only configures its ruleset bypass. The manual release runs as you using OIDC. See [GitHub setup](GITHUB.md) for repository protection details.
5. Set these **environment secrets** under **Settings → Environments → production → Environment secrets**. The role ARN comes from the next section; complete it before release.

| Name | Value | Required when |
| --- | --- | --- |
| `SITE_DOMAIN` | `example.com` | Both operations |
| `AWS_ACCOUNT_ID` | Your 12-digit AWS account ID | Both operations |
| `AWS_DEPLOY_ROLE_ARN` | `arn:aws:iam::YOUR_ACCOUNT_ID:role/wedding-github-deploy` | Both operations |
| `ADMIN_USERNAME` | Website administrator username (3–100 letters, digits, or `_.@+-`) | Website deployment |
| `EMAIL_FROM` | `wedding@example.com` | Website deployment |
| `WEDDING_GROOM_NAME` | Groom display name | Website deployment |
| `WEDDING_GROOM_EMAIL` | Groom email address | Website deployment |
| `WEDDING_BRIDE_NAME` | Bride display name | Website deployment |
| `WEDDING_BRIDE_EMAIL` | Bride email address | Website deployment |
| `RSVP_NOTIFICATION_EMAIL` | An existing inbox you read | Optional |

There are **no AWS access-key secrets**, certificate secrets, or application-key secrets to add in GitHub. The workflow supplies `STAGE`, AWS region, and the Git commit SHA. The invitation encryption key lives in SST, configured in step 6.

## 3. Let GitHub authenticate to AWS with OIDC

1. In **IAM → Identity providers → Add provider**, choose OpenID Connect. Provider URL: `https://token.actions.githubusercontent.com`; Audience: `sts.amazonaws.com`. Reuse it if it already exists.
2. In **IAM → Roles → Create role**, choose Web identity, select that provider and audience, and name the role `wedding-github-deploy`.
3. Set its trust relationship to the following, replacing `YOUR_ACCOUNT_ID`, `OWNER`, and `REPOSITORY`. This example uses GitHub's traditional subject format. Check your repository/organization OIDC subject configuration: if it uses immutable owner/repository IDs or a customized subject, use the **exact subject for this repository and the `production` environment**, not the example. See [GitHub's AWS OIDC instructions](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws).

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::YOUR_ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
        "token.actions.githubusercontent.com:sub": "repo:OWNER/REPOSITORY:environment:production"
      }
    }
  }]
}
```

4. For a straightforward initial deployment in a **dedicated wedding AWS account**, attach AWS managed `AdministratorAccess` to this deployment role. This grants infrastructure automation full account control, including creation of runtime IAM roles; only trusted code on protected `main` should be deployed. This is an infrastructure role, never the application's role. If this account hosts other workloads, use an administrator-reviewed scoped deployment policy instead. It must cover SST bootstrap/state (S3/SSM and associated resources), Route 53, ACM in `us-east-1`, SES identities, CloudFront, API Gateway, Lambda, EventBridge Scheduler, ECR, DSQL including `dsql:DbConnectAdmin`, CloudWatch Logs and IAM role/policy management with `iam:PassRole`. [SST credential guidance](https://sst.dev/docs/iam-credentials/) explains the bootstrap permissions. Tighten the deployment policy after reviewing actual resource ARNs and CloudTrail activity.
5. Copy the role ARN to GitHub's `production` secret `AWS_DEPLOY_ROLE_ARN`. Your existing IAM service account is for local administration; GitHub assumes this new role without a stored password or access key.

## 4. Push the code

Before committing, review `git status` and ensure no `.env`, AWS credential files, `.sst`, database dumps or invitation data are included. Keep the checked-in examples. Check `.github/CODEOWNERS` names match your GitHub account.

From the project directory, if the repository has no commit yet:

```sh
git add .
git commit -m "Add wedding website and AWS deployment"
git branch -M main
git remote -v
# Only if origin is not configured:
git remote add origin https://github.com/OWNER/REPOSITORY.git
git push -u origin main
```

The first push can run repository-setup workflows, which is why `GH_TOKEN` and `RELEASE_APP_ID` should be configured beforehand. It **does not deploy AWS**. Run **Pull request checks** and confirm **Pre-commit** and **All tests** pass; inspect **Synchronize repository rulesets** and **Setup issue templates**. Fix failures before continuing. Workflows appear in the Actions UI after they exist on the default branch.

## 5. Create DNS with SST, then delegate the domain

Before running `setup-dns`, add the domain in Resend and set `ResendDkim`, `ResendRsend` and `ResendSend` in SST stage `production-dns`, using the interactive commands in [email setup](EMAIL.md#dns-values-stored-as-aws-backed-sst-secrets).

1. Open **Actions → Release to AWS → Run workflow**. Choose branch `main`, operation `setup-dns`, and enter `deploy` in the approval field. Approve any configured environment review.
2. This runs checks, then deploys the protected SST stage `production-dns`. It creates one public Route 53 zone, the secret-backed Resend DKIM TXT and `rsend`/`send` CNAME records, and the retained SES identity/verification/DKIM and monitoring-mode DMARC resources. It does not create the application or wait for DNS verification.
3. Open the AWS Route 53 console with your operator account, select the hosted zone for your domain, and copy all four NS record values. Deployment outputs are deliberately withheld from public job summaries.
4. At your domain registrar, change the domain's **authoritative nameservers** to those four values. If registered with Route 53, change them under **Registered domains**, not just the hosted zone's NS record. This one manual step proves control of the domain; SST cannot change an unrelated registrar account.
5. Wait for delegation to propagate, potentially up to 48 hours. Check with `nslookup -type=NS example.com` (Windows/macOS/Linux where installed), or `dig NS example.com`. The public result must match the SST output. Existing DNSSEC/DS records from a previous provider must be removed or correctly migrated to avoid `SERVFAIL`.
6. Verify the SST-managed DNS records in Resend and wait for verification, following [the email setup guide](EMAIL.md). Existing SES records remain managed for compatibility but are not used for production delivery. Do not remove certificate validation or mailbox records.
7. Create a domain-scoped Resend sending API key and store it in SST as described below. There is no AWS SES production-access request.

If DNS setup is rerun, it updates the same DNS stage. It cannot remove the separate application stage. Do not change `SITE_DOMAIN` casually after publication: DNS migration and old invitation URLs need deliberate handling.

## 6. Set the application secrets once

Install Node at the version in `.node-version`, npm, AWS CLI v2, and [uv](https://docs.astral.sh/uv/getting-started/installation/). Use an operator terminal with your AWS administrator/service profile, in this project directory. Configure that profile with `aws configure --profile wedding-admin` if using your existing service account's keys, or use your organization's SSO profile. Keep credentials local.

Linux/macOS:

```sh
export AWS_PROFILE=wedding-admin
export AWS_REGION=eu-central-1
```

PowerShell:

```powershell
$env:AWS_PROFILE = "wedding-admin"
$env:AWS_REGION = "eu-central-1"
```

Then, on either platform:

```sh
aws sts get-caller-identity
npm ci
npm --prefix frontend ci
uv sync --frozen --all-packages --all-groups
uv run --frozen --package wedding-api python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
npx sst secret set InviteEncryptionKey --stage production
npx sst secret set AdminPassword --stage production
npx sst secret set ResendApiKey --stage production
```

Check the AWS account ID first. Paste the generated key into the SST prompt and save it in your password manager. Do not paste it into GitHub logs or commit it. Keep it stable for future releases: replacing it invalidates existing encrypted invitation credentials. This command sets a secret; it does not deploy the app. A local SST diff/deploy also requires the environment variables from step 2, set in that terminal.

Enter a separate password of 14–1024 characters at the `AdminPassword` prompt and save it in your password manager. SST uses it only to create a missing administrator; redeployment never resets an existing account. The username comes from the `ADMIN_USERNAME` GitHub environment secret.

Paste the dedicated Resend sending key at the `ResendApiKey` prompt. See [email setup](EMAIL.md) for domain verification and sender configuration.

## 7. Publish the HTTPS site

1. Run **Release to AWS** again with operation `deploy`, branch `main`, approval `deploy`.
2. SST finds the public zone for `SITE_DOMAIN`, creates the CloudFront certificate with DNS validation, HTTPS routing and DNS aliases. Both the apex domain and `www` receive certificates; `www` redirects to the apex. HTTP requests redirect to HTTPS. Leave DNS validation records in place for automatic certificate renewal.
3. The workflow builds the frontend and Lambda container, deploys resources, applies database migrations/grants, then checks API health and the admin login page. Allow time for certificate issuance and CloudFront propagation. If the certificate waits for validation, fix delegation/CAA restrictions before rerunning. If a new account's Lambda concurrency quota is too low for the configured reservation, request an increase in Service Quotas before retrying.
4. Deployment outputs are deliberately withheld from the public job summary. Open `https://example.com`. Check `http://example.com` and `https://www.example.com` redirect correctly and the browser reports a trusted certificate.

## 8. Sign in and verify guest flows

SST has already run migrations, granted the runtime database role, and created the administrator if missing. No local database connection or manual SQL is needed. Open `https://example.com/admin`, sign in using `ADMIN_USERNAME` and the initial password stored as `AdminPassword`, and configure MFA as described in [administration](ADMIN.md). Existing accounts retain their current password and MFA.

The release does not check provider delivery. Follow [the Resend smoke test](EMAIL.md) using an inbox you control. Verify receipt, invitation login, RSVP confirmation/calendar, organiser notifications, photo upload/moderation and original download before inviting guests. A successful health endpoint alone does not prove these flows.

Future updates: push/merge reviewed changes and run operation `deploy` again. DNS setup and secret creation are one-time tasks. Both production stages retain/protect resources; do not use `sst remove` as a routine rollback. Retained resources continue billing until deliberately removed.

## Costs and HTTPS

Use the **non-exportable ACM public certificate** that SST provisions for CloudFront: it has [no certificate fee](https://aws.amazon.com/certificate-manager/pricing/) and managed renewal. A self-signed certificate would produce browser trust errors and saves no certificate cost here. Do not create an ACM Private CA or request an exportable certificate for this site.

One [Route 53 public hosted zone costs $0.50/month](https://aws.amazon.com/route53/pricing/) for the first 25 zones; CloudFront alias A/AAAA queries are free. Other DNS queries may cost a small amount. Domain registration/renewal, S3 storage/downloads, CloudFront, Lambda, API Gateway, Resend, ECR, logs and Aurora DSQL are separate usage charges. There is no always-on VM, load balancer, NAT gateway or database server in this architecture. Free-tier eligibility and media traffic affect the final bill; this is not a zero-cost guarantee.

## Public repository privacy

For existing setups, copy each deployment variable to a production environment secret with the same name, add the four host secrets above, then remove the old variables. The workflow intentionally has no variable fallback. Do this before the next release. Host secrets seed fresh databases only; update existing invitations through the admin UI.

For temporary troubleshooting, enable `debug_deploy` when dispatching **Release to AWS**. This forwards deployment and routing output, skips generated-output masking, and includes bootstrap exception details in CloudWatch and the SST failure. GitHub automatic secret masking still applies. Leave the checkbox off on the next deployment to restore suppression; the bootstrap debug setting persists until that deployment updates the function. Clean up diagnostic logs in both GitHub Actions and CloudWatch afterward.

With `debug_deploy` disabled (the default), deployment, database migration and routing checks suppress both stdout and stderr, including on failure. Generated SST outputs are registered for masking before downstream steps, are never published as summaries/artifacts, and `.sst` is removed at the end of the job. Failures retain a failing status but only show a generic message. Diagnose privately with an authorized local terminal or the AWS console; do not enable Actions step/runner debug logging for production or upload deployment logs as public artifacts.

These changes affect future runs and the current source tree. Previously committed personal data remains in Git history and copies/forks. Existing Actions logs and summaries require separate deletion; coordinate any history rewrite with collaborators. Rotate exposed credentials if any were published. ARNs and account IDs identify resources but do not grant access by themselves. Public DNS, certificates and browser-delivered site content cannot be made confidential by workflow masking. Review frontend and backend locale files, images, Git author metadata and historical artifacts before publishing if those details should be private.
