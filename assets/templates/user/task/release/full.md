# TASK: FULL RELEASE WITH GIT FLOW (EVERYTHING EXCEPT PUSH)

**OBJECTIVE:**
Cut a new release of the repository in the current folder, locally: work out the version, start a
release branch, bump the version, update the changelog, commit, finish the release (merge into the
production branch, tag, merge back into the development branch) and verify the result.
**Never push.** The user pushes themselves.

This task works on any project. Do not assume a language, a version file or a changelog format:
**discover the project's conventions first and follow them.** When the project has no convention for
something, use the defaults given below.

**PLACEHOLDERS:**
Words in curly braces, like `{production}`, `{development}`, `{tag}` or `{X.Y.Z}`, are placeholders.
Replace the whole placeholder, **braces included**, with the real value before running a command.
Example: with `{previous_tag}` = `v1.4.2` and `{development}` = `develop`,
`git log --no-merges --format="%s" {previous_tag}..{development}` becomes
`git log --no-merges --format="%s" v1.4.2..develop`.
Never send a command that still contains `{`, `}`, `<` or `>` from a placeholder.

**HOW TO RUN COMMANDS:**
- Run every git command non-interactively. Prefix commands that might open an editor with
  `GIT_EDITOR=true GIT_MERGE_AUTOEDIT=no`.
- Run one command per step and check its output before moving on. If a command fails, read its
  `stderr`, fix the cause (usually a placeholder left in the command or a wrong name) and try once
  more. Never resend the exact same failing command. If it still fails, stop and report the exact
  error. Do not improvise a workaround that rewrites history.

---

## 1. Discover the repository's conventions (read-only)

**Branches and tag prefix:**
- Production branch: `git config gitflow.branch.master`. If it is empty, use `main` if it exists
  (`git rev-parse --verify --quiet main`), otherwise `master`.
- Development branch: `git config gitflow.branch.develop`. If it is empty, use `develop`.
- Tag prefix: `git config gitflow.prefix.versiontag`. If that is empty, look at the existing tags
  (`git tag --merged {production}`). If they look like `v1.2.3`, the prefix is `v`. If they look like
  `1.2.3`, there is no prefix. With no tags at all, use `v`.
- Whether git-flow is usable: `git flow version` works **and** `git config gitflow.branch.develop`
  is set. If not, use the plain git fallback described in steps 6 and 9.

**Version files:** look in the repository root (and, for monorepos, mention any others you find)
for the files that hold the project version, for example:
`pyproject.toml`, `setup.py`, `setup.cfg`, `package.json` (+ `package-lock.json`), `Cargo.toml`,
`*.csproj`, `pom.xml`, `build.gradle(.kts)`, `pubspec.yaml`, `composer.json`, `VERSION`,
`version.txt`, `__version__ = "..."` in a package `__init__.py`.
Use `git grep -n -F "{current version}"` to find the places that hold the current version string,
and update only those that clearly are the project version (not dependency versions).

**Changelog:** look for `CHANGELOG.md` (or `changelog.md`, `CHANGES.md`, `HISTORY.md`). If it
exists, read its top two release blocks. Note the exact heading style (e.g. `## [v1.2.0] - 2026-01-31`,
`## 1.2.0 (2026-01-31)`), the group headings (their exact text, spacing and any emoji), and how
entries are written. If there is no changelog, you will create `CHANGELOG.md` with the default
format from step 7.

**Release commit message:** look at the previous release commits with
`git log --no-merges --format="%s" -5 --grep="release" {production}`. If they follow a pattern
(e.g. `chore(release): Bump version to 1.2.0 and update CHANGELOG`), use that same pattern.
Otherwise use the default `chore(release): Bump version to {X.Y.Z} and update CHANGELOG`.

## 2. Preflight checks (read-only)
Run each command and compare its output with the expected result. All four must pass. If one does
not, stop and report which one.

| Command | Expected result | Means |
|---------|-----------------|-------|
| `git rev-parse --abbrev-ref HEAD` | exactly `{development}` (e.g. `develop`) | releases start **from** the development branch: being on it is correct |
| `git status --porcelain` | empty output | clean working tree |
| `git branch --list 'release/*'` | empty output | no release already in progress |
| `git log --oneline {production}..{development}` | at least one line | there is something to release |

