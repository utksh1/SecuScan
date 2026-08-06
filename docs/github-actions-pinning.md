# Pinning GitHub Actions to Commit SHAs

> **Scope:** Every third-party action referenced from the GitHub Actions
> workflows under [`.github/workflows/`](../.github/workflows/) is pinned to an
> immutable commit SHA. This document explains why, and how to keep those pins
> current during normal maintenance.

---

## 1. Why this matters

Workflows reference actions such as `actions/checkout`, `actions/setup-python`,
and `aquasecurity/trivy-action`. Two styles are possible:

```yaml
# Mutable tag — can be retargeted by the action author at any time.
uses: actions/checkout@v4

# Immutable SHA — exactly this commit, forever.
uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4
```

Version tags (`@v4`, `@v5`, `@v0.36.0`) are convenient but **mutable**: the
action author can move a tag to a different commit, silently changing what CI
runs. Pinning to the full 40-character SHA means every workflow execution uses
reviewed, fixed code, which:

- improves reproducibility of CI runs, and
- reduces the supply-chain attack surface from compromised or re-tagged
  upstream actions.

This is the [GitHub-recommended](https://docs.github.com/actions/security-guides/security-hardening-for-github-actions#using-third-party-actions)
approach for third-party actions. The original version tag is kept as a `# vX`
comment so the intended version stays readable next to the SHA.

---

## 2. Current state

All third-party actions in the workflows are pinned to full commit SHAs with
the corresponding version tag kept as an inline comment, for example:

- `actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4`
- `actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 # v5`
- `aquasecurity/trivy-action@a9c7b0f06e461e9d4b4d1711f154ee024b8d7ab8 # v0.36.0`

A quick audit to confirm nothing slipped back to a bare tag:

```bash
git grep -n "@v[0-9]" -- .github
```

This must return no matches. Every `uses:` line in the workflows should carry a
full SHA plus a `# vX` comment.

---

## 3. How to update a pinned action

When you need to move an action to a newer version (or backport a fix):

### 3.1 Resolve the SHA that the new tag points to

```bash
# Replace <owner>/<repo> and <tag> with the real values.
git ls-remote https://github.com/<owner>/<repo>.git refs/tags/<tag>
```

For example, to find the commit behind `actions/checkout` `v4`:

```bash
git ls-remote https://github.com/actions/checkout.git refs/tags/v4
```

The output is the full 40-character commit SHA to use.

> **Note:** always resolve the tag from the upstream repository at update
> time. Never copy a SHA from a third-party source; the `git ls-remote` output
> is authoritative.

### 3.2 Replace the reference in the workflow

Keep the new version as the comment, so the file stays readable:

```yaml
# before
- uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4
# after
- uses: actions/checkout@<new-full-40-char-sha> # v4
```

If the update is also a major version bump, update the comment to match the new
tag (for example `# v5`).

### 3.3 Verify the change

Run a local grep to confirm every `uses:` is still SHA-pinned:

```bash
git grep -n "@v[0-9]" -- .github   # must be empty
git grep -n "uses:" -- .github/workflows | grep -v "# v"
```

Any `uses:` line without a SHA plus comment is a red flag. Optionally validate
the workflow syntax with [`actionlint`](https://github.com/rhysd/actionlint)
and confirm the affected workflow runs green on the PR.

---

## 4. Automated updates via Dependabot

The repository-level [Dependabot configuration](../.github/dependabot.yml)
includes the `github-actions` ecosystem. Dependabot will open PRs that bump
both the SHA and the trailing `# vX` comment together, so the two stay in
sync. Review these PRs like any other dependency update; a maintainer must
approve the merge.

---

## 5. Ownership & review cadence

| Responsibility | Owner |
|---|---|
| Reviewing SHA-pin update PRs and approving merges | **Project maintainers** |
| Proposing action updates (security patches, deprecations) | **Any contributor** may open a PR; a maintainer must review it |
| Automated update proposals | **Dependabot** (weekly schedule, `github-actions` ecosystem) |

| Trigger | Who | Action |
|---|---|---|
| Critical advisory affecting an action in use | Any contributor / maintainer | Update within **24 hours** of disclosure |
| New upstream release of an action in use | Dependabot or any contributor | Update in a PR and link the upstream changelog |
| Quarterly | Maintainer | Full review of all pinned action SHAs and comments |
