import ai.functions as func
from ai.core.llms.base_llm import BaseModel

class HFPipelineMixin:
    """
    Mixin class providing utility methods for preparing chat history and inputs
    for Hugging Face (HF) based LLM pipelines.

    This class handles data cleaning to ensure alternating message roles,
    and prepares the final input tensor based on the presence of a tokenizer
    and a system prompt.
    """

    def _ensure_alternating_roles(self, messages: list) -> list:
        """
        Cleans the list of messages to ensure that roles alternate sequentially.

        If consecutive messages have the same role (e.g., two 'user' messages in a row),
        their contents are concatenated into a single message entry. System messages
        are preserved at the beginning.

        Args:
            messages: A list of message dictionaries, each expected to have 'role' and 'content'.

        Returns:
            A new list of messages with alternating roles, or the original list if empty.
        """
        if not messages:
            return []

        cleaned_messages = []
        system_messages = [msg for msg in messages if msg["role"] == "system"]
        other_messages = [msg for msg in messages if msg["role"] != "system"]

        if system_messages:
            cleaned_messages.extend(system_messages)

        if not other_messages:
            return cleaned_messages

        current_message = {
            "role": other_messages[0]["role"],
            "content": other_messages[0]["content"],
        }

        for i in range(1, len(other_messages)):
            msg = other_messages[i]
            if msg["role"] == current_message["role"]:
                current_message["content"] += "\n" + msg["content"]
            else:
                cleaned_messages.append(current_message)
                current_message = {"role": msg["role"], "content": msg["content"]}

        cleaned_messages.append(current_message)

        if len(cleaned_messages) < len(messages):
            func.log(f"WARNING: Chat history was cleaned to ensure alternating roles. Original length: {len(messages)}, Cleaned length: {len(cleaned_messages)}. Consider adjusting upstream history management.")

        return cleaned_messages

    def _prepare_input(self, messages: list):
        """
        Prepares the final input tensors for the tokenizer based on the message history.

        It first ensures a system prompt is present if one is defined and missing.
        It prioritizes using tokenizer.apply_chat_template if available; otherwise,
        it manually formats the conversation into a string.

        Args:
            messages: The list of message dictionaries to be tokenized.

        Returns:
            A dictionary containing PyTorch tensors ready for model input.
        """
        if self.system_prompt and not any(m["role"] == "system" for m in messages):
            messages.insert(0, BaseModel.create_message("system", self.system_prompt))
            
        if hasattr(self.tokenizer, "apply_chat_template") and self.tokenizer.apply_chat_template is not None:
            input_string = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            inputs = self.tokenizer(input_string, return_tensors="pt")
            func.debug(f"_prepare_input using apply_chat_template. Input string length: {len(input_string)}")
            return inputs
        else:
            prepared_messages = []
            if self.system_prompt and not any(m["role"] == "system" for m in messages):
                prepared_messages.append(BaseModel.create_message("system", self.system_prompt))

            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                prepared_messages.append(BaseModel.create_message(role, content))

            input_text = ""
            for msg in prepared_messages:
                if msg["role"] == "system":
                    input_text += f"System: {msg['content']}\n"
                elif msg["role"] == "user":
                    input_text += f"User: {msg['content']}\n"
                elif msg["role"] == "assistant":
                    input_text += f"Jarvis Ai: {msg['content']}\n"

            if messages and messages[-1]["role"] == "user":
                input_text += "Jarvis Ai:"

            inputs = self.tokenizer(input_text, return_tensors="pt")
            func.debug(f"_prepare_input using manual formatting. Input text length: {len(input_text)}")
            return inputs