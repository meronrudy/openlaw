"""
Core Data Models for Legal Hypergraph System

Pydantic models for Node, Hyperedge, Provenance, and Context with validation.
This implements the minimal requirements to pass the TDD tests.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
import uuid


class Provenance(BaseModel):
    """
    Provenance model - tracks where legal information came from
    
    Required for all entities in the system to ensure explainability.
    """
    source: List[Dict[str, Any]] = Field(...)
    method: str = Field(..., min_length=1)
    agent: str = Field(..., min_length=1)
    time: datetime
    confidence: float = Field(...)
    hash: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None
    derivation: Optional[List[str]] = None
    
    @field_validator('source')
    @classmethod
    def source_cannot_be_empty(cls, v):
        if not v:
            raise ValueError("Source cannot be empty")
        return v
    
    @field_validator('confidence')
    @classmethod
    def confidence_bounds(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v


class Context(BaseModel):
    """
    Legal context for jurisdiction and temporal validity
    """
    jurisdiction: Optional[str] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    law_type: Optional[str] = None
    authority_level: Optional[str] = None
    
    def is_applicable_in(self, other: 'Context') -> bool:
        """Check if this context applies within another context"""
        if not other:
            return True
            
        # Jurisdiction check - hierarchical (e.g., "US" applies to "US-CA")
        if self.jurisdiction and other.jurisdiction:
            if not other.jurisdiction.startswith(self.jurisdiction):
                return False
        
        # Temporal validity checks
        if self.valid_from and other.valid_from:
            if other.valid_from < self.valid_from:
                return False
                
        if self.valid_to and other.valid_to:
            if other.valid_to > self.valid_to:
                return False
                
        return True


class Node(BaseModel):
    """
    Hypergraph node with provenance
    """
    id: str = Field(default_factory=lambda: f"node:{uuid.uuid4().hex[:12]}")
    type: str
    labels: List[str] = Field(default_factory=list)
    data: Dict[str, Any] = Field(default_factory=dict)
    context: Optional[Context] = None
    prov: Provenance


class Hyperedge(BaseModel):
    """
    Hypergraph edge supporting many-to-many relationships
    """
    id: str = Field(default_factory=lambda: f"edge:{uuid.uuid4().hex[:12]}")
    relation: str
    tails: List[str] = Field(...)
    heads: List[str] = Field(...)
    qualifiers: Dict[str, Any] = Field(default_factory=dict)
    context: Optional[Context] = None
    prov: Provenance
    
    @field_validator('tails')
    @classmethod
    def tails_not_empty(cls, v):
        if not v:
            raise ValueError("Hyperedge must have at least one tail")
        return v
    
    @field_validator('heads')
    @classmethod
    def heads_not_empty(cls, v):
        if not v:
            raise ValueError("Hyperedge must have at least one head")
        return v


# Helper functions for creating nodes and edges

def mk_node(type: str, data: Dict[str, Any], prov: Provenance, 
           labels: Optional[List[str]] = None, ctx: Optional[Context] = None, 
           id: Optional[str] = None) -> Node:
    """Factory function for creating nodes with validation"""
    return Node(
        id=id or f"node:{uuid.uuid4().hex[:12]}",
        type=type,
        data=data,
        prov=prov,
        labels=labels or [],
        context=ctx
    )


def mk_edge(relation: str, tails: List[str], heads: List[str], prov: Provenance,
           qualifiers: Optional[Dict[str, Any]] = None, ctx: Optional[Context] = None, 
           id: Optional[str] = None) -> Hyperedge:
    """Factory function for creating hyperedges with validation"""
    if not tails:
        raise ValueError("Hyperedge must have at least one tail")
    if not heads:
        raise ValueError("Hyperedge must have at least one head")
    
    return Hyperedge(
        id=id or f"edge:{uuid.uuid4().hex[:12]}",
        relation=relation,
        tails=tails,
        heads=heads,
        prov=prov,
        qualifiers=qualifiers or {},
        context=ctx
    )