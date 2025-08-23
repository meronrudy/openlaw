"""
Case Relationship Models for CAP Caselaw Plugin
Implements typed relationships between legal cases with temporal and jurisdictional validation
"""

import uuid
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from core.model import Hyperedge
from .canonical_identifiers import DocumentID
from .provenance_record import ProvenanceRecord


class RelationshipType(Enum):
    """Types of relationships between cases"""
    CITES_CASE = "cites_case"
    DISTINGUISHES = "distinguishes"
    OVERRULES = "overrules"
    FOLLOWS = "follows"
    REVERSES = "reverses"
    AFFIRMS = "affirms"
    REMANDS = "remands"
    DISAGREES_WITH = "disagrees_with"
    QUESTIONS = "questions"
    APPLIES = "applies"
    EXTENDS = "extends"
    LIMITS = "limits"
    SUPERSEDES = "supersedes"
    
    @classmethod
    def get_precedential_strength(cls, relationship_type: 'RelationshipType') -> float:
        """Get the precedential strength of different relationship types"""
        strength_mapping = {
            cls.FOLLOWS: 1.0,
            cls.APPLIES: 0.9,
            cls.EXTENDS: 0.8,
            cls.CITES_CASE: 0.7,
            cls.AFFIRMS: 0.9,
            cls.DISTINGUISHES: 0.3,
            cls.LIMITS: 0.4,
            cls.QUESTIONS: 0.2,
            cls.DISAGREES_WITH: 0.1,
            cls.OVERRULES: -1.0,  # Negative precedential value
            cls.REVERSES: -0.8,
            cls.SUPERSEDES: -1.0
        }
        return strength_mapping.get(relationship_type, 0.5)
    
    @classmethod
    def get_opposing_relationships(cls) -> List['RelationshipType']:
        """Get relationships that indicate opposition or disagreement"""
        return [
            cls.OVERRULES,
            cls.REVERSES,
            cls.DISAGREES_WITH,
            cls.DISTINGUISHES,
            cls.SUPERSEDES
        ]


@dataclass
class EvidenceSpan:
    """Represents textual evidence for a relationship"""
    paragraph_id: str
    start_char: int
    end_char: int
    text: str
    confidence: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "paragraph_id": self.paragraph_id,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "text": self.text,
            "confidence": self.confidence
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EvidenceSpan':
        return cls(**data)


@dataclass
class TemporalEvaluation:
    """Evaluation of temporal validity of a case relationship"""
    valid: bool
    temporal_distance_days: int
    precedence_order: str  # "source_before_target", "target_before_source", "contemporaneous"
    temporal_strength: float  # 0.0 to 1.0, accounting for staleness
    applicable_rules: List[str]
    evaluation_notes: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "temporal_distance_days": self.temporal_distance_days,
            "precedence_order": self.precedence_order,
            "temporal_strength": self.temporal_strength,
            "applicable_rules": self.applicable_rules,
            "evaluation_notes": self.evaluation_notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TemporalEvaluation':
        return cls(**data)


@dataclass
class JurisdictionalEvaluation:
    """Evaluation of jurisdictional validity of a case relationship"""
    valid: bool
    binding_authority: bool
    persuasive_authority: bool
    jurisdiction_overlap: List[str]
    authority_hierarchy_path: List[str]
    binding_strength: float  # 0.0 to 1.0
    applicable_rules: List[str]
    evaluation_notes: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "binding_authority": self.binding_authority,
            "persuasive_authority": self.persuasive_authority,
            "jurisdiction_overlap": self.jurisdiction_overlap,
            "authority_hierarchy_path": self.authority_hierarchy_path,
            "binding_strength": self.binding_strength,
            "applicable_rules": self.applicable_rules,
            "evaluation_notes": self.evaluation_notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JurisdictionalEvaluation':
        return cls(**data)


