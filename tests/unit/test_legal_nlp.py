"""
TDD Tests for Legal NLP Infrastructure

Following Test-Driven Development methodology:
1. RED: Write failing tests first
2. GREEN: Implement minimal code to pass
3. REFACTOR: Clean up and optimize

Tests cover legal NER, citation extraction, and obligation parsing.
"""

import pytest
from typing import List, Dict, Any
from nlp.legal_ner import LegalNERPipeline, CitationExtractor


class TestLegalNERPipeline:
    """Test the legal named entity recognition pipeline"""
    
    def test_legal_ner_initialization(self):
        """
        TDD: LegalNERPipeline should initialize with configurable model
        """
        # Test with default model (mock for testing)
        ner = LegalNERPipeline(model_name="mock-legal-bert")
        assert ner.model_name == "mock-legal-bert"
        assert ner.patterns is not None
        assert "STATUTE" in ner.patterns
        assert "CASE" in ner.patterns
        assert "MONEY" in ner.patterns
        assert "DATE" in ner.patterns
        
    def test_extract_legal_entities_basic(self):
        """
        TDD: Should extract basic legal entities from text
        """
        ner = LegalNERPipeline(model_name="mock-legal-bert")
        
        text = "The plaintiff filed under 42 USC 1981 seeking $50,000 in damages."
        entities = ner.extract_legal_entities(text)
        
        # Should find statute and money entities
        entity_types = [e["entity_group"] for e in entities]
        assert "STATUTE" in entity_types
        assert "MONEY" in entity_types
        
        # Check specific extractions
        statute_entities = [e for e in entities if e["entity_group"] == "STATUTE"]
        assert len(statute_entities) >= 1
        assert "42 USC 1981" in statute_entities[0]["word"]
        
        money_entities = [e for e in entities if e["entity_group"] == "MONEY"]
        assert len(money_entities) >= 1
        assert "$50,000" in money_entities[0]["word"]
        
    def test_extract_legal_entities_case_citations(self):
        """
        TDD: Should extract case citations correctly
        """
        ner = LegalNERPipeline(model_name="mock-legal-bert")
        
        text = "In Brown v. Board of Education, the Court held that separate is not equal."
        entities = ner.extract_legal_entities(text)
        
        case_entities = [e for e in entities if e["entity_group"] == "CASE"]
        assert len(case_entities) >= 1
        assert "Brown v. Board" in case_entities[0]["word"]
        
    def test_extract_legal_entities_dates(self):
        """
        TDD: Should extract various date formats
        """
        ner = LegalNERPipeline(model_name="mock-legal-bert")
        
        text = "The contract was signed on January 15, 2024 and expires 12/31/2025."
        entities = ner.extract_legal_entities(text)
        
        date_entities = [e for e in entities if e["entity_group"] == "DATE"]
        assert len(date_entities) >= 2
        
        # Check for different date formats
        date_texts = [e["word"] for e in date_entities]
        assert any("January 15, 2024" in date for date in date_texts)
        assert any("12/31/2025" in date for date in date_texts)
        
    def test_extract_obligations_basic(self):
        """
        TDD: Should extract legal obligations and duties
        """
        ner = LegalNERPipeline(model_name="mock-legal-bert")
        
        text = "The employer must provide reasonable accommodation to qualified disabled employees."
        obligations = ner.extract_obligations(text)
        
        assert len(obligations) >= 1
        
        obligation = obligations[0]
        assert "bearer" in obligation
        assert "duty" in obligation
        assert "employer" in obligation["bearer"].lower()
        assert "provide reasonable accommodation" in obligation["duty"].lower()
        assert obligation["confidence"] > 0.0
        
    def test_extract_obligations_multiple_patterns(self):
        """
        TDD: Should extract obligations using different patterns
        """
        ner = LegalNERPipeline(model_name="mock-legal-bert")
        
        text = """
        The company shall provide notice to employees.
        Workers are required to follow safety protocols.
        The manager has a duty to investigate complaints.
        """
        
        obligations = ner.extract_obligations(text)
        assert len(obligations) >= 3
        
        # Check different obligation patterns
        bearers = [o["bearer"].lower() for o in obligations]
        assert any("company" in bearer for bearer in bearers)
        assert any("workers" in bearer for bearer in bearers)
        assert any("manager" in bearer for bearer in bearers)
        
    def test_extract_pattern_entities(self):
        """
        TDD: Should extract entities using regex patterns
        """
        ner = LegalNERPipeline(model_name="mock-legal-bert")
        
        text = "See 29 CFR 1630.2 and Section 501 of the ADA."
        pattern_entities = ner._extract_pattern_entities(text)
        
        # Should find statute patterns
        statute_entities = [e for e in pattern_entities if e["entity_group"] == "STATUTE"]
        assert len(statute_entities) >= 2
        
        # Check confidence and method
        for entity in pattern_entities:
            assert entity["score"] > 0.8  # High confidence for patterns
            assert entity["method"] == "pattern_based"
            
    def test_deduplicate_entities(self):
        """
        TDD: Should remove overlapping entities, keeping highest confidence
        """
        ner = LegalNERPipeline(model_name="mock-legal-bert")
        
        # Create overlapping entities
        entities = [
            {"entity_group": "STATUTE", "word": "42 USC", "start": 0, "end": 6, "score": 0.7},
            {"entity_group": "STATUTE", "word": "42 USC 1981", "start": 0, "end": 11, "score": 0.9},
            {"entity_group": "MONEY", "word": "$50", "start": 20, "end": 23, "score": 0.8}
        ]
        
        deduplicated = ner._deduplicate_entities(entities)
        
        # Should keep the higher confidence overlapping entity
        assert len(deduplicated) == 2
        statute_entity = next(e for e in deduplicated if e["entity_group"] == "STATUTE")
        assert statute_entity["word"] == "42 USC 1981"  # Higher confidence
        assert statute_entity["score"] == 0.9


