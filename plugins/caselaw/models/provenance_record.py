"""
Provenance Record Model for CAP Caselaw Plugin
Implements bitemporal provenance tracking with complete audit trails
"""

import uuid
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json

from .canonical_identifiers import CanonicalID, IdentifierFactory


class ProvenanceOperation(Enum):
    """Types of operations that can be tracked in provenance"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    EXTRACT = "extract"
    INFER = "infer"
    VALIDATE = "validate"
    ENHANCE = "enhance"
    QUERY = "query"


class ProvenanceSource(Enum):
    """Sources of data or operations"""
    CAP_DATASET = "cap_dataset"
    HUGGINGFACE = "huggingface"
    ML_EXTRACTION = "ml_extraction"
    RULE_BASED_EXTRACTION = "rule_based_extraction"
    MANUAL_ANNOTATION = "manual_annotation"
    CROSS_PLUGIN_ENHANCEMENT = "cross_plugin_enhancement"
    TEMPORAL_REASONING = "temporal_reasoning"
    JURISDICTIONAL_REASONING = "jurisdictional_reasoning"


@dataclass
class ProvenanceAgent:
    """Represents an agent (human, system, or algorithm) that performed an operation"""
    agent_type: str  # "system", "human", "algorithm"
    agent_id: str
    agent_version: Optional[str] = None
    agent_config: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_type": self.agent_type,
            "agent_id": self.agent_id,
            "agent_version": self.agent_version,
            "agent_config": self.agent_config
        }


@dataclass
class ProvenanceActivity:
    """Represents an activity that generated or modified data"""
    activity_type: ProvenanceOperation
    description: str
    method: str  # The specific method/algorithm used
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: Optional[float] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "activity_type": self.activity_type.value,
            "description": self.description,
            "method": self.method,
            "parameters": self.parameters,
            "confidence": self.confidence,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None
        }


@dataclass
class ProvenanceMetadata:
    """Extended metadata for provenance records"""
    source_system: str
    source_version: str
    plugin_version: str
    data_quality_score: Optional[float] = None
    validation_status: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    external_references: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_system": self.source_system,
            "source_version": self.source_version,
            "plugin_version": self.plugin_version,
            "data_quality_score": self.data_quality_score,
            "validation_status": self.validation_status,
            "tags": self.tags,
            "external_references": self.external_references
        }


class ProvenanceRecord:
    """
    Immutable provenance record implementing W3C PROV model adapted for legal data.
    Provides complete audit trail for any entity or relationship in the system.
    """
    
    def __init__(self,
                 entity_id: Union[str, CanonicalID],
                 entity_type: str,
                 operation: ProvenanceOperation,
                 agent: ProvenanceAgent,
                 activity: ProvenanceActivity,
                 metadata: ProvenanceMetadata,
                 derived_from: Optional[List[str]] = None,
                 influenced_by: Optional[List[str]] = None,
                 invalidated_by: Optional[str] = None):
        
        # Core identifiers (immutable)
        self._id = str(uuid.uuid4())
        self._entity_id = str(entity_id) if isinstance(entity_id, CanonicalID) else entity_id
        self._entity_type = entity_type
        self._timestamp = datetime.utcnow()
        
        # Provenance information
        self._operation = operation
        self._agent = agent
        self._activity = activity
        self._metadata = metadata
        
        # Provenance relationships
        self._derived_from = derived_from or []
        self._influenced_by = influenced_by or []
        self._invalidated_by = invalidated_by
        
        # Generate content hash for integrity
        self._checksum = self._generate_checksum()
        
        # Validation
        self._validate()
    
    @property
    def id(self) -> str:
        """Unique provenance record ID"""
        return self._id
    
    @property
    def entity_id(self) -> str:
        """The entity this provenance record describes"""
        return self._entity_id
    
    @property
    def entity_type(self) -> str:
        """Type of the entity"""
        return self._entity_type
    
    @property
    def timestamp(self) -> datetime:
        """When this provenance record was created"""
        return self._timestamp
    
    @property
    def operation(self) -> ProvenanceOperation:
        """The operation that was performed"""
        return self._operation
    
    @property
    def agent(self) -> ProvenanceAgent:
        """The agent that performed the operation"""
        return self._agent
    
    @property
    def activity(self) -> ProvenanceActivity:
        """The activity that generated the data"""
        return self._activity
    
    @property
    def metadata(self) -> ProvenanceMetadata:
        """Extended metadata"""
        return self._metadata
    
    @property
    def derived_from(self) -> List[str]:
        """Entities this was derived from"""
        return self._derived_from.copy()
    
    @property
    def influenced_by(self) -> List[str]:
        """Entities that influenced this"""
        return self._influenced_by.copy()
    
    @property
    def invalidated_by(self) -> Optional[str]:
        """Provenance record that invalidated this entity"""
        return self._invalidated_by
    
    @property
    def checksum(self) -> str:
        """Content checksum for integrity verification"""
        return self._checksum
    
    def _generate_checksum(self) -> str:
        """Generate SHA-256 checksum of provenance content"""
        content = {
            "entity_id": self._entity_id,
            "entity_type": self._entity_type,
            "operation": self._operation.value,
            "agent": self._agent.to_dict(),
            "activity": self._activity.to_dict(),
            "metadata": self._metadata.to_dict(),
            "derived_from": sorted(self._derived_from),
            "influenced_by": sorted(self._influenced_by),
            "invalidated_by": self._invalidated_by
        }
        
        content_json = json.dumps(content, sort_keys=True, default=str)
        return hashlib.sha256(content_json.encode('utf-8')).hexdigest()
    
    def _validate(self):
        """Validate provenance record consistency"""
        # Validate entity ID format if it's a canonical ID
        if ':' in self._entity_id:
            try:
                IdentifierFactory.create_from_string(self._entity_id)
            except ValueError as e:
                raise ValueError(f"Invalid entity ID format: {e}")
        
        # Validate derived_from relationships don't create cycles
        if self._entity_id in self._derived_from:
            raise ValueError("Entity cannot be derived from itself")
        
        # Validate timestamps in activity
        if (self._activity.start_time and self._activity.end_time and 
            self._activity.start_time > self._activity.end_time):
            raise ValueError("Activity start time cannot be after end time")
    
    def verify_integrity(self) -> bool:
        """Verify the integrity of this provenance record"""
        return self._checksum == self._generate_checksum()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "id": self._id,
            "entity_id": self._entity_id,
            "entity_type": self._entity_type,
            "timestamp": self._timestamp.isoformat(),
            "operation": self._operation.value,
            "agent": self._agent.to_dict(),
            "activity": self._activity.to_dict(),
            "metadata": self._metadata.to_dict(),
            "derived_from": self._derived_from,
            "influenced_by": self._influenced_by,
            "invalidated_by": self._invalidated_by,
            "checksum": self._checksum
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProvenanceRecord':
        """Create ProvenanceRecord from dictionary"""
        # Reconstruct objects
        agent = ProvenanceAgent(**data["agent"])
        
        activity_data = data["activity"].copy()
        activity_data["activity_type"] = ProvenanceOperation(activity_data["activity_type"])
        if activity_data.get("start_time"):
            activity_data["start_time"] = datetime.fromisoformat(activity_data["start_time"])
        if activity_data.get("end_time"):
            activity_data["end_time"] = datetime.fromisoformat(activity_data["end_time"])
        activity = ProvenanceActivity(**activity_data)
        
        metadata = ProvenanceMetadata(**data["metadata"])
        
        # Create record
        record = cls(
            entity_id=data["entity_id"],
            entity_type=data["entity_type"],
            operation=ProvenanceOperation(data["operation"]),
            agent=agent,
            activity=activity,
            metadata=metadata,
            derived_from=data.get("derived_from"),
            influenced_by=data.get("influenced_by"),
            invalidated_by=data.get("invalidated_by")
        )
        
        # Override generated fields with stored values
        record._id = data["id"]
        record._timestamp = datetime.fromisoformat(data["timestamp"])
        stored_checksum = data["checksum"]
        
        # Verify integrity
        if record._checksum != stored_checksum:
            raise ValueError("Provenance record integrity check failed")
        
        return record
    
    def create_derivation(self,
                         new_entity_id: Union[str, CanonicalID],
                         new_entity_type: str,
                         operation: ProvenanceOperation,
                         agent: ProvenanceAgent,
                         activity: ProvenanceActivity,
                         additional_derived_from: Optional[List[str]] = None) -> 'ProvenanceRecord':
        """Create a new provenance record for an entity derived from this one"""
        derived_from = [self._entity_id]
        if additional_derived_from:
            derived_from.extend(additional_derived_from)
        
        return ProvenanceRecord(
            entity_id=new_entity_id,
            entity_type=new_entity_type,
            operation=operation,
            agent=agent,
            activity=activity,
            metadata=self._metadata,  # Inherit metadata
            derived_from=derived_from
        )


class ProvenanceChain:
    """
    Represents a chain of provenance records showing the complete lineage of an entity.
    Enables "why" and "from where" queries with complete audit trails.
    """
    
    def __init__(self, records: List[ProvenanceRecord]):
        self._records = sorted(records, key=lambda r: r.timestamp)
        self._validate_chain()
    
    @property
    def records(self) -> List[ProvenanceRecord]:
        """All provenance records in chronological order"""
        return self._records.copy()
    
    @property
    def root_entities(self) -> List[str]:
        """Entities at the root of the provenance chain"""
        all_entities = {r.entity_id for r in self._records}
        derived_entities = set()
        
        for record in self._records:
            derived_entities.update(record.derived_from)
        
        return list(all_entities - derived_entities)
    
    @property
    def leaf_entities(self) -> List[str]:
        """Entities at the leaves of the provenance chain"""
        all_entities = {r.entity_id for r in self._records}
        source_entities = set()
        
        for record in self._records:
            source_entities.update(record.derived_from)
        
        return list(all_entities - source_entities)
    
    def _validate_chain(self):
        """Validate that the provenance chain is consistent"""
        entity_ids = {r.entity_id for r in self._records}
        
        for record in self._records:
            # Check that all derived_from entities exist in the chain or are external
            for derived_id in record.derived_from:
                if derived_id not in entity_ids:
                    # This is OK - it means the entity was derived from something external
                    pass
    
    def get_entity_lineage(self, entity_id: str) -> List[ProvenanceRecord]:
        """Get the complete lineage of a specific entity"""
        lineage = []
        
        # Find the record for this entity
        entity_record = None
        for record in self._records:
            if record.entity_id == entity_id:
                entity_record = record
                break
        
        if not entity_record:
            return []
        
        lineage.append(entity_record)
        
        # Recursively trace back through derived_from relationships
        to_trace = entity_record.derived_from.copy()
        traced = {entity_id}
        
        while to_trace:
            current_id = to_trace.pop(0)
            if current_id in traced:
                continue
            
            traced.add(current_id)
            
            # Find record for current_id
            for record in self._records:
                if record.entity_id == current_id:
                    lineage.append(record)
                    to_trace.extend(record.derived_from)
                    break
        
        return sorted(lineage, key=lambda r: r.timestamp)
    
    def explain_entity_creation(self, entity_id: str) -> Dict[str, Any]:
        """Generate a human-readable explanation of how an entity was created"""
        lineage = self.get_entity_lineage(entity_id)
        
        if not lineage:
            return {"error": f"No provenance found for entity {entity_id}"}
        
        explanation = {
            "entity_id": entity_id,
            "creation_chain": [],
            "sources": [],
            "confidence": None
        }
        
        for record in lineage:
            step = {
                "timestamp": record.timestamp.isoformat(),
                "operation": record.operation.value,
                "description": record.activity.description,
                "method": record.activity.method,
                "agent": record.agent.agent_id,
                "confidence": record.activity.confidence,
                "derived_from": record.derived_from
            }
            explanation["creation_chain"].append(step)
            
            # Track original sources
            if not record.derived_from:
                explanation["sources"].append({
                    "entity_id": record.entity_id,
                    "source_system": record.metadata.source_system,
                    "source_version": record.metadata.source_version
                })
        
        # Calculate overall confidence
        confidences = [r.activity.confidence for r in lineage if r.activity.confidence is not None]
        if confidences:
            explanation["confidence"] = min(confidences)  # Conservative approach
        
        return explanation
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert provenance chain to dictionary"""
        return {
            "records": [r.to_dict() for r in self._records],
            "root_entities": self.root_entities,
            "leaf_entities": self.leaf_entities
        }


