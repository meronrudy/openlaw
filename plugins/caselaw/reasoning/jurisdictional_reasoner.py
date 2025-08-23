"""
Jurisdictional Reasoning Engine for CAP Caselaw Plugin
Handles court hierarchy, jurisdictional authority, and precedential value analysis
"""

import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

from ..models.canonical_identifiers import DocumentID
from ..models.caselaw_node import CaselawNode, CourtLevel, JurisdictionType

logger = logging.getLogger(__name__)


class AuthorityLevel(Enum):
    """Levels of precedential authority"""
    BINDING = "binding"           # Must be followed
    PERSUASIVE = "persuasive"     # Should be considered
    INFORMATIVE = "informative"   # May be referenced
    CONFLICTING = "conflicting"   # Creates circuit split
    NO_AUTHORITY = "no_authority" # No precedential value


@dataclass
class JurisdictionalRelation:
    """Relationship between jurisdictions"""
    superior_jurisdiction: str
    subordinate_jurisdiction: str
    relation_type: str  # "appellate", "supervisory", "administrative"
    binding_authority: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "superior_jurisdiction": self.superior_jurisdiction,
            "subordinate_jurisdiction": self.subordinate_jurisdiction,
            "relation_type": self.relation_type,
            "binding_authority": self.binding_authority
        }


@dataclass
class AuthorityAnalysis:
    """Analysis of precedential authority between cases"""
    source_case_id: DocumentID
    target_case_id: DocumentID
    authority_level: AuthorityLevel
    confidence: float
    reasoning: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_case_id": str(self.source_case_id),
            "target_case_id": str(self.target_case_id),
            "authority_level": self.authority_level.value,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "metadata": self.metadata
        }


