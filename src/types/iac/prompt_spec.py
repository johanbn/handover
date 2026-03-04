from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel

class PromptSpec(BaseModel):
    template: str

    @property
    def prompt(self) -> PromptTemplate:
        return PromptTemplate.from_template(self.template)
