# TASK: FULL RELEASE WITH GIT FLOW (EVERYTHING EXCEPT PUSH)

**OBJECTIVE:**
Cut a new release of this repository locally, following the project's git-flow conventions:
work out the version, start the release branch, bump the version, update `CHANGELOG.md`, commit,
finish the release (merge into `master`, tag, merge back into `develop`), and verify the result.
**Never push.** The user pushes themselves.

**HOW TO RUN COMMANDS:**
- Run every git command non-interactively. Prefix commands that might open an editor with
  `GIT_EDITOR=true GIT_MERGE_AUTOEDIT=no`.
- Run one command per step and check its output before moving on. If a command fails, stop and
  report the exact error. Do not improvise a workaround that rewrites history.

---

## 1. Preflight checks (read-only)
Run these and stop with a clear report if any check fails:
- `git rev-parse --abbrev-ref HEAD` must print `develop`.
- `git status --porcelain` must print nothing (clean working tree).
- `git flow version` must work (git-flow is installed).
- `git branch --list 'release/*'` must print nothing (no release already in progress).
- `git log --oneline master..develop` must list at least one commit (there is something to release).

## 2. Find the previous release
- Get the last release tag with `git describe --tags --abbrev=0 master`.
  Do **not** use `git tag --sort=-v:refname`: an old tag named `v330` sorts above the real ones.
- Read the current version from the `version = "..."` line of `pyproject.toml`. It should match
  the tag without the `v`. If they differ, mention it in your report but continue with the tag.

## 3. Collect the commits for this release
- List them with `git log --no-merges --format="%s" <previous_tag>..develop`.
- Leave out commits whose subject starts with `Merge`.
- Copy the subjects exactly as written. Do not reword, merge, translate or invent entries.

## 4. Work out the new version (Semantic Versioning)
From the subjects collected in step 3:
- Any subject containing `BREAKING CHANGE` or a `!` before the colon (e.g. `feat!:`) → **major** bump.
- Otherwise, any subject starting with `feat` → **minor** bump (e.g. `3.8.1` → `3.9.0`).
- Otherwise → **patch** bump (e.g. `3.8.1` → `3.8.2`).
If the user's message names a version, use that one instead.

## 5. Checkpoint: confirm with the user
Before changing anything, hand control back to the user with a short summary:
- the previous tag and the new version (and why: major/minor/patch);
- the CHANGELOG block you are going to add (see step 7 for the format);
- the list of steps you will run next (6 to 10).
Wait for the user to confirm. If the user's original message already says to go ahead without
confirming, skip this checkpoint.

## 6. Start the release branch
- `git flow release start v<X.Y.Z>`
- Check that `git rev-parse --abbrev-ref HEAD` now prints `release/v<X.Y.Z>`.

## 7. Bump the version and update the changelog
Edit files with the patch/edit tool, changing only the lines involved. Do not rewrite whole files.

**`pyproject.toml`:** change only the `version = "..."` line to `version = "<X.Y.Z>"`.

**`CHANGELOG.md`:** insert the new block right after the `# Changelog` line and its blank line,
above the previous release. Get today's date with `date +%F`. Match the existing format exactly.
The headings have **two spaces** after `###`. Leave out any group that has no entries. Keep the
`Features`, `Bug Fixes`, `Maintenance` order:

```
## [v<X.Y.Z>] - <YYYY-MM-DD>

###  Features
- <subjects starting with feat>

###  Bug Fixes
- <subjects starting with fix>

###  Maintenance
- <every other subject>
- chore(release): Bump version to <X.Y.Z>

```

The last Maintenance entry is always `- chore(release): Bump version to <X.Y.Z>`, like in the
previous releases. Read the top of `CHANGELOG.md` after editing to check the result.

## 8. Commit the release changes
- `git add pyproject.toml CHANGELOG.md`
- `git commit -m "chore(release): Bump version to <X.Y.Z> and update CHANGELOG"`
- No other files may be part of this commit. Check with `git show --stat HEAD`.

## 9. Finish the release
- `GIT_EDITOR=true GIT_MERGE_AUTOEDIT=no git flow release finish -m "v<X.Y.Z>" v<X.Y.Z>`
- git-flow writes the tag message twice (`v<X.Y.Z> v<X.Y.Z>`). Fix it while the tag is still local:
  1. Check that `git rev-parse "v<X.Y.Z>^{commit}"` and `git rev-parse master` print the same hash.
  2. `git tag -f -a v<X.Y.Z> -m "v<X.Y.Z>" master`
- The release branch is deleted by git-flow, and you end up on `develop`.

## 10. Verify
Run these and include their output in the report:
- `git rev-parse --abbrev-ref HEAD` → `develop`
- `git status --porcelain` → empty
- `git tag -n1 v<X.Y.Z>` → exactly `v<X.Y.Z>          v<X.Y.Z>` (the message once)
- `git log --oneline -3 master`
- `git log --oneline -3 develop`
- `git show master:pyproject.toml | grep '^version'` → `version = "<X.Y.Z>"`
- `git branch --list 'release/*'` → empty

## 11. Report
Finish with a short report: the version released, the CHANGELOG block, the verification results,
and the commands the user should run to publish (do **not** run them):

```
git push origin master --follow-tags
git push origin develop
```

---

**CONSTRAINTS:**
- **NO PUSH:** never run `git push`, and never touch remotes (`git remote`, `git fetch --prune`, etc.).
- **NO HISTORY REWRITES:** no `reset --hard`, `rebase`, `commit --amend`, or `push --force`. The only
  forced operation allowed is the `git tag -f` in step 9, on the tag you just created.
- **NO EXTRA CHANGES:** only `pyproject.toml` and `CHANGELOG.md` change. Do not run formatters, do
  not edit other files, do not fix anything you notice along the way (mention it in the report instead).
- **DATA INTEGRITY:** CHANGELOG entries come only from the commit subjects in step 3.
- **ON FAILURE:** stop, show the failing command and its output, and say which state the repository
  is in (for example "on release/v3.9.0, changes not committed"). Do not try to undo things on your own.
