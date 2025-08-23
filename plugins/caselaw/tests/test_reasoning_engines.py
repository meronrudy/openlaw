"""
Test suite for Reasoning Engine components
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any
from datetime import datetime, timedelta

from ..reasoning.temporal_reasoner import TemporalReasoner, AuthorityTrend, TemporalAnalysis
from ..reasoning.jurisdictional_reasoner import (
    JurisdictionalReasoner, AuthorityLevel, AuthorityAnalysis, JurisdictionalRelation
)
from ..models.caselaw_node import CaselawNode, CourtLevel, JurisdictionType
from ..models.canonical_identifiers import DocumentID


class TestTemporalReasoner:
    """Test suite for TemporalReasoner"""
    
    @pytest.fixture
    def temporal_reasoner(self):
        """Create temporal reasoner for testing"""
        return TemporalReasoner()
    
    @pytest.fixture
    def old_case(self):
        """Create an old case for testing"""
        return CaselawNode(
            case_id=DocumentID("cap:old123"),
            case_name="Old v. Case",
            full_text="Old case text...",
            court_level=CourtLevel.SUPREME,
            jurisdiction_type=JurisdictionType.FEDERAL,
            decision_date=datetime(1950, 1, 1),
            metadata={
                "court_slug": "us",
                "jurisdiction_slug": "us",
                "decision_date": "1950-01-01"
            }
        )
    
    @pytest.fixture
    def recent_case(self):
        """Create a recent case for testing"""
        return CaselawNode(
            case_id=DocumentID("cap:recent123"),
            case_name="Recent v. Case",
            full_text="Recent case text...",
            court_level=CourtLevel.SUPREME,
            jurisdiction_type=JurisdictionType.FEDERAL,
            decision_date=datetime(2020, 1, 1),
            metadata={
                "court_slug": "us",
                "jurisdiction_slug": "us",
                "decision_date": "2020-01-01"
            }
        )
    
    @pytest.mark.asyncio
    async def test_analyze_temporal_authority(self, temporal_reasoner, old_case, recent_case):
        """Test temporal authority analysis"""
        cases = [old_case, recent_case]
        
        analysis = await temporal_reasoner.analyze_temporal_authority(cases, "constitutional law")
        
        assert isinstance(analysis, TemporalAnalysis)
        assert analysis.legal_issue == "constitutional law"
        assert len(analysis.authority_timeline) >= 2
        assert analysis.current_authority is not None
        assert 0.0 <= analysis.stability_score <= 1.0
    
    @pytest.mark.asyncio
    async def test_calculate_precedent_strength(self, temporal_reasoner, recent_case):
        """Test precedent strength calculation"""
        strength = await temporal_reasoner.calculate_precedent_strength(recent_case)
        
        assert 0.0 <= strength <= 1.0
        
        # Recent Supreme Court case should have high strength
        assert strength > 0.7
    
    @pytest.mark.asyncio
    async def test_calculate_precedent_strength_old_case(self, temporal_reasoner, old_case):
        """Test precedent strength for old case"""
        strength = await temporal_reasoner.calculate_precedent_strength(old_case)
        
        assert 0.0 <= strength <= 1.0
        
        # Old case should have somewhat reduced strength due to age
        # but still significant as Supreme Court case
        assert strength > 0.4
    
    @pytest.mark.asyncio
    async def test_identify_authority_trends(self, temporal_reasoner, old_case, recent_case):
        """Test authority trend identification"""
        cases = [old_case, recent_case]
        
        trends = await temporal_reasoner.identify_authority_trends(cases, "constitutional law")
        
        assert isinstance(trends, list)
        assert len(trends) >= 0
        
        # Each trend should have proper structure
        for trend in trends:
            assert isinstance(trend, AuthorityTrend)
            assert trend.trend_type in ["increasing", "decreasing", "stable", "emerging", "declining"]
            assert 0.0 <= trend.confidence <= 1.0
    
    @pytest.mark.asyncio
    async def test_calculate_temporal_relevance(self, temporal_reasoner, recent_case):
        """Test temporal relevance calculation"""
        current_date = datetime.now()
        relevance = await temporal_reasoner.calculate_temporal_relevance(recent_case, current_date)
        
        assert 0.0 <= relevance <= 1.0
        
        # Recent case should have high relevance
        assert relevance > 0.8
    
    @pytest.mark.asyncio
    async def test_calculate_temporal_relevance_old_case(self, temporal_reasoner, old_case):
        """Test temporal relevance for old case"""
        current_date = datetime.now()
        relevance = await temporal_reasoner.calculate_temporal_relevance(old_case, current_date)
        
        assert 0.0 <= relevance <= 1.0
        
        # Old case should have lower relevance but not zero
        assert 0.2 <= relevance <= 0.8
    
    def test_calculate_age_factor(self, temporal_reasoner):
        """Test age factor calculation"""
        # Recent date
        recent_date = datetime.now() - timedelta(days=30)
        recent_factor = temporal_reasoner._calculate_age_factor(recent_date)
        assert recent_factor > 0.9
        
        # Old date
        old_date = datetime.now() - timedelta(days=365 * 50)  # 50 years ago
        old_factor = temporal_reasoner._calculate_age_factor(old_date)
        assert 0.1 <= old_factor <= 0.7
        
        # Very old date
        very_old_date = datetime.now() - timedelta(days=365 * 100)  # 100 years ago
        very_old_factor = temporal_reasoner._calculate_age_factor(very_old_date)
        assert 0.1 <= very_old_factor <= 0.5
    
    def test_calculate_citation_momentum(self, temporal_reasoner):
        """Test citation momentum calculation"""
        # Mock citation data
        citation_history = [
            {"year": 2020, "count": 50},
            {"year": 2021, "count": 75},
            {"year": 2022, "count": 100},
            {"year": 2023, "count": 120}
        ]
        
        momentum = temporal_reasoner._calculate_citation_momentum(citation_history)
        
        assert momentum > 0  # Increasing citations should give positive momentum
        assert momentum <= 2.0  # Should be reasonable upper bound
    
    def test_assess_doctrinal_stability(self, temporal_reasoner):
        """Test doctrinal stability assessment"""
        # Mock case history showing stability
        stable_cases = [
            {"year": 2010, "holding": "principle A"},
            {"year": 2015, "holding": "principle A"},
            {"year": 2020, "holding": "principle A"}
        ]
        
        stability = temporal_reasoner._assess_doctrinal_stability(stable_cases)
        assert stability > 0.8
        
        # Mock case history showing instability
        unstable_cases = [
            {"year": 2010, "holding": "principle A"},
            {"year": 2015, "holding": "principle B"},
            {"year": 2020, "holding": "principle C"}
        ]
        
        instability = temporal_reasoner._assess_doctrinal_stability(unstable_cases)
        assert instability < 0.5


class TestJurisdictionalReasoner:
    """Test suite for JurisdictionalReasoner"""
    
    @pytest.fixture
    def jurisdictional_reasoner(self):
        """Create jurisdictional reasoner for testing"""
        return JurisdictionalReasoner()
    
    @pytest.fixture
    def supreme_court_case(self):
        """Create Supreme Court case for testing"""
        return CaselawNode(
            case_id=DocumentID("cap:scotus123"),
            case_name="Supreme v. Court",
            full_text="Supreme Court case text...",
            court_level=CourtLevel.SUPREME,
            jurisdiction_type=JurisdictionType.FEDERAL,
            decision_date=datetime(2020, 1, 1),
            metadata={
                "court_slug": "us",
                "jurisdiction_slug": "us",
                "decision_date": "2020-01-01"
            }
        )
    
    @pytest.fixture
    def circuit_court_case(self):
        """Create Circuit Court case for testing"""
        return CaselawNode(
            case_id=DocumentID("cap:circuit123"),
            case_name="Circuit v. Court",
            full_text="Circuit court case text...",
            court_level=CourtLevel.APPELLATE,
            jurisdiction_type=JurisdictionType.FEDERAL,
            decision_date=datetime(2020, 1, 1),
            metadata={
                "court_slug": "us.ca9",
                "jurisdiction_slug": "us",
                "decision_date": "2020-01-01"
            }
        )
    
    @pytest.fixture
    def district_court_case(self):
        """Create District Court case for testing"""
        return CaselawNode(
            case_id=DocumentID("cap:district123"),
            case_name="District v. Court",
            full_text="District court case text...",
            court_level=CourtLevel.DISTRICT,
            jurisdiction_type=JurisdictionType.FEDERAL,
            decision_date=datetime(2020, 1, 1),
            metadata={
                "court_slug": "us.d.ca",
                "jurisdiction_slug": "us",
                "decision_date": "2020-01-01"
            }
        )
    
    @pytest.mark.asyncio
    async def test_analyze_precedential_authority_supreme_over_circuit(
        self, jurisdictional_reasoner, circuit_court_case, supreme_court_case
    ):
        """Test authority analysis: Supreme Court over Circuit Court"""
        analysis = await jurisdictional_reasoner.analyze_precedential_authority(
            circuit_court_case, supreme_court_case
        )
        
        assert isinstance(analysis, AuthorityAnalysis)
        assert analysis.authority_level == AuthorityLevel.BINDING
        assert analysis.confidence > 0.8
        assert len(analysis.reasoning) > 0
        assert "Superior court" in analysis.reasoning[0] or "Supreme Court" in analysis.reasoning[0]
    
    @pytest.mark.asyncio
    async def test_analyze_precedential_authority_circuit_over_district(
        self, jurisdictional_reasoner, district_court_case, circuit_court_case
    ):
        """Test authority analysis: Circuit Court over District Court"""
        analysis = await jurisdictional_reasoner.analyze_precedential_authority(
            district_court_case, circuit_court_case
        )
        
        assert isinstance(analysis, AuthorityAnalysis)
        assert analysis.authority_level == AuthorityLevel.BINDING
        assert analysis.confidence > 0.7
    
    @pytest.mark.asyncio
    async def test_analyze_precedential_authority_same_court(
        self, jurisdictional_reasoner, circuit_court_case
    ):
        """Test authority analysis within same court"""
        # Create another circuit court case (older)
        older_case = CaselawNode(
            case_id=DocumentID("cap:circuit456"),
            case_name="Older v. Case",
            full_text="Older case text...",
            court_level=CourtLevel.APPELLATE,
            jurisdiction_type=JurisdictionType.FEDERAL,
            decision_date=datetime(2010, 1, 1),
            metadata={
                "court_slug": "us.ca9",
                "jurisdiction_slug": "us",
                "decision_date": "2010-01-01"
            }
        )
        
        analysis = await jurisdictional_reasoner.analyze_precedential_authority(
            circuit_court_case, older_case
        )
        
        assert isinstance(analysis, AuthorityAnalysis)
        assert analysis.authority_level in [AuthorityLevel.BINDING, AuthorityLevel.PERSUASIVE]
    
    @pytest.mark.asyncio
    async def test_analyze_precedential_authority_cross_jurisdiction(
        self, jurisdictional_reasoner, supreme_court_case
    ):
        """Test authority analysis across jurisdictions"""
        state_case = CaselawNode(
            case_id=DocumentID("cap:state123"),
            case_name="State v. Case",
            full_text="State case text...",
            court_level=CourtLevel.SUPREME,
            jurisdiction_type=JurisdictionType.STATE,
            decision_date=datetime(2020, 1, 1),
            metadata={
                "court_slug": "cal",
                "jurisdiction_slug": "cal",
                "decision_date": "2020-01-01"
            }
        )
        
        analysis = await jurisdictional_reasoner.analyze_precedential_authority(
            state_case, supreme_court_case
        )
        
        assert isinstance(analysis, AuthorityAnalysis)
        assert analysis.authority_level == AuthorityLevel.BINDING
        assert analysis.confidence > 0.9
        assert "U.S. Supreme Court binding" in analysis.reasoning[0]
    
    def test_is_superior_court(self, jurisdictional_reasoner):
        """Test superior court identification"""
        # US Supreme Court over Circuit Court
        assert jurisdictional_reasoner._is_superior_court("us", "us.ca9")
        
        # Circuit Court over District Court
        assert jurisdictional_reasoner._is_superior_court("us.ca9", "us.d.ca")
        
        # Not superior relationships
        assert not jurisdictional_reasoner._is_superior_court("us.ca9", "us")
        assert not jurisdictional_reasoner._is_superior_court("us.d.ca", "us.ca9")
    
    def test_is_same_court_level(self, jurisdictional_reasoner):
        """Test same court level identification"""
        # Same circuit courts
        assert jurisdictional_reasoner._is_same_court_level("us.ca9", "us.ca2")
        
        # Same district courts
        assert jurisdictional_reasoner._is_same_court_level("us.d.ca", "us.d.ny")
        
        # Different levels
        assert not jurisdictional_reasoner._is_same_court_level("us", "us.ca9")
        assert not jurisdictional_reasoner._is_same_court_level("us.ca9", "us.d.ca")
    
    def test_is_high_prestige_court(self, jurisdictional_reasoner):
        """Test high prestige court identification"""
        # High prestige state courts
        assert jurisdictional_reasoner._is_high_prestige_court("cal")
        assert jurisdictional_reasoner._is_high_prestige_court("ny")
        assert jurisdictional_reasoner._is_high_prestige_court("tex")
        
        # Lower prestige courts
        assert not jurisdictional_reasoner._is_high_prestige_court("wy")  # Wyoming
        assert not jurisdictional_reasoner._is_high_prestige_court("unknown")
    
    def test_calculate_temporal_authority_adjustment(self, jurisdictional_reasoner):
        """Test temporal authority adjustment"""
        recent_case = CaselawNode(
            case_id=DocumentID("cap:recent"),
            case_name="Recent Case",
            full_text="Recent case text...",
            court_level=CourtLevel.SUPREME,
            jurisdiction_type=JurisdictionType.FEDERAL,
            decision_date=datetime.now() - timedelta(days=365),  # 1 year ago
            metadata={"decision_date": (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")}
        )
        
        old_case = CaselawNode(
            case_id=DocumentID("cap:old"),
            case_name="Old Case",
            full_text="Old case text...",
            court_level=CourtLevel.SUPREME,
            jurisdiction_type=JurisdictionType.FEDERAL,
            decision_date=datetime.now() - timedelta(days=365 * 50),  # 50 years ago
            metadata={"decision_date": (datetime.now() - timedelta(days=365 * 50)).strftime("%Y-%m-%d")}
        )
        
        recent_adjustment = jurisdictional_reasoner._calculate_temporal_authority_adjustment(
            recent_case, recent_case
        )
        old_adjustment = jurisdictional_reasoner._calculate_temporal_authority_adjustment(
            recent_case, old_case
        )
        
        # Recent cases should have higher adjustment
        assert recent_adjustment >= old_adjustment
        assert 0.8 <= recent_adjustment <= 1.0
        assert 0.6 <= old_adjustment <= 1.0
    
    @pytest.mark.asyncio
    async def test_find_binding_precedents(self, jurisdictional_reasoner, district_court_case):
        """Test finding binding precedents"""
        # Create various precedent candidates
        supreme_case = CaselawNode(
            case_id=DocumentID("cap:supreme"),
            case_name="Supreme Case",
            full_text="Supreme case text...",
            court_level=CourtLevel.SUPREME,
            jurisdiction_type=JurisdictionType.FEDERAL,
            decision_date=datetime(2020, 1, 1),
            metadata={"court_slug": "us", "decision_date": "2020-01-01"}
        )
        
        circuit_case = CaselawNode(
            case_id=DocumentID("cap:circuit"),
            case_name="Circuit Case",
            full_text="Circuit case text...",
            court_level=CourtLevel.APPELLATE,
            jurisdiction_type=JurisdictionType.FEDERAL,
            decision_date=datetime(2020, 1, 1),
            metadata={"court_slug": "us.ca9", "decision_date": "2020-01-01"}
        )
        
        candidates = [supreme_case, circuit_case]
        
        binding_precedents = await jurisdictional_reasoner.find_binding_precedents(
            district_court_case, candidates
        )
        
        assert isinstance(binding_precedents, list)
        assert len(binding_precedents) >= 1  # Should find at least the Supreme Court case
        
        # Should be sorted by confidence
        if len(binding_precedents) > 1:
            for i in range(len(binding_precedents) - 1):
                assert binding_precedents[i].confidence >= binding_precedents[i + 1].confidence
    
    @pytest.mark.asyncio
    async def test_detect_circuit_splits(self, jurisdictional_reasoner):
        """Test circuit split detection"""
        # Create cases from different circuits
        ca9_case = CaselawNode(
            case_id=DocumentID("cap:ca9"),
            case_name="Ninth Circuit Case",
            full_text="Ninth circuit case text...",
            court_level=CourtLevel.APPELLATE,
            jurisdiction_type=JurisdictionType.FEDERAL,
            decision_date=datetime(2020, 1, 1),
            metadata={"court_slug": "us.ca9"}
        )
        
        ca2_case = CaselawNode(
            case_id=DocumentID("cap:ca2"),
            case_name="Second Circuit Case",
            full_text="Second circuit case text...",
            court_level=CourtLevel.APPELLATE,
            jurisdiction_type=JurisdictionType.FEDERAL,
            decision_date=datetime(2020, 1, 1),
            metadata={"court_slug": "us.ca2"}
        )
        
        cases = [ca9_case, ca2_case]
        
        splits = await jurisdictional_reasoner.detect_circuit_splits(cases, "constitutional interpretation")
        
        assert isinstance(splits, list)
        # May or may not detect splits depending on implementation
        # but should return valid structure
        for split in splits:
            assert "issue" in split
            assert "circuit1" in split
            assert "circuit2" in split
            assert "confidence" in split
    
    def test_get_jurisdiction_hierarchy(self, jurisdictional_reasoner):
        """Test jurisdiction hierarchy retrieval"""
        # Federal hierarchy
        federal_hierarchy = jurisdictional_reasoner.get_jurisdiction_hierarchy("us.d.ca")
        assert "us" in federal_hierarchy  # Supreme Court should be in hierarchy
        
        # State hierarchy
        state_hierarchy = jurisdictional_reasoner.get_jurisdiction_hierarchy("cal")
        assert "cal" in state_hierarchy  # State supreme court should be in hierarchy


class TestReasoningIntegration:
    """Integration tests for reasoning engines"""
    
    @pytest.mark.asyncio
    async def test_combined_temporal_jurisdictional_analysis(self):
        """Test combined temporal and jurisdictional analysis"""
        temporal_reasoner = TemporalReasoner()
        jurisdictional_reasoner = JurisdictionalReasoner()
        
        # Create test cases
        old_supreme_case = CaselawNode(
            case_id=DocumentID("cap:old_supreme"),
            case_name="Old Supreme Case",
            full_text="Old Supreme case text...",
            court_level=CourtLevel.SUPREME,
            jurisdiction_type=JurisdictionType.FEDERAL,
            decision_date=datetime(1970, 1, 1),
            metadata={
                "court_slug": "us",
                "jurisdiction_slug": "us",
                "decision_date": "1970-01-01"
            }
        )
        
        recent_circuit_case = CaselawNode(
            case_id=DocumentID("cap:recent_circuit"),
            case_name="Recent Circuit Case",
            full_text="Recent circuit case text...",
            court_level=CourtLevel.APPELLATE,
            jurisdiction_type=JurisdictionType.FEDERAL,
            decision_date=datetime(2022, 1, 1),
            metadata={
                "court_slug": "us.ca9",
                "jurisdiction_slug": "us",
                "decision_date": "2022-01-01"
            }
        )
        
        # Temporal analysis
        temporal_strength_old = await temporal_reasoner.calculate_precedent_strength(old_supreme_case)
        temporal_strength_recent = await temporal_reasoner.calculate_precedent_strength(recent_circuit_case)
        
        # Jurisdictional analysis
        jurisdictional_analysis = await jurisdictional_reasoner.analyze_precedential_authority(
            recent_circuit_case, old_supreme_case
        )
        
        # Combined analysis should show:
        # - Old Supreme Court case has binding authority despite age
        # - Recent circuit case has high temporal relevance but lower authority
        assert temporal_strength_old > 0.4  # Still strong due to Supreme Court
        assert temporal_strength_recent > 0.8  # Very recent
        assert jurisdictional_analysis.authority_level == AuthorityLevel.BINDING
        assert jurisdictional_analysis.confidence > 0.8
    
    @pytest.mark.asyncio
    async def test_reasoning_with_missing_data(self):
        """Test reasoning engines with incomplete data"""
        temporal_reasoner = TemporalReasoner()
        jurisdictional_reasoner = JurisdictionalReasoner()
        
        # Case with missing date
        incomplete_case = CaselawNode(
            case_id=DocumentID("cap:incomplete"),
            case_name="Incomplete Case",
            full_text="Incomplete case text...",
            court_level=CourtLevel.DISTRICT,
            jurisdiction_type=JurisdictionType.FEDERAL,
            decision_date=None,  # Missing date
            metadata={"court_slug": "us.d.ca"}  # Missing decision_date in metadata too
        )
        
        complete_case = CaselawNode(
            case_id=DocumentID("cap:complete"),
            case_name="Complete Case",
            full_text="Complete case text...",
            court_level=CourtLevel.SUPREME,
            jurisdiction_type=JurisdictionType.FEDERAL,
            decision_date=datetime(2020, 1, 1),
            metadata={
                "court_slug": "us",
                "decision_date": "2020-01-01"
            }
        )
        
        # Should handle missing data gracefully
        strength = await temporal_reasoner.calculate_precedent_strength(incomplete_case)
        assert 0.0 <= strength <= 1.0
        
        analysis = await jurisdictional_reasoner.analyze_precedential_authority(
            incomplete_case, complete_case
        )
        assert isinstance(analysis, AuthorityAnalysis)
        assert analysis.confidence >= 0.0
    
    @pytest.mark.asyncio
    async def test_performance_with_large_case_sets(self):
        """Test reasoning engine performance with large case sets"""
        temporal_reasoner = TemporalReasoner()
        
        # Create many test cases
        cases = []
        for i in range(100):
            case = CaselawNode(
                case_id=DocumentID(f"cap:case{i}"),
                case_name=f"Case {i}",
                full_text=f"Case {i} text...",
                court_level=CourtLevel.DISTRICT,
                jurisdiction_type=JurisdictionType.FEDERAL,
                decision_date=datetime(2000 + i % 24, 1, 1),  # Spread over 24 years
                metadata={
                    "court_slug": "us.d.ca",
                    "decision_date": f"{2000 + i % 24}-01-01"
                }
            )
            cases.append(case)
        
        # Should complete temporal analysis in reasonable time
        import time
        start_time = time.time()
        
        analysis = await temporal_reasoner.analyze_temporal_authority(cases, "test issue")
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should complete within reasonable time (less than 5 seconds)
        assert processing_time < 5.0
        assert isinstance(analysis, TemporalAnalysis)
        assert len(analysis.authority_timeline) > 0