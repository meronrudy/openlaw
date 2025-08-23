"""
Plugin SDK for Legal Hypergraph System

Abstract interfaces for domain experts to extend the system with legal knowledge
without modifying core code. Provides clean separation between core substrate
and domain-specific implementations.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from core.model import Node, Hyperedge, Context


class RawDoc(BaseModel):
    """
    Input document for plugin processing
    
    Encapsulates legal documents with metadata for domain-specific extraction.
    """
    id: str = Field(..., description="Unique document identifier")
    text: str = Field(..., description="Full document text")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Document metadata")
    source_info: Optional[Dict[str, Any]] = Field(None, description="Citation, URL, etc.")


class OntologyProvider(ABC):
    """
    Interface for providing domain-specific legal ontologies
    
    Domain experts implement this to define legal concepts, properties,
    and validation constraints for their area of expertise.
    """
    
    @abstractmethod
    def classes(self) -> List[Dict[str, Any]]:
        """
        Return legal concept classes for this domain
        
        Returns:
            List of class definitions with name, description, properties
        """
        pass
        
    @abstractmethod
    def properties(self) -> List[Dict[str, Any]]:
        """
        Return properties/relations for this domain
        
        Returns:
            List of property definitions with name, domain, range
        """
        pass
        
    @abstractmethod
    def constraints(self) -> List[Dict[str, Any]]:
        """
        Return validation constraints (SHACL-like)
        
        Returns:
            List of constraint definitions for validation
        """
        pass


class MappingProvider(ABC):
    """
    Interface for extracting legal entities and relations from text
    
    Domain experts implement this to provide NLP extraction specialized
    for their legal domain (employment law, contracts, etc.).
    """
    
    @abstractmethod
    def extract_entities(self, doc: RawDoc, ctx: Optional[Context] = None) -> List[Node]:
        """
        Extract legal entities using domain-specific NER
        
        Args:
            doc: Input document to process
            ctx: Optional legal context for jurisdiction/temporal validity
            
        Returns:
            List of extracted entity nodes with provenance
        """
        pass
        
    @abstractmethod
    def extract_relations(self, nodes: List[Node], doc: RawDoc, 
                         ctx: Optional[Context] = None) -> List[Hyperedge]:
        """
        Extract relations and citations between entities
        
        Args:
            nodes: Previously extracted entities
            doc: Input document to process
            ctx: Optional legal context
            
        Returns:
            List of relation hyperedges with provenance
        """
        pass
        
    @abstractmethod
    def extract_obligations(self, doc: RawDoc, 
                           ctx: Optional[Context] = None) -> List[Hyperedge]:
        """
        Extract duty/right/obligation patterns
        
        Args:
            doc: Input document to process
            ctx: Optional legal context
            
        Returns:
            List of obligation hyperedges with provenance
        """
        pass


class RuleProvider(ABC):
    """
    Interface for providing domain-specific legal rules
    
    Domain experts implement this to encode statutory rules, case law,
    and defeasible reasoning patterns for their area of law.
    """
    
    @abstractmethod
    def statutory_rules(self, ctx: Optional[Context] = None) -> List[Hyperedge]:
        """
        Rules derived from statutes and regulations
        
        Args:
            ctx: Optional context to filter applicable rules
            
        Returns:
            List of statutory rule hyperedges with strong provenance
        """
        pass
        
    @abstractmethod
    def case_law_rules(self, ctx: Optional[Context] = None) -> List[Hyperedge]:
        """
        Rules derived from judicial precedents
        
        Args:
            ctx: Optional context to filter applicable precedents
            
        Returns:
            List of case law rule hyperedges with precedential provenance
        """
        pass
        
    @abstractmethod
    def exception_rules(self, ctx: Optional[Context] = None) -> List[Hyperedge]:
        """
        Defeasible rules and exceptions
        
        Args:
            ctx: Optional context to filter applicable exceptions
            
        Returns:
            List of exception rule hyperedges for defeasible reasoning
        """
        pass


class LegalExplainer(ABC):
    """
    Interface for generating legal explanations
    
    Domain experts implement this to provide human-readable explanations
    of reasoning chains with appropriate legal citations and precedents.
    """
    
    @abstractmethod
    def statutory_explanation(self, conclusion_id: str, graph) -> str:
        """
        Explain reasoning chain back to statutory authority
        
        Args:
            conclusion_id: ID of the conclusion node to explain
            graph: Graph containing the reasoning chain
            
        Returns:
            Human-readable explanation with statutory citations
        """
        pass
        
    @abstractmethod
    def precedential_explanation(self, conclusion_id: str, graph) -> str:
        """
        Explain reasoning using case law precedents
        
        Args:
            conclusion_id: ID of the conclusion node to explain
            graph: Graph containing the reasoning chain
            
        Returns:
            Human-readable explanation with case citations
        """
        pass
        
    @abstractmethod
    def counterfactual_explanation(self, conclusion_id: str, graph) -> str:
        """
        Show what would change if key facts were different
        
        Args:
            conclusion_id: ID of the conclusion node to explain
            graph: Graph containing the reasoning chain
            
        Returns:
            Human-readable counterfactual explanation
        """
        pass


class ValidationProvider(ABC):
    """
    Interface for domain-specific validation
    
    Domain experts implement this to validate that extractions and
    reasoning meet domain-specific requirements and legal standards.
    """
    
    @abstractmethod
    def validate_extraction(self, nodes: List[Node], edges: List[Hyperedge]) -> List[str]:
        """
        Validate extracted entities meet domain requirements
        
        Args:
            nodes: Extracted entity nodes
            edges: Extracted relation edges
            
        Returns:
            List of validation error messages (empty if valid)
        """
        pass
        
    @abstractmethod
    def validate_reasoning(self, conclusion: Node, support: List[Hyperedge]) -> bool:
        """
        Validate that reasoning chain is sound
        
        Args:
            conclusion: Conclusion node to validate
            support: Supporting evidence edges
            
        Returns:
            True if reasoning is valid, False otherwise
        """
        pass