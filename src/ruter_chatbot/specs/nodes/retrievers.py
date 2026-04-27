'''
Provides various RetrieverNodeSpecs.
Note that node names must be unique within a GraphSpec.
However, they can be reused between GraphSpecs.
'''
from ruter_chatbot.types.iac.node_spec import NodeSpec, RetrieverNodeSpec

retriever_ruter_aws_extern: NodeSpec = RetrieverNodeSpec(
    name="retrieve_docs",
    kind="retriever",
    store_key="ruter_store_aws_extern",
    top_k=5,
    output_key="docs",
)
'''Generic retriever for AWS-based external Ruter store.'''

retriever_ruter_local: NodeSpec = RetrieverNodeSpec(
    name="retrieve_docs",
    kind="retriever",
    store_key="ruter_store",
    top_k=5,
    output_key="docs",
)
'''Generic retriever for local ruter store.'''

retriever_ruter_aws_extern_big: NodeSpec = RetrieverNodeSpec(
    name="retrieve_docs",
    kind="retriever",
    store_key="ruter_store_aws_extern",
    search_type="mmr",
    top_k=15,
    fetch_k=40,
    lambda_mult=0.5,
    output_key="docs",
)
'''Like retriever_ruter_aws_extern but retrieves a lot more than default.'''

retriever_ruter_aws_intern: NodeSpec = RetrieverNodeSpec(
    name="retrieve_docs",
    kind="retriever",
    store_key="ruter_store_aws_intern",
    top_k=5,
    output_key="docs",
)
'''Generic retriever for AWS-based internal Ruter store.'''
