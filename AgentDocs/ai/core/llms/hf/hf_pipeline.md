## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **HFPipelineMixin** | [src/ai/core/llms/hf/hf_pipeline.py](/AgentDocs/ai/core/llms/hf/hf_pipeline.md) |

The `HFPipelineMixin` is a utility class designed to bridge the gap between raw chat histories and the specific input requirements of Hugging Face (HF) based Large Language Models. Its primary responsibility is to sanitize conversation data, ensuring that message roles (e.g., 'user', 'assistant', 'system') alternate correctly to prevent errors during model inference.

This component functions as a mixin within the LLM orchestration layer. It provides specialized data transformation logic that can be integrated into classes inheriting from [BaseModel](/AgentDocs/ai/core/llms/base_llm.md), specifically targeting pipelines that utilize Hugging Face tokenizers and chat templates.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `HFPipelineMixin` | Class | A mixin providing methods for cleaning chat history and preparing input tensors for HF tokenizers. |

## 3. Implementation Details & Side Effects
- **Core Logic:**
    - **Role Alternation (`_ensure_alternating_roles`):** Iterates through a list of message dictionaries. If consecutive messages share the same role, their content is concatenated with a newline separator. System messages are extracted and prioritized at the start of the sequence.
    - **Input Preparation (`_prepare_input`):** 
        - If a `system_prompt` is defined on the host object but missing from the message list, it is prepended.
        - It attempts to use the `tokenizer.apply_chat_template` method if available.
        - As a fallback, it performs manual string formatting using a predefined schema: `System:`, `