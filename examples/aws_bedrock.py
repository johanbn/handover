from langchain_aws import ChatBedrockConverse, BedrockEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.vectorstores import FAISS
import boto3

print("\n=== Starting RAG demo ===\n")

my_data = [
    "The weather is nice today.",
    "Last night's game ended in a tie.",
    "Don likes to eat pizza.",
    "Don likes to eat pasta.",
]

question = "What does Don like to eat?"

AWS_REGION = "eu-west-1"
LLM_MODEL_ID = "eu.anthropic.claude-sonnet-4-20250514-v1:0"
EMBED_MODEL_ID = "cohere.embed-multilingual-v3"

print("Loaded source data:")
for i, item in enumerate(my_data, start=1):
    print(f"  {i}. {item}")

print(f"\nQuestion: {question}")
print(f"AWS region: {AWS_REGION}")
print(f"LLM inference profile: {LLM_MODEL_ID}")
print(f"Embedding model: {EMBED_MODEL_ID}")

print("\nCreating Bedrock runtime client...")
bedrock_runtime = boto3.client("bedrock-runtime", region_name=AWS_REGION)
print("Bedrock runtime client created.")

print("\nInitializing Claude chat model...")
chat_model = ChatBedrockConverse(
    client=bedrock_runtime,
    model=LLM_MODEL_ID,
    temperature=0,
    max_tokens=200,
)
print("Claude chat model initialized.")

print("\nInitializing embedding model...")
bedrock_embeddings = BedrockEmbeddings(
    client=bedrock_runtime,
    model_id=EMBED_MODEL_ID,
)
print("Embedding model initialized.")

print("\nCreating FAISS vector store...")
vector_store = FAISS.from_texts(my_data, bedrock_embeddings)
print("Vector store created.")

print("\nCreating retriever with top-k = 2...")
retriever = vector_store.as_retriever(search_kwargs={"k": 2})
print("Retriever ready.")

print("\nRunning retrieval...")
results = retriever.invoke(question)

print("\nRetrieved documents:")
context_chunks = []
for i, result in enumerate(results, start=1):
    print(f"  {i}. {result.page_content}")
    context_chunks.append(result.page_content)

context_text = "\n".join(context_chunks)

print("\nContext that will be sent to Claude:")
print(context_text)

print("\nBuilding prompt template...")
template = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Answer the user's question based only on the following context:\n\n{context}",
        ),
        ("human", "{input}"),
    ]
)
print("Prompt template created.")

print("\nCreating chain...")
chain = template | chat_model
print("Chain ready.")

print("\nInvoking Claude...")
response = chain.invoke(
    {
        "input": question,
        "context": context_text,
    }
)

print("\n=== FINAL RESPONSE ===")
print(response.content)
print("\n=== Done ===")