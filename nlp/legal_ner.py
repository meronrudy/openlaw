"""
Legal NLP Infrastructure - NER and Citation Extraction

Provides domain-specific NLP capabilities for legal document processing,
including legal entity recognition using LegalBERT, citation extraction,
and obligation parsing with pattern-based and transformer approaches.
"""

from typing import List, Dict, Any, Tuple, Optional
import re
from datetime import datetime


class LegalNERPipeline:
    """
    Legal Named Entity Recognition using domain-specific models
    
    Combines transformer-based NER with pattern-based extraction for
    comprehensive legal entity recognition in documents.
    """
    
    def __init__(self, model_name: str = "nlpaueb/legal-bert-base-uncased"):
        """
        Initialize Legal NER pipeline
        
        Args:
            model_name: HuggingFace model name for legal NER
        """
        self.model_name = model_name
        
        # For TDD, we'll mock the transformer components
        # In production, these would load actual models
        self.tokenizer = None  # AutoTokenizer.from_pretrained(model_name)
        self.model = None      # AutoModelForTokenClassification.from_pretrained(model_name)
        self.pipeline = None   # pipeline("ner", model=self.model, tokenizer=self.tokenizer)
        
        # Legal entity regex patterns for pattern-based extraction
        self.patterns = {
            "STATUTE": [
                r"\b\d+\s+U\.?S\.?C\.?\s*§?\s*\d+(?:\([a-z0-9]+\))*\b",
                r"\b\d+\s+USC\s*§?\s*\d+(?:\([a-z0-9]+\))*\b", 
                r"\b\d+\s+C\.?F\.?R\.?\s*§?\s*\d+(?:\.\d+)*\b",
                r"\bSection\s+\d+\b",
                r"\b§\s*\d+\b"
            ],
            "CASE": [
                r"\b[A-Z][a-zA-Z\s&]+\s+v\.?\s+[A-Z][a-zA-Z\s&]+(?:,?\s+\d+\s+[A-Z][a-zA-Z\.]+\s+\d+)?\b",
                r"\b[A-Z][a-zA-Z\s&]+\s+v\.?\s+[A-Z][a-zA-Z\s&]+\b"
            ],
            "MONEY": [
                r"\$[\d,]+(?:\.\d{2})?(?:\s+(?:million|billion|thousand))?\b",
                r"\$\d+(?:,\d{3})*(?:\.\d{2})?\b"
            ],
            "DATE": [
                r"\b\d{1,2}/\d{1,2}/\d{4}\b",
                r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
                r"\b\d{4}-\d{2}-\d{2}\b"
            ]
        }
        
    def extract_legal_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract legal entities with confidence scores
        
        Args:
            text: Input text to process
            
        Returns:
            List of extracted entities with type, text, span, and confidence
        """
        # In production, would use transformer-based NER
        # For TDD, use pattern-based extraction
        transformer_entities = self._mock_transformer_entities(text)
        
        # Add pattern-based entities
        pattern_entities = self._extract_pattern_entities(text)
        
        # Combine and deduplicate
        all_entities = transformer_entities + pattern_entities
        return self._deduplicate_entities(all_entities)
        
    def extract_obligations(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract legal obligations and duties from text
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of obligation dictionaries with bearer, duty, span, confidence
        """
        obligations = []
        
        # Legal obligation patterns
        obligation_patterns = [
            r"(\w+(?:\s+\w+)*)\s+(?:shall|must|is required to|has a duty to)\s+([^.!?]+)",
            r"(\w+(?:\s+\w+)*)\s+(?:are required to|is obligated to|is responsible for)\s+([^.!?]+)",
            r"(\w+(?:\s+\w+)*)\s+(?:owes|has an obligation to)\s+([^.!?]+)"
        ]
        
        for pattern in obligation_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                obligations.append({
                    "bearer": match.group(1).strip(),
                    "duty": match.group(2).strip(),
                    "span": match.span(),
                    "confidence": 0.8,
                    "pattern": "obligation_extraction"
                })
                
        return obligations
        
    def _mock_transformer_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Mock transformer-based entity extraction for TDD
        
        In production, this would call self.pipeline(text)
        """
        # Simple mock that recognizes some basic patterns
        entities = []
        
        # Mock person recognition (very basic)
        person_patterns = [r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b"]
        for pattern in person_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                # Skip if it looks like a case citation
                if " v. " not in match.group() and " v " not in match.group():
                    entities.append({
                        "entity_group": "PERSON",
                        "word": match.group(),
                        "start": match.start(),
                        "end": match.end(),
                        "score": 0.85,
                        "method": "transformer_mock"
                    })
                    
        return entities
        
    def _extract_pattern_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract entities using regex patterns
        
        Args:
            text: Input text to process
            
        Returns:
            List of pattern-based entities
        """
        entities = []
        
        for entity_type, patterns in self.patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    entities.append({
                        "entity_group": entity_type,
                        "word": match.group(),
                        "start": match.start(),
                        "end": match.end(),
                        "score": 0.9,  # High confidence for pattern matches
                        "method": "pattern_based"
                    })
                    
        return entities
        
    def _deduplicate_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove overlapping entities, keeping highest confidence
        
        Args:
            entities: List of entities to deduplicate
            
        Returns:
            Filtered list without overlaps
        """
        if not entities:
            return []
            
        # Sort by confidence score (highest first)
        sorted_entities = sorted(entities, key=lambda x: x.get("score", 0), reverse=True)
        
        filtered = []
        used_spans = set()
        
        for entity in sorted_entities:
            start = entity.get("start", 0)
            end = entity.get("end", 0)
            
            # Check for overlap with existing spans
            overlap = any(
                (start < used_end and end > used_start) 
                for used_start, used_end in used_spans
            )
            
            if not overlap:
                filtered.append(entity)
                used_spans.add((start, end))
                
        return filtered


class CitationExtractor:
    """
    Extract and parse legal citations using Bluebook patterns
    
    Recognizes various citation formats for cases, statutes, regulations,
    and constitutional provisions with structured parsing.
    """
    
    def __init__(self):
        """Initialize citation extractor with Bluebook patterns"""
        # Bluebook citation patterns
        self.citation_patterns = {
            "case": [
                # Full case citation: "Brown v. Board, 347 U.S. 483 (1954)"
                r"([A-Z][\w\s&\.]+)\s+v\.?\s+([A-Z][\w\s&\.]+),?\s+(\d+)\s+([A-Z][\w\.]+)\s+(\d+)(?:\s+\((\d{4})\))?",
                # Simple case citation: "Brown v. Board"
                r"([A-Z][\w\s&\.]+)\s+v\.?\s+([A-Z][\w\s&\.]+)"
            ],
            "statute": [
                # USC citations: "42 U.S.C. § 1981" or "42 USC 1981"
                r"(\d+)\s+U\.?S\.?C\.?\s*§?\s*(\d+(?:\([a-z0-9]+\))*)",
                r"(\d+)\s+USC\s*§?\s*(\d+(?:\([a-z0-9]+\))*)",
                # CFR citations: "29 CFR 1630.2"
                r"(\d+)\s+C\.?F\.?R\.?\s*§?\s*(\d+(?:\.\d+)*)"
            ],
            "constitution": [
                # Constitutional articles: "U.S. Const. Art. I, § 8"
                r"U\.?S\.?\s+Const\.?\s+[Aa]rt\.?\s+([IVX]+),?\s*§?\s*(\d+)",
                # Constitutional amendments: "U.S. Const. Amend. XIV"
                r"U\.?S\.?\s+Const\.?\s+[Aa]mend\.?\s+([IVX]+)"
            ]
        }
        
    def extract_citations(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract structured citations from text
        
        Args:
            text: Input text to process
            
        Returns:
            List of citation dictionaries with type, raw text, and parsed components
        """
        citations = []
        
        for citation_type, patterns in self.citation_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    citation = {
                        "type": citation_type,
                        "raw": match.group(),
                        "span": match.span(),
                        "groups": match.groups(),
                        "confidence": self._calculate_confidence(match.groups(), citation_type)
                    }
                    
                    citations.append(citation)
                    
        return citations
        
    def parse_citation_components(self, citation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse individual citation components into structured format
        
        Args:
            citation: Citation dictionary from extract_citations
            
        Returns:
            Parsed citation with structured components
        """
        parsed = {
            "type": citation["type"],
            "raw": citation["raw"]
        }
        
        groups = citation.get("groups", ())
        
        if citation["type"] == "case":
            if len(groups) >= 2:
                parsed["plaintiff"] = groups[0].strip()
                parsed["defendant"] = groups[1].strip()
            if len(groups) >= 5:
                parsed["volume"] = groups[2]
                parsed["reporter"] = groups[3]
                parsed["page"] = groups[4]
            if len(groups) >= 6 and groups[5]:
                parsed["year"] = groups[5]
                
        elif citation["type"] == "statute":
            if len(groups) >= 2:
                parsed["title"] = groups[0]
                parsed["section"] = groups[1]
                
        elif citation["type"] == "constitution":
            if len(groups) >= 1:
                parsed["article_or_amendment"] = groups[0]
            if len(groups) >= 2:
                parsed["section"] = groups[1]
                
        return parsed
        
    def normalize_citation(self, citation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize citation to standard Bluebook format
        
        Args:
            citation: Citation to normalize
            
        Returns:
            Normalized citation dictionary
        """
        normalized = citation.copy()
        
        if citation["type"] == "statute":
            groups = citation.get("groups", ())
            if len(groups) >= 2:
                title = groups[0]
                section = groups[1]
                normalized["standard_form"] = f"{title} U.S.C. § {section}"
                normalized["title"] = title
                normalized["section"] = section
                
        elif citation["type"] == "case":
            # For cases, the standard form depends on the completeness
            groups = citation.get("groups", ())
            if len(groups) >= 5:
                plaintiff = groups[0].strip()
                defendant = groups[1].strip()
                volume = groups[2]
                reporter = groups[3]
                page = groups[4]
                normalized["standard_form"] = f"{plaintiff} v. {defendant}, {volume} {reporter} {page}"
            elif len(groups) >= 2:
                plaintiff = groups[0].strip()
                defendant = groups[1].strip()
                normalized["standard_form"] = f"{plaintiff} v. {defendant}"
                
        return normalized
        
    def _calculate_confidence(self, groups: Tuple[str, ...], citation_type: str) -> float:
        """
        Calculate confidence score based on citation completeness
        
        Args:
            groups: Regex match groups
            citation_type: Type of citation
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        base_confidence = 0.9
        
        if citation_type == "case":
            # Full citation with volume/reporter/page gets higher confidence
            if len(groups) >= 5:
                return 0.95
            elif len(groups) >= 2:
                return 0.85
            else:
                return 0.7
                
        elif citation_type == "statute":
            # USC/CFR with title and section
            if len(groups) >= 2:
                return 0.9
            else:
                return 0.8
                
        elif citation_type == "constitution":
            # Constitutional citations are usually high confidence
            return 0.95
            
        return base_confidence