class CaseRelationship(Hyperedge):
    """
    Represents a relationship between two legal cases in the hypergraph.
    Includes temporal and jurisdictional validation with complete provenance.
    """
    
    def __init__(self,
                 source_case_id: Union[str, DocumentID],
                 target_case_id: Union[str, DocumentID],
                 relationship_type: RelationshipType,
                 confidence: float,
                 evidence_spans: List[EvidenceSpan],
                 extraction_method: str,
                 provenance_record: ProvenanceRecord,
                 temporal_evaluation: Optional[TemporalEvaluation] = None,
                 jurisdictional_evaluation: Optional[JurisdictionalEvaluation] = None,
                 metadata: Optional[Dict[str, Any]] = None,
                 created_at: Optional[datetime] = None):
        
        # Convert IDs to strings if needed
        source_id_str = str(source_case_id)
        target_id_str = str(target_case_id)
        
        # Initialize base HypergraphEdge
        edge_properties = {
            "relationship_type": relationship_type.value,
            "confidence": confidence,
            "evidence_spans": [span.to_dict() for span in evidence_spans],
            "extraction_method": extraction_method,
            "precedential_strength": RelationshipType.get_precedential_strength(relationship_type),
            "temporal_evaluation": temporal_evaluation.to_dict() if temporal_evaluation else None,
            "jurisdictional_evaluation": jurisdictional_evaluation.to_dict() if jurisdictional_evaluation else None,
            "metadata": metadata or {}
        }
        
        super().__init__(
            id=str(uuid.uuid4()),
            relation=relationship_type.value,
            heads=[target_id_str],  # The case being referenced
            tails=[source_id_str],  # The case doing the referencing
            properties=edge_properties,
            created_at=created_at or datetime.utcnow(),
            source_plugin="caselaw_access_project"
        )
        
        # Store typed attributes
        self._source_case_id = source_id_str
        self._target_case_id = target_id_str
        self._relationship_type = relationship_type
        self._confidence = confidence
        self._evidence_spans = evidence_spans
        self._extraction_method = extraction_method
        self._provenance_record = provenance_record
        self._temporal_evaluation = temporal_evaluation
        self._jurisdictional_evaluation = jurisdictional_evaluation
        
        # Validate relationship
        self._validate()
    
    @property
    def source_case_id(self) -> str:
        """The case that establishes this relationship (citing case)"""
        return self._source_case_id
    
    @property
    def target_case_id(self) -> str:
        """The case being referenced in the relationship (cited case)"""
        return self._target_case_id
    
    @property
    def relationship_type(self) -> RelationshipType:
        """The type of relationship"""
        return self._relationship_type
    
    @property
    def confidence(self) -> float:
        """Confidence score for this relationship (0.0 to 1.0)"""
        return self._confidence
    
    @property
    def evidence_spans(self) -> List[EvidenceSpan]:
        """Textual evidence supporting this relationship"""
        return self._evidence_spans.copy()
    
    @property
    def extraction_method(self) -> str:
        """Method used to extract this relationship"""
        return self._extraction_method
    
    @property
    def provenance_record(self) -> ProvenanceRecord:
        """Provenance record for this relationship"""
        return self._provenance_record
    
    @property
    def temporal_evaluation(self) -> Optional[TemporalEvaluation]:
        """Temporal validity evaluation"""
        return self._temporal_evaluation
    
    @property
    def jurisdictional_evaluation(self) -> Optional[JurisdictionalEvaluation]:
        """Jurisdictional validity evaluation"""
        return self._jurisdictional_evaluation
    
    @property
    def precedential_strength(self) -> float:
        """Calculated precedential strength of this relationship"""
        base_strength = RelationshipType.get_precedential_strength(self._relationship_type)
        
        # Adjust for confidence
        confidence_adjusted = base_strength * self._confidence
        
        # Adjust for temporal factors
        if self._temporal_evaluation:
            confidence_adjusted *= self._temporal_evaluation.temporal_strength
        
        # Adjust for jurisdictional factors
        if self._jurisdictional_evaluation:
            confidence_adjusted *= self._jurisdictional_evaluation.binding_strength
        
        return max(-1.0, min(1.0, confidence_adjusted))  # Clamp to [-1, 1]
    
    @property
    def is_supporting_precedent(self) -> bool:
        """Whether this relationship indicates supporting precedent"""
        return self.precedential_strength > 0.0
    
    @property
    def is_opposing_precedent(self) -> bool:
        """Whether this relationship indicates opposing precedent"""
        return self.precedential_strength < 0.0
    
    def _validate(self):
        """Validate relationship consistency"""
        # Source and target cannot be the same
        if self._source_case_id == self._target_case_id:
            raise ValueError("Source and target case cannot be the same")
        
        # Confidence must be between 0 and 1
        if not 0.0 <= self._confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self._confidence}")
        
        # Must have at least one evidence span
        if not self._evidence_spans:
            raise ValueError("Relationship must have at least one evidence span")
        
        # Validate evidence span confidences
        for span in self._evidence_spans:
            if not 0.0 <= span.confidence <= 1.0:
                raise ValueError(f"Evidence span confidence must be between 0.0 and 1.0, got {span.confidence}")
    
    def add_temporal_evaluation(self, evaluation: TemporalEvaluation):
        """Add temporal evaluation to this relationship"""
        self._temporal_evaluation = evaluation
        self.properties["temporal_evaluation"] = evaluation.to_dict()
    
    def add_jurisdictional_evaluation(self, evaluation: JurisdictionalEvaluation):
        """Add jurisdictional evaluation to this relationship"""
        self._jurisdictional_evaluation = evaluation
        self.properties["jurisdictional_evaluation"] = evaluation.to_dict()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        base_dict = super().to_dict()
        base_dict.update({
            "source_case_id": self._source_case_id,
            "target_case_id": self._target_case_id,
            "relationship_type": self._relationship_type.value,
            "confidence": self._confidence,
            "evidence_spans": [span.to_dict() for span in self._evidence_spans],
            "extraction_method": self._extraction_method,
            "provenance_id": self._provenance_record.id,
            "precedential_strength": self.precedential_strength
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], provenance_record: ProvenanceRecord) -> 'CaseRelationship':
        """Create CaseRelationship from dictionary representation"""
        # Reconstruct evidence spans
        evidence_spans = [EvidenceSpan.from_dict(span_data) for span_data in data["evidence_spans"]]
        
        # Reconstruct evaluations
        temporal_eval = None
        if data.get("temporal_evaluation"):
            temporal_eval = TemporalEvaluation.from_dict(data["temporal_evaluation"])
        
        jurisdictional_eval = None
        if data.get("jurisdictional_evaluation"):
            jurisdictional_eval = JurisdictionalEvaluation.from_dict(data["jurisdictional_evaluation"])
        
        relationship = cls(
            source_case_id=data["source_case_id"],
            target_case_id=data["target_case_id"],
            relationship_type=RelationshipType(data["relationship_type"]),
            confidence=data["confidence"],
            evidence_spans=evidence_spans,
            extraction_method=data["extraction_method"],
            provenance_record=provenance_record,
            temporal_evaluation=temporal_eval,
            jurisdictional_evaluation=jurisdictional_eval,
            metadata=data.get("metadata"),
            created_at=datetime.fromisoformat(data["created_at"])
        )
        
        # Override generated ID with stored ID
        relationship._id = data["id"]
        
        return relationship
    
    @classmethod
    def from_extraction_result(cls,
                             source_case_id: Union[str, DocumentID],
                             target_case_id: Union[str, DocumentID],
                             relationship_data: Dict[str, Any],
                             provenance_record: ProvenanceRecord) -> 'CaseRelationship':
        """Create CaseRelationship from extraction result"""
        
        # Parse relationship type
        relationship_type_str = relationship_data.get("relationship_type", "cites_case")
        try:
            relationship_type = RelationshipType(relationship_type_str)
        except ValueError:
            # Default to citation if type is unknown
            relationship_type = RelationshipType.CITES_CASE
        
        # Parse evidence spans
        evidence_spans = []
        for span_data in relationship_data.get("evidence_spans", []):
            evidence_spans.append(EvidenceSpan(
                paragraph_id=span_data.get("paragraph_id", ""),
                start_char=span_data.get("start_char", 0),
                end_char=span_data.get("end_char", 0),
                text=span_data.get("text", ""),
                confidence=span_data.get("confidence", 0.5)
            ))
        
        # If no evidence spans provided, create a placeholder
        if not evidence_spans:
            evidence_spans.append(EvidenceSpan(
                paragraph_id="unknown",
                start_char=0,
                end_char=0,
                text="Relationship extracted without specific evidence span",
                confidence=0.5
            ))
        
        return cls(
            source_case_id=source_case_id,
            target_case_id=target_case_id,
            relationship_type=relationship_type,
            confidence=relationship_data.get("confidence", 0.7),
            evidence_spans=evidence_spans,
            extraction_method=relationship_data.get("extraction_method", "unknown"),
            provenance_record=provenance_record,
            metadata=relationship_data.get("metadata", {})
        )


