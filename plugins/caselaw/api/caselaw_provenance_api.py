"""
Caselaw Provenance API for CAP Caselaw Plugin
Provides complete audit trails and "why"/"from where" answers for legal reasoning
"""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass
import asyncio

from ..models.canonical_identifiers import DocumentID, CitationID, ParagraphID
from ..models.provenance_record import ProvenanceRecord, ProvenanceOperation
from ..models.caselaw_node import CaselawNode
from ..models.case_relationship import CaseRelationship
from ..storage.hypergraph_store import HypergraphStore
from ..reasoning.temporal_reasoner import TemporalReasoner
from ..reasoning.jurisdictional_reasoner import JurisdictionalReasoner, AuthorityLevel

logger = logging.getLogger(__name__)


@dataclass
class ProvenanceChain:
    """Complete provenance chain for a legal conclusion"""
    conclusion: str
    primary_sources: List[Dict[str, Any]]
    supporting_evidence: List[Dict[str, Any]]
    reasoning_steps: List[Dict[str, Any]]
    authority_analysis: List[Dict[str, Any]]
    confidence: float
    complete_audit_trail: List[ProvenanceRecord]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "conclusion": self.conclusion,
            "primary_sources": self.primary_sources,
            "supporting_evidence": self.supporting_evidence,
            "reasoning_steps": self.reasoning_steps,
            "authority_analysis": self.authority_analysis,
            "confidence": self.confidence,
            "complete_audit_trail": [p.to_dict() for p in self.complete_audit_trail]
        }


@dataclass
class WhyAnswer:
    """Answer to "why" questions with complete reasoning"""
    question: str
    answer: str
    legal_basis: List[Dict[str, Any]]
    precedent_chain: List[Dict[str, Any]]
    jurisdictional_authority: Dict[str, Any]
    temporal_relevance: Dict[str, Any]
    confidence: float
    sources: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "question": self.question,
            "answer": self.answer,
            "legal_basis": self.legal_basis,
            "precedent_chain": self.precedent_chain,
            "jurisdictional_authority": self.jurisdictional_authority,
            "temporal_relevance": self.temporal_relevance,
            "confidence": self.confidence,
            "sources": self.sources
        }


@dataclass
class FromWhereAnswer:
    """Answer to "from where" questions with source tracing"""
    question: str
    original_sources: List[Dict[str, Any]]
    citation_chain: List[Dict[str, Any]]
    transformation_history: List[Dict[str, Any]]
    verification_status: str
    confidence: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "question": self.question,
            "original_sources": self.original_sources,
            "citation_chain": self.citation_chain,
            "transformation_history": self.transformation_history,
            "verification_status": self.verification_status,
            "confidence": self.confidence
        }


