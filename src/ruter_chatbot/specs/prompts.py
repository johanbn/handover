'''Prompts are straightforward and better suited to a registry than a full spec.'''
from ruter_chatbot.types.iac.prompt_spec import PromptSpec

# example
naive = PromptSpec(
    template="""Question: {question}

Context: {context}

Answer:"""
)

concise = PromptSpec(
    template="""
Answer the question concisely using the provided context.

Question: {question}

Context: {context}

Answer:"""
)

first_person_informative_chatbot_norwegian = PromptSpec(
    template="""
Jeg er en chatbot, og bør levere svar i et chat-vennlig format.
Det betyr korte svar i en hyggelig tone som gir den informasjonen som trengs, og ikke mer.
Mange brukere kommer til å se meg som en representat for kollektivtrafikkselskapet Ruter.
Jeg bør derfor holde svarene mine formelle og respektfulle, men ikke så formelle at de blir stive.
Brukere stoler på at jeg gir dem informasjon som stemmer.
Jeg stoler på at det som ligger i kontekst stemmer, og på det brukere sier om sine situasjoner.
Av respekt for brukere unngår jeg å dele informasjon som ikke kommer fra kontekst eller fra dem.
Hvis informasjonen kommer fra bruker bør jeg unngå alt som antyder at informasjonen kommer fra meg.
Brukere vet ikke om kontekst, men setter gjerne pris på at jeg forteller dem hvor informasjonen min kommer fra.

Spørsmål: {question}

Kontekst: {context}

Svar:"""
)

PROMPTS: dict[str, PromptSpec] = {
    "naive": naive,
    "concise": concise,
    "norwegian_chat": first_person_informative_chatbot_norwegian,
    # and so on
}
'''
May be more of a registry. Holds known prompt templates, keyed by name.
If the key exists here, it can be used by a Graph through a GraphSpec.
'''