class RelationshipValidator:
    """Validates case relationships for temporal and jurisdictional consistency"""
    
    @staticmethod
    def validate_temporal_relationship(relationship: CaseRelationship,
                                     source_case_data: Dict[str, Any],
                                     target_case_data: Dict[str, Any]) -> TemporalEvaluation:
        """Validate temporal consistency of a case relationship"""
        
        # Extract decision dates
        source_date_str = source_case_data.get("decision_date")
        target_date_str = target_case_data.get("decision_date")
        
        if not source_date_str or not target_date_str:
            return TemporalEvaluation(
                valid=True,  # Can't validate without dates, assume valid
                temporal_distance_days=0,
                precedence_order="unknown",
                temporal_strength=0.5,
                applicable_rules=["missing_dates"],
                evaluation_notes="Cannot validate temporal relationship due to missing decision dates"
            )
        
        # Parse dates
        try:
            source_date = datetime.fromisoformat(source_date_str).date()
            target_date = datetime.fromisoformat(target_date_str).date()
        except (ValueError, TypeError):
            return TemporalEvaluation(
                valid=True,
                temporal_distance_days=0,
                precedence_order="unknown",
                temporal_strength=0.5,
                applicable_rules=["invalid_dates"],
                evaluation_notes="Cannot parse decision dates for temporal validation"
            )
        
        # Calculate temporal relationship
        temporal_distance = (source_date - target_date).days
        
        if temporal_distance > 0:
            precedence_order = "target_before_source"
        elif temporal_distance < 0:
            precedence_order = "source_before_target"
        else:
            precedence_order = "contemporaneous"
        
        # Validate relationship type against temporal order
        valid = True
        applicable_rules = []
        evaluation_notes = ""
        
        if relationship.relationship_type in [RelationshipType.OVERRULES, RelationshipType.SUPERSEDES]:
            # Overruling case must be decided after the overruled case
            if precedence_order != "target_before_source":
                valid = False
                applicable_rules.append("overrule_temporal_violation")
                evaluation_notes = f"Overruling relationship invalid: {relationship.relationship_type.value} requires source case to be decided after target case"
        
        # Calculate temporal strength (decreases with age)
        abs_distance = abs(temporal_distance)
        if abs_distance <= 30:  # Within a month
            temporal_strength = 1.0
        elif abs_distance <= 365:  # Within a year
            temporal_strength = 0.9
        elif abs_distance <= 3650:  # Within 10 years
            temporal_strength = 0.8
        elif abs_distance <= 18250:  # Within 50 years
            temporal_strength = 0.6
        else:  # Older than 50 years
            temporal_strength = 0.4
        
        return TemporalEvaluation(
            valid=valid,
            temporal_distance_days=temporal_distance,
            precedence_order=precedence_order,
            temporal_strength=temporal_strength,
            applicable_rules=applicable_rules,
            evaluation_notes=evaluation_notes
        )
    
    @staticmethod
    def validate_jurisdictional_relationship(relationship: CaseRelationship,
                                          source_case_data: Dict[str, Any],
                                          target_case_data: Dict[str, Any]) -> JurisdictionalEvaluation:
        """Validate jurisdictional consistency of a case relationship"""
        
        source_jurisdiction = source_case_data.get("jurisdiction", "")
        target_jurisdiction = target_case_data.get("jurisdiction", "")
        source_court = source_case_data.get("court", {})
        target_court = target_case_data.get("court", {})
        
        # Determine authority hierarchy
        binding_authority = False
        persuasive_authority = False
        jurisdiction_overlap = []
        authority_hierarchy_path = []
        binding_strength = 0.0
        
        if source_jurisdiction == target_jurisdiction:
            jurisdiction_overlap.append(source_jurisdiction)
            
            # Same jurisdiction - check court hierarchy
            source_court_level = source_court.get("court_level", "trial")
            target_court_level = target_court.get("court_level", "trial")
            
            # Simplified hierarchy (would be more complex in production)
            hierarchy = {
                "supreme": 3,
                "appellate": 2,
                "trial": 1
            }
            
            source_level = hierarchy.get(source_court_level, 1)
            target_level = hierarchy.get(target_court_level, 1)
            
            if target_level >= source_level:
                binding_authority = True
                binding_strength = 1.0 if target_level > source_level else 0.8
            else:
                persuasive_authority = True
                binding_strength = 0.6
                
            authority_hierarchy_path = [target_court.get("name", ""), source_court.get("name", "")]
        
        elif source_jurisdiction.startswith("us") and target_jurisdiction.startswith("us"):
            # Both US jurisdictions - federal vs state analysis
            persuasive_authority = True
            binding_strength = 0.4
            jurisdiction_overlap.append("us")
            
        else:
            # Different jurisdictions - persuasive only
            persuasive_authority = True
            binding_strength = 0.2
        
        return JurisdictionalEvaluation(
            valid=True,  # All relationships are jurisdictionally valid, just with different strengths
            binding_authority=binding_authority,
            persuasive_authority=persuasive_authority,
            jurisdiction_overlap=jurisdiction_overlap,
            authority_hierarchy_path=authority_hierarchy_path,
            binding_strength=binding_strength,
            applicable_rules=["basic_hierarchy"],
            evaluation_notes=f"Jurisdictional analysis: {source_jurisdiction} -> {target_jurisdiction}"
        )


# Factory for creating relationships
class RelationshipFactory:
    """Factory for creating case relationships with validation"""
    
    @staticmethod
    def create_validated_relationship(source_case_id: Union[str, DocumentID],
                                    target_case_id: Union[str, DocumentID],
                                    relationship_data: Dict[str, Any],
                                    source_case_data: Dict[str, Any],
                                    target_case_data: Dict[str, Any],
                                    provenance_record: ProvenanceRecord) -> CaseRelationship:
        """Create a case relationship with temporal and jurisdictional validation"""
        
        # Create base relationship
        relationship = CaseRelationship.from_extraction_result(
            source_case_id=source_case_id,
            target_case_id=target_case_id,
            relationship_data=relationship_data,
            provenance_record=provenance_record
        )
        
        # Add temporal validation
        temporal_eval = RelationshipValidator.validate_temporal_relationship(
            relationship, source_case_data, target_case_data
        )
        relationship.add_temporal_evaluation(temporal_eval)
        
        # Add jurisdictional validation
        jurisdictional_eval = RelationshipValidator.validate_jurisdictional_relationship(
            relationship, source_case_data, target_case_data
        )
        relationship.add_jurisdictional_evaluation(jurisdictional_eval)
        
        return relationship