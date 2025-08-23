"""
Canonical Identifier System for CAP Caselaw Plugin
Implements the specification for unique, immutable identifiers across the hypergraph
"""

import re
from typing import Optional, Union, Dict, Any
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


class CanonicalID(ABC):
    """
    Base class for all canonical identifiers in the caselaw system.
    Ensures immutable, globally unique identifiers with validation.
    """
    
    def __init__(self, identifier: str):
        self._validate_format(identifier)
        self._identifier = identifier
        self._created_at = datetime.utcnow()
    
    @property
    def identifier(self) -> str:
        """The canonical identifier string"""
        return self._identifier
    
    @property
    def created_at(self) -> datetime:
        """When this identifier was created"""
        return self._created_at
    
    @abstractmethod
    def _validate_format(self, identifier: str) -> None:
        """Validate the identifier format - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    def get_type(self) -> str:
        """Get the identifier type"""
        pass
    
    def __str__(self) -> str:
        return self._identifier
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{self._identifier}')"
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, CanonicalID):
            return False
        return self._identifier == other._identifier
    
    def __hash__(self) -> int:
        return hash(self._identifier)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "identifier": self._identifier,
            "type": self.get_type(),
            "created_at": self._created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CanonicalID':
        """Create from dictionary representation"""
        return cls(data["identifier"])


class DocumentID(CanonicalID):
    """
    Document-level canonical identifier for CAP cases
    Format: cap:{numeric_id}
    Example: cap:12345
    """
    
    PATTERN = re.compile(r'^cap:\d+$')
    
    def _validate_format(self, identifier: str) -> None:
        if not self.PATTERN.match(identifier):
            raise ValueError(f"Invalid DocumentID format: {identifier}. Expected format: cap:{{numeric_id}}")
    
    def get_type(self) -> str:
        return "document_id"
    
    @property
    def case_id(self) -> int:
        """Extract the numeric case ID"""
        return int(self._identifier.split(':')[1])
    
    @classmethod
    def from_case_id(cls, case_id: int) -> 'DocumentID':
        """Create DocumentID from numeric case ID"""
        return cls(f"cap:{case_id}")


class ParagraphID(CanonicalID):
    """
    Paragraph-level canonical identifier
    Format: cap:{case_id}#¶{paragraph_number}
    Example: cap:12345#¶3
    """
    
    PATTERN = re.compile(r'^cap:\d+#¶\d+$')
    
    def _validate_format(self, identifier: str) -> None:
        if not self.PATTERN.match(identifier):
            raise ValueError(f"Invalid ParagraphID format: {identifier}. Expected format: cap:{{case_id}}#¶{{paragraph_number}}")
    
    def get_type(self) -> str:
        return "paragraph_id"
    
    @property
    def case_id(self) -> int:
        """Extract the case ID"""
        return int(self._identifier.split('#')[0].split(':')[1])
    
    @property
    def paragraph_number(self) -> int:
        """Extract the paragraph number"""
        return int(self._identifier.split('¶')[1])
    
    @property
    def document_id(self) -> DocumentID:
        """Get the parent document ID"""
        return DocumentID.from_case_id(self.case_id)
    
    @classmethod
    def from_case_and_paragraph(cls, case_id: int, paragraph_number: int) -> 'ParagraphID':
        """Create ParagraphID from case ID and paragraph number"""
        return cls(f"cap:{case_id}#¶{paragraph_number}")


class CitationID(CanonicalID):
    """
    Citation canonical identifier
    Format: {reporter}:{volume}:{page}
    Example: us:347:483 (for 347 U.S. 483)
    """
    
    PATTERN = re.compile(r'^[a-z0-9_]+:\d+:\d+$')
    
    def _validate_format(self, identifier: str) -> None:
        if not self.PATTERN.match(identifier):
            raise ValueError(f"Invalid CitationID format: {identifier}. Expected format: {{reporter}}:{{volume}}:{{page}}")
    
    def get_type(self) -> str:
        return "citation_id"
    
    @property
    def reporter(self) -> str:
        """Extract the reporter abbreviation"""
        return self._identifier.split(':')[0]
    
    @property
    def volume(self) -> int:
        """Extract the volume number"""
        return int(self._identifier.split(':')[1])
    
    @property
    def page(self) -> int:
        """Extract the page number"""
        return int(self._identifier.split(':')[2])
    
    @classmethod
    def from_components(cls, reporter: str, volume: int, page: int) -> 'CitationID':
        """Create CitationID from reporter, volume, and page"""
        # Normalize reporter to lowercase and replace spaces/periods
        normalized_reporter = reporter.lower().replace(' ', '_').replace('.', '')
        return cls(f"{normalized_reporter}:{volume}:{page}")
    
    @classmethod
    def from_citation_string(cls, citation: str) -> Optional['CitationID']:
        """
        Parse a citation string and create CitationID
        Examples:
        - "347 U.S. 483" -> us:347:483
        - "524 F.3d 425" -> f3d:524:425
        """
        # Common citation patterns
        patterns = [
            # U.S. Supreme Court: "347 U.S. 483"
            (r'(\d+)\s+U\.?S\.?\s+(\d+)', 'us'),
            # Federal Circuit: "524 F.3d 425"
            (r'(\d+)\s+F\.?3d\s+(\d+)', 'f3d'),
            # Federal Circuit 2d: "789 F.2d 123"
            (r'(\d+)\s+F\.?2d\s+(\d+)', 'f2d'),
            # Federal: "456 F. 789"
            (r'(\d+)\s+F\.?\s+(\d+)', 'f'),
            # Federal Supplement: "123 F.Supp. 456"
            (r'(\d+)\s+F\.?Supp\.?\s+(\d+)', 'fsupp'),
        ]
        
        for pattern, reporter in patterns:
            match = re.search(pattern, citation, re.IGNORECASE)
            if match:
                volume = int(match.group(1))
                page = int(match.group(2))
                return cls.from_components(reporter, volume, page)
        
        return None


class CourtID(CanonicalID):
    """
    Court canonical identifier
    Format: {jurisdiction}:{court_type}:{court_code}
    Example: us:supreme:scotus, ny:supreme:1st_dept
    """
    
    PATTERN = re.compile(r'^[a-z0-9_]+:[a-z0-9_]+:[a-z0-9_]+$')
    
    def _validate_format(self, identifier: str) -> None:
        if not self.PATTERN.match(identifier):
            raise ValueError(f"Invalid CourtID format: {identifier}. Expected format: {{jurisdiction}}:{{court_type}}:{{court_code}}")
    
    def get_type(self) -> str:
        return "court_id"
    
    @property
    def jurisdiction(self) -> str:
        """Extract the jurisdiction"""
        return self._identifier.split(':')[0]
    
    @property
    def court_type(self) -> str:
        """Extract the court type"""
        return self._identifier.split(':')[1]
    
    @property
    def court_code(self) -> str:
        """Extract the court code"""
        return self._identifier.split(':')[2]
    
    @classmethod
    def from_components(cls, jurisdiction: str, court_type: str, court_code: str) -> 'CourtID':
        """Create CourtID from components"""
        # Normalize components
        jurisdiction = jurisdiction.lower().replace(' ', '_')
        court_type = court_type.lower().replace(' ', '_')
        court_code = court_code.lower().replace(' ', '_')
        return cls(f"{jurisdiction}:{court_type}:{court_code}")


class JudgeID(CanonicalID):
    """
    Judge canonical identifier
    Format: judge:{normalized_name}:{birth_year}
    Example: judge:ruth_bader_ginsburg:1933
    """
    
    PATTERN = re.compile(r'^judge:[a-z0-9_]+:\d{4}$')
    
    def _validate_format(self, identifier: str) -> None:
        if not self.PATTERN.match(identifier):
            raise ValueError(f"Invalid JudgeID format: {identifier}. Expected format: judge:{{normalized_name}}:{{birth_year}}")
    
    def get_type(self) -> str:
        return "judge_id"
    
    @property
    def normalized_name(self) -> str:
        """Extract the normalized judge name"""
        return self._identifier.split(':')[1]
    
    @property
    def birth_year(self) -> int:
        """Extract the birth year"""
        return int(self._identifier.split(':')[2])
    
    @classmethod
    def from_name_and_year(cls, name: str, birth_year: int) -> 'JudgeID':
        """Create JudgeID from name and birth year"""
        # Normalize name: lowercase, replace spaces with underscores, remove punctuation
        normalized_name = re.sub(r'[^\w\s]', '', name.lower()).replace(' ', '_')
        return cls(f"judge:{normalized_name}:{birth_year}")


class ConceptID(CanonicalID):
    """
    Legal concept canonical identifier
    Format: concept:{domain}:{concept_name}
    Example: concept:employment:discrimination, concept:constitutional:due_process
    """
    
    PATTERN = re.compile(r'^concept:[a-z0-9_]+:[a-z0-9_]+$')
    
    def _validate_format(self, identifier: str) -> None:
        if not self.PATTERN.match(identifier):
            raise ValueError(f"Invalid ConceptID format: {identifier}. Expected format: concept:{{domain}}:{{concept_name}}")
    
    def get_type(self) -> str:
        return "concept_id"
    
    @property
    def domain(self) -> str:
        """Extract the legal domain"""
        return self._identifier.split(':')[1]
    
    @property
    def concept_name(self) -> str:
        """Extract the concept name"""
        return self._identifier.split(':')[2]
    
    @classmethod
    def from_domain_and_concept(cls, domain: str, concept_name: str) -> 'ConceptID':
        """Create ConceptID from domain and concept name"""
        # Normalize components
        domain = domain.lower().replace(' ', '_')
        concept_name = concept_name.lower().replace(' ', '_')
        return cls(f"concept:{domain}:{concept_name}")


# Utility functions for identifier management
class IdentifierFactory:
    """Factory for creating and managing canonical identifiers"""
    
    ID_TYPE_MAP = {
        'document_id': DocumentID,
        'paragraph_id': ParagraphID,
        'citation_id': CitationID,
        'court_id': CourtID,
        'judge_id': JudgeID,
        'concept_id': ConceptID
    }
    
    @classmethod
    def create_from_string(cls, identifier: str) -> CanonicalID:
        """Create appropriate identifier type from string"""
        # Try each type in order of specificity
        for id_class in [ParagraphID, DocumentID, CitationID, CourtID, JudgeID, ConceptID]:
            try:
                return id_class(identifier)
            except ValueError:
                continue
        
        raise ValueError(f"Unknown identifier format: {identifier}")
    
    @classmethod
    def create_from_dict(cls, data: Dict[str, Any]) -> CanonicalID:
        """Create identifier from dictionary representation"""
        id_type = data.get('type')
        if id_type not in cls.ID_TYPE_MAP:
            raise ValueError(f"Unknown identifier type: {id_type}")
        
        id_class = cls.ID_TYPE_MAP[id_type]
        return id_class.from_dict(data)
    
    @classmethod
    def validate_identifier(cls, identifier: str) -> bool:
        """Validate if string is a valid canonical identifier"""
        try:
            cls.create_from_string(identifier)
            return True
        except ValueError:
            return False


# ID generation utilities
class IDGenerator:
    """Utilities for generating canonical identifiers"""
    
    @staticmethod
    def generate_document_id(cap_case_id: int) -> DocumentID:
        """Generate document ID from CAP case ID"""
        return DocumentID.from_case_id(cap_case_id)
    
    @staticmethod
    def generate_paragraph_id(cap_case_id: int, paragraph_num: int) -> ParagraphID:
        """Generate paragraph ID from case ID and paragraph number"""
        return ParagraphID.from_case_and_paragraph(cap_case_id, paragraph_num)
    
    @staticmethod
    def generate_citation_id_from_citation(citation_text: str) -> Optional[CitationID]:
        """Generate citation ID from citation text"""
        return CitationID.from_citation_string(citation_text)
    
    @staticmethod
    def generate_court_id_from_name(court_name: str, jurisdiction: str = "us") -> CourtID:
        """Generate court ID from court name"""
        # Simplified court mapping - would be more comprehensive in production
        court_mappings = {
            "supreme court of the united states": "us:supreme:scotus",
            "united states supreme court": "us:supreme:scotus",
            "court of appeals": "us:appellate:circuit",
            "district court": "us:district:federal",
        }
        
        normalized_name = court_name.lower()
        
        for name_pattern, court_id in court_mappings.items():
            if name_pattern in normalized_name:
                return CourtID(court_id)
        
        # Default fallback
        court_code = re.sub(r'[^\w\s]', '', court_name.lower()).replace(' ', '_')
        return CourtID.from_components(jurisdiction, "unknown", court_code)


# Validation and testing utilities
def validate_all_id_formats():
    """Test validation of all identifier formats"""
    test_cases = [
        # Valid cases
        (DocumentID, "cap:12345", True),
        (ParagraphID, "cap:12345#¶3", True),
        (CitationID, "us:347:483", True),
        (CourtID, "us:supreme:scotus", True),
        (JudgeID, "judge:ruth_bader_ginsburg:1933", True),
        (ConceptID, "concept:employment:discrimination", True),
        
        # Invalid cases
        (DocumentID, "invalid:12345", False),
        (ParagraphID, "cap:12345#3", False),
        (CitationID, "us:347", False),
        (CourtID, "us:supreme", False),
        (JudgeID, "judge:ruth_bader_ginsburg", False),
        (ConceptID, "concept:employment", False),
    ]
    
    for id_class, identifier, should_be_valid in test_cases:
        try:
            id_class(identifier)
            is_valid = True
        except ValueError:
            is_valid = False
        
        assert is_valid == should_be_valid, f"Validation failed for {id_class.__name__}('{identifier}'): expected {should_be_valid}, got {is_valid}"
    
    print("All identifier format validations passed!")


if __name__ == "__main__":
    # Run validation tests
    validate_all_id_formats()
    
    # Example usage
    doc_id = DocumentID.from_case_id(12345)
    para_id = ParagraphID.from_case_and_paragraph(12345, 3)
    cite_id = CitationID.from_citation_string("347 U.S. 483")
    
    print(f"Document ID: {doc_id}")
    print(f"Paragraph ID: {para_id}")
    print(f"Citation ID: {cite_id}")
    print(f"Parent document of paragraph: {para_id.document_id}")