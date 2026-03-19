
from ruter_chatbot.types.iac.app_spec import AppSpec

from ruter_chatbot.specs.prompts import PROMPTS
from ruter_chatbot.specs.models import MODELS
from ruter_chatbot.specs.pipelines import PIPELINES
from ruter_chatbot.specs.vector_stores import VECTOR_STORES
from ruter_chatbot.specs.graphs import GRAPHS


APP = AppSpec(
    models=MODELS,
    pipelines=PIPELINES,
    prompts=PROMPTS,
    vector_stores=VECTOR_STORES,
    graph=GRAPHS["aws_demo"],
)
