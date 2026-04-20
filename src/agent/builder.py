import json

from pydantic import BaseModel


class PromptBuilder:
    """Builds LLM prompt strings from structured components (Builder Pattern).

    All methods are stateless and can be called without instantiation.
    Each agent passes its own class-level constants (SYSTEM_PROMPT, RESPONSE_SCHEMA,
    MESSAGE_LABEL) so the builder remains decoupled from the agent hierarchy.
    """

    @staticmethod
    def build_prompt(
        system_prompt: str,
        schema: type[BaseModel] | None,
        message: str,
        message_label: str = "Message",
    ) -> str:
        """Assemble the full prompt: system prompt + schema instructions + user message."""
        parts: list[str] = []

        if system_prompt.strip():
            parts.append(system_prompt.strip())

        schema_instructions = PromptBuilder.build_schema_instructions(schema)
        if schema_instructions:
            parts.append(schema_instructions)

        parts.append(f"{message_label}:\n{message}")
        return "\n\n".join(parts)

    
    @staticmethod
    def build_schema_instructions(schema: type[BaseModel] | None) -> str:
        """Generate JSON schema instructions that tell the LLM the expected output format."""
        if schema is None:
            return ""

        schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False, indent=2)
        return (
            "FORMAT RULES (MANDATORY):\n"
            "1) Return exactly one UTF-8 JSON object and nothing else.\n"
            "2) Do not use markdown, code fences, comments, or explanations.\n"
            "3) Do not add keys not defined by the schema.\n"
            "4) Every required field in the schema must be present with the correct type.\n"
            "5) If uncertain, still return the best valid JSON object that matches the schema.\n"
            "JSON SCHEMA (must be respected exactly):\n"
            f"{schema_json}"
        )


    @staticmethod
    def build_repair_prompt(original_prompt: str, invalid_output: str, error: Exception) -> str:
        """Build a repair prompt to send back to the LLM when its output failed validation."""
        return "\n\n".join([
            "Your previous output is invalid and must be corrected.",
            f"Validation error: {error}",
            "Return exactly one valid JSON object and nothing else.",
            "Do not include markdown, prose, or extra keys.",
            "Original prompt:",
            original_prompt,
            "Invalid output:",
            invalid_output,
        ])
