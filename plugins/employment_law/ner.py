"""
Employment Law NER (Named Entity Recognition)

Specialized NER for employment law documents including:
- ADA accommodation requests and disability-related entities
- FLSA wage/hour violations and overtime calculations
- At-will employment and wrongful termination indicators  
- Workers' compensation claims and injury documentation

Uses pattern-based extraction optimized for legal employment documents.
"""

import re
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class Entity:
    """Represents an extracted employment law entity"""
    text: str
    type: str
    start: int
    end: int
    confidence: float
    metadata: Dict[str, Any]


class EmploymentNER:
    """
    Employment law NER pipeline for extracting domain-specific entities
    
    Extracts employment law entities using pattern-based matching
    optimized for legal documents and case files.
    """
    
    def __init__(self):
        """Initialize employment law NER with specialized patterns"""
        self._init_patterns()
        
    def _init_patterns(self):
        """Initialize regex patterns for employment law entities"""
        
        # ADA patterns
        self.ada_patterns = {
            "ADA_REQUEST": [
                r"(?:reasonable )?accommodation(?:\s+request)?",
                r"ADA(?:\s+(?:accommodation|request))?",
                r"(?:requested?|seeking)\s+(?:reasonable\s+)?accommodation",
                r"interactive\s+process\s+(?:request|required)"
            ],
            "DISABILITY": [
                r"(?:mobility|visual|hearing|cognitive|mental)\s+(?:disability|impairment)",
                r"(?:disabled|handicapped)\s+(?:employee|worker|individual)",
                r"(?:wheelchair|walker|cane|prosthetic)",
                r"(?:depression|anxiety|PTSD|bipolar)",
                r"(?:back|spine|joint)\s+(?:injury|condition|disorder)"
            ],
            "REASONABLE_ACCOMMODATION": [
                r"ergonomic\s+(?:equipment|chair|keyboard|mouse)",
                r"modified\s+work\s+schedule",
                r"modified\s+(?:hours|duties|schedule)",
                r"(?:flexible|alternative)\s+(?:schedule|hours|work\s+arrangement)",
                r"(?:wheelchair\s+accessible|accessible)\s+(?:workspace|parking)",
                r"(?:screen\s+reader|voice\s+recognition|assistive\s+technology)",
                r"(?:interpreter|captioning|hearing\s+aid)",
                r"(?:job\s+restructuring|reassignment|transfer)"
            ],
            "INTERACTIVE_PROCESS": [
                r"interactive\s+process",
                r"engage\s+in\s+(?:good\s+faith\s+)?dialogue",
                r"accommodation\s+(?:discussion|meeting|conference)"
            ]
        }
        
        # FLSA patterns
        self.flsa_patterns = {
            "FLSA_VIOLATION": [
                r"FLSA\s+violation",
                r"(?:unpaid|withheld)\s+(?:overtime|wages)",
                r"off[\-\s]the[\-\s]clock\s+work",
                r"(?:wage|hour)\s+violation",
                r"misclassified\s+(?:as\s+)?(?:exempt|independent\s+contractor)"
            ],
            "OVERTIME": [
                r"overtime\s+(?:pay|compensation|wages)",
                r"time[\-\s]and[\-\s]a[\-\s]half",
                r"(?:1\.5|one\s+and\s+a\s+half)\s*(?:times|x)\s+(?:regular\s+)?(?:rate|pay)",
                r"(?:worked|hours)\s+(?:over|more\s+than)\s+40\s+hours"
            ],
            "WAGE_RATE": [
                r"\$\d+(?:\.\d{2})?\s*(?:per\s+hour|\/hour|hourly)",
                r"\$\d+(?:\.\d{2})?\s*(?:per\s+week|\/week|weekly)",
                r"(?:minimum\s+wage|hourly\s+rate|base\s+pay)"
            ],
            "WORK_HOURS": [
                r"\d+\s+hours?\s+(?:per\s+week|weekly)",
                r"worked\s+\d+\s+hours?",
                r"\d+\s+hour\s+(?:work\s+)?(?:week|shift)"
            ]
        }
        
        # At-will employment patterns
        self.at_will_patterns = {
            "AT_WILL_EMPLOYMENT": [
                r"at[\-\s]will\s+(?:employment|employee|state)",
                r"(?:employment\s+)?at\s+will",
                r"terminat(?:e|ed|ion)\s+(?:for\s+any\s+reason|without\s+cause)"
            ],
            "WRONGFUL_TERMINATION": [
                r"wrongful\s+(?:termination|discharge|dismissal)",
                r"(?:illegal|unlawful)\s+(?:termination|firing)",
                r"(?:retaliatory|discriminatory)\s+(?:termination|discharge)"
            ],
            "WHISTLEBLOWING": [
                r"whistleblow(?:ing|er)",
                r"report(?:ed|ing)\s+(?:safety\s+violations|illegal\s+activity)",
                r"(?:OSHA|safety)\s+complaint",
                r"(?:fraud|corruption|illegal\s+activity)\s+report"
            ],
            "PUBLIC_POLICY_EXCEPTION": [
                r"public\s+policy\s+exception",
                r"protected\s+activity",
                r"(?:jury\s+duty|voting|filing\s+(?:workers?\s+comp|discrimination)\s+claim)"
            ]
        }
        
        # Workers' compensation patterns
        self.workers_comp_patterns = {
            "WORK_INJURY": [
                r"(?:work(?:place)?|job)[\-\s]related\s+injury",
                r"injured\s+(?:on\s+the\s+job|at\s+work|during\s+work)",
                r"(?:back|neck|shoulder|hand|leg)\s+injury",
                r"(?:lifting|falling|slip\s+and\s+fall|repetitive\s+stress)\s+injury",
                r"injured\s+(?:back|neck|shoulder|hand|leg)\s+(?:lifting|carrying|moving)\s+.*?during\s+work",
                r"injured\s+(?:back|neck|shoulder|hand|leg).*?during\s+work\s+hours"
            ],
            "WORKERS_COMP_CLAIM": [
                r"workers?'?\s+comp(?:ensation)?\s+claim",
                r"filed\s+(?:workers?'?\s+comp(?:ensation)?|work\s+injury)\s+claim",
                r"industrial\s+(?:accident|injury)\s+claim"
            ],
            "MEDICAL_TREATMENT": [
                r"medical\s+(?:treatment|care|expenses)",
                r"(?:doctor|physician|hospital)\s+(?:visits?|treatment)",
                r"(?:physical\s+therapy|rehabilitation|surgery)"
            ],
            "LOST_WAGES": [
                r"lost\s+(?:wages|income|pay)",
                r"(?:temporary|permanent)\s+(?:disability|impairment)",
                r"(?:time\s+off|unable\s+to)\s+work"
            ],
            "RETALIATION": [
                r"retaliat(?:ed|ion|ory|e)",
                r"cannot\s+retaliate",
                r"(?:disciplined|terminated|demoted)\s+(?:for\s+filing|after\s+filing)",
                r"(?:harassment|discrimination)\s+(?:for|after)\s+(?:filing|workers?\s+comp)"
            ]
        }
        
        # Compile all patterns with DOTALL flag to handle multiline
        self.compiled_patterns = {}
        for category, patterns in [
            ("ada", self.ada_patterns),
            ("flsa", self.flsa_patterns),
            ("at_will", self.at_will_patterns),
            ("workers_comp", self.workers_comp_patterns)
        ]:
            self.compiled_patterns[category] = {}
            for entity_type, pattern_list in patterns.items():
                self.compiled_patterns[category][entity_type] = [
                    re.compile(pattern, re.IGNORECASE | re.DOTALL) for pattern in pattern_list
                ]
    
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract employment law entities from text
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of extracted entities with type, text, and metadata
        """
        entities = []
        
        # Extract entities from each category
        for category, entity_patterns in self.compiled_patterns.items():
            for entity_type, patterns in entity_patterns.items():
                for pattern in patterns:
                    for match in pattern.finditer(text):
                        # Normalize whitespace in extracted text
                        normalized_text = re.sub(r'\s+', ' ', match.group()).strip()
                        entity = {
                            "text": normalized_text,
                            "type": entity_type,
                            "start": match.start(),
                            "end": match.end(),
                            "confidence": 0.85,  # Pattern-based confidence
                            "metadata": {
                                "category": category,
                                "pattern": pattern.pattern,
                                "original_text": match.group()
                            }
                        }
                        entities.append(entity)
        
        # Remove duplicates and overlaps
        entities = self._remove_overlaps(entities)
        
        return entities
    
    def _remove_overlaps(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove overlapping entities, keeping higher confidence ones"""
        if not entities:
            return entities
            
        # Sort by start position
        entities.sort(key=lambda x: x["start"])
        
        filtered = [entities[0]]
        
        for entity in entities[1:]:
            last_entity = filtered[-1]
            
            # Check for overlap
            if entity["start"] < last_entity["end"]:
                # Keep entity with higher confidence
                if entity["confidence"] > last_entity["confidence"]:
                    filtered[-1] = entity
            else:
                filtered.append(entity)
                
        return filtered
    
    def extract_legal_citations(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract legal citations relevant to employment law
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of legal citations with normalized forms
        """
        citations = []
        
        # Employment law specific citation patterns
        citation_patterns = [
            r"42\s+U\.?S\.?C\.?\s+(?:§\s*)?12112",  # ADA
            r"29\s+U\.?S\.?C\.?\s+(?:§\s*)?207",    # FLSA
            r"29\s+U\.?S\.?C\.?\s+(?:§\s*)?203",    # FLSA definitions
            r"42\s+U\.?S\.?C\.?\s+(?:§\s*)?2000e",  # Title VII
            r"29\s+U\.?S\.?C\.?\s+(?:§\s*)?651",    # OSHA
        ]
        
        for pattern in citation_patterns:
            regex = re.compile(pattern, re.IGNORECASE)
            for match in regex.finditer(text):
                citations.append({
                    "text": match.group(),
                    "type": "LEGAL_CITATION",
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 0.95,
                    "metadata": {
                        "citation_type": "statute",
                        "normalized": self._normalize_citation(match.group())
                    }
                })
        
        return citations
    
    def _normalize_citation(self, citation: str) -> str:
        """Normalize legal citation to standard format"""
        # Simple normalization - add periods and proper spacing
        normalized = re.sub(r"(\d+)\s*USC?\s*", r"\1 U.S.C. ", citation, flags=re.IGNORECASE)
        normalized = re.sub(r"§\s*(\d+)", r"§ \1", normalized)
        return normalized.strip()