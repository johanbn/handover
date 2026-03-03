from pydantic import BaseModel
from typing import Literal

class BaseNode(BaseModel):
    kind: Literal[]