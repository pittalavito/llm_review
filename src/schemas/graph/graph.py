
import operator
from typing import Annotated, TypedDict


class GraphState(TypedDict):
    # Il paper da revisionare
    paper: str
    
    # Messaggi tra agenti — operator.add li accumula invece di sovrascriverli
    messages: Annotated[list, operator.add]
    
    # Review prodotte dai reviewer
    reviews: Annotated[list, operator.add]

    # Round corrente
    current_round: int
    max_rounds: int