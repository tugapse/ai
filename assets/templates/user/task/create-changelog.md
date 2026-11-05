use `git` to identify the current Git branch name for the version designation. Perform a granular analysis of the Git delta between this branch and 'master' by examining both 'git log --pretty=format:"%s - %b"' and 'git diff --stat'.

Your objective is to capture not only high-level features but also 'intermediate' technical developments, such as:
- Logic refactors and performance optimizations.
- Updates to internal APIs or utility functions.
- Dependency shifts and structural directory changes.

Synthesize these into a Markdown changelog ([Added], [Changed], [Fixed], [Removed]). If @ROOT/CHANGELOG.md exists, prepend this new section. If not, initialize the file with a '# Changelog' header. Save the update to the root directory.

Use the Available tools. 