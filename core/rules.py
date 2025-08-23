"""
Legal Rule Representation and Management

Defines the LegalRule class for representing legal rules with metadata,
authority, and context information for use in the reasoning engine.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from .model import Hyperedge, Provenance, Context, mk_edge


class LegalRule(BaseModel):
    """
    Represents a legal rule with metadata and reasoning structure
    
    Encapsulates rules derived from statutes, case law, or regulations
    with authority information, priority, and contextual applicability.
    """
    id: str = Field(..., description="Unique rule identifier")
    rule_type: str = Field(..., description="Type: statutory, case_law, regulation, etc.")
    priority: int = Field(default=100, description="Rule priority for conflict resolution")
    authority: str = Field(..., description="Legal authority citation")
    jurisdiction: Optional[Context] = Field(None, description="Applicable context")
    
    # Rule structure
    premises: List[str] = Field(..., description="Premise node IDs or patterns")
    conclusions: List[str] = Field(..., description="Conclusion node IDs or patterns")
    
    # Optional metadata
    rule_text: Optional[str] = Field(None, description="Human-readable rule text")
    exceptions: List[str] = Field(default_factory=list, description="Exception conditions")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Rule confidence")
    
    def to_hyperedge(self) -> Hyperedge:
        """
        Convert this legal rule to a Hyperedge for graph storage
        
        Returns:
            Hyperedge representing this rule in the graph
        """
        # Create provenance for the rule
        prov = Provenance(
            source=[{
                "type": "legal_rule",
                "authority": self.authority,
                "rule_type": self.rule_type
            }],
            method=f"rule.{self.rule_type}",
            agent="legal.rule.system",
            time=datetime.utcnow(),
            confidence=self.confidence
        )
        
        # Create qualifiers with rule metadata
        qualifiers = {
            "rule_id": self.id,
            "rule_type": self.rule_type,
            "authority": self.authority,
            "priority": self.priority
        }
        
        if self.rule_text:
            qualifiers["rule_text"] = self.rule_text
            
        if self.exceptions:
            qualifiers["exceptions"] = self.exceptions
        
        # Create hyperedge
        return mk_edge(
            relation="implies",
            tails=self.premises,
            heads=self.conclusions,
            prov=prov,
            qualifiers=qualifiers,
            ctx=self.jurisdiction
        )
        
    def is_applicable_in(self, context: Optional[Context]) -> bool:
        """
        Check if this rule is applicable in the given context
        
        Args:
            context: Legal context to check against
            
        Returns:
            True if rule applies in the given context
        """
        if not self.jurisdiction or not context:
            return True
            
        return self.jurisdiction.is_applicable_in(context)
        
    def matches_premises(self, available_facts: List[str]) -> bool:
        """
        Check if all premises of this rule are satisfied by available facts
        
        Args:
            available_facts: List of available fact node IDs
            
        Returns:
            True if all premises are satisfied
        """
        available_set = set(available_facts)
        return all(premise in available_set for premise in self.premises)
        
    def get_priority_score(self, context: Optional[Context] = None) -> float:
        """
        Calculate priority score for conflict resolution
        
        Args:
            context: Current legal context
            
        Returns:
            Priority score (higher = more authoritative)
        """
        base_score = self.priority
        
        # Boost score based on rule type
        type_boosts = {
            "constitutional": 1000,
            "statutory": 500,
            "regulation": 300,
            "case_law": 200,
            "administrative": 100
        }
        
        base_score += type_boosts.get(self.rule_type, 0)
        
        # Boost score based on authority level
        if self.jurisdiction and self.jurisdiction.authority_level:
            authority_boosts = {
                "federal": 300,
                "state": 200,
                "local": 100
            }
            base_score += authority_boosts.get(self.jurisdiction.authority_level, 0)
            
        # Apply confidence factor
        return base_score * self.confidence