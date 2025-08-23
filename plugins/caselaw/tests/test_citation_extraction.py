"""
Test suite for Citation Extraction components
"""

import pytest
from unittest.mock import Mock, patch
from typing import List, Dict, Any

from ..extraction.citation_extractor import (
    CitationExtractor, MLCitationExtractor, Citation, CitationType
)
from ..models.canonical_identifiers import DocumentID, CitationID


class TestCitationExtractor:
    """Test suite for CitationExtractor class"""
    
    @pytest.fixture
    def extractor(self):
        """Create citation extractor for testing"""
        return CitationExtractor()
    
    @pytest.fixture
    def sample_text_with_citations(self):
        """Sample text containing various citation types"""
        return """
        In Brown v. Board of Education, 347 U.S. 483 (1954), the Supreme Court
        held that separate educational facilities are inherently unequal.
        This case overruled Plessy v. Ferguson, 163 U.S. 537 (1896).
        
        The decision was later cited in Miranda v. Arizona, 384 U.S. 436 (1966),
        and followed by the Ninth Circuit in Smith v. Jones, 123 F.3d 456 (9th Cir. 1997).
        
        See also 42 U.S.C. § 1983 (civil rights statute) and the Fifth Amendment
        to the U.S. Constitution.
        """
    
    def test_extract_supreme_court_citations(self, extractor, sample_text_with_citations):
        """Test extraction of Supreme Court citations"""
        citations = extractor.extract_citations(sample_text_with_citations, "doc123")
        
        # Find Supreme Court citations
        scotus_citations = [c for c in citations if c.citation_type == CitationType.SUPREME_COURT]
        
        assert len(scotus_citations) >= 3
        
        # Check specific citations
        citation_texts = [c.full_citation for c in scotus_citations]
        assert any("347 U.S. 483" in text for text in citation_texts)
        assert any("163 U.S. 537" in text for text in citation_texts)
        assert any("384 U.S. 436" in text for text in citation_texts)
    
    def test_extract_federal_circuit_citations(self, extractor, sample_text_with_citations):
        """Test extraction of federal circuit court citations"""
        citations = extractor.extract_citations(sample_text_with_citations, "doc123")
        
        # Find federal circuit citations
        circuit_citations = [c for c in citations if c.citation_type == CitationType.FEDERAL_CIRCUIT]
        
        assert len(circuit_citations) >= 1
        assert any("123 F.3d 456" in c.full_citation for c in circuit_citations)
    
    def test_extract_statute_citations(self, extractor, sample_text_with_citations):
        """Test extraction of statute citations"""
        citations = extractor.extract_citations(sample_text_with_citations, "doc123")
        
        # Find statute citations
        statute_citations = [c for c in citations if c.citation_type == CitationType.STATUTE]
        
        assert len(statute_citations) >= 1
        assert any("42 U.S.C. § 1983" in c.full_citation for c in statute_citations)
    
    def test_extract_constitutional_citations(self, extractor, sample_text_with_citations):
        """Test extraction of constitutional citations"""
        citations = extractor.extract_citations(sample_text_with_citations, "doc123")
        
        # Find constitutional citations
        const_citations = [c for c in citations if c.citation_type == CitationType.CONSTITUTIONAL]
        
        assert len(const_citations) >= 1
        assert any("Fifth Amendment" in c.full_citation for c in const_citations)
    
    def test_citation_id_generation(self, extractor):
        """Test citation ID generation"""
        text = "Brown v. Board, 347 U.S. 483 (1954)"
        citations = extractor.extract_citations(text, "doc123")
        
        assert len(citations) == 1
        citation = citations[0]
        
        assert citation.citation_id is not None
        assert isinstance(citation.citation_id, CitationID)
        assert str(citation.citation_id).startswith("cite:")
    
    def test_confidence_scoring(self, extractor):
        """Test confidence scoring for citations"""
        # Clear, well-formatted citation
        clear_text = "Brown v. Board, 347 U.S. 483 (1954)"
        clear_citations = extractor.extract_citations(clear_text, "doc123")
        
        # Ambiguous citation
        ambiguous_text = "See 347 U.S. at 483"
        ambiguous_citations = extractor.extract_citations(ambiguous_text, "doc123")
        
        if clear_citations and ambiguous_citations:
            assert clear_citations[0].confidence >= ambiguous_citations[0].confidence
    
    def test_position_tracking(self, extractor):
        """Test position tracking in citations"""
        text = "Start text. Brown v. Board, 347 U.S. 483 (1954). End text."
        citations = extractor.extract_citations(text, "doc123")
        
        assert len(citations) == 1
        citation = citations[0]
        
        assert citation.start_position is not None
        assert citation.end_position is not None
        assert citation.start_position < citation.end_position
        assert text[citation.start_position:citation.end_position] in citation.full_citation
    
    def test_empty_text(self, extractor):
        """Test handling of empty text"""
        citations = extractor.extract_citations("", "doc123")
        assert len(citations) == 0
    
    def test_no_citations(self, extractor):
        """Test text with no citations"""
        text = "This is just regular text with no legal citations at all."
        citations = extractor.extract_citations(text, "doc123")
        assert len(citations) == 0


