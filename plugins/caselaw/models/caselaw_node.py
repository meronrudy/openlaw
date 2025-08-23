"""
Caselaw Node Models for Hypergraph Integration
Implements typed nodes for cases, citations, courts, judges, and legal concepts
"""

from typing import Dict, List, Any, Optional, Union
from datetime import datetime, date
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import json

from core.model import Node, Provenance
from .canonical_identifiers import CanonicalID, DocumentID, ParagraphID, CitationID, CourtID, JudgeID, ConceptID
from .provenance_record import ProvenanceRecord


class CaselawNode(Node):
    """
    Base class for all caselaw-specific hypergraph nodes.
    Extends the core Node with caselaw-specific functionality.
    """
    
    def __init__(self,
                 canonical_id: CanonicalID,
                 node_type: str,
                 properties: Dict[str, Any],
                 provenance_record: ProvenanceRecord,
                 created_at: Optional[datetime] = None,
                 updated_at: Optional[datetime] = None):
        
        # Initialize base HypergraphNode
        super().__init__(
            id=str(canonical_id),
            node_type=node_type,
            properties=properties,
            created_at=created_at or datetime.utcnow(),
            source_plugin="caselaw_access_project"
        )
        
        # Caselaw-specific attributes
        self._canonical_id = canonical_id
        self._provenance_record = provenance_record
        self._updated_at = updated_at or self.created_at
        
        # Validate node consistency
        self._validate()
    
    @property
    def canonical_id(self) -> CanonicalID:
        """The canonical identifier for this node"""
        return self._canonical_id
    
    @property
    def provenance_record(self) -> ProvenanceRecord:
        """The provenance record for this node"""
        return self._provenance_record
    
    @property
    def updated_at(self) -> datetime:
        """When this node was last updated"""
        return self._updated_at
    
    @property
    def provenance_id(self) -> str:
        """ID of the associated provenance record"""
        return self._provenance_record.id
    
    def _validate(self):
        """Validate node consistency"""
        # Ensure canonical ID matches node ID
        if str(self._canonical_id) != self.id:
            raise ValueError(f"Canonical ID {self._canonical_id} doesn't match node ID {self.id}")
        
        # Ensure provenance record entity ID matches
        if self._provenance_record.entity_id != self.id:
            raise ValueError(f"Provenance entity ID {self._provenance_record.entity_id} doesn't match node ID {self.id}")
    
    def update_properties(self, new_properties: Dict[str, Any], provenance_record: ProvenanceRecord):
        """Update node properties with new provenance record"""
        self.properties.update(new_properties)
        self._provenance_record = provenance_record
        self._updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        base_dict = super().to_dict()
        base_dict.update({
            "canonical_id": self._canonical_id.to_dict(),
            "provenance_id": self._provenance_record.id,
            "updated_at": self._updated_at.isoformat()
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], provenance_record: ProvenanceRecord) -> 'CaselawNode':
        """Create node from dictionary representation"""
        # This is abstract - subclasses must implement
        raise NotImplementedError("Subclasses must implement from_dict")


