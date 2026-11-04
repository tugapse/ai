## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **HFPipelineMixin** | [src/ai/core/llms/hf/hf_pipeline.py](/src/ai/core/llms/hf/hf_pipeline.py) |

The `HFPipelineMixin` is a utility class designed to standardize the preparation of conversation histories and input tensors for Large Language Models (LLMs) utilizing the Hugging Face ecosystem. It addresses the common requirement of ensuring that chat histories conform to specific role-alternation patterns required by many transformer-based models.

This component serves as a middleware layer within the LLM pipeline architecture. It sits between the raw conversation management and the actual model inference, ensuring that data is cleaned, system prompts are correctly injected, and tokenization is handled either through optimized chat templates or manual string formatting.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `HFPipelineMixin` | Class | A mixin providing `_ensure_alternating_roles` and `_prepare_input` methods for HF-based LLM implementations. |

## 3. Implementation Details & Side Effects
- **Core Logic:**
    - **Role Alternation:** The `_ensure_alternating_roles` method iterates through a list of message dictionaries. If consecutive messages share the same role (e.g., two consecutive 'user' messages), it merges their content into a single entry separated by a newline. It treats 'system' messages as a priority group to be placed at the start of the sequence.
    - **Input Preparation:** The `_prepare_input` method handles the conversion of message lists into PyTorch tensors. It first checks for the existence of a `system_prompt` and injects it if missing. It then attempts to use the tokenizer's `apply_chat_template` method. If that is unavailable, it falls back to a manual string formatting pattern: `System: ...`, `