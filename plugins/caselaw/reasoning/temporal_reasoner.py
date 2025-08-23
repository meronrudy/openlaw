"""
Temporal Reasoning Engine for CAP Caselaw Plugin
Analyzes temporal relationships and precedential authority over time
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime, date, timedelta
from dataclasses import dataclass, field
from enum import Enum

from ..models.case_relationship import CaseRelationship, RelationshipType
from ..models.canonical_identifiers import DocumentID
from ..models.provenance_record import ProvenanceRecord, ProvenanceOperation, ProvenanceSource

logger = logging.getLogger(__name__)


class TemporalTrend(Enum):
    """Types of temporal trends in legal authority"""
    STRENGTHENING = "strengthening"
    WEAKENING = "weakening"
    STABLE = "stable"
    EMERGING = "emerging"
    DECLINING = "declining"
    OVERTURNED = "overturned"


@dataclass
class TemporalEvaluation:
    """Results of temporal precedent analysis"""
    case_id: DocumentID
    current_authority: float  # 0.0 to 1.0
    historical_authority: List[Tuple[date, float]]  # Authority over time
    trend: TemporalTrend
    trend_confidence: float
    superseding_cases: List[DocumentID] = field(default_factory=list)
    supporting_cases: List[DocumentID] = field(default_factory=list)
    timeline_events: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": str(self.case_id),
            "current_authority": self.current_authority,
            "historical_authority": [(d.isoformat(), a) for d, a in self.historical_authority],
            "trend": self.trend.value,
            "trend_confidence": self.trend_confidence,
            "superseding_cases": [str(c) for c in self.superseding_cases],
            "supporting_cases": [str(c) for c in self.supporting_cases],
            "timeline_events": self.timeline_events
        }


class TemporalReasoner:
    """
    Analyzes temporal relationships between cases and tracks how legal
    authority changes over time through subsequent decisions.
    """
    
    def __init__(self, store=None):
        self.store = store
        self.authority_decay_rate = 0.95  # Authority decays slowly over time
        self.overrule_threshold = 0.9  # Confidence needed to consider overruling
        
    def analyze_temporal_authority(self, case_id: DocumentID, 
                                 as_of_date: Optional[date] = None) -> TemporalEvaluation:
        """
        Analyze the temporal authority of a case as of a specific date
        
        Args:
            case_id: Case to analyze
            as_of_date: Date to analyze authority (defaults to today)
            
        Returns:
            Temporal evaluation of the case's authority
        """
        if as_of_date is None:
            as_of_date = date.today()
        
        # Get case decision date and initial authority
        case_info = self._get_case_info(case_id)
        if not case_info:
            return self._create_default_evaluation(case_id)
        
        decision_date = case_info.get("decision_date")
        if not decision_date:
            return self._create_default_evaluation(case_id)
        
        # Build timeline of authority changes
        timeline = self._build_authority_timeline(case_id, decision_date, as_of_date)
        
        # Calculate current authority
        current_authority = self._calculate_current_authority(timeline, as_of_date)
        
        # Identify trend
        trend, trend_confidence = self._identify_trend(timeline)
        
        # Find superseding and supporting cases
        superseding_cases = self._find_superseding_cases(case_id, as_of_date)
        supporting_cases = self._find_supporting_cases(case_id, as_of_date)
        
        return TemporalEvaluation(
            case_id=case_id,
            current_authority=current_authority,
            historical_authority=timeline,
            trend=trend,
            trend_confidence=trend_confidence,
            superseding_cases=superseding_cases,
            supporting_cases=supporting_cases,
            timeline_events=self._extract_timeline_events(case_id, as_of_date)
        )
    
    def _build_authority_timeline(self, case_id: DocumentID, 
                                decision_date: date, as_of_date: date) -> List[Tuple[date, float]]:
        """Build timeline of authority changes for a case"""
        timeline = []
        
        # Start with initial authority (1.0 at decision)
        timeline.append((decision_date, 1.0))
        
        # Get all relationships affecting this case
        relationships = self._get_case_relationships(case_id, decision_date, as_of_date)
        
        current_authority = 1.0
        current_date = decision_date
        
        # Process each relationship chronologically
        for relationship in sorted(relationships, key=lambda r: r.get("date", decision_date)):
            rel_date = relationship.get("date", current_date)
            rel_type = relationship.get("type")
            rel_confidence = relationship.get("confidence", 0.5)
            
            # Calculate authority impact
            authority_change = self._calculate_authority_change(rel_type, rel_confidence)
            current_authority = max(0.0, min(1.0, current_authority + authority_change))
            
            timeline.append((rel_date, current_authority))
            current_date = rel_date
        
        # Apply natural decay over time
        if as_of_date > current_date:
            days_elapsed = (as_of_date - current_date).days
            decay_factor = self.authority_decay_rate ** (days_elapsed / 365.25)  # Annual decay
            final_authority = current_authority * decay_factor
            timeline.append((as_of_date, final_authority))
        
        return timeline
    
    def _calculate_authority_change(self, relationship_type: str, confidence: float) -> float:
        """Calculate how much a relationship changes authority"""
        base_impacts = {
            "overrules": -0.9,
            "reverses": -0.8,
            "supersedes": -0.9,
            "distinguishes": -0.3,
            "limits": -0.2,
            "questions": -0.1,
            "disagrees_with": -0.1,
            "follows": 0.1,
            "affirms": 0.2,
            "applies": 0.1,
            "extends": 0.1,
            "cites_case": 0.05
        }
        
        base_impact = base_impacts.get(relationship_type, 0.0)
        return base_impact * confidence
    
    def _identify_trend(self, timeline: List[Tuple[date, float]]) -> Tuple[TemporalTrend, float]:
        """Identify the overall trend in authority over time"""
        if len(timeline) < 2:
            return TemporalTrend.STABLE, 0.5
        
        # Calculate trend using linear regression on recent data
        recent_timeline = timeline[-min(10, len(timeline)):]  # Last 10 points
        
        if len(recent_timeline) < 2:
            return TemporalTrend.STABLE, 0.5
        
        # Simple slope calculation
        x_vals = [(d - recent_timeline[0][0]).days for d, _ in recent_timeline]
        y_vals = [a for _, a in recent_timeline]
        
        if len(x_vals) < 2:
            return TemporalTrend.STABLE, 0.5
        
        # Calculate slope
        n = len(x_vals)
        slope = (n * sum(x * y for x, y in zip(x_vals, y_vals)) - sum(x_vals) * sum(y_vals)) / \
                (n * sum(x * x for x in x_vals) - sum(x_vals) ** 2) if sum(x * x for x in x_vals) != (sum(x_vals) ** 2) / n else 0
        
        # Determine trend based on slope
        if abs(slope) < 0.0001:  # Essentially flat
            return TemporalTrend.STABLE, 0.8
        elif slope > 0.001:
            return TemporalTrend.STRENGTHENING, min(0.9, abs(slope) * 1000)
        elif slope < -0.001:
            if recent_timeline[-1][1] < 0.1:  # Very low authority
                return TemporalTrend.OVERTURNED, min(0.9, abs(slope) * 1000)
            else:
                return TemporalTrend.WEAKENING, min(0.9, abs(slope) * 1000)
        else:
            return TemporalTrend.STABLE, 0.6
    
    def _calculate_current_authority(self, timeline: List[Tuple[date, float]], 
                                   as_of_date: date) -> float:
        """Calculate current authority as of a specific date"""
        if not timeline:
            return 0.0
        
        # Find the most recent authority value
        relevant_entries = [(d, a) for d, a in timeline if d <= as_of_date]
        
        if not relevant_entries:
            return 0.0
        
        return relevant_entries[-1][1]
    
    def _find_superseding_cases(self, case_id: DocumentID, as_of_date: date) -> List[DocumentID]:
        """Find cases that supersede or overrule the given case"""
        superseding = []
        
        # Query for cases that overrule, reverse, or supersede this case
        relationships = self._query_relationships_targeting_case(case_id, as_of_date)
        
        for rel in relationships:
            if rel.get("type") in ["overrules", "reverses", "supersedes"]:
                if rel.get("confidence", 0) >= self.overrule_threshold:
                    superseding.append(DocumentID(rel.get("source_case")))
        
        return superseding
    
    def _find_supporting_cases(self, case_id: DocumentID, as_of_date: date) -> List[DocumentID]:
        """Find cases that support or follow the given case"""
        supporting = []
        
        # Query for cases that follow, apply, or extend this case
        relationships = self._query_relationships_targeting_case(case_id, as_of_date)
        
        for rel in relationships:
            if rel.get("type") in ["follows", "applies", "extends", "affirms"]:
                if rel.get("confidence", 0) >= 0.7:
                    supporting.append(DocumentID(rel.get("source_case")))
        
        return supporting[:10]  # Limit to most relevant
    
    def _extract_timeline_events(self, case_id: DocumentID, as_of_date: date) -> List[Dict[str, Any]]:
        """Extract key timeline events affecting the case's authority"""
        events = []
        
        # Get case decision as first event
        case_info = self._get_case_info(case_id)
        if case_info and case_info.get("decision_date"):
            events.append({
                "date": case_info["decision_date"].isoformat(),
                "type": "decision",
                "description": f"Case decided",
                "impact": "initial_authority",
                "authority_level": 1.0
            })
        
        # Get significant relationship events
        relationships = self._get_case_relationships(case_id, case_info.get("decision_date"), as_of_date)
        
        for rel in relationships:
            if rel.get("confidence", 0) >= 0.8:  # Only high-confidence relationships
                events.append({
                    "date": rel.get("date", "").isoformat() if rel.get("date") else "",
                    "type": "relationship",
                    "relationship_type": rel.get("type"),
                    "source_case": rel.get("source_case"),
                    "description": f"Case {rel.get('type')} by {rel.get('source_case')}",
                    "confidence": rel.get("confidence")
                })
        
        return sorted(events, key=lambda e: e.get("date", ""))
    
    def compute_precedential_strength(self, citing_case: DocumentID, 
                                    cited_case: DocumentID, 
                                    relationship_type: RelationshipType) -> float:
        """
        Compute the precedential strength between two cases
        
        Args:
            citing_case: Case doing the citing
            cited_case: Case being cited
            relationship_type: Type of relationship
            
        Returns:
            Precedential strength score (0.0 to 1.0)
        """
        # Get base strength from relationship type
        base_strength = RelationshipType.get_precedential_strength(relationship_type)
        
        # Adjust based on temporal factors
        temporal_factor = self._calculate_temporal_factor(citing_case, cited_case)
        
        # Adjust based on jurisdictional factors (simplified)
        jurisdictional_factor = self._calculate_jurisdictional_factor(citing_case, cited_case)
        
        # Combine factors
        final_strength = base_strength * temporal_factor * jurisdictional_factor
        
        return max(0.0, min(1.0, final_strength))
    
    def _calculate_temporal_factor(self, citing_case: DocumentID, cited_case: DocumentID) -> float:
        """Calculate temporal adjustment factor"""
        citing_info = self._get_case_info(citing_case)
        cited_info = self._get_case_info(cited_case)
        
        if not citing_info or not cited_info:
            return 1.0
        
        citing_date = citing_info.get("decision_date")
        cited_date = cited_info.get("decision_date")
        
        if not citing_date or not cited_date:
            return 1.0
        
        # Cases can only cite earlier cases
        if citing_date <= cited_date:
            return 0.1  # Very weak if temporal order is wrong
        
        # Calculate age factor
        days_between = (citing_date - cited_date).days
        years_between = days_between / 365.25
        
        # Authority decays slowly over time
        if years_between <= 5:
            return 1.0
        elif years_between <= 20:
            return 0.9
        elif years_between <= 50:
            return 0.8
        else:
            return 0.7
    
    def _calculate_jurisdictional_factor(self, citing_case: DocumentID, cited_case: DocumentID) -> float:
        """Calculate jurisdictional adjustment factor (simplified)"""
        # This would be enhanced with actual jurisdictional analysis
        return 1.0
    
    # Helper methods for data access (would integrate with actual storage)
    def _get_case_info(self, case_id: DocumentID) -> Optional[Dict[str, Any]]:
        """Get basic case information"""
        # Placeholder - would query actual storage
        return {
            "case_id": str(case_id),
            "decision_date": date(2000, 1, 1),  # Default date
            "court": "Unknown",
            "jurisdiction": "US"
        }
    
    def _get_case_relationships(self, case_id: DocumentID, 
                              start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Get relationships affecting a case within date range"""
        # Placeholder - would query actual storage
        return []
    
    def _query_relationships_targeting_case(self, case_id: DocumentID, 
                                          as_of_date: date) -> List[Dict[str, Any]]:
        """Query relationships where the case is the target"""
        # Placeholder - would query actual storage
        return []
    
    def _create_default_evaluation(self, case_id: DocumentID) -> TemporalEvaluation:
        """Create default evaluation when case info is unavailable"""
        return TemporalEvaluation(
            case_id=case_id,
            current_authority=0.5,
            historical_authority=[(date.today(), 0.5)],
            trend=TemporalTrend.STABLE,
            trend_confidence=0.1,
            superseding_cases=[],
            supporting_cases=[],
            timeline_events=[]
        )