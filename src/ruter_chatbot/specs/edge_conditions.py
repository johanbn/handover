from typing import Callable
from pydantic import BaseModel

RouterFn = Callable[[BaseModel], str]

router_registry: dict[str, RouterFn] = {}
'''Registry for Router Edge spec callables.'''
