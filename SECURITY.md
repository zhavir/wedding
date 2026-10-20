# Security

Do not report vulnerabilities, invitation codes, session tokens, guest details or private photo URLs in public issues. Use the repository's GitHub **Security → Report a vulnerability** feature. The repository owner must enable private vulnerability reporting before publication.

Only the current main branch and latest release are maintained. Treat all guest data, originals and exports as private. The MIT license covers the source code, not guests' photographs or third-party placeholder images.

AWS deployments use GitHub OIDC and a protected `production` environment. Do not create long-lived AWS keys for Actions. Never run deployment credentials on pull requests or forks. Review infrastructure changes before release. Report suspected leaked credentials privately and revoke affected invitations/secrets promptly.