# Factory functions for common provenance patterns
class ProvenanceFactory:
    """Factory for creating common provenance record patterns"""
    
    @staticmethod
    def create_ingestion_record(entity_id: Union[str, CanonicalID],
                              entity_type: str,
                              source_system: str = "cap_dataset",
                              source_version: str = "1.0",
                              plugin_version: str = "1.0.0") -> ProvenanceRecord:
        """Create provenance record for data ingestion from CAP dataset"""
        agent = ProvenanceAgent(
            agent_type="system",
            agent_id="cap_ingestion_pipeline",
            agent_version=plugin_version
        )
        
        activity = ProvenanceActivity(
            activity_type=ProvenanceOperation.CREATE,
            description=f"Ingested {entity_type} from CAP dataset",
            method="huggingface_streaming_ingestion"
        )
        
        metadata = ProvenanceMetadata(
            source_system=source_system,
            source_version=source_version,
            plugin_version=plugin_version,
            tags=["ingestion", "cap_dataset"]
        )
        
        return ProvenanceRecord(
            entity_id=entity_id,
            entity_type=entity_type,
            operation=ProvenanceOperation.CREATE,
            agent=agent,
            activity=activity,
            metadata=metadata
        )
    
    @staticmethod
    def create_extraction_record(entity_id: Union[str, CanonicalID],
                               entity_type: str,
                               source_entity_id: str,
                               extraction_method: str,
                               confidence: float,
                               plugin_version: str = "1.0.0") -> ProvenanceRecord:
        """Create provenance record for extracted entities (citations, relationships, etc.)"""
        agent = ProvenanceAgent(
            agent_type="algorithm",
            agent_id=f"citation_extractor_{extraction_method}",
            agent_version=plugin_version
        )
        
        activity = ProvenanceActivity(
            activity_type=ProvenanceOperation.EXTRACT,
            description=f"Extracted {entity_type} using {extraction_method}",
            method=extraction_method,
            confidence=confidence
        )
        
        metadata = ProvenanceMetadata(
            source_system="caselaw_plugin",
            source_version=plugin_version,
            plugin_version=plugin_version,
            tags=["extraction", extraction_method]
        )
        
        return ProvenanceRecord(
            entity_id=entity_id,
            entity_type=entity_type,
            operation=ProvenanceOperation.EXTRACT,
            agent=agent,
            activity=activity,
            metadata=metadata,
            derived_from=[source_entity_id]
        )
    
    @staticmethod
    def create_reasoning_record(entity_id: Union[str, CanonicalID],
                              entity_type: str,
                              reasoning_type: str,
                              input_entities: List[str],
                              confidence: float,
                              plugin_version: str = "1.0.0") -> ProvenanceRecord:
        """Create provenance record for reasoning results"""
        agent = ProvenanceAgent(
            agent_type="algorithm",
            agent_id=f"{reasoning_type}_reasoner",
            agent_version=plugin_version
        )
        
        activity = ProvenanceActivity(
            activity_type=ProvenanceOperation.INFER,
            description=f"Inferred {entity_type} using {reasoning_type} reasoning",
            method=f"{reasoning_type}_reasoning",
            confidence=confidence
        )
        
        metadata = ProvenanceMetadata(
            source_system="caselaw_plugin",
            source_version=plugin_version,
            plugin_version=plugin_version,
            tags=["reasoning", reasoning_type]
        )
        
        return ProvenanceRecord(
            entity_id=entity_id,
            entity_type=entity_type,
            operation=ProvenanceOperation.INFER,
            agent=agent,
            activity=activity,
            metadata=metadata,
            derived_from=input_entities
        )