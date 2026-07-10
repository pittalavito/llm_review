from pydantic import BaseModel
from pypdf.constants import StrEnum


class GraphNode(StrEnum):
    REVIEWER = "",
    META_REVIEWER = "",
    AREA_CHAIR = "",
    AUTHOR_AGENT = ""
    
    
class GraphEdge(StrEnum):
    REVIEWER_TO_META = "",
    META_TO_AREA_CHAIR = "",
    AREA_CHAIR_TO_AUTHOR = "",
    AUTHOR_TO_REVIEWER = ""
    
    
class GraphConditionalEdge(StrEnum