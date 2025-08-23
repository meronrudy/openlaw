"""
Case Relationship Extractor for CAP Caselaw Plugin
Identifies and classifies relationships between legal cases (cites, overrules, distinguishes, etc.)
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from ..models.case_relationship import CaseRelationship, RelationshipType
from ..models.canonical_identifiers import DocumentID
from ..models.provenance_record import ProvenanceRecord, ProvenanceOperation, ProvenanceSource
from .citation_extractor import CitationMatch

logger = logging.getLogger(__name__)


@dataclass
class RelationshipMatch:
    """Represents a detected relationship between cases"""
    source_case: Optional[str]
    target_citation: CitationMatch
    relationship_type: RelationshipType
    confidence: float
    context_text: str
    start_pos: int
    end_pos: int
    signal_words: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_case": self.source_case,
            "target_citation": self.target_citation.to_dict(),
            "relationship_type": self.relationship_type.value,
            "confidence": self.confidence,
            "context_text": self.context_text,
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
            "signal_words": self.signal_words
        }


class CaseRelationshipExtractor:
    """
    Extracts relationships between cases from legal text using pattern matching
    and contextual analysis of signal words and phrases.
    """
    
    def __init__(self, confidence_threshold: float = 0.7):
        self.confidence_threshold = confidence_threshold
        self._compile_signal_patterns()
        
    def _compile_signal_patterns(self):
        """Compile regex patterns for relationship signal words"""
        
        # Citing relationships - neutral reference
        self.cites_patterns = [
            re.compile(r'\b(?:see|citing|cited\s+in|as\s+noted\s+in|discussed\s+in)\b', re.IGNORECASE),
            re.compile(r'\b(?:accord|see\s+also|cf\.)\b', re.IGNORECASE),
            re.compile(r'\b(?:relied\s+on|referenced\s+in)\b', re.IGNORECASE)
        ]
        
        # Following relationships - positive precedent
        self.follows_patterns = [
            re.compile(r'\b(?:follow(?:s|ing|ed)|adher(?:es?|ing)\s+to)\b', re.IGNORECASE),
            re.compile(r'\b(?:consistent\s+with|in\s+accord(?:ance)?\s+with)\b', re.IGNORECASE),
            re.compile(r'\b(?:as\s+held\s+in|pursuant\s+to|under|applying)\b', re.IGNORECASE),
            re.compile(r'\b(?:guided\s+by|controlled\s+by|governed\s+by)\b', re.IGNORECASE)
        ]
        
        # Overruling relationships - negative precedent
        self.overrules_patterns = [
            re.compile(r'\b(?:overrul(?:es?|ed|ing)|overturned?|reversed?)\b', re.IGNORECASE),
            re.compile(r'\b(?:abrogat(?:es?|ed|ing)|superseded?|displaced?)\b', re.IGNORECASE),
            re.compile(r'\b(?:no\s+longer\s+good\s+law|invalid(?:ated)?)\b', re.IGNORECASE),
            re.compile(r'\b(?:expressly\s+overruled|explicitly\s+rejected)\b', re.IGNORECASE)
        ]
        
        # Distinguishing relationships - limiting precedent
        self.distinguishes_patterns = [
            re.compile(r'\b(?:distinguish(?:es?|ed|ing|able)|different(?:iated)?)\b', re.IGNORECASE),
            re.compile(r'\b(?:limit(?:s|ed|ing)|narrow(?:s|ed|ing))\b', re.IGNORECASE),
            re.compile(r'\b(?:not\s+applicable|inapplicable|distinguishable)\b', re.IGNORECASE),
            re.compile(r'\b(?:factually\s+distinct|legally\s+distinct)\b', re.IGNORECASE)
        ]
        
        # Disagreeing relationships - criticism
        self.disagrees_patterns = [
            re.compile(r'\b(?:disagree(?:s|d|ing)|reject(?:s|ed|ing))\b', re.IGNORECASE),
            re.compile(r'\b(?:criticiz(?:es?|ed|ing)|question(?:s|ed|ing))\b', re.IGNORECASE),
            re.compile(r'\b(?:doubt(?:s|ed|ing)|undermined?)\b', re.IGNORECASE),
            re.compile(r'\b(?:wrongly\s+decided|incorrectly\s+decided)\b', re.IGNORECASE)
        ]
        
        # Affirming relationships - appellate context
        self.affirms_patterns = [
            re.compile(r'\b(?:affirm(?:s|ed|ing)|uphold(?:s|ing)?|upheld)\b', re.IGNORECASE),
            re.compile(r'\b(?:confirmed?|sustained?|maintained?)\b', re.IGNORECASE),
            re.compile(r'\b(?:judgment\s+affirmed|decision\s+affirmed)\b', re.IGNORECASE)
        ]
        
        # Reversing relationships - appellate context
        self.reverses_patterns = [
            re.compile(r'\b(?:revers(?:es?|ed|ing)|vacated?)\b', re.IGNORECASE),
            re.compile(r'\b(?:set\s+aside|struck\s+down)\b', re.IGNORECASE),
            re.compile(r'\b(?:judgment\s+reversed|decision\s+reversed)\b', re.IGNORECASE)
        ]
        
        # Extending relationships - expanding precedent
        self.extends_patterns = [
            re.compile(r'\b(?:extend(?:s|ed|ing)|expand(?:s|ed|ing))\b', re.IGNORECASE),
            re.compile(r'\b(?:broaden(?:s|ed|ing)|amplif(?:ies?|ied|ying))\b', re.IGNORECASE),
            re.compile(r'\b(?:builds?\s+on|further\s+develops?)\b', re.IGNORECASE)
        ]
        
        # Applying relationships - direct application
        self.applies_patterns = [
            re.compile(r'\b(?:appl(?:ies|ied|ying)|implement(?:s|ed|ing))\b', re.IGNORECASE),
            re.compile(r'\b(?:enforce(?:s|d|ing)|effectuat(?:es?|ed|ing))\b', re.IGNORECASE),
            re.compile(r'\b(?:in\s+accordance\s+with|consistent\s+with)\b', re.IGNORECASE)
        ]
    
    def extract_relationships(self, text: str, citations: List[CitationMatch], 
                            source_case_id: Optional[str] = None) -> List[RelationshipMatch]:
        """
        Extract case relationships from text using citations and signal words
        
        Args:
            text: Input text to analyze
            citations: Previously extracted citations
            source_case_id: Optional ID of the source case
            
        Returns:
            List of relationship matches found
        """
        relationships = []
        
        for citation in citations:
            # Analyze context around each citation for relationship signals
            context_relationships = self._analyze_citation_context(text, citation, source_case_id)
            relationships.extend(context_relationships)
        
        # Filter by confidence threshold
        filtered_relationships = [r for r in relationships if r.confidence >= self.confidence_threshold]
        
        # Sort by position in text
        filtered_relationships.sort(key=lambda x: x.start_pos)
        
        return filtered_relationships
    
    def _analyze_citation_context(self, text: str, citation: CitationMatch, 
                                 source_case_id: Optional[str]) -> List[RelationshipMatch]:
        """Analyze context around a citation to identify relationships"""
        relationships = []
        
        # Define context window around citation
        context_window = 200  # characters before and after citation
        start_pos = max(0, citation.start_pos - context_window)
        end_pos = min(len(text), citation.end_pos + context_window)
        context_text = text[start_pos:end_pos]
        
        # Test each relationship type
        relationship_tests = [
            (self.follows_patterns, RelationshipType.FOLLOWS, 0.8),
            (self.overrules_patterns, RelationshipType.OVERRULES, 0.9),
            (self.distinguishes_patterns, RelationshipType.DISTINGUISHES, 0.8),
            (self.disagrees_patterns, RelationshipType.DISAGREES_WITH, 0.7),
            (self.affirms_patterns, RelationshipType.AFFIRMS, 0.8),
            (self.reverses_patterns, RelationshipType.REVERSES, 0.9),
            (self.extends_patterns, RelationshipType.EXTENDS, 0.7),
            (self.applies_patterns, RelationshipType.APPLIES, 0.8),
            (self.cites_patterns, RelationshipType.CITES_CASE, 0.6)  # Default/fallback
        ]
        
        best_match = None
        best_confidence = 0.0
        best_signals = []
        
        for patterns, rel_type, base_confidence in relationship_tests:
            signals = []
            total_matches = 0
            
            for pattern in patterns:
                matches = list(pattern.finditer(context_text))
                if matches:
                    signals.extend([m.group(0) for m in matches])
                    total_matches += len(matches)
            
            if signals:
                # Calculate confidence based on signal strength and proximity
                proximity_bonus = self._calculate_proximity_bonus(context_text, citation.text, signals)
                final_confidence = min(base_confidence + proximity_bonus, 1.0)
                
                if final_confidence > best_confidence:
                    best_match = rel_type
                    best_confidence = final_confidence
                    best_signals = signals
        
        # Create relationship match if we found a good signal
        if best_match and best_confidence >= self.confidence_threshold:
            relationship = RelationshipMatch(
                source_case=source_case_id,
                target_citation=citation,
                relationship_type=best_match,
                confidence=best_confidence,
                context_text=context_text,
                start_pos=start_pos,
                end_pos=end_pos,
                signal_words=best_signals
            )
            relationships.append(relationship)
        
        return relationships
    
    def _calculate_proximity_bonus(self, context: str, citation_text: str, signals: List[str]) -> float:
        """Calculate confidence bonus based on proximity of signals to citation"""
        citation_pos = context.find(citation_text)
        if citation_pos == -1:
            return 0.0
        
        proximity_scores = []
        
        for signal in signals:
            signal_pos = context.find(signal)
            if signal_pos != -1:
                distance = abs(citation_pos - signal_pos)
                # Closer signals get higher scores
                if distance <= 50:
                    proximity_scores.append(0.2)
                elif distance <= 100:
                    proximity_scores.append(0.1)
                else:
                    proximity_scores.append(0.05)
        
        return min(sum(proximity_scores), 0.3)  # Cap bonus at 0.3
    
    def extract_explicit_relationships(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract explicitly stated relationships using specialized patterns
        """
        explicit_relationships = []
        
        # Pattern for explicit overruling statements
        overrule_pattern = re.compile(
            r'(?:we\s+)?(?:expressly\s+)?overrule\s+([^,\.]+?)(?:,|\.|;|\s+to\s+the\s+extent)',
            re.IGNORECASE
        )
        
        for match in overrule_pattern.finditer(text):
            case_reference = match.group(1).strip()
            explicit_relationships.append({
                "type": "explicit_overrule",
                "case_reference": case_reference,
                "text": match.group(0),
                "confidence": 0.95,
                "start_pos": match.start(),
                "end_pos": match.end()
            })
        
        # Pattern for following precedent
        follow_pattern = re.compile(
            r'(?:we\s+)?follow\s+(?:the\s+holding\s+(?:in\s+)?)?([^,\.]+?)(?:,|\.|;|\s+and)',
            re.IGNORECASE
        )
        
        for match in follow_pattern.finditer(text):
            case_reference = match.group(1).strip()
            explicit_relationships.append({
                "type": "explicit_follow",
                "case_reference": case_reference,
                "text": match.group(0),
                "confidence": 0.9,
                "start_pos": match.start(),
                "end_pos": match.end()
            })
        
        return explicit_relationships
    
    def validate_relationships(self, relationships: List[RelationshipMatch]) -> List[RelationshipMatch]:
        """
        Validate and filter relationships based on legal logic
        """
        validated = []
        
        for relationship in relationships:
            # Check for logical consistency
            if self._is_logically_consistent(relationship):
                validated.append(relationship)
            else:
                logger.debug(f"Filtered out inconsistent relationship: {relationship.relationship_type}")
        
        return validated
    
    def _is_logically_consistent(self, relationship: RelationshipMatch) -> bool:
        """Check if a relationship is logically consistent"""
        
        # Supreme Court cases can't be overruled by lower courts
        if (relationship.relationship_type == RelationshipType.OVERRULES and 
            relationship.target_citation.citation_type.value == "supreme_court"):
            return False
        
        # Other consistency checks can be added here
        
        return True
    
    def create_relationship_hyperedge(self, relationship: RelationshipMatch, 
                                    source_doc_id: str) -> CaseRelationship:
        """Create a CaseRelationship hyperedge from a relationship match"""
        
        # Create provenance record
        provenance = ProvenanceRecord(
            operation=ProvenanceOperation.EXTRACT,
            source=ProvenanceSource.RULE_BASED_EXTRACTION,
            agent_type="system",
            agent_id="relationship_extractor",
            timestamp=datetime.utcnow(),
            confidence=relationship.confidence,
            metadata={
                "signal_words": relationship.signal_words,
                "context_length": len(relationship.context_text),
                "extraction_method": "pattern_matching"
            }
        )
        
        # Create relationship hyperedge
        case_relationship = CaseRelationship(
            source_case_id=DocumentID(source_doc_id),
            target_case_id=relationship.target_citation.canonical_id,
            relationship_type=relationship.relationship_type,
            confidence=relationship.confidence,
            provenance=provenance,
            context_text=relationship.context_text,
            signal_phrases=relationship.signal_words
        )
        
        return case_relationship