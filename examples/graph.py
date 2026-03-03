# Skrive om til og bruke Langchain i stedet for huggingface_hub direkte, 
# for å gjøre det mer fleksibelt og enklere å bytte modell senere.

# MessegesState Langgraph for å holde styr på samtalens tilstand, og bruke den i chat-funksjonen.

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import MessagesState, StateGraph, START, END
from langchain_ollama import ChatOllama

# Recall:
# class MessagesState(TypedDict):
#    messages: Annotated[list[AnyMessage], add_messages]
class CustomState(MessagesState):
    docs : list[Document]

builder = StateGraph(CustomState)
model = ChatOllama(model="qwen2.5:3b")

def chatbot_node(state: CustomState) -> dict:
    question = ""

    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            question = msg.content
            break

    response = model.invoke(question)
    return {
        **state,
        "messages": state["messages"] + [response],
    }


builder.add_node("chatbot", chatbot_node)
builder.add_edge(START, "chatbot")
builder.add_edge("chatbot", END)
graph = builder.compile()

## Under here using the graph to have a conversation with the chatbot.
q = "Do I need to eat?"
state = {"messages": [HumanMessage(content=q)], "docs": []}
answer = graph.invoke(state)
print(answer)