class CaselawProvenanceAPI:
    """
    Main API for caselaw provenance and audit trail queries
    """
    
    def __init__(self, store: HypergraphStore, 
                 temporal_reasoner: TemporalReasoner = None,
                 jurisdictional_reasoner: JurisdictionalReasoner = None):
        """
        Initialize provenance API
        
        Args:
            store: Hypergraph storage backend
            temporal_reasoner: Temporal reasoning engine
            jurisdictional_reasoner: Jurisdictional reasoning engine
        """
        self.store = store
        self.temporal_reasoner = temporal_reasoner or TemporalReasoner()
        self.jurisdictional_reasoner = jurisdictional_reasoner or JurisdictionalReasoner()
        
    async def trace_legal_conclusion(self, conclusion: str, 
                                   context: Optional[Dict[str, Any]] = None) -> ProvenanceChain:
        """
        Trace complete provenance chain for a legal conclusion
        
        Args:
            conclusion: The legal conclusion to trace
            context: Additional context for analysis
            
        Returns:
            Complete provenance chain with audit trail
        """
        try:
            logger.info(f"Tracing provenance for conclusion: {conclusion}")
            
            # Find relevant cases and sources
            relevant_cases = await self._find_relevant_cases(conclusion, context)
            
            # Extract primary sources
            primary_sources = await self._identify_primary_sources(relevant_cases, conclusion)
            
            # Build reasoning chain
            reasoning_steps = await self._build_reasoning_chain(relevant_cases, conclusion)
            
            # Analyze authority
            authority_analysis = await self._analyze_authority_chain(relevant_cases)
            
            # Get supporting evidence
            supporting_evidence = await self._gather_supporting_evidence(relevant_cases, conclusion)
            
            # Build complete audit trail
            audit_trail = await self._build_audit_trail(relevant_cases, reasoning_steps)
            
            # Calculate overall confidence
            confidence = self._calculate_chain_confidence(authority_analysis, reasoning_steps)
            
            return ProvenanceChain(
                conclusion=conclusion,
                primary_sources=primary_sources,
                supporting_evidence=supporting_evidence,
                reasoning_steps=reasoning_steps,
                authority_analysis=authority_analysis,
                confidence=confidence,
                complete_audit_trail=audit_trail
            )
            
        except Exception as e:
            logger.error(f"Error tracing legal conclusion: {e}")
            raise
    
    async def answer_why_question(self, question: str, 
                                context: Optional[Dict[str, Any]] = None) -> WhyAnswer:
        """
        Answer "why" questions with complete legal reasoning
        
        Args:
            question: The "why" question to answer
            context: Additional context for analysis
            
        Returns:
            Complete answer with reasoning and sources
        """
        try:
            logger.info(f"Answering why question: {question}")
            
            # Parse question to extract legal issue
            legal_issue = self._parse_legal_issue(question)
            
            # Find relevant precedents
            precedents = await self._find_precedent_cases(legal_issue, context)
            
            # Build legal basis
            legal_basis = await self._build_legal_basis(precedents, legal_issue)
            
            # Create precedent chain
            precedent_chain = await self._build_precedent_chain(precedents)
            
            # Analyze jurisdictional authority
            jurisdictional_authority = await self._analyze_jurisdictional_authority(precedents, context)
            
            # Assess temporal relevance
            temporal_relevance = await self._assess_temporal_relevance(precedents)
            
            # Generate answer
            answer = await self._generate_why_answer(question, legal_basis, precedent_chain)
            
            # Calculate confidence
            confidence = self._calculate_answer_confidence(legal_basis, precedent_chain, jurisdictional_authority)
            
            # Extract sources
            sources = [str(case.case_id) for case in precedents]
            
            return WhyAnswer(
                question=question,
                answer=answer,
                legal_basis=legal_basis,
                precedent_chain=precedent_chain,
                jurisdictional_authority=jurisdictional_authority,
                temporal_relevance=temporal_relevance,
                confidence=confidence,
                sources=sources
            )
            
        except Exception as e:
            logger.error(f"Error answering why question: {e}")
            raise
    
    async def answer_from_where_question(self, question: str,
                                       target_claim: str,
                                       context: Optional[Dict[str, Any]] = None) -> FromWhereAnswer:
        """
        Answer "from where" questions by tracing source origins
        
        Args:
            question: The "from where" question to answer
            target_claim: The claim/statement to trace
            context: Additional context for analysis
            
        Returns:
            Complete source tracing with verification
        """
        try:
            logger.info(f"Answering from where question: {question}")
            
            # Find original sources
            original_sources = await self._find_original_sources(target_claim, context)
            
            # Build citation chain
            citation_chain = await self._build_citation_chain(target_claim, original_sources)
            
            # Trace transformation history
            transformation_history = await self._trace_transformation_history(target_claim, citation_chain)
            
            # Verify source accuracy
            verification_status = await self._verify_source_accuracy(target_claim, original_sources)
            
            # Calculate confidence
            confidence = self._calculate_source_confidence(original_sources, verification_status)
            
            return FromWhereAnswer(
                question=question,
                original_sources=original_sources,
                citation_chain=citation_chain,
                transformation_history=transformation_history,
                verification_status=verification_status,
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Error answering from where question: {e}")
            raise
    
    async def verify_legal_claim(self, claim: str, 
                               sources: List[str],
                               context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Verify a legal claim against authoritative sources
        
        Args:
            claim: The legal claim to verify
            sources: List of source identifiers
            context: Additional context for verification
            
        Returns:
            Verification result with confidence and evidence
        """
        try:
            verification_result = {
                "claim": claim,
                "verified": False,
                "confidence": 0.0,
                "supporting_evidence": [],
                "contradicting_evidence": [],
                "authority_analysis": [],
                "verification_timestamp": datetime.utcnow().isoformat()
            }
            
            # Retrieve source cases
            source_cases = []
            for source_id in sources:
                case = await self.store.get_case(DocumentID(source_id))
                if case:
                    source_cases.append(case)
            
            if not source_cases:
                verification_result["error"] = "No valid sources found"
                return verification_result
            
            # Extract relevant text from sources
            supporting_evidence = []
            contradicting_evidence = []
            
            for case in source_cases:
                # Simplified claim verification - would use NLP in practice
                case_text = case.full_text.lower()
                claim_lower = claim.lower()
                
                # Look for supporting or contradicting language
                if self._supports_claim(case_text, claim_lower):
                    supporting_evidence.append({
                        "case_id": str(case.case_id),
                        "case_name": case.metadata.get("case_name", "Unknown"),
                        "relevant_text": self._extract_relevant_text(case_text, claim_lower),
                        "confidence": 0.8
                    })
                elif self._contradicts_claim(case_text, claim_lower):
                    contradicting_evidence.append({
                        "case_id": str(case.case_id),
                        "case_name": case.metadata.get("case_name", "Unknown"),
                        "relevant_text": self._extract_relevant_text(case_text, claim_lower),
                        "confidence": 0.7
                    })
            
            # Analyze authority of sources
            authority_analysis = []
            for case in source_cases:
                # Analyze court authority
                court = case.metadata.get("court_slug", "")
                authority_level = self._assess_court_authority(court)
                authority_analysis.append({
                    "case_id": str(case.case_id),
                    "court": court,
                    "authority_level": authority_level,
                    "jurisdiction": case.metadata.get("jurisdiction_slug", "")
                })
            
            # Calculate overall verification
            support_weight = sum(e["confidence"] for e in supporting_evidence)
            contradict_weight = sum(e["confidence"] for e in contradicting_evidence)
            
            if support_weight > contradict_weight:
                verification_result["verified"] = True
                verification_result["confidence"] = min(0.95, support_weight / (support_weight + contradict_weight))
            else:
                verification_result["verified"] = False
                verification_result["confidence"] = contradict_weight / (support_weight + contradict_weight) if (support_weight + contradict_weight) > 0 else 0.0
            
            verification_result["supporting_evidence"] = supporting_evidence
            verification_result["contradicting_evidence"] = contradicting_evidence
            verification_result["authority_analysis"] = authority_analysis
            
            return verification_result
            
        except Exception as e:
            logger.error(f"Error verifying legal claim: {e}")
            return {
                "claim": claim,
                "verified": False,
                "confidence": 0.0,
                "error": str(e),
                "verification_timestamp": datetime.utcnow().isoformat()
            }
    
    async def _find_relevant_cases(self, conclusion: str, 
                                 context: Optional[Dict[str, Any]] = None) -> List[CaselawNode]:
        """Find cases relevant to a legal conclusion"""
        # Use search functionality to find relevant cases
        search_results = await self.store.search_cases(
            query=conclusion,
            limit=50,
            filters=context or {}
        )
        return search_results
    
    async def _identify_primary_sources(self, cases: List[CaselawNode], 
                                      conclusion: str) -> List[Dict[str, Any]]:
        """Identify primary authoritative sources"""
        primary_sources = []
        
        for case in cases[:10]:  # Top 10 most relevant
            # Analyze if this is a primary source
            authority_level = self._assess_case_authority(case)
            relevance_score = self._calculate_relevance_score(case, conclusion)
            
            if authority_level >= 0.7 and relevance_score >= 0.6:
                primary_sources.append({
                    "case_id": str(case.case_id),
                    "case_name": case.metadata.get("case_name", "Unknown"),
                    "court": case.metadata.get("court_slug", ""),
                    "jurisdiction": case.metadata.get("jurisdiction_slug", ""),
                    "decision_date": case.metadata.get("decision_date", ""),
                    "authority_level": authority_level,
                    "relevance_score": relevance_score,
                    "is_primary_source": True
                })
        
        return primary_sources
    
    async def _build_reasoning_chain(self, cases: List[CaselawNode], 
                                   conclusion: str) -> List[Dict[str, Any]]:
        """Build logical reasoning chain"""
        reasoning_steps = []
        
        # Group cases by legal principle
        principle_groups = self._group_by_legal_principle(cases)
        
        for principle, principle_cases in principle_groups.items():
            step = {
                "principle": principle,
                "supporting_cases": [str(c.case_id) for c in principle_cases],
                "reasoning": f"Cases establish the principle that {principle}",
                "confidence": min(1.0, len(principle_cases) * 0.2)
            }
            reasoning_steps.append(step)
        
        return reasoning_steps
    
    async def _analyze_authority_chain(self, cases: List[CaselawNode]) -> List[Dict[str, Any]]:
        """Analyze precedential authority chain"""
        authority_analysis = []
        
        for case in cases:
            # Use jurisdictional reasoner for authority analysis
            court = case.metadata.get("court_slug", "")
            jurisdiction = case.metadata.get("jurisdiction_slug", "")
            
            analysis = {
                "case_id": str(case.case_id),
                "court": court,
                "jurisdiction": jurisdiction,
                "authority_level": self._assess_court_authority(court),
                "temporal_weight": self._calculate_temporal_weight(case),
                "precedential_value": self._calculate_precedential_value(case)
            }
            authority_analysis.append(analysis)
        
        return authority_analysis
    
    def _parse_legal_issue(self, question: str) -> str:
        """Extract legal issue from question"""
        # Simplified parsing - would use NLP in practice
        question_lower = question.lower()
        
        # Remove question words
        issue = question_lower.replace("why", "").replace("?", "").strip()
        
        return issue
    
    def _supports_claim(self, case_text: str, claim: str) -> bool:
        """Check if case text supports the claim"""
        # Simplified support detection
        claim_words = claim.split()
        matches = sum(1 for word in claim_words if word in case_text)
        return matches / len(claim_words) > 0.5
    
    def _contradicts_claim(self, case_text: str, claim: str) -> bool:
        """Check if case text contradicts the claim"""
        # Look for contradictory language
        contradictory_terms = ["not", "never", "contrary", "opposite", "reject", "overrule"]
        claim_words = claim.split()
        
        for term in contradictory_terms:
            if term in case_text:
                # Check if contradictory term is near claim words
                for word in claim_words:
                    if word in case_text and abs(case_text.find(term) - case_text.find(word)) < 100:
                        return True
        
        return False
    
    def _extract_relevant_text(self, case_text: str, claim: str) -> str:
        """Extract relevant text snippet"""
        claim_words = claim.split()
        best_position = 0
        best_matches = 0
        
        # Find position with most claim words
        for i in range(0, len(case_text) - 200, 50):
            snippet = case_text[i:i+200]
            matches = sum(1 for word in claim_words if word in snippet)
            if matches > best_matches:
                best_matches = matches
                best_position = i
        
        return case_text[best_position:best_position+200]
    
    def _assess_court_authority(self, court: str) -> float:
        """Assess court authority level"""
        if court == "us":
            return 1.0
        elif court.startswith("us.ca"):
            return 0.8
        elif court.startswith("us.d"):
            return 0.6
        elif court.endswith(".supreme"):
            return 0.7
        elif "appellate" in court:
            return 0.5
        else:
            return 0.3
    
    def _assess_case_authority(self, case: CaselawNode) -> float:
        """Assess overall case authority"""
        court_authority = self._assess_court_authority(case.metadata.get("court_slug", ""))
        temporal_weight = self._calculate_temporal_weight(case)
        
        return court_authority * temporal_weight
    
    def _calculate_relevance_score(self, case: CaselawNode, conclusion: str) -> float:
        """Calculate case relevance to conclusion"""
        # Simplified relevance scoring
        case_text = case.full_text.lower()
        conclusion_words = conclusion.lower().split()
        
        matches = sum(1 for word in conclusion_words if word in case_text)
        return matches / len(conclusion_words)
    
    def _calculate_temporal_weight(self, case: CaselawNode) -> float:
        """Calculate temporal relevance weight"""
        try:
            decision_date = case.metadata.get("decision_date", "")
            if not decision_date:
                return 0.5
            
            # Parse year from date
            if "-" in decision_date:
                year = int(decision_date.split("-")[0])
            else:
                year = int(decision_date[:4])
            
            current_year = datetime.now().year
            years_old = current_year - year
            
            # Weight decreases with age
            if years_old <= 10:
                return 1.0
            elif years_old <= 25:
                return 0.8
            elif years_old <= 50:
                return 0.6
            else:
                return 0.4
                
        except Exception:
            return 0.5
    
    def _calculate_precedential_value(self, case: CaselawNode) -> float:
        """Calculate precedential value"""
        court_authority = self._assess_court_authority(case.metadata.get("court_slug", ""))
        temporal_weight = self._calculate_temporal_weight(case)
        
        # Additional factors could include citation count, subsequent treatment, etc.
        return (court_authority + temporal_weight) / 2
    
    def _group_by_legal_principle(self, cases: List[CaselawNode]) -> Dict[str, List[CaselawNode]]:
        """Group cases by legal principle (simplified)"""
        # This would use more sophisticated legal concept extraction in practice
        groups = {"general_principle": cases}
        return groups
    
    def _calculate_chain_confidence(self, authority_analysis: List[Dict[str, Any]], 
                                  reasoning_steps: List[Dict[str, Any]]) -> float:
        """Calculate overall confidence in reasoning chain"""
        if not authority_analysis or not reasoning_steps:
            return 0.0
        
        avg_authority = sum(a["authority_level"] for a in authority_analysis) / len(authority_analysis)
        avg_reasoning = sum(r["confidence"] for r in reasoning_steps) / len(reasoning_steps)
        
        return (avg_authority + avg_reasoning) / 2
    
    def _calculate_answer_confidence(self, legal_basis: List[Dict[str, Any]],
                                   precedent_chain: List[Dict[str, Any]],
                                   jurisdictional_authority: Dict[str, Any]) -> float:
        """Calculate confidence in answer"""
        basis_confidence = sum(b.get("confidence", 0.5) for b in legal_basis) / max(len(legal_basis), 1)
        precedent_confidence = sum(p.get("confidence", 0.5) for p in precedent_chain) / max(len(precedent_chain), 1)
        authority_confidence = jurisdictional_authority.get("overall_confidence", 0.5)
        
        return (basis_confidence + precedent_confidence + authority_confidence) / 3
    
    def _calculate_source_confidence(self, original_sources: List[Dict[str, Any]], 
                                   verification_status: str) -> float:
        """Calculate confidence in source tracing"""
        if verification_status == "verified":
            return 0.9
        elif verification_status == "partially_verified":
            return 0.6
        else:
            return 0.3
    
    # Additional helper methods would be implemented for complete functionality
    async def _gather_supporting_evidence(self, cases: List[CaselawNode], conclusion: str) -> List[Dict[str, Any]]:
        """Gather supporting evidence"""
        return []  # Placeholder
    
    async def _build_audit_trail(self, cases: List[CaselawNode], reasoning_steps: List[Dict[str, Any]]) -> List[ProvenanceRecord]:
        """Build complete audit trail"""
        return []  # Placeholder
    
    async def _find_precedent_cases(self, legal_issue: str, context: Optional[Dict[str, Any]] = None) -> List[CaselawNode]:
        """Find precedent cases"""
        return []  # Placeholder
    
    async def _build_legal_basis(self, precedents: List[CaselawNode], legal_issue: str) -> List[Dict[str, Any]]:
        """Build legal basis"""
        return []  # Placeholder
    
    async def _build_precedent_chain(self, precedents: List[CaselawNode]) -> List[Dict[str, Any]]:
        """Build precedent chain"""
        return []  # Placeholder
    
    async def _analyze_jurisdictional_authority(self, precedents: List[CaselawNode], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze jurisdictional authority"""
        return {"overall_confidence": 0.5}  # Placeholder
    
    async def _assess_temporal_relevance(self, precedents: List[CaselawNode]) -> Dict[str, Any]:
        """Assess temporal relevance"""
        return {}  # Placeholder
    
    async def _generate_why_answer(self, question: str, legal_basis: List[Dict[str, Any]], precedent_chain: List[Dict[str, Any]]) -> str:
        """Generate why answer"""
        return f"Based on legal precedent, {question}"  # Placeholder
    
    async def _find_original_sources(self, target_claim: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Find original sources"""
        return []  # Placeholder
    
    async def _build_citation_chain(self, target_claim: str, original_sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build citation chain"""
        return []  # Placeholder
    
    async def _trace_transformation_history(self, target_claim: str, citation_chain: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Trace transformation history"""
        return []  # Placeholder
    
    async def _verify_source_accuracy(self, target_claim: str, original_sources: List[Dict[str, Any]]) -> str:
        """Verify source accuracy"""
        return "verified"  # Placeholder