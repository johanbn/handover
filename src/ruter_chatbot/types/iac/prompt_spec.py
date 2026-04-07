from pydantic import BaseModel

class PromptSpec(BaseModel):
    key: str
    template: str
