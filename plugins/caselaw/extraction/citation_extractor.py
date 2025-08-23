"""
Advanced Citation Extraction for CAP Caselaw Plugin
Combines rule-based patterns with ML models for high-accuracy citation detection
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from ..models.canonical_identifiers import CitationID, IdentifierFactory
from ..models.provenance_record import ProvenanceRecord, ProvenanceOperation, ProvenanceSource

logger = logging.getLogger(__name__)


class CitationType(Enum):
    """Types of legal citations"""
    FEDERAL_CASE = "federal_case"
    SUPREME_COURT = "supreme_court"
    STATE_CASE = "state_case"
    STATUTE = "statute"
    REGULATION = "regulation"
    CONSTITUTIONAL = "constitutional"
    LAW_REVIEW = "law_review"
    UNKNOWN = "unknown"


@dataclass
class CitationMatch:
    """Represents a detected citation with metadata"""
    text: str
    citation_type: CitationType
    confidence: float
    start_pos: int
    end_pos: int
    components: Dict[str, Any]
    canonical_id: Optional[CitationID] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "type": self.citation_type.value,
            "confidence": self.confidence,
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
            "components": self.components,
            "canonical_id": str(self.canonical_id) if self.canonical_id else None
        }


class CitationExtractor:
    """
    Rule-based citation extractor with comprehensive pattern matching
    """
    
    def __init__(self, confidence_threshold: float = 0.7):
        self.confidence_threshold = confidence_threshold
        self.identifier_factory = IdentifierFactory()
        self._compile_patterns()
        
    def _compile_patterns(self):
        """Compile regex patterns for different citation types"""
        
        # Federal Reporter patterns
        self.federal_patterns = [
            # F., F.2d, F.3d - Federal Reporter
            re.compile(r'\b(\d+)\s+F\.\s*(?:2d|3d)?\s+(\d+)(?:\s*\(([^)]+)\s+(\d{4})\))?', re.IGNORECASE),
            # F.Supp., F.Supp.2d - Federal Supplement
            re.compile(r'\b(\d+)\s+F\.\s*Supp\.\s*(?:2d|3d)?\s+(\d+)(?:\s*\(([^)]+)\s+(\d{4})\))?', re.IGNORECASE),
            # F.App'x - Federal Appendix
            re.compile(r'\b(\d+)\s+F\.\s*App[\'''']x\s+(\d+)(?:\s*\(([^)]+)\s+(\d{4})\))?', re.IGNORECASE)
        ]
        
        # Supreme Court patterns
        self.supreme_court_patterns = [
            # U.S. Reports
            re.compile(r'\b(\d+)\s+U\.S\.\s+(\d+)(?:\s*\((\d{4})\))?', re.IGNORECASE),
            # S.Ct. - Supreme Court Reporter
            re.compile(r'\b(\d+)\s+S\.\s*Ct\.\s+(\d+)(?:\s*\((\d{4})\))?', re.IGNORECASE),
            # L.Ed., L.Ed.2d - Lawyers' Edition
            re.compile(r'\b(\d+)\s+L\.\s*Ed\.\s*(?:2d)?\s+(\d+)(?:\s*\((\d{4})\))?', re.IGNORECASE)
        ]
        
        # State court patterns
        self.state_patterns = [
            # State reporters (e.g., "123 Cal.App.4th 456")
            re.compile(r'\b(\d+)\s+([A-Z][a-z]*\.?\s*(?:App\.?\s*)?(?:\d+[a-z]*)?)\s+(\d+)(?:\s*\(([^)]+)\s+(\d{4})\))?'),
            # Regional reporters (e.g., "123 P.2d 456")
            re.compile(r'\b(\d+)\s+([NSEW]\.?[WE]\.?\d*[a-z]*)\s+(\d+)(?:\s*\(([^)]+)\s+(\d{4})\))?')
        ]
        
        # Statute patterns
        self.statute_patterns = [
            # U.S.C. (e.g., "42 U.S.C. § 1983")
            re.compile(r'\b(\d+)\s+U\.S\.C\.?\s*§?\s*(\d+(?:\([a-zA-Z0-9]+\))?)', re.IGNORECASE),
            # State statutes (e.g., "Cal. Civ. Code § 1234")
            re.compile(r'\b([A-Z][a-z]*\.?)\s+([A-Z][a-z]*\.?\s*[A-Z][a-z]*\.?)\s*§?\s*(\d+(?:\.[a-zA-Z0-9]+)?)', re.IGNORECASE)
        ]
        
        # Constitutional patterns
        self.constitutional_patterns = [
            # U.S. Constitution (e.g., "U.S. Const. amend. XIV, § 1")
            re.compile(r'\bU\.S\.\s*Const\.?\s*(?:amend\.?\s*([IVX]+)|art\.?\s*([IVX]+)(?:,?\s*§\s*(\d+))?)', re.IGNORECASE),
            # State constitutions
            re.compile(r'\b([A-Z][a-z]*\.?)\s*Const\.?\s*(?:art\.?\s*([IVX]+)(?:,?\s*§\s*(\d+))?)', re.IGNORECASE)
        ]
    
    def extract_citations(self, text: str, document_id: str = None) -> List[CitationMatch]:
        """
        Extract all citations from text using rule-based patterns
        
        Args:
            text: Input text to analyze
            document_id: Optional document identifier for provenance
            
        Returns:
            List of citation matches found
        """
        citations = []
        
        # Extract each type of citation
        citations.extend(self._extract_federal_citations(text))
        citations.extend(self._extract_supreme_court_citations(text))
        citations.extend(self._extract_state_citations(text))
        citations.extend(self._extract_statute_citations(text))
        citations.extend(self._extract_constitutional_citations(text))
        
        # Filter by confidence threshold
        filtered_citations = [c for c in citations if c.confidence >= self.confidence_threshold]
        
        # Sort by position in text
        filtered_citations.sort(key=lambda x: x.start_pos)
        
        # Generate canonical IDs for valid citations
        for citation in filtered_citations:
            try:
                citation.canonical_id = self._generate_canonical_id(citation)
            except Exception as e:
                logger.warning(f"Failed to generate canonical ID for citation {citation.text}: {e}")
        
        return filtered_citations
    
    def _extract_federal_citations(self, text: str) -> List[CitationMatch]:
        """Extract federal court citations"""
        citations = []
        
        for pattern in self.federal_patterns:
            for match in pattern.finditer(text):
                volume = match.group(1)
                page = match.group(2)
                court = match.group(3) if len(match.groups()) >= 3 else None
                year = match.group(4) if len(match.groups()) >= 4 else None
                
                # Determine reporter type
                reporter = "F."
                if "Supp" in match.group(0):
                    reporter = "F.Supp."
                elif "App" in match.group(0):
                    reporter = "F.App'x"
                elif "2d" in match.group(0):
                    reporter += "2d"
                elif "3d" in match.group(0):
                    reporter += "3d"
                
                citation = CitationMatch(
                    text=match.group(0).strip(),
                    citation_type=CitationType.FEDERAL_CASE,
                    confidence=0.9,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    components={
                        "volume": volume,
                        "reporter": reporter,
                        "page": page,
                        "court": court,
                        "year": year
                    }
                )
                citations.append(citation)
        
        return citations
    
    def _extract_supreme_court_citations(self, text: str) -> List[CitationMatch]:
        """Extract Supreme Court citations"""
        citations = []
        
        for pattern in self.supreme_court_patterns:
            for match in pattern.finditer(text):
                volume = match.group(1)
                page = match.group(2)
                year = match.group(3) if len(match.groups()) >= 3 else None
                
                # Determine reporter type
                if "U.S." in match.group(0):
                    reporter = "U.S."
                elif "S.Ct." in match.group(0):
                    reporter = "S.Ct."
                else:
                    reporter = "L.Ed."
                    if "2d" in match.group(0):
                        reporter += "2d"
                
                citation = CitationMatch(
                    text=match.group(0).strip(),
                    citation_type=CitationType.SUPREME_COURT,
                    confidence=0.95,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    components={
                        "volume": volume,
                        "reporter": reporter,
                        "page": page,
                        "year": year,
                        "court": "Supreme Court of the United States"
                    }
                )
                citations.append(citation)
        
        return citations
    
    def _extract_state_citations(self, text: str) -> List[CitationMatch]:
        """Extract state court citations"""
        citations = []
        
        for pattern in self.state_patterns:
            for match in pattern.finditer(text):
                volume = match.group(1)
                reporter = match.group(2)
                page = match.group(3)
                court = match.group(4) if len(match.groups()) >= 4 else None
                year = match.group(5) if len(match.groups()) >= 5 else None
                
                citation = CitationMatch(
                    text=match.group(0).strip(),
                    citation_type=CitationType.STATE_CASE,
                    confidence=0.8,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    components={
                        "volume": volume,
                        "reporter": reporter,
                        "page": page,
                        "court": court,
                        "year": year
                    }
                )
                citations.append(citation)
        
        return citations
    
    def _extract_statute_citations(self, text: str) -> List[CitationMatch]:
        """Extract statutory citations"""
        citations = []
        
        for pattern in self.statute_patterns:
            for match in pattern.finditer(text):
                if "U.S.C." in match.group(0):
                    # Federal statute
                    title = match.group(1)
                    section = match.group(2)
                    
                    citation = CitationMatch(
                        text=match.group(0).strip(),
                        citation_type=CitationType.STATUTE,
                        confidence=0.9,
                        start_pos=match.start(),
                        end_pos=match.end(),
                        components={
                            "title": title,
                            "code": "U.S.C.",
                            "section": section,
                            "jurisdiction": "federal"
                        }
                    )
                else:
                    # State statute
                    state = match.group(1)
                    code = match.group(2)
                    section = match.group(3)
                    
                    citation = CitationMatch(
                        text=match.group(0).strip(),
                        citation_type=CitationType.STATUTE,
                        confidence=0.8,
                        start_pos=match.start(),
                        end_pos=match.end(),
                        components={
                            "state": state,
                            "code": code,
                            "section": section,
                            "jurisdiction": "state"
                        }
                    )
                
                citations.append(citation)
        
        return citations
    
    def _extract_constitutional_citations(self, text: str) -> List[CitationMatch]:
        """Extract constitutional citations"""
        citations = []
        
        for pattern in self.constitutional_patterns:
            for match in pattern.finditer(text):
                if "U.S." in match.group(0):
                    # U.S. Constitution
                    amendment = match.group(1) if len(match.groups()) >= 1 else None
                    article = match.group(2) if len(match.groups()) >= 2 else None
                    section = match.group(3) if len(match.groups()) >= 3 else None
                    
                    citation = CitationMatch(
                        text=match.group(0).strip(),
                        citation_type=CitationType.CONSTITUTIONAL,
                        confidence=0.95,
                        start_pos=match.start(),
                        end_pos=match.end(),
                        components={
                            "constitution": "U.S.",
                            "amendment": amendment,
                            "article": article,
                            "section": section,
                            "jurisdiction": "federal"
                        }
                    )
                else:
                    # State constitution
                    state = match.group(1)
                    article = match.group(2) if len(match.groups()) >= 2 else None
                    section = match.group(3) if len(match.groups()) >= 3 else None
                    
                    citation = CitationMatch(
                        text=match.group(0).strip(),
                        citation_type=CitationType.CONSTITUTIONAL,
                        confidence=0.85,
                        start_pos=match.start(),
                        end_pos=match.end(),
                        components={
                            "constitution": state,
                            "article": article,
                            "section": section,
                            "jurisdiction": "state"
                        }
                    )
                
                citations.append(citation)
        
        return citations
    
    def _generate_canonical_id(self, citation: CitationMatch) -> Optional[CitationID]:
        """Generate canonical ID for a citation"""
        try:
            if citation.citation_type in [CitationType.FEDERAL_CASE, CitationType.SUPREME_COURT]:
                reporter = citation.components.get("reporter", "")
                volume = citation.components.get("volume", "")
                page = citation.components.get("page", "")
                
                if reporter and volume and page:
                    return CitationID.from_components(reporter, volume, page)
            
        except Exception as e:
            logger.debug(f"Could not generate canonical ID for citation: {e}")
        
        return None


class MLCitationExtractor:
    """
    Machine learning-based citation extractor for enhanced accuracy
    """
    
    def __init__(self, model_path: Optional[str] = None, confidence_threshold: float = 0.8):
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.rule_based_extractor = CitationExtractor(confidence_threshold)
        self._model_loaded = False
        
    def extract_citations(self, text: str, document_id: str = None) -> List[CitationMatch]:
        """
        Extract citations using ML model with rule-based fallback
        
        Args:
            text: Input text to analyze
            document_id: Optional document identifier
            
        Returns:
            List of citation matches
        """
        # For now, use rule-based extraction as foundation
        # TODO: Implement ML model integration when model is available
        rule_based_citations = self.rule_based_extractor.extract_citations(text, document_id)
        
        if not self._model_loaded:
            logger.info("ML model not loaded, using rule-based extraction")
            return rule_based_citations
        
        # TODO: Enhance with ML predictions
        return self._enhance_with_ml(text, rule_based_citations)
    
    def _enhance_with_ml(self, text: str, rule_citations: List[CitationMatch]) -> List[CitationMatch]:
        """Enhance rule-based citations with ML predictions"""
        # Placeholder for ML enhancement
        # This would integrate with a trained model for citation detection
        return rule_citations
    
    def load_model(self, model_path: str):
        """Load ML model for citation extraction"""
        # Placeholder for model loading
        logger.info(f"Loading ML model from {model_path}")
        self._model_loaded = True