## Module Purpose
This file defines` tags, as well as control characters and partial tags. When a `<think>` tag is detected` tag, it clears the animation line, deactivates the thinking state, and resets internal counters. Tokens outside of active thinking tags are passed` tag, it clears the animation line, deactivates the thinking state, and resets internal counters. Tokens outside of active thinking tags are passed through for display.

## Dependencies
*   `functions` (imported as `func`)
*   `re`
*   `extras.thinking_log_manager.ThinkingLogManager`

## Constants & Environment
*   `SPINNER_CHARS`: `["|", "/", "-", "\\"]`
*   `PROGRESS_BAR_LENGTH`: `5`
*   `THINKING_PREFIX`: `"Thinking"`
*   `MAX_UNTILL\s*")`
*   `CONTROL_CHARS_PATTERN`: `re.compile(r"[\x00-\x09\x0B-\x1F\x7F]")`
*   `PARTIAL_TAG_PATTERN`: `re.compile(r"<th(?:in(?:k>)?|/th(?:ink>)?|i|n|k|/i|/n|/k)?")`