class CaseNode(CaselawNode):
    """
    Represents a legal case in the hypergraph.
    Contains all case metadata and connects to related entities.
    """
    
    def __init__(self,
                 case_id: DocumentID,
                 properties: Dict[str, Any],
                 provenance_record: ProvenanceRecord,
                 created_at: Optional[datetime] = None):
        
        # Validate required case properties
        required_fields = ["name", "jurisdiction"]
        for field in required_fields:
            if field not in properties:
                raise ValueError(f"Case node missing required field: {field}")
        
        super().__init__(
            canonical_id=case_id,
            node_type="case",
            properties=properties,
            provenance_record=provenance_record,
            created_at=created_at
        )
    
    @property
    def case_name(self) -> str:
        """The name of the case"""
        return self.properties["name"]
    
    @property
    def jurisdiction(self) -> str:
        """The jurisdiction of the case"""
        return self.properties["jurisdiction"]
    
    @property
    def decision_date(self) -> Optional[date]:
        """The decision date of the case"""
        date_str = self.properties.get("decision_date")
        if date_str:
            if isinstance(date_str, str):
                return datetime.fromisoformat(date_str).date()
            elif isinstance(date_str, date):
                return date_str
        return None
    
    @property
    def court(self) -> Optional[str]:
        """The court that decided the case"""
        return self.properties.get("court")
    
    @property
    def docket_number(self) -> Optional[str]:
        """The docket number of the case"""
        return self.properties.get("docket_number")
    
    @property
    def citations(self) -> List[str]:
        """List of citations for this case"""
        return self.properties.get("citations", [])
    
    @property
    def precedential_value(self) -> float:
        """Calculated precedential value of this case"""
        return self.properties.get("precedential_value", 0.0)
    
    @property
    def legal_concepts(self) -> List[str]:
        """Extracted legal concepts from this case"""
        return self.properties.get("legal_concepts", [])
    
    @classmethod
    def from_cap_data(cls,
                      cap_case_data: Dict[str, Any],
                      provenance_record: ProvenanceRecord) -> 'CaseNode':
        """Create CaseNode from CAP dataset format"""
        case_id = DocumentID.from_case_id(cap_case_data["id"])
        
        # Extract and normalize properties from CAP format
        properties = {
            "name": cap_case_data.get("name", ""),
            "name_abbreviation": cap_case_data.get("name_abbreviation"),
            "jurisdiction": cap_case_data.get("jurisdiction", ""),
            "decision_date": cap_case_data.get("decision_date"),
            "court": cap_case_data.get("court", {}).get("name"),
            "docket_number": cap_case_data.get("docket_number"),
            "first_page": cap_case_data.get("first_page"),
            "last_page": cap_case_data.get("last_page"),
            "frontend_url": cap_case_data.get("frontend_url"),
            "frontend_pdf_url": cap_case_data.get("frontend_pdf_url"),
            "citations": [cite.get("cite", "") for cite in cap_case_data.get("citations", [])],
            "reporter": cap_case_data.get("reporter", {}).get("full_name"),
            "volume": cap_case_data.get("volume", {}).get("volume_number"),
            "analysis": cap_case_data.get("analysis", {}),
            "legal_concepts": [],  # Will be populated by extraction
            "precedential_value": 0.0  # Will be calculated
        }
        
        return cls(case_id, properties, provenance_record)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], provenance_record: ProvenanceRecord) -> 'CaseNode':
        """Create CaseNode from dictionary representation"""
        canonical_id_data = data["canonical_id"]
        case_id = DocumentID(canonical_id_data["identifier"])
        
        return cls(
            case_id=case_id,
            properties=data["properties"],
            provenance_record=provenance_record,
            created_at=datetime.fromisoformat(data["created_at"])
        )


class CitationNode(CaselawNode):
    """
    Represents a legal citation in the hypergraph.
    Links cases to their formal citations.
    """
    
    def __init__(self,
                 citation_id: CitationID,
                 properties: Dict[str, Any],
                 provenance_record: ProvenanceRecord,
                 created_at: Optional[datetime] = None):
        
        # Validate required citation properties
        required_fields = ["cite", "type"]
        for field in required_fields:
            if field not in properties:
                raise ValueError(f"Citation node missing required field: {field}")
        
        super().__init__(
            canonical_id=citation_id,
            node_type="citation",
            properties=properties,
            provenance_record=provenance_record,
            created_at=created_at
        )
    
    @property
    def cite_text(self) -> str:
        """The citation text"""
        return self.properties["cite"]
    
    @property
    def citation_type(self) -> str:
        """The type of citation (official, parallel, etc.)"""
        return self.properties["type"]
    
    @property
    def normalized_cite(self) -> str:
        """Normalized citation text"""
        return self.properties.get("normalized_cite", self.cite_text)
    
    @property
    def reporter(self) -> str:
        """The reporter abbreviation"""
        return self.canonical_id.reporter
    
    @property
    def volume(self) -> int:
        """The volume number"""
        return self.canonical_id.volume
    
    @property
    def page(self) -> int:
        """The page number"""
        return self.canonical_id.page
    
    @classmethod
    def from_citation_data(cls,
                          citation_data: Dict[str, Any],
                          provenance_record: ProvenanceRecord) -> Optional['CitationNode']:
        """Create CitationNode from citation data"""
        cite_text = citation_data.get("cite", "")
        if not cite_text:
            return None
        
        # Try to create canonical citation ID
        citation_id = CitationID.from_citation_string(cite_text)
        if not citation_id:
            return None
        
        properties = {
            "cite": cite_text,
            "type": citation_data.get("type", "unknown"),
            "normalized_cite": citation_data.get("normalized_cite", cite_text)
        }
        
        return cls(citation_id, properties, provenance_record)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], provenance_record: ProvenanceRecord) -> 'CitationNode':
        """Create CitationNode from dictionary representation"""
        canonical_id_data = data["canonical_id"]
        citation_id = CitationID(canonical_id_data["identifier"])
        
        return cls(
            citation_id=citation_id,
            properties=data["properties"],
            provenance_record=provenance_record,
            created_at=datetime.fromisoformat(data["created_at"])
        )


