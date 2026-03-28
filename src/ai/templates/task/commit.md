**Task:** Generate a professional Git commit message based **strictly** on the provided `git diff`.

**Constraints:**
1. **Subject Line:**
    * Pattern: `<type>(<scope>): <Description>`
    * Types: `feat`, `fix`, `docs`, `refactor`, `style`, `chore`, `test`, `build`, `ci`, `perf`.
    * Character limit: 72 characters.
    * Format: Imperative mood, capitalized first letter, no trailing period.
2. **Body:**
    * Leave one blank line after the subject.
    * Use bullet points (`-`) to list functional changes.
    * Focus on **what** changed. Only include **why** if it is explicitly evident in the code (e.g., a commented bug fix or a config change).
    * Do not speculate on intent or impact.
    * Wrap lines at 72 characters.
3. **Output:** Provide **ONLY** the raw commit message. Do not include markdown code blocks (```), conversational filler, or explanations.

**Input Diff:**