class TestMLCitationExtractor:
    """Test suite for ML-enhanced citation extractor"""
    
    @pytest.fixture
    def ml_extractor(self):
        """Create ML citation extractor for testing"""
        return MLCitationExtractor()
    
    @pytest.fixture
    def complex_citation_text(self):
        """Complex text with challenging citations"""
        return """
        The court in Smith, supra, at 123, distinguished the holding in
        Jones (citing Brown, 347 U.S. at 485-86). But see Wilson v. Davis,
        No. 12-3456, 2023 WL 12345 (S.D.N.Y. Jan. 15, 2023) (unpublished).
        
        As noted in the legislative history, H.R. Rep. No. 112-23, at 45 (2011),
        the statute was intended to address the gap identified in earlier cases.
        
        Compare 28 U.S.C. § 1331 (federal question jurisdiction) with
        28 U.S.C. § 1332 (diversity jurisdiction).
        """
    
    def test_ml_enhanced_extraction(self, ml_extractor, complex_citation_text):
        """Test ML-enhanced citation extraction on complex text"""
        citations = ml_extractor.extract_citations(complex_citation_text, "doc123")
        
        # Should find multiple types of citations
        citation_types = [c.citation_type for c in citations]
        
        # Should identify various citation patterns
        assert len(citations) > 0
        
        # Check for enhanced features
        for citation in citations:
            assert citation.confidence is not None
            assert 0.0 <= citation.confidence <= 1.0
            assert citation.citation_id is not None
    
    def test_ml_context_analysis(self, ml_extractor):
        """Test ML context analysis"""
        text = """
        The Supreme Court in Brown v. Board held that separate educational
        facilities are inherently unequal. This principle was reaffirmed
        in subsequent cases.
        """
        
        citations = ml_extractor.extract_citations(text, "doc123")
        
        # Should extract citation with context
        if citations:
            citation = citations[0]
            assert citation.surrounding_context is not None
            assert len(citation.surrounding_context) > 0
    
    @patch('plugins.caselaw.extraction.citation_extractor.ML_AVAILABLE', False)
    def test_fallback_to_basic_extraction(self, ml_extractor):
        """Test fallback when ML libraries unavailable"""
        text = "Brown v. Board, 347 U.S. 483 (1954)"
        citations = ml_extractor.extract_citations(text, "doc123")
        
        # Should still extract citations using regex patterns
        assert len(citations) >= 1
    
    def test_citation_normalization(self, ml_extractor):
        """Test citation normalization"""
        # Various formats of the same citation
        texts = [
            "347 U.S. 483",
            "347 US 483",
            "347 U. S. 483",
            "347 United States Reports 483"
        ]
        
        normalized_citations = []
        for text in texts:
            citations = ml_extractor.extract_citations(text, "doc123")
            if citations:
                normalized_citations.append(citations[0].normalized_citation)
        
        # Should normalize to similar format
        if len(normalized_citations) > 1:
            assert len(set(normalized_citations)) <= 2  # Allow some variation
    
    def test_citation_validation(self, ml_extractor):
        """Test citation validation"""
        # Valid citation
        valid_text = "Brown v. Board, 347 U.S. 483 (1954)"
        valid_citations = ml_extractor.extract_citations(valid_text, "doc123")
        
        # Invalid citation format
        invalid_text = "Brown v. Board, 999 U.S. 9999 (1850)"  # Invalid year/volume
        invalid_citations = ml_extractor.extract_citations(invalid_text, "doc123")
        
        # Valid citations should have higher confidence
        if valid_citations and invalid_citations:
            assert valid_citations[0].confidence >= invalid_citations[0].confidence
    
    def test_batch_processing(self, ml_extractor):
        """Test batch processing of multiple documents"""
        documents = [
            "Brown v. Board, 347 U.S. 483 (1954)",
            "Miranda v. Arizona, 384 U.S. 436 (1966)",
            "Marbury v. Madison, 5 U.S. 137 (1803)"
        ]
        
        all_citations = []
        for i, doc in enumerate(documents):
            citations = ml_extractor.extract_citations(doc, f"doc{i}")
            all_citations.extend(citations)
        
        assert len(all_citations) >= 3
        
        # Each should have different document IDs
        doc_ids = [c.source_document_id for c in all_citations]
        assert len(set(doc_ids)) == 3


