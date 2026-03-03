from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel

class PromptSpec(BaseModel):
    name: str
    template: PromptTemplate