class TestCitationExtractor:
    """Test the legal citation extraction"""
    
    def test_citation_extractor_initialization(self):
        """
        TDD: CitationExtractor should initialize with citation patterns
        """
        extractor = CitationExtractor()
        assert extractor.citation_patterns is not None
        assert "case" in extractor.citation_patterns
        assert "statute" in extractor.citation_patterns
        assert "constitution" in extractor.citation_patterns
        
    def test_extract_case_citations(self):
        """
        TDD: Should extract case citations in various formats
        """
        extractor = CitationExtractor()
        
        text = "Brown v. Board of Education, 347 U.S. 483 (1954) established precedent."
        citations = extractor.extract_citations(text)
        
        case_citations = [c for c in citations if c["type"] == "case"]
        assert len(case_citations) >= 1
        
        citation = case_citations[0]
        assert "Brown" in citation["raw"]
        assert "Board" in citation["raw"]
        assert citation["confidence"] > 0.8
        assert "groups" in citation
        
    def test_extract_statute_citations(self):
        """
        TDD: Should extract statute citations (USC, CFR)
        """
        extractor = CitationExtractor()
        
        text = "Under 42 U.S.C. § 1981 and 29 CFR 1630.2, the following applies."
        citations = extractor.extract_citations(text)
        
        statute_citations = [c for c in citations if c["type"] == "statute"]
        assert len(statute_citations) >= 2
        
        # Check USC citation
        usc_citation = next((c for c in statute_citations if "U.S.C" in c["raw"]), None)
        assert usc_citation is not None
        assert "42" in usc_citation["raw"]
        assert "1981" in usc_citation["raw"]
        
        # Check CFR citation
        cfr_citation = next((c for c in statute_citations if "CFR" in c["raw"]), None)
        assert cfr_citation is not None
        assert "29" in cfr_citation["raw"]
        assert "1630.2" in cfr_citation["raw"]
        
    def test_extract_constitutional_citations(self):
        """
        TDD: Should extract constitutional citations
        """
        extractor = CitationExtractor()
        
        text = "The U.S. Const. Art. I, § 8 grants Congress power. The First Amendment protects speech."
        citations = extractor.extract_citations(text)
        
        const_citations = [c for c in citations if c["type"] == "constitution"]
        assert len(const_citations) >= 1
        
        # Check Article citation
        article_citation = next((c for c in const_citations if "Art." in c["raw"]), None)
        if article_citation:
            assert "I" in article_citation["raw"]
            assert "8" in article_citation["raw"]
            
    def test_parse_citation_components(self):
        """
        TDD: Should parse individual citation components
        """
        extractor = CitationExtractor()
        
        # Test case citation parsing
        case_citation = {
            "type": "case",
            "raw": "Brown v. Board, 347 U.S. 483",
            "groups": ("Brown", "Board", "347", "U.S.", "483")
        }
        
        parsed = extractor.parse_citation_components(case_citation)
        
        assert parsed["type"] == "case"
        assert parsed["plaintiff"] == "Brown"
        assert parsed["defendant"] == "Board"
        assert parsed["volume"] == "347"
        assert parsed["reporter"] == "U.S."
        assert parsed["page"] == "483"
        
    def test_normalize_citations(self):
        """
        TDD: Should normalize citations to standard format
        """
        extractor = CitationExtractor()
        
        # Test various USC formats
        citations = [
            {"type": "statute", "raw": "42 USC 1981", "groups": ("42", "1981")},
            {"type": "statute", "raw": "42 U.S.C. § 1981", "groups": ("42", "1981")},
            {"type": "statute", "raw": "42 USC § 1981", "groups": ("42", "1981")}
        ]
        
        for citation in citations:
            normalized = extractor.normalize_citation(citation)
            assert normalized["standard_form"] == "42 U.S.C. § 1981"
            assert normalized["title"] == "42"
            assert normalized["section"] == "1981"
            
    def test_citation_confidence_scoring(self):
        """
        TDD: Should assign appropriate confidence scores
        """
        extractor = CitationExtractor()
        
        text = """
        Brown v. Board of Education, 347 U.S. 483 (1954).
        42 U.S.C. § 1981.
        Some case v. Another case.
        """
        
        citations = extractor.extract_citations(text)
        
        # Complete citations should have higher confidence
        complete_citations = [c for c in citations if len(c["groups"]) >= 5]
        incomplete_citations = [c for c in citations if len(c["groups"]) < 3]
        
        if complete_citations and incomplete_citations:
            assert complete_citations[0]["confidence"] > incomplete_citations[0]["confidence"]
            
    def test_extract_pinpoint_citations(self):
        """
        TDD: Should extract pinpoint citations with specific pages/sections
        """
        extractor = CitationExtractor()
        
        text = "See Brown v. Board, 347 U.S. 483, 495 (1954) (discussing separate but equal)."
        citations = extractor.extract_citations(text)
        
        case_citation = next((c for c in citations if c["type"] == "case"), None)
        assert case_citation is not None
        
        parsed = extractor.parse_citation_components(case_citation)
        if "pinpoint" in parsed:
            assert parsed["pinpoint"] == "495"