class CourtNode(CaselawNode):
    """
    Represents a court in the hypergraph.
    Contains court hierarchy and jurisdictional information.
    """
    
    def __init__(self,
                 court_id: CourtID,
                 properties: Dict[str, Any],
                 provenance_record: ProvenanceRecord,
                 created_at: Optional[datetime] = None):
        
        # Validate required court properties
        required_fields = ["name", "jurisdiction"]
        for field in required_fields:
            if field not in properties:
                raise ValueError(f"Court node missing required field: {field}")
        
        super().__init__(
            canonical_id=court_id,
            node_type="court",
            properties=properties,
            provenance_record=provenance_record,
            created_at=created_at
        )
    
    @property
    def court_name(self) -> str:
        """The name of the court"""
        return self.properties["name"]
    
    @property
    def jurisdiction(self) -> str:
        """The jurisdiction of the court"""
        return self.properties["jurisdiction"]
    
    @property
    def court_level(self) -> str:
        """The level of the court (trial, appellate, supreme)"""
        return self.properties.get("court_level", "unknown")
    
    @property
    def authority_level(self) -> int:
        """Numeric authority level for precedent calculations"""
        return self.properties.get("authority_level", 0)
    
    @property
    def geographic_scope(self) -> List[str]:
        """Geographic areas under this court's jurisdiction"""
        return self.properties.get("geographic_scope", [])
    
    @classmethod
    def from_court_data(cls,
                       court_data: Dict[str, Any],
                       provenance_record: ProvenanceRecord) -> 'CourtNode':
        """Create CourtNode from court data"""
        # Generate court ID from court name and jurisdiction
        court_name = court_data.get("name", "")
        jurisdiction = court_data.get("jurisdiction", "us")
        
        from .canonical_identifiers import IDGenerator
        court_id = IDGenerator.generate_court_id_from_name(court_name, jurisdiction)
        
        properties = {
            "name": court_name,
            "name_abbreviation": court_data.get("name_abbreviation"),
            "jurisdiction": jurisdiction,
            "court_level": court_data.get("court_level", "trial"),
            "authority_level": court_data.get("authority_level", 1),
            "geographic_scope": court_data.get("geographic_scope", [jurisdiction])
        }
        
        return cls(court_id, properties, provenance_record)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], provenance_record: ProvenanceRecord) -> 'CourtNode':
        """Create CourtNode from dictionary representation"""
        canonical_id_data = data["canonical_id"]
        court_id = CourtID(canonical_id_data["identifier"])
        
        return cls(
            court_id=court_id,
            properties=data["properties"],
            provenance_record=provenance_record,
            created_at=datetime.fromisoformat(data["created_at"])
        )


