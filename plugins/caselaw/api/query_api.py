"""
Caselaw Query API for CAP Plugin
Provides REST endpoints for legal precedent queries and analysis
"""

import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, date
from dataclasses import dataclass, asdict
from enum import Enum
import json

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from ..models.canonical_identifiers import DocumentID, CitationID
from ..reasoning.temporal_reasoner import TemporalReasoner, TemporalEvaluation
from ..extraction.citation_extractor import CitationExtractor
from ..extraction.relationship_extractor import CaseRelationshipExtractor

logger = logging.getLogger(__name__)


# Request/Response Models
class PrecedentQueryRequest(BaseModel):
    """Request model for precedent queries"""
    legal_concept: str = Field(..., description="Legal concept to search for")
    jurisdiction: Optional[str] = Field("US", description="Legal jurisdiction")
    temporal_scope: Optional[str] = Field("current", description="Temporal scope: current, historical, all")
    date_range: Optional[Dict[str, str]] = Field(None, description="Start and end dates")
    limit: int = Field(10, ge=1, le=100, description="Maximum results to return")
    include_relationships: bool = Field(True, description="Include case relationships")
    confidence_threshold: float = Field(0.7, ge=0.0, le=1.0, description="Minimum confidence threshold")


class CaseSearchRequest(BaseModel):
    """Request model for case searches"""
    query: str = Field(..., description="Search query")
    jurisdiction: Optional[str] = Field(None, description="Filter by jurisdiction")
    court: Optional[str] = Field(None, description="Filter by court")
    date_range: Optional[Dict[str, str]] = Field(None, description="Date range filter")
    case_type: Optional[str] = Field(None, description="Type of case")
    limit: int = Field(20, ge=1, le=100, description="Maximum results")


class CitationResolutionRequest(BaseModel):
    """Request model for citation resolution"""
    citations: List[str] = Field(..., description="List of citation strings to resolve")
    include_metadata: bool = Field(True, description="Include case metadata")
    validate_format: bool = Field(True, description="Validate citation format")


class PrecedentAnalysisResponse(BaseModel):
    """Response model for precedent analysis"""
    query_id: str
    legal_concept: str
    supporting_cases: List[Dict[str, Any]]
    contrary_cases: List[Dict[str, Any]]
    authority_hierarchy: List[Dict[str, Any]]
    temporal_analysis: Dict[str, Any]
    summary: str
    confidence: float
    total_cases_analyzed: int


class CaseSearchResponse(BaseModel):
    """Response model for case searches"""
    query: str
    results: List[Dict[str, Any]]
    total_results: int
    page: int
    per_page: int
    filters_applied: Dict[str, Any]


