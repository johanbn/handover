import string
from typing import Literal, Any
from pydantic import BaseModel, field_validator
from uuid import UUID

from langchain.messages import SystemMessage, HumanMessage

class MessageTemplate(BaseModel):
    role: Literal["system", "user"]
    content: str
    """Expects to .format content"""

    kind: Literal[
        "instruction",
        "context",
        "question",
        "example",
        "other"
    ] = "other"
    """
    `other` denotes it does not fit cleanly in another category.
    Override if that is false.
    """

    def required_fields(self) -> set[str]:
        """
        Returns the set of format keys used by this template.
        """
        formatter = string.Formatter()
        fields = set()

        for _, field_name, _, _ in formatter.parse(self.content):
            if field_name:
                fields.add(field_name)

        return fields
    
    def render(self, values: dict[str, Any]) -> str:
        """
        Renders the template with the provided values.
        Extra values are ignored.
        Missing values raise a KeyError.
        """
        return self.content.format_map(values)
    
    @classmethod
    def from_any(cls, value):
        """
        Normalize input into a MessageTemplate.
        """
        if isinstance(value, cls):
            return value
        if isinstance(value, dict):
            return cls(**value)
        raise TypeError(
            f"Cannot create MessageTemplate from {type(value).__name__}"
        )

class PromptSpec(BaseModel):
    key: str
    message_templates: list[MessageTemplate]

    def required_arguments(self) -> set[str]:
        """
        Union of all arguments required by all message templates.
        """
        required = set()
        for tmpl in self.message_templates:
            required |= tmpl.required_fields()
        return required

    def render_messages(self, turn_id: UUID, **kwargs: Any):
        
        """
        Renders the prompt into LangChain messages with a turn_id.

        Extra kwargs are ignored.
        Missing required arguments raise a clear error.
        """
        required = self.required_arguments()
        missing = required - kwargs.keys()

        if missing:
            raise ValueError(
                f"PromptSpec `{self.key}` is missing required arguments: {sorted(missing)}"
            )

        messages = []

        for tmpl in self.message_templates:
            content = tmpl.render(kwargs)

            if tmpl.role == "system":
                messages.append(
                    SystemMessage(
                        content=content,
                        additional_kwargs={
                            "turn_id": turn_id,
                            "kind": tmpl.kind,
                        }
                    )
                )
            elif tmpl.role == "user":
                messages.append(
                    HumanMessage(
                        content=content,
                        additional_kwargs={
                            "turn_id": turn_id,
                            "kind": tmpl.kind,
                        }
                    )
                )
            else:
                raise ValueError(f"Unsupported role: {tmpl.role}")
        
        return messages

    @field_validator("message_templates", mode="before")
    @classmethod
    def coerce_message_templates(cls, value):
        if not isinstance(value, list):
            raise TypeError("message_templates must be a list")
        
        normalized = []
        for i, item in enumerate(value):
            try:
                normalized.append(
                    MessageTemplate.from_any(item)
                )
            except Exception as e:
                raise TypeError(
                    f"Invalid message_templates[{i}]: {e}"
                ) from e

        return normalized
    
    def add_message_template(self, value: Any):
        self.message_templates.append(
            MessageTemplate.from_any(value)
        )
