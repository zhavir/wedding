# GitHub repository configuration

This public MIT repository is maintained by its owner and explicitly authorized automation. Public visibility allows forks, but does not grant push or merge access. Keep write/admin access limited to the owner and review installed apps and deploy keys.

For a fresh repository, follow [first publication](PUBLISH.md) in order; it separates settings needed before the first push from workflows run afterward.

## Manual owner setup

1. Disable Discussions in Settings → General. Keep pull requests enabled for the owner review flow; restrict pull request access to collaborators where that setting is available. Otherwise external PRs may be opened, but cannot be merged without write access. Never grant external contributors repository write access.
2. Keep Actions default workflow permissions read-only and disable workflow approval of pull requests. CI uses pull_request, never pull_request_target, with no deployment secrets.
3. Store a fine-grained token scoped to this repository as secret `GH_TOKEN`, with Administration read/write and Metadata read access. Its owner must be a repository administrator. Only ruleset synchronization uses this token.
4. Set repository variable `RELEASE_APP_ID` to the authorized release GitHub App's positive numeric App ID, not its installation ID. Synchronization replaces Integration actor ID 0 in the checked-in rulesets with this value.
5. Run **Pull request checks** and verify **Pre-commit** and **All tests** succeed. Then run **Synchronize repository rulesets** and review Settings → Rules → Rulesets. Administrator bypass permits initial setup.
6. Run **Setup issue templates** to validate forms and create/update labels from `.github/issue-labels.json`. Unrelated labels are retained.
7. Create the production environment restricted to main. Configure production owner review, accounting for GitHub self-review restrictions for single-maintainer repositories. Follow [AWS deployment](DEPLOYMENT.md) for environment secrets and OIDC. Enable secret scanning and push protection where available.

## Rules and workflows

`protect-all-tags.json` prevents deletion and force updates of every tag. `protect-default-branch.json` prevents deletion/force pushes, requires linear history, squash-only pull requests, and the exact checks **Pre-commit** and **All tests**. Repository administrators (role ID 5) and the release app bypass these rules. Access permissions control who can merge; required reviews alone do not enforce owner-only access.

**Synchronize repository rulesets** validates credentials and administrator access before any writes, then creates or updates rulesets by exact name. Only after both updates succeed does it delete the exact retired ruleset `Restrict default branch updates administrators`. Repeated runs are safe; unrelated and organization rulesets are untouched. The workflow runs manually or after its configuration changes on main.

**Pull request checks** replaces the old CI workflow and is reused by **Release to AWS**. It validates formatting, linting, types, tests, migrations, browser flows, and builds without coverage collection. Releases require manual owner dispatch and explicit deployment approval; pushes never deploy.

Implementing these files does not apply remote settings. Run the synchronization workflows only when ready to authorize those changes. No AWS deployment or remote repository mutation was performed during implementation.