class JurisdictionalReasoner:
    """
    Handles jurisdictional reasoning for legal precedent analysis
    """
    
    def __init__(self):
        """Initialize jurisdictional reasoner"""
        self.jurisdiction_hierarchy = self._build_jurisdiction_hierarchy()
        self.court_rankings = self._build_court_rankings()
        self.geographic_mappings = self._build_geographic_mappings()
        
    def _build_jurisdiction_hierarchy(self) -> Dict[str, List[JurisdictionalRelation]]:
        """Build comprehensive jurisdiction hierarchy"""
        hierarchy = {}
        
        # Federal Court System
        federal_relations = [
            # Supreme Court over all federal courts
            JurisdictionalRelation("us", "us.ca1", "appellate"),
            JurisdictionalRelation("us", "us.ca2", "appellate"),
            JurisdictionalRelation("us", "us.ca3", "appellate"),
            JurisdictionalRelation("us", "us.ca4", "appellate"),
            JurisdictionalRelation("us", "us.ca5", "appellate"),
            JurisdictionalRelation("us", "us.ca6", "appellate"),
            JurisdictionalRelation("us", "us.ca7", "appellate"),
            JurisdictionalRelation("us", "us.ca8", "appellate"),
            JurisdictionalRelation("us", "us.ca9", "appellate"),
            JurisdictionalRelation("us", "us.ca10", "appellate"),
            JurisdictionalRelation("us", "us.ca11", "appellate"),
            JurisdictionalRelation("us", "us.cadc", "appellate"),
            JurisdictionalRelation("us", "us.cafc", "appellate"),
            
            # Circuit Courts over District Courts
            JurisdictionalRelation("us.ca1", "us.d.me", "appellate"),
            JurisdictionalRelation("us.ca1", "us.d.nh", "appellate"),
            JurisdictionalRelation("us.ca1", "us.d.ma", "appellate"),
            JurisdictionalRelation("us.ca1", "us.d.ri", "appellate"),
            JurisdictionalRelation("us.ca1", "us.d.pr", "appellate"),
            
            # Add more circuit-district mappings...
        ]
        
        hierarchy["federal"] = federal_relations
        
        # State Court Systems (example for major states)
        state_relations = []
        
        # California
        state_relations.extend([
            JurisdictionalRelation("cal", "cal.appellate", "appellate"),
            JurisdictionalRelation("cal.appellate", "cal.superior", "appellate"),
        ])
        
        # New York
        state_relations.extend([
            JurisdictionalRelation("ny", "ny.appellate", "appellate"),
            JurisdictionalRelation("ny.appellate", "ny.supreme", "appellate"),
        ])
        
        # Texas
        state_relations.extend([
            JurisdictionalRelation("tex", "tex.appellate", "appellate"),
            JurisdictionalRelation("tex.appellate", "tex.district", "appellate"),
        ])
        
        hierarchy["state"] = state_relations
        
        return hierarchy
    
    def _build_court_rankings(self) -> Dict[str, int]:
        """Build court authority rankings (higher number = more authority)"""
        return {
            # Federal Courts
            "us": 1000,              # U.S. Supreme Court
            "us.ca1": 800, "us.ca2": 800, "us.ca3": 800,    # Circuit Courts
            "us.ca4": 800, "us.ca5": 800, "us.ca6": 800,
            "us.ca7": 800, "us.ca8": 800, "us.ca9": 800,
            "us.ca10": 800, "us.ca11": 800, "us.cadc": 800,
            "us.cafc": 850,          # Federal Circuit (specialized)
            "us.d.me": 600, "us.d.nh": 600, "us.d.ma": 600,  # District Courts
            
            # State Supreme Courts
            "cal": 700, "ny": 700, "tex": 700, "fla": 700,
            
            # State Appellate Courts
            "cal.appellate": 500, "ny.appellate": 500,
            "tex.appellate": 500, "fla.appellate": 500,
            
            # State Trial Courts
            "cal.superior": 300, "ny.supreme": 300,
            "tex.district": 300, "fla.circuit": 300,
        }
    
    def _build_geographic_mappings(self) -> Dict[str, Set[str]]:
        """Build geographic jurisdiction mappings"""
        return {
            # Federal Circuits
            "us.ca1": {"me", "nh", "ma", "ri", "pr"},
            "us.ca2": {"ny", "ct", "vt"},
            "us.ca3": {"pa", "nj", "de", "vi"},
            "us.ca4": {"va", "wv", "nc", "sc", "md"},
            "us.ca5": {"tx", "la", "ms"},
            "us.ca6": {"oh", "mi", "ky", "tn"},
            "us.ca7": {"il", "in", "wi"},
            "us.ca8": {"mn", "ia", "mo", "ar", "nd", "sd", "ne"},
            "us.ca9": {"ca", "or", "wa", "az", "nv", "id", "mt", "ak", "hi"},
            "us.ca10": {"co", "ut", "wy", "nm", "ks", "ok"},
            "us.ca11": {"ga", "fl", "al"},
            "us.cadc": {"dc"},
            
            # States
            "cal": {"ca"},
            "ny": {"ny"},
            "tex": {"tx"},
            "fla": {"fl"},
        }
    
    async def analyze_precedential_authority(self, 
                                           source_case: CaselawNode,
                                           target_case: CaselawNode) -> AuthorityAnalysis:
        """
        Analyze precedential authority between two cases
        
        Args:
            source_case: The citing/current case
            target_case: The cited/precedent case
            
        Returns:
            Authority analysis with level and reasoning
        """
        try:
            reasoning = []
            confidence = 0.0
            authority_level = AuthorityLevel.NO_AUTHORITY
            
            # Get court information
            source_court = source_case.metadata.get("court_slug", "")
            target_court = target_case.metadata.get("court_slug", "")
            
            source_jurisdiction = source_case.metadata.get("jurisdiction_slug", "")
            target_jurisdiction = target_case.metadata.get("jurisdiction_slug", "")
            
            # Same court analysis
            if source_court == target_court:
                authority_level, conf, reason = self._analyze_same_court_authority(
                    source_case, target_case
                )
                confidence = max(confidence, conf)
                reasoning.extend(reason)
            
            # Hierarchical analysis
            elif self._is_superior_court(target_court, source_court):
                authority_level = AuthorityLevel.BINDING
                confidence = 0.9
                reasoning.append(f"Superior court {target_court} has binding authority over {source_court}")
            
            # Same jurisdiction analysis
            elif source_jurisdiction == target_jurisdiction:
                authority_level, conf, reason = self._analyze_same_jurisdiction_authority(
                    source_case, target_case
                )
                confidence = max(confidence, conf)
                reasoning.extend(reason)
            
            # Cross-jurisdiction analysis
            else:
                authority_level, conf, reason = self._analyze_cross_jurisdiction_authority(
                    source_case, target_case
                )
                confidence = max(confidence, conf)
                reasoning.extend(reason)
            
            # Consider temporal factors
            temporal_adjustment = self._calculate_temporal_authority_adjustment(
                source_case, target_case
            )
            confidence *= temporal_adjustment
            
            if temporal_adjustment < 1.0:
                reasoning.append(f"Authority reduced due to age (factor: {temporal_adjustment:.2f})")
            
            return AuthorityAnalysis(
                source_case_id=source_case.case_id,
                target_case_id=target_case.case_id,
                authority_level=authority_level,
                confidence=confidence,
                reasoning=reasoning,
                metadata={
                    "source_court": source_court,
                    "target_court": target_court,
                    "source_jurisdiction": source_jurisdiction,
                    "target_jurisdiction": target_jurisdiction,
                    "temporal_adjustment": temporal_adjustment
                }
            )
            
        except Exception as e:
            logger.error(f"Error analyzing precedential authority: {e}")
            return AuthorityAnalysis(
                source_case_id=source_case.case_id,
                target_case_id=target_case.case_id,
                authority_level=AuthorityLevel.NO_AUTHORITY,
                confidence=0.0,
                reasoning=[f"Error in analysis: {str(e)}"]
            )
    
    def _analyze_same_court_authority(self, source_case: CaselawNode, 
                                    target_case: CaselawNode) -> Tuple[AuthorityLevel, float, List[str]]:
        """Analyze authority when cases are from the same court"""
        reasoning = []
        
        # Check if target case is older (required for precedent)
        source_date = source_case.metadata.get("decision_date")
        target_date = target_case.metadata.get("decision_date")
        
        if target_date and source_date and target_date >= source_date:
            return AuthorityLevel.NO_AUTHORITY, 0.1, ["Target case is not older than source case"]
        
        court_slug = source_case.metadata.get("court_slug", "")
        
        # Supreme Court cases are binding on same court
        if court_slug == "us" or court_slug.endswith(".supreme"):
            reasoning.append("Supreme Court precedent within same court")
            return AuthorityLevel.BINDING, 0.95, reasoning
        
        # Appellate court cases are generally binding on same court
        elif "appellate" in court_slug or ".ca" in court_slug:
            reasoning.append("Appellate court precedent within same court")
            return AuthorityLevel.BINDING, 0.9, reasoning
        
        # Trial court cases are persuasive within same court
        else:
            reasoning.append("Trial court precedent within same court")
            return AuthorityLevel.PERSUASIVE, 0.6, reasoning
    
    def _analyze_same_jurisdiction_authority(self, source_case: CaselawNode,
                                           target_case: CaselawNode) -> Tuple[AuthorityLevel, float, List[str]]:
        """Analyze authority when cases are from the same jurisdiction"""
        reasoning = []
        
        source_court = source_case.metadata.get("court_slug", "")
        target_court = target_case.metadata.get("court_slug", "")
        
        # Check court hierarchy within jurisdiction
        if self._is_superior_court(target_court, source_court):
            reasoning.append(f"Superior court {target_court} within same jurisdiction")
            return AuthorityLevel.BINDING, 0.9, reasoning
        
        # Same level courts are persuasive
        elif self._is_same_court_level(source_court, target_court):
            reasoning.append("Same level court within jurisdiction")
            return AuthorityLevel.PERSUASIVE, 0.7, reasoning
        
        # Lower court cases are informative
        else:
            reasoning.append("Lower court within jurisdiction")
            return AuthorityLevel.INFORMATIVE, 0.4, reasoning
    
    def _analyze_cross_jurisdiction_authority(self, source_case: CaselawNode,
                                            target_case: CaselawNode) -> Tuple[AuthorityLevel, float, List[str]]:
        """Analyze authority across different jurisdictions"""
        reasoning = []
        
        source_court = source_case.metadata.get("court_slug", "")
        target_court = target_case.metadata.get("court_slug", "")
        
        # US Supreme Court is binding on all jurisdictions
        if target_court == "us":
            reasoning.append("U.S. Supreme Court binding on all jurisdictions")
            return AuthorityLevel.BINDING, 0.95, reasoning
        
        # Federal circuit courts
        if target_court.startswith("us.ca") and source_court.startswith("us.ca"):
            if target_court == source_court:
                reasoning.append("Same federal circuit")
                return AuthorityLevel.BINDING, 0.9, reasoning
            else:
                reasoning.append("Different federal circuit - persuasive authority")
                return AuthorityLevel.PERSUASIVE, 0.6, reasoning
        
        # Federal to state
        if target_court.startswith("us.") and not source_court.startswith("us."):
            reasoning.append("Federal court persuasive to state court")
            return AuthorityLevel.PERSUASIVE, 0.5, reasoning
        
        # State to federal
        if not target_court.startswith("us.") and source_court.startswith("us."):
            reasoning.append("State court informative to federal court")
            return AuthorityLevel.INFORMATIVE, 0.3, reasoning
        
        # State to state
        if not target_court.startswith("us.") and not source_court.startswith("us."):
            # High-prestige state courts are more persuasive
            if self._is_high_prestige_court(target_court):
                reasoning.append("High-prestige state court")
                return AuthorityLevel.PERSUASIVE, 0.6, reasoning
            else:
                reasoning.append("Cross-state persuasive authority")
                return AuthorityLevel.PERSUASIVE, 0.4, reasoning
        
        return AuthorityLevel.INFORMATIVE, 0.2, reasoning
    
    def _is_superior_court(self, court1: str, court2: str) -> bool:
        """Check if court1 is superior to court2 in hierarchy"""
        rank1 = self.court_rankings.get(court1, 0)
        rank2 = self.court_rankings.get(court2, 0)
        return rank1 > rank2
    
    def _is_same_court_level(self, court1: str, court2: str) -> bool:
        """Check if courts are at the same hierarchical level"""
        rank1 = self.court_rankings.get(court1, 0)
        rank2 = self.court_rankings.get(court2, 0)
        # Allow small differences for courts at same level
        return abs(rank1 - rank2) <= 50
    
    def _is_high_prestige_court(self, court: str) -> bool:
        """Check if this is a high-prestige state court"""
        high_prestige = {
            "cal", "ny", "tex", "fla", "il", "pa", "ma", "va"
        }
        return any(court.startswith(state) for state in high_prestige)
    
    def _calculate_temporal_authority_adjustment(self, source_case: CaselawNode,
                                               target_case: CaselawNode) -> float:
        """Calculate authority adjustment based on temporal factors"""
        try:
            source_date_str = source_case.metadata.get("decision_date")
            target_date_str = target_case.metadata.get("decision_date")
            
            if not source_date_str or not target_date_str:
                return 1.0  # No adjustment if dates unavailable
            
            # Parse dates (handle various formats)
            source_date = self._parse_date(source_date_str)
            target_date = self._parse_date(target_date_str)
            
            if not source_date or not target_date:
                return 1.0
            
            # Calculate years difference
            years_diff = (source_date - target_date).days / 365.25
            
            # Authority decreases with age, but slowly
            if years_diff <= 5:
                return 1.0  # Full authority for recent cases
            elif years_diff <= 20:
                return 0.95  # Slight reduction
            elif years_diff <= 50:
                return 0.9   # Moderate reduction
            else:
                return 0.8   # Older cases still have substantial authority
                
        except Exception as e:
            logger.warning(f"Error calculating temporal adjustment: {e}")
            return 1.0
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string in various formats"""
        try:
            # Try ISO format first
            if "T" in date_str:
                return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            
            # Try date-only formats
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%Y"]:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            return None
            
        except Exception:
            return None
    
    async def find_binding_precedents(self, case: CaselawNode,
                                    candidates: List[CaselawNode]) -> List[AuthorityAnalysis]:
        """Find all binding precedents for a given case"""
        binding_precedents = []
        
        for candidate in candidates:
            analysis = await self.analyze_precedential_authority(case, candidate)
            if analysis.authority_level == AuthorityLevel.BINDING:
                binding_precedents.append(analysis)
        
        # Sort by confidence
        binding_precedents.sort(key=lambda x: x.confidence, reverse=True)
        return binding_precedents
    
    async def detect_circuit_splits(self, cases: List[CaselawNode],
                                  legal_issue: str) -> List[Dict[str, Any]]:
        """Detect circuit splits on legal issues"""
        splits = []
        
        # Group cases by circuit
        circuit_cases = {}
        for case in cases:
            court = case.metadata.get("court_slug", "")
            if court.startswith("us.ca"):
                circuit = court[:6]  # e.g., "us.ca1"
                if circuit not in circuit_cases:
                    circuit_cases[circuit] = []
                circuit_cases[circuit].append(case)
        
        # Look for conflicting holdings
        if len(circuit_cases) > 1:
            circuits = list(circuit_cases.keys())
            for i in range(len(circuits)):
                for j in range(i + 1, len(circuits)):
                    circuit1, circuit2 = circuits[i], circuits[j]
                    
                    # Simplified conflict detection
                    # In practice, this would analyze case holdings
                    split = {
                        "issue": legal_issue,
                        "circuit1": circuit1,
                        "circuit1_cases": [str(c.case_id) for c in circuit_cases[circuit1]],
                        "circuit2": circuit2,
                        "circuit2_cases": [str(c.case_id) for c in circuit_cases[circuit2]],
                        "confidence": 0.7,  # Would be calculated based on actual analysis
                        "analysis_needed": True
                    }
                    splits.append(split)
        
        return splits
    
    def get_jurisdiction_hierarchy(self, jurisdiction: str) -> List[str]:
        """Get hierarchical chain for a jurisdiction"""
        hierarchy = []
        
        # Federal hierarchy
        if jurisdiction.startswith("us."):
            hierarchy.append("us")  # Supreme Court
            if jurisdiction.startswith("us.ca"):
                hierarchy.append(jurisdiction)  # Circuit Court
            elif jurisdiction.startswith("us.d"):
                # Find which circuit this district belongs to
                for circuit, states in self.geographic_mappings.items():
                    if any(state in jurisdiction for state in states):
                        hierarchy.append(circuit)
                        break
                hierarchy.append(jurisdiction)  # District Court
        
        # State hierarchy (simplified)
        else:
            hierarchy.append(jurisdiction)  # State supreme court
            # Add intermediate appellate if exists
            if f"{jurisdiction}.appellate" in self.court_rankings:
                hierarchy.append(f"{jurisdiction}.appellate")
        
        return hierarchy