class CaselawQueryAPI:
    """
    Main query API for caselaw precedent analysis and case retrieval
    """
    
    def __init__(self, store=None, citation_extractor=None, 
                 temporal_reasoner=None, relationship_extractor=None):
        self.store = store
        self.citation_extractor = citation_extractor or CitationExtractor()
        self.temporal_reasoner = temporal_reasoner or TemporalReasoner(store)
        self.relationship_extractor = relationship_extractor or CaseRelationshipExtractor()
        self.router = APIRouter(prefix="/api/v1/caselaw", tags=["caselaw"])
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup API routes"""
        
        @self.router.post("/precedents", response_model=PrecedentAnalysisResponse)
        async def query_precedents(request: PrecedentQueryRequest):
            """Query legal precedents for a given concept"""
            return await self.query_precedents_for_concept(
                legal_concept=request.legal_concept,
                jurisdiction=request.jurisdiction,
                temporal_scope=request.temporal_scope,
                date_range=request.date_range,
                limit=request.limit,
                include_relationships=request.include_relationships,
                confidence_threshold=request.confidence_threshold
            )
        
        @self.router.get("/cases/{case_id}")
        async def get_case(case_id: str, include_relationships: bool = True):
            """Retrieve a specific case by ID"""
            return await self.get_case_by_id(case_id, include_relationships)
        
        @self.router.post("/search", response_model=CaseSearchResponse)
        async def search_cases(request: CaseSearchRequest):
            """Search cases by text query"""
            return await self.search_cases_by_query(
                query=request.query,
                jurisdiction=request.jurisdiction,
                court=request.court,
                date_range=request.date_range,
                case_type=request.case_type,
                limit=request.limit
            )
        
        @self.router.post("/citations/resolve")
        async def resolve_citations(request: CitationResolutionRequest):
            """Resolve citation strings to canonical case references"""
            return await self.resolve_citation_strings(
                citations=request.citations,
                include_metadata=request.include_metadata,
                validate_format=request.validate_format
            )
        
        @self.router.get("/cases/{case_id}/temporal-analysis")
        async def get_temporal_analysis(case_id: str, as_of_date: Optional[str] = None):
            """Get temporal authority analysis for a case"""
            return await self.analyze_temporal_authority(case_id, as_of_date)
        
        @self.router.get("/cases/{case_id}/relationships")
        async def get_case_relationships(case_id: str, relationship_type: Optional[str] = None):
            """Get relationships for a specific case"""
            return await self.get_case_relationships_data(case_id, relationship_type)
    
    async def query_precedents_for_concept(self, legal_concept: str, 
                                         jurisdiction: str = "US",
                                         temporal_scope: str = "current",
                                         date_range: Optional[Dict[str, str]] = None,
                                         limit: int = 10,
                                         include_relationships: bool = True,
                                         confidence_threshold: float = 0.7) -> PrecedentAnalysisResponse:
        """
        Query precedents for a legal concept with comprehensive analysis
        """
        try:
            query_id = f"precedent_{datetime.utcnow().isoformat()}"
            
            # Search for relevant cases
            cases = await self._search_cases_for_concept(
                legal_concept, jurisdiction, temporal_scope, date_range, limit * 2
            )
            
            # Analyze case relationships and authority
            supporting_cases = []
            contrary_cases = []
            authority_hierarchy = []
            
            for case in cases:
                case_analysis = await self._analyze_case_for_concept(
                    case, legal_concept, include_relationships
                )
                
                if case_analysis["supports_concept"]:
                    supporting_cases.append(case_analysis)
                elif case_analysis["contradicts_concept"]:
                    contrary_cases.append(case_analysis)
                
                # Add to authority hierarchy
                authority_hierarchy.append({
                    "case_id": case["case_id"],
                    "authority_level": case_analysis.get("authority_level", 0.5),
                    "court": case.get("court", "Unknown"),
                    "date": case.get("decision_date", ""),
                    "precedential_value": case_analysis.get("precedential_value", 0.5)
                })
            
            # Sort by authority
            supporting_cases = sorted(supporting_cases, 
                                    key=lambda x: x.get("authority_level", 0), reverse=True)[:limit]
            contrary_cases = sorted(contrary_cases,
                                  key=lambda x: x.get("authority_level", 0), reverse=True)[:limit//2]
            authority_hierarchy = sorted(authority_hierarchy,
                                       key=lambda x: x["authority_level"], reverse=True)
            
            # Perform temporal analysis
            temporal_analysis = await self._perform_temporal_analysis(
                supporting_cases + contrary_cases, legal_concept
            )
            
            # Generate summary
            summary = self._generate_precedent_summary(
                legal_concept, supporting_cases, contrary_cases, temporal_analysis
            )
            
            # Calculate overall confidence
            confidence = self._calculate_precedent_confidence(
                supporting_cases, contrary_cases, temporal_analysis
            )
            
            return PrecedentAnalysisResponse(
                query_id=query_id,
                legal_concept=legal_concept,
                supporting_cases=supporting_cases,
                contrary_cases=contrary_cases,
                authority_hierarchy=authority_hierarchy,
                temporal_analysis=temporal_analysis,
                summary=summary,
                confidence=confidence,
                total_cases_analyzed=len(cases)
            )
            
        except Exception as e:
            logger.error(f"Error in precedent query: {e}")
            raise HTTPException(status_code=500, detail=f"Precedent query failed: {str(e)}")
    
    async def get_case_by_id(self, case_id: str, include_relationships: bool = True) -> Dict[str, Any]:
        """Retrieve detailed case information"""
        try:
            # Get basic case info
            case_info = await self._get_case_info(case_id)
            if not case_info:
                raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
            
            result = {
                "case_id": case_id,
                "basic_info": case_info,
                "retrieved_at": datetime.utcnow().isoformat()
            }
            
            if include_relationships:
                # Get case relationships
                relationships = await self._get_case_relationships(case_id)
                result["relationships"] = relationships
                
                # Get temporal analysis
                temporal_analysis = await self.analyze_temporal_authority(case_id)
                result["temporal_analysis"] = temporal_analysis
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving case {case_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Case retrieval failed: {str(e)}")
    
    async def search_cases_by_query(self, query: str, jurisdiction: Optional[str] = None,
                                  court: Optional[str] = None, date_range: Optional[Dict[str, str]] = None,
                                  case_type: Optional[str] = None, limit: int = 20) -> CaseSearchResponse:
        """Search cases using text query with filters"""
        try:
            # Build search filters
            filters = {}
            if jurisdiction:
                filters["jurisdiction"] = jurisdiction
            if court:
                filters["court"] = court
            if date_range:
                filters["date_range"] = date_range
            if case_type:
                filters["case_type"] = case_type
            
            # Perform search (placeholder implementation)
            results = await self._perform_text_search(query, filters, limit)
            
            return CaseSearchResponse(
                query=query,
                results=results,
                total_results=len(results),
                page=1,
                per_page=limit,
                filters_applied=filters
            )
            
        except Exception as e:
            logger.error(f"Error in case search: {e}")
            raise HTTPException(status_code=500, detail=f"Case search failed: {str(e)}")
    
    async def resolve_citation_strings(self, citations: List[str], 
                                     include_metadata: bool = True,
                                     validate_format: bool = True) -> Dict[str, Any]:
        """Resolve citation strings to canonical references"""
        try:
            resolved_citations = []
            
            for citation_text in citations:
                # Extract and validate citation
                citation_matches = self.citation_extractor.extract_citations(citation_text)
                
                if not citation_matches and validate_format:
                    resolved_citations.append({
                        "original_text": citation_text,
                        "status": "invalid_format",
                        "error": "Could not parse citation format"
                    })
                    continue
                
                for match in citation_matches:
                    result = {
                        "original_text": citation_text,
                        "canonical_id": str(match.canonical_id) if match.canonical_id else None,
                        "citation_type": match.citation_type.value,
                        "confidence": match.confidence,
                        "components": match.components,
                        "status": "resolved"
                    }
                    
                    if include_metadata and match.canonical_id:
                        # Get case metadata
                        metadata = await self._get_citation_metadata(match.canonical_id)
                        result["metadata"] = metadata
                    
                    resolved_citations.append(result)
            
            return {
                "resolved_citations": resolved_citations,
                "total_processed": len(citations),
                "total_resolved": len([c for c in resolved_citations if c.get("status") == "resolved"]),
                "processing_time": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error resolving citations: {e}")
            raise HTTPException(status_code=500, detail=f"Citation resolution failed: {str(e)}")
    
    async def analyze_temporal_authority(self, case_id: str, 
                                       as_of_date: Optional[str] = None) -> Dict[str, Any]:
        """Analyze temporal authority of a case"""
        try:
            doc_id = DocumentID(case_id)
            target_date = date.fromisoformat(as_of_date) if as_of_date else date.today()
            
            evaluation = self.temporal_reasoner.analyze_temporal_authority(doc_id, target_date)
            
            return {
                "case_id": case_id,
                "as_of_date": target_date.isoformat(),
                "temporal_evaluation": evaluation.to_dict(),
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in temporal analysis for {case_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Temporal analysis failed: {str(e)}")
    
    # Helper methods (placeholder implementations)
    async def _search_cases_for_concept(self, concept: str, jurisdiction: str,
                                      temporal_scope: str, date_range: Optional[Dict],
                                      limit: int) -> List[Dict[str, Any]]:
        """Search for cases related to a legal concept"""
        # Placeholder - would integrate with actual search backend
        return []
    
    async def _analyze_case_for_concept(self, case: Dict[str, Any], concept: str,
                                      include_relationships: bool) -> Dict[str, Any]:
        """Analyze how a case relates to a legal concept"""
        # Placeholder - would perform detailed analysis
        return {
            "case_id": case.get("case_id"),
            "supports_concept": True,
            "contradicts_concept": False,
            "authority_level": 0.8,
            "precedential_value": 0.7,
            "relevance_score": 0.9
        }
    
    async def _perform_temporal_analysis(self, cases: List[Dict], concept: str) -> Dict[str, Any]:
        """Perform temporal analysis across multiple cases"""
        return {
            "trend": "stable",
            "authority_over_time": [],
            "key_developments": [],
            "current_status": "well_established"
        }
    
    def _generate_precedent_summary(self, concept: str, supporting: List, 
                                  contrary: List, temporal: Dict) -> str:
        """Generate human-readable summary of precedent analysis"""
        return f"Analysis of {len(supporting)} supporting and {len(contrary)} contrary cases for '{concept}'"
    
    def _calculate_precedent_confidence(self, supporting: List, contrary: List, 
                                      temporal: Dict) -> float:
        """Calculate overall confidence in precedent analysis"""
        if not supporting:
            return 0.0
        
        support_strength = sum(c.get("authority_level", 0) for c in supporting) / len(supporting)
        contrary_strength = sum(c.get("authority_level", 0) for c in contrary) / max(len(contrary), 1)
        
        return max(0.0, min(1.0, support_strength - (contrary_strength * 0.5)))
    
    async def _get_case_info(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Get basic case information"""
        # Placeholder - would query actual storage
        return {"case_id": case_id, "title": "Sample Case", "court": "Sample Court"}
    
    async def _get_case_relationships(self, case_id: str) -> List[Dict[str, Any]]:
        """Get relationships for a case"""
        # Placeholder - would query actual storage
        return []
    
    async def _perform_text_search(self, query: str, filters: Dict, limit: int) -> List[Dict[str, Any]]:
        """Perform text search with filters"""
        # Placeholder - would integrate with Elasticsearch
        return []
    
    async def _get_citation_metadata(self, citation_id: CitationID) -> Dict[str, Any]:
        """Get metadata for a citation"""
        # Placeholder - would query actual storage
        return {"citation_id": str(citation_id), "metadata": "placeholder"}
    
    async def get_case_relationships_data(self, case_id: str, 
                                        relationship_type: Optional[str] = None) -> Dict[str, Any]:
        """Get detailed relationship data for a case"""
        try:
            relationships = await self._get_case_relationships(case_id)
            
            if relationship_type:
                relationships = [r for r in relationships 
                               if r.get("type") == relationship_type]
            
            return {
                "case_id": case_id,
                "relationships": relationships,
                "total_relationships": len(relationships),
                "relationship_types": list(set(r.get("type") for r in relationships)),
                "retrieved_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting relationships for {case_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Relationship query failed: {str(e)}")