class JudgeNode(CaselawNode):
    """
    Represents a judge in the hypergraph.
    Contains biographical and career information.
    """
    
    def __init__(self,
                 judge_id: JudgeID,
                 properties: Dict[str, Any],
                 provenance_record: ProvenanceRecord,
                 created_at: Optional[datetime] = None):
        
        # Validate required judge properties
        required_fields = ["name"]
        for field in required_fields:
            if field not in properties:
                raise ValueError(f"Judge node missing required field: {field}")
        
        super().__init__(
            canonical_id=judge_id,
            node_type="judge",
            properties=properties,
            provenance_record=provenance_record,
            created_at=created_at
        )
    
    @property
    def judge_name(self) -> str:
        """The name of the judge"""
        return self.properties["name"]
    
    @property
    def birth_year(self) -> int:
        """The birth year of the judge"""
        return self.canonical_id.birth_year
    
    @property
    def courts_served(self) -> List[str]:
        """Courts where this judge has served"""
        return self.properties.get("courts_served", [])
    
    @property
    def appointment_date(self) -> Optional[date]:
        """Date of judicial appointment"""
        date_str = self.properties.get("appointment_date")
        if date_str:
            return datetime.fromisoformat(date_str).date()
        return None
    
    @classmethod
    def from_judge_data(cls,
                       judge_data: Dict[str, Any],
                       provenance_record: ProvenanceRecord) -> 'JudgeNode':
        """Create JudgeNode from judge data"""
        judge_name = judge_data.get("name", "")
        birth_year = judge_data.get("birth_year", 1900)
        
        judge_id = JudgeID.from_name_and_year(judge_name, birth_year)
        
        properties = {
            "name": judge_name,
            "birth_year": birth_year,
            "appointment_date": judge_data.get("appointment_date"),
            "courts_served": judge_data.get("courts_served", []),
            "biographical_info": judge_data.get("biographical_info", {})
        }
        
        return cls(judge_id, properties, provenance_record)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], provenance_record: ProvenanceRecord) -> 'JudgeNode':
        """Create JudgeNode from dictionary representation"""
        canonical_id_data = data["canonical_id"]
        judge_id = JudgeID(canonical_id_data["identifier"])
        
        return cls(
            judge_id=judge_id,
            properties=data["properties"],
            provenance_record=provenance_record,
            created_at=datetime.fromisoformat(data["created_at"])
        )


class LegalConceptNode(CaselawNode):
    """
    Represents a legal concept in the hypergraph.
    Extracted from case text and used for legal reasoning.
    """
    
    def __init__(self,
                 concept_id: ConceptID,
                 properties: Dict[str, Any],
                 provenance_record: ProvenanceRecord,
                 created_at: Optional[datetime] = None):
        
        # Validate required concept properties
        required_fields = ["concept_name", "domain"]
        for field in required_fields:
            if field not in properties:
                raise ValueError(f"Legal concept node missing required field: {field}")
        
        super().__init__(
            canonical_id=concept_id,
            node_type="legal_concept",
            properties=properties,
            provenance_record=provenance_record,
            created_at=created_at
        )
    
    @property
    def concept_name(self) -> str:
        """The name of the legal concept"""
        return self.properties["concept_name"]
    
    @property
    def domain(self) -> str:
        """The legal domain of this concept"""
        return self.properties["domain"]
    
    @property
    def definition(self) -> Optional[str]:
        """Definition of the legal concept"""
        return self.properties.get("definition")
    
    @property
    def synonyms(self) -> List[str]:
        """Synonymous terms for this concept"""
        return self.properties.get("synonyms", [])
    
    @property
    def related_concepts(self) -> List[str]:
        """Related legal concepts"""
        return self.properties.get("related_concepts", [])
    
    @classmethod
    def from_concept_data(cls,
                         concept_data: Dict[str, Any],
                         provenance_record: ProvenanceRecord) -> 'LegalConceptNode':
        """Create LegalConceptNode from concept data"""
        concept_name = concept_data.get("concept_name", "")
        domain = concept_data.get("domain", "general")
        
        concept_id = ConceptID.from_domain_and_concept(domain, concept_name)
        
        properties = {
            "concept_name": concept_name,
            "domain": domain,
            "definition": concept_data.get("definition"),
            "synonyms": concept_data.get("synonyms", []),
            "related_concepts": concept_data.get("related_concepts", []),
            "extraction_confidence": concept_data.get("extraction_confidence", 0.0)
        }
        
        return cls(concept_id, properties, provenance_record)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], provenance_record: ProvenanceRecord) -> 'LegalConceptNode':
        """Create LegalConceptNode from dictionary representation"""
        canonical_id_data = data["canonical_id"]
        concept_id = ConceptID(canonical_id_data["identifier"])
        
        return cls(
            concept_id=concept_id,
            properties=data["properties"],
            provenance_record=provenance_record,
            created_at=datetime.fromisoformat(data["created_at"])
        )