## 3. Find the previous release and the commits since
- Previous release tag: `git describe --tags --abbrev=0 {production}`.
  Do not pick it by sorting tag names: stray or badly named tags can sort above the real ones.
  If there is no tag at all, this is the first release: the commits are the whole history.
- Current version: read it from the main version file. If it differs from the tag, mention it in
  the report and continue from the tag.
- Commits: `git log --no-merges --format="%s" {previous_tag}..{development}`
  (or `git log --no-merges --format="%s" {development}` for a first release).
  Leave out subjects that start with `Merge`. Copy the subjects exactly as written: do not reword,
  translate, merge or invent entries.

## 4. Work out the new version (Semantic Versioning)
- Any subject with `BREAKING CHANGE` or a `!` before the colon (e.g. `feat!:`) → **major** bump.
- Otherwise, any subject starting with `feat` → **minor** bump (`1.4.2` → `1.5.0`).
- Otherwise → **patch** bump (`1.4.2` → `1.4.3`).
- First release with no previous version: use the version already in the version file, or `0.1.0`.
If the user's message names a version, use that one instead. The tag is `{prefix}{X.Y.Z}`.

## 5. Checkpoint: confirm with the user
Before changing anything, hand control back to the user with a short summary. Start it with the
release values, written out in full, because every later step uses them:

```
RELEASE VALUES
production  = master
development = develop
version     = 1.5.0          (X.Y.Z, no prefix)
tag         = v1.5.0         (prefix + version: a VERSION, never a branch name)
release     = release/v1.5.0
git-flow    = yes
commit msg  = chore(release): Bump version to 1.5.0 and update CHANGELOG
```

Then:
- the conventions you found (version files, changelog);
- the previous tag, the new version and why (major/minor/patch);
- the changelog block you are going to add;
- the steps you will run next (6 to 10).
Wait for the user to confirm. If the user's original message already says to go ahead without
confirming, skip this checkpoint.

When the user replies with a confirmation ("yes", "ok", "confirmed", "go ahead", …), the checkpoint
is done: continue with step 6 using the release values you showed, possibly with the corrections the
user gave. Do not show the summary again and do not ask again.

From here on, `{tag}` is always the **tag** from the release values (e.g. `v1.5.0`). It is never
`develop`, `master` or any other branch name. Check each command against the release values before
sending it.

## 6. Start the release branch
- With git-flow: `git flow release start {tag}` (e.g. `git flow release start v1.5.0`)
- Plain git fallback: `git checkout -b release/{tag} {development}`
- Check that `git rev-parse --abbrev-ref HEAD` now prints `release/{tag}`.

## 7. Bump the version and update the changelog
Edit files with the patch/edit tool, changing only the lines involved. Never rewrite whole files.

**Version files:** change only the project version lines found in step 1.
For `package.json`, prefer `npm version {X.Y.Z} --no-git-tag-version` (it also updates
`package-lock.json`). For `Cargo.toml`, also refresh `Cargo.lock` if it is tracked
(`cargo update -p {crate name} --offline`, or mention it in the report if that fails).

**Changelog:** insert the new block above the previous release, with today's date from `date +%F`.
- Read only the **first 40 lines** of the changelog. That is enough to see the format. Do not page
  through the whole file.
- Never use `write_file` on an existing changelog. Use `patch_file` like this:
  - `search` = the heading line of the previous release, exactly as it is in the file
    (e.g. `## [v1.4.2] - 2026-01-31`);
  - `replace` = the new block, a blank line, then that same heading line again.
- If the changelog exists, **copy the format of the previous release blocks exactly**: heading
  style, group names and their order, spacing, emoji, and any extra line they always have (for
  example a final `- chore(release): Bump version to {X.Y.Z}` entry).
- If there is no changelog, create `CHANGELOG.md` with this default format:

```
# Changelog

## [{tag}] - {YYYY-MM-DD}

### Features
- {subjects starting with feat}

### Bug Fixes
- {subjects starting with fix}

### Maintenance
- {every other subject}
```

Group the subjects by their type: `feat` → features, `fix` → bug fixes, everything else (including
subjects without a conventional type) → maintenance. Leave out empty groups.