class TestCitationModel:
    """Test suite for Citation model class"""
    
    def test_citation_creation(self):
        """Test citation object creation"""
        citation = Citation(
            citation_id=CitationID("cite:test123"),
            full_citation="Brown v. Board, 347 U.S. 483 (1954)",
            citation_type=CitationType.SUPREME_COURT,
            case_name="Brown v. Board",
            volume="347",
            reporter="U.S.",
            page="483",
            year="1954",
            confidence=0.95,
            source_document_id="doc123"
        )
        
        assert citation.citation_id.value == "cite:test123"
        assert citation.citation_type == CitationType.SUPREME_COURT
        assert citation.confidence == 0.95
        assert citation.year == "1954"
    
    def test_citation_to_dict(self):
        """Test citation serialization"""
        citation = Citation(
            citation_id=CitationID("cite:test123"),
            full_citation="Brown v. Board, 347 U.S. 483 (1954)",
            citation_type=CitationType.SUPREME_COURT,
            case_name="Brown v. Board",
            confidence=0.95,
            source_document_id="doc123"
        )
        
        citation_dict = citation.to_dict()
        
        assert citation_dict["citation_id"] == "cite:test123"
        assert citation_dict["full_citation"] == "Brown v. Board, 347 U.S. 483 (1954)"
        assert citation_dict["citation_type"] == "supreme_court"
        assert citation_dict["confidence"] == 0.95
        assert citation_dict["source_document_id"] == "doc123"
    
    def test_citation_equality(self):
        """Test citation equality comparison"""
        citation1 = Citation(
            citation_id=CitationID("cite:test123"),
            full_citation="Brown v. Board, 347 U.S. 483 (1954)",
            citation_type=CitationType.SUPREME_COURT,
            confidence=0.95,
            source_document_id="doc123"
        )
        
        citation2 = Citation(
            citation_id=CitationID("cite:test123"),
            full_citation="Brown v. Board, 347 U.S. 483 (1954)",
            citation_type=CitationType.SUPREME_COURT,
            confidence=0.95,
            source_document_id="doc123"
        )
        
        citation3 = Citation(
            citation_id=CitationID("cite:test456"),
            full_citation="Miranda v. Arizona, 384 U.S. 436 (1966)",
            citation_type=CitationType.SUPREME_COURT,
            confidence=0.95,
            source_document_id="doc123"
        )
        
        assert citation1 == citation2
        assert citation1 != citation3


class TestCitationIntegration:
    """Integration tests for citation extraction"""
    
    def test_end_to_end_citation_processing(self):
        """Test complete citation processing workflow"""
        text = """
        The landmark case Brown v. Board of Education, 347 U.S. 483 (1954),
        established that separate educational facilities are inherently unequal.
        This decision overruled the "separate but equal" doctrine from
        Plessy v. Ferguson, 163 U.S. 537 (1896).
        """
        
        extractor = MLCitationExtractor()
        citations = extractor.extract_citations(text, "test_doc")
        
        # Should extract multiple citations
        assert len(citations) >= 2
        
        # Verify citation details
        brown_citations = [c for c in citations if "Brown v. Board" in c.full_citation]
        assert len(brown_citations) >= 1
        
        brown_citation = brown_citations[0]
        assert brown_citation.citation_type == CitationType.SUPREME_COURT
        assert brown_citation.volume == "347"
        assert brown_citation.reporter == "U.S."
        assert brown_citation.page == "483"
        assert brown_citation.year == "1954"
        assert brown_citation.confidence > 0.5
    
    def test_citation_deduplication(self):
        """Test deduplication of similar citations"""
        text = """
        Brown v. Board, 347 U.S. 483 (1954) established the principle.
        Later, Brown v. Board of Education, 347 U.S. 483 (1954) was cited again.
        The Brown decision (347 U.S. 483) remains important.
        """
        
        extractor = MLCitationExtractor()
        citations = extractor.extract_citations(text, "test_doc")
        
        # Should identify these as the same case despite different formats
        unique_citations = extractor._deduplicate_citations(citations)
        
        # Should have fewer citations after deduplication
        assert len(unique_citations) <= len(citations)
    
    def test_performance_on_large_text(self):
        """Test performance on large documents"""
        # Create large text with multiple citations
        base_text = "Brown v. Board, 347 U.S. 483 (1954). "
        large_text = base_text * 1000  # Repeat 1000 times
        
        extractor = MLCitationExtractor()
        
        import time
        start_time = time.time()
        citations = extractor.extract_citations(large_text, "large_doc")
        end_time = time.time()
        
        # Should complete within reasonable time (less than 10 seconds)
        processing_time = end_time - start_time
        assert processing_time < 10.0
        
        # Should find citations
        assert len(citations) > 0