class ParagraphNode(CaselawNode):
    """
    Represents a paragraph within a case document.
    Enables paragraph-level citation tracking and provenance.
    """
    
    def __init__(self,
                 paragraph_id: ParagraphID,
                 properties: Dict[str, Any],
                 provenance_record: ProvenanceRecord,
                 created_at: Optional[datetime] = None):
        
        # Validate required paragraph properties
        required_fields = ["text", "paragraph_number"]
        for field in required_fields:
            if field not in properties:
                raise ValueError(f"Paragraph node missing required field: {field}")
        
        super().__init__(
            canonical_id=paragraph_id,
            node_type="paragraph",
            properties=properties,
            provenance_record=provenance_record,
            created_at=created_at
        )
    
    @property
    def text(self) -> str:
        """The text content of the paragraph"""
        return self.properties["text"]
    
    @property
    def paragraph_number(self) -> int:
        """The paragraph number within the case"""
        return self.properties["paragraph_number"]
    
    @property
    def case_id(self) -> str:
        """The ID of the parent case"""
        return str(self.canonical_id.document_id)
    
    @property
    def extracted_citations(self) -> List[Dict[str, Any]]:
        """Citations extracted from this paragraph"""
        return self.properties.get("extracted_citations", [])
    
    @property
    def legal_concepts(self) -> List[str]:
        """Legal concepts identified in this paragraph"""
        return self.properties.get("legal_concepts", [])
    
    @classmethod
    def from_case_text(cls,
                      case_id: int,
                      paragraph_number: int,
                      text: str,
                      provenance_record: ProvenanceRecord) -> 'ParagraphNode':
        """Create ParagraphNode from case text"""
        paragraph_id = ParagraphID.from_case_and_paragraph(case_id, paragraph_number)
        
        properties = {
            "text": text,
            "paragraph_number": paragraph_number,
            "extracted_citations": [],  # Will be populated by extraction
            "legal_concepts": [],  # Will be populated by extraction
            "character_count": len(text),
            "word_count": len(text.split())
        }
        
        return cls(paragraph_id, properties, provenance_record)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], provenance_record: ProvenanceRecord) -> 'ParagraphNode':
        """Create ParagraphNode from dictionary representation"""
        canonical_id_data = data["canonical_id"]
        paragraph_id = ParagraphID(canonical_id_data["identifier"])
        
        return cls(
            paragraph_id=paragraph_id,
            properties=data["properties"],
            provenance_record=provenance_record,
            created_at=datetime.fromisoformat(data["created_at"])
        )


# Node factory for creating appropriate node types
class CaselawNodeFactory:
    """Factory for creating appropriate caselaw node types"""
    
    NODE_TYPE_MAP = {
        "case": CaseNode,
        "citation": CitationNode,
        "court": CourtNode,
        "judge": JudgeNode,
        "legal_concept": LegalConceptNode,
        "paragraph": ParagraphNode
    }
    
    @classmethod
    def create_node(cls,
                   node_type: str,
                   data: Dict[str, Any],
                   provenance_record: ProvenanceRecord) -> CaselawNode:
        """Create appropriate node type from data"""
        if node_type not in cls.NODE_TYPE_MAP:
            raise ValueError(f"Unknown node type: {node_type}")
        
        node_class = cls.NODE_TYPE_MAP[node_type]
        return node_class.from_dict(data, provenance_record)
    
    @classmethod
    def create_from_cap_data(cls,
                            cap_data: Dict[str, Any],
                            provenance_record: ProvenanceRecord) -> CaseNode:
        """Create CaseNode specifically from CAP dataset format"""
        return CaseNode.from_cap_data(cap_data, provenance_record)