class TestLegalNLPIntegration:
    """Test integration between NLP components"""
    
    def test_ner_and_citation_integration(self):
        """
        TDD: NER and citation extraction should work together
        """
        ner = LegalNERPipeline(model_name="mock-legal-bert")
        extractor = CitationExtractor()
        
        text = """
        In Brown v. Board of Education, 347 U.S. 483 (1954), the Supreme Court
        ruled that under the 14th Amendment and 42 U.S.C. § 1981, segregation
        in public schools was unconstitutional. The Court awarded $1,000,000
        in damages on January 15, 2024.
        """
        
        # Extract entities and citations
        entities = ner.extract_legal_entities(text)
        citations = extractor.extract_citations(text)
        
        # Should find various entity types
        entity_types = {e["entity_group"] for e in entities}
        assert "CASE" in entity_types
        assert "STATUTE" in entity_types
        assert "MONEY" in entity_types
        assert "DATE" in entity_types
        
        # Should find case and statute citations
        citation_types = {c["type"] for c in citations}
        assert "case" in citation_types
        assert "statute" in citation_types
        
        # Citations should provide more detailed structure than basic NER
        case_citations = [c for c in citations if c["type"] == "case"]
        assert len(case_citations) >= 1
        assert len(case_citations[0]["groups"]) >= 3  # Structured components
        
    def test_obligation_and_entity_correlation(self):
        """
        TDD: Obligation extraction should correlate with entity recognition
        """
        ner = LegalNERPipeline(model_name="mock-legal-bert")
        
        text = "Under 42 U.S.C. § 1981, the employer must provide accommodation costing up to $5,000."
        
        entities = ner.extract_legal_entities(text)
        obligations = ner.extract_obligations(text)
        
        # Should extract statute, money, and obligation
        assert any(e["entity_group"] == "STATUTE" for e in entities)
        assert any(e["entity_group"] == "MONEY" for e in entities)
        assert len(obligations) >= 1
        
        # Obligation should reference the legal authority
        obligation = obligations[0]
        assert "employer" in obligation["bearer"].lower()
        assert "accommodation" in obligation["duty"].lower()