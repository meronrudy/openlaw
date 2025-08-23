# CAP Caselaw Plugin - Data Models
# Provenance-first hypergraph models with canonical identifiers

from .canonical_identifiers import CanonicalID, DocumentID, ParagraphID, CitationID, IdentifierFactory, IDGenerator
from .provenance_record import ProvenanceRecord
from .case_relationship import CaseRelationship, RelationshipType

__all__ = [
    # Canonical identifier classes
    "CanonicalID",
    "DocumentID",
    "ParagraphID", 
    "CitationID",
    "IdentifierFactory",
    "IDGenerator",
    
    # Provenance
    "ProvenanceRecord",
    
    # Relationships
    "CaseRelationship",
    "RelationshipType"
]