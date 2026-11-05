# TASK: AUTOMATED RELEASE PREPARATION (VERSION & CHANGELOG)

**OBJECTIVE:**
Automate the version bumping and changelog generation for the upcoming release. Modify project configurations and documentation using patch operations based on the current Git state.

**PREREQUISITES:**
The working directory is already on the target release branch (e.g., `release/v[NEW_VERSION]`). All code changes for this release are already committed to this branch.

---

## 1. Resolve Target Version
- Parse the branch name to determine the target release version (e.g., extract `1.2.0` from `release/v1.2.0`). 
- If the branch name does not specify a version, calculate the next Semantic Version (Major, Minor, or Patch) based on the commit history since the last Git tag.

## 2. Patch Version Configurations
- Scan the repository for standard package manifests (`package.json`, `pyproject.toml`, `Cargo.toml`, `.csproj`, etc.).
- Update the version string in these files to match the target version.
- **PATCH REQUIREMENT:** You must use an edit, patch, or line-replacement tool to modify only the specific lines containing the version. Do not use full-file write tools.

## 3. Generate or Update Changelog
- Locate `CHANGELOG.md` in the project root. If it does not exist, initialize it.
- Parse the commit messages and diffs added since the previous release tag.
- Draft a new release block with the header format: `## [vX.Y.Z] - YYYY-MM-DD`.
- Group the parsed commits into standard categories:
  - `### ✨ Features`
  - `### 🐛 Bug Fixes`
  - `### 🔧 Maintenance`
  - `### ⚠️ Breaking Changes`
- **PATCH REQUIREMENT:** You must use an edit or line-insertion tool to prepend this new block at the top of the historical entries in `CHANGELOG.md`. Do not read and rewrite the entire file from scratch.

---

**EXECUTION CONSTRAINTS:**
- **TOOLING EFFICIENCY:** Always prioritize non-destructive editing/patching tools over full-file overwrites. 
- **SCOPE LIMIT:** Do not execute Git commands that alter the working tree state (no `checkout`, `branch`, or `commit`). Do not attempt to run test suites. 
- **DATA INTEGRITY:** Changelog entries must strictly reflect the actual Git commit history. Do not hallucinate features, embellish notes, or invent changes.