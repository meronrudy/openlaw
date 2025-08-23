# CAP Caselaw Plugin - API Layer
# REST endpoints for downstream legal AI integration

from .query_api import CaselawQueryAPI
from .provenance_api import CaselawProvenanceAPI
from .search_api import CaselawSearchAPI
from .citation_api import CitationResolutionAPI

__all__ = [
    "CaselawQueryAPI",
    "CaselawProvenanceAPI", 
    "CaselawSearchAPI",
    "CitationResolutionAPI"
]