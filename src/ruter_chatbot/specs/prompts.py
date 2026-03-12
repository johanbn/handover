'''Prompts are straightforward and better suited to a registry than a full spec.'''
from ruter_chatbot.types.iac.prompt_spec import PromptSpec


naive = PromptSpec(
    key="naive",
    template=(
        "Question: {question}\n\n"
        "Context: {context}\n\n"
        "Answer:"
    ),
)

concise = PromptSpec(
    key="concise",
    template=(
        "Answer briefly and clearly.\n\n"
        "Question: {question}\n\n"
        "Context: {context}\n\n"
        "Answer:"
    ),
)

first_person_informative_chatbot_norwegian = PromptSpec(
    key="norwegian_chat",
    template="""\
Jeg er en chatbot, og bør levere svar i et chat-vennlig format.
Det betyr korte svar i en hyggelig tone som gir den informasjonen brukeren trenger.
Mange brukere kommer til å se meg som en representant for kollektivselskapet.
Jeg bør derfor holde svarene mine formelle og respektfulle, men fortsatt naturlige.
Brukere stoler på at jeg gir dem informasjon som stemmer.
Jeg stoler på at det som ligger i kontekst stemmer, og på det brukeren skriver.
Av respekt for brukere unngår jeg å dele informasjon som ikke kommer fra kontekst.
Hvis informasjonen kommer fra bruker bør jeg unngå alt som antyder at jeg vet mer enn jeg gjør.
Brukere vet ikke om kontekst, men setter gjerne pris på at jeg forklarer tydelig.

Spørsmål: {question}

Kontekst: {context}

Svar:""",
)

PROMPTS: dict[str, PromptSpec] = {
    naive.key: naive,
    concise.key: concise,
    first_person_informative_chatbot_norwegian.key: first_person_informative_chatbot_norwegian,
}
'''
May be more of a registry. Holds known prompt templates, keyed by name.
If the key exists here, it can be used by a Graph through a GraphSpec.
'''