After editing, read the top of the changelog and compare the new block with the previous release
block, line by line: same heading style, same group headings (spacing included), and the same fixed
lines (if the previous block ends its Maintenance group with `- chore(release): Bump version to …`,
yours must end with `- chore(release): Bump version to {X.Y.Z}`). Fix any difference with patch_file.

## 8. Commit the release changes
- `git add` only the version files and the changelog you changed.
- `git commit -m "{commit msg}"` with the commit message from the release values, e.g.
  `git commit -m "chore(release): Bump version to 1.5.0 and update CHANGELOG"`.
- Check with `git show --stat HEAD` that no other file is part of the commit.

## 9. Finish the release
**With git-flow** (all three sub-steps are part of this step, do not skip 9b and 9c):
- **9a.** `GIT_EDITOR=true GIT_MERGE_AUTOEDIT=no git flow release finish -m "{tag}" {tag}`
  e.g. `GIT_EDITOR=true GIT_MERGE_AUTOEDIT=no git flow release finish -m "v1.5.0" v1.5.0`.
  The `-m "{tag}"` is required: without it the tag cannot be created and the release stops halfway.
- **9b.** Run `git tag -n1 {tag}`. git-flow often writes the message twice (`v1.5.0          v1.5.0 v1.5.0`).
- **9c.** If the message is duplicated, fix it while the tag is still local:
  1. Check that `git rev-parse "{tag}^{commit}"` and `git rev-parse {production}` print the same hash.
  2. `git tag -f -a {tag} -m "{tag}" {production}`
  3. Run `git tag -n1 {tag}` again: the message must now appear once.

**Plain git fallback:**
1. `git checkout {production}`
2. `GIT_MERGE_AUTOEDIT=no git merge --no-ff release/{tag} -m "Merge branch 'release/{tag}'"`
3. `git tag -a {tag} -m "{tag}"`
4. `git checkout {development}`
5. `GIT_MERGE_AUTOEDIT=no git merge --no-ff {tag} -m "Merge tag '{tag}' into {development}"`
6. `git branch -d release/{tag}`

If a merge reports a conflict, stop and report it. Do not resolve conflicts on your own.

## 10. Verify
This step is **mandatory**, even when everything looked fine. You may run it as one command:

```
git rev-parse --abbrev-ref HEAD; git status --porcelain; git tag -n1 {tag}; git describe --tags --abbrev=0 {production}; git branch --list 'release/*'; git log --oneline -3 {production}; git log --oneline -3 {development}
```

Plus the version check, e.g. `git show {production}:pyproject.toml | grep -n "{X.Y.Z}"`.
Expected results:
- `git rev-parse --abbrev-ref HEAD` → the development branch
- `git status --porcelain` → empty
- `git tag -n1 {tag}` → the tag message appears once
- `git log --oneline -3 {production}` and `git log --oneline -3 {development}`
- `git describe --tags --abbrev=0 {production}` → `{tag}`
- the version in the main version file on the production branch, e.g.
  `git show {production}:{version file} | grep -n "{X.Y.Z}"`
- `git branch --list 'release/*'` → empty

## 11. Report
You may only write the report **after** running step 10, and the report must quote its output.
The release is done **only if every check in step 10 passed**. If any check failed, or any command in
steps 6 to 9 failed, the report must say the release is NOT complete, which step failed, and the
current state of the repository. Never report success otherwise.

Finish with a short report: the version released, the conventions used, the changelog block, the
verification results, anything odd you noticed (without fixing it), and the commands the user
should run to publish (do **not** run them):

```
git push origin {production} --follow-tags
git push origin {development}
```

---

**CONSTRAINTS:**
- **NO PUSH:** never run `git push`, and never touch remotes (`git remote`, `git fetch --prune`, etc.).
- **NO HISTORY REWRITES:** no `reset --hard`, `rebase`, `commit --amend`, or `push --force`. The only
  forced operation allowed is the `git tag -f` in step 9, on the tag you just created.
- **NO EXTRA CHANGES:** only the version files and the changelog change. Do not run formatters, do
  not edit other files, do not fix anything you notice along the way (mention it in the report instead).
- **DATA INTEGRITY:** changelog entries come only from the commit subjects in step 3.
- **ON FAILURE:** stop, show the failing command and its output, and say which state the repository
  is in (for example "on release/v1.5.0, changes not committed"). Do not try to undo things on your own.
