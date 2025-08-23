# CAP Caselaw Plugin - Integration Guide

## Overview

This document provides comprehensive guidance for integrating the CAP caselaw plugin with the OpenLaw core system and other plugins, enabling enhanced legal reasoning through cross-plugin composition.

## 🔗 Core System Integration

### Plugin Registration & Discovery

```python
# plugins/caselaw/plugin.py
from typing import Dict, List, Any, Optional
from sdk.plugin import BasePlugin, PluginCapability, EnhancementResult
from core.reasoning import ReasoningContext, LegalConcept
from .models import CaselawNode, CaseRelationship, ProvenanceRecord
from .api import CaselawProvenanceAPI, CaselawQueryAPI

class CaselawPlugin(BasePlugin):
    """
    CAP Caselaw Plugin - Provides provenance-first access to 37M+ case law documents
    with complete audit trails for legal AI reasoning.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.plugin_id = "caselaw_access_project"
        self.version = "1.0.0"
        
        # Initialize core components
        self._initialize_storage(config)
        self._initialize_extractors(config)
        self._initialize_reasoners(config)
        self._initialize_apis(config)
    
    @property
    def capabilities(self) -> List[PluginCapability]:
        """Define plugin capabilities for the core system"""
        return [
            PluginCapability(
                name="case_precedent_analysis",
                description="Analyze case law precedents for legal concepts",
                input_types=["legal_concept", "jurisdiction", "date_range"],
                output_types=["precedent_analysis", "authority_hierarchy"],
                enhancement_compatible=True
            ),
            PluginCapability(
                name="citation_resolution",
                description="Resolve legal citations to canonical case references",
                input_types=["citation_text", "jurisdiction"],
                output_types=["resolved_citation", "case_reference"],
                enhancement_compatible=True
            ),
            PluginCapability(
                name="provenance_tracing",
                description="Provide complete audit trails for legal reasoning",
                input_types=["entity_id", "reasoning_path"],
                output_types=["provenance_trace", "source_verification"],
                enhancement_compatible=False  # Core capability, not enhancement
            ),
            PluginCapability(
                name="temporal_authority_analysis",
                description="Analyze temporal relationships and precedential authority",
                input_types=["case_relationship", "temporal_context"],
                output_types=["authority_evaluation", "temporal_analysis"],
                enhancement_compatible=True
            )
        ]
    
    def register_with_core(self, core_registry) -> bool:
        """Register plugin capabilities with the core reasoning system"""
        try:
            # Register as hypergraph data source
            core_registry.register_hypergraph_source(
                plugin_id=self.plugin_id,
                node_types=["case", "citation", "court", "judge", "legal_concept"],
                edge_types=["cites_case", "distinguishes", "overrules", "follows", "decided_by"],
                query_interface=self.hypergraph_query_api
            )
            
            # Register reasoning enhancers
            core_registry.register_reasoning_enhancer(
                concept_types=["employment_discrimination", "constitutional_law", "contract_law"],
                enhancer=self.enhance_legal_reasoning,
                priority=100  # High priority for authoritative case law
            )
            
            # Register provenance provider
            core_registry.register_provenance_provider(
                provider_id=self.plugin_id,
                provider=self.provenance_api,
                entity_types=["case", "citation", "legal_precedent"]
            )
            
            # Register cross-plugin composition hooks
            core_registry.register_composition_hook(
                hook_type="pre_analysis",
                callback=self.pre_analysis_enhancement
            )
            core_registry.register_composition_hook(
                hook_type="post_analysis", 
                callback=self.post_analysis_enhancement
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register with core system: {e}")
            return False
```

### Hypergraph Integration

```python
# plugins/caselaw/integration/hypergraph_adapter.py
from typing import List, Dict, Any, Optional, Iterator
from core.model import HypergraphNode, HypergraphEdge, QueryResult
from ..models import CaselawNode, CaseRelationship
from ..storage import CaselawHypergraphStore

class CaselawHypergraphAdapter:
    """Adapter for integrating caselaw data with core hypergraph system"""
    
    def __init__(self, store: CaselawHypergraphStore):
        self.store = store
        self.node_type_mapping = {
            "case": self._convert_case_node,
            "citation": self._convert_citation_node,
            "court": self._convert_court_node,
            "judge": self._convert_judge_node,
            "legal_concept": self._convert_concept_node
        }
    
    def query_nodes(self, 
                   node_types: List[str], 
                   filters: Dict[str, Any],
                   limit: int = 1000) -> Iterator[HypergraphNode]:
        """Query caselaw nodes for core hypergraph operations"""
        
        # Translate core filters to caselaw-specific queries
        caselaw_filters = self._translate_filters(filters)
        
        for node_type in node_types:
            if node_type not in self.node_type_mapping:
                continue
                
            # Query caselaw store
            caselaw_nodes = self.store.query_nodes_by_type(
                node_type, caselaw_filters, limit
            )
            
            # Convert to core hypergraph format
            converter = self.node_type_mapping[node_type]
            for caselaw_node in caselaw_nodes:
                yield converter(caselaw_node)
    
    def query_edges(self,
                   source_nodes: List[str],
                   relation_types: List[str],
                   filters: Dict[str, Any],
                   limit: int = 1000) -> Iterator[HypergraphEdge]:
        """Query caselaw relationships for core hypergraph operations"""
        
        caselaw_filters = self._translate_filters(filters)
        
        # Query relationships from caselaw store
        relationships = self.store.query_relationships(
            source_nodes, relation_types, caselaw_filters, limit
        )
        
        for relationship in relationships:
            yield self._convert_relationship_to_edge(relationship)
    
    def _convert_case_node(self, caselaw_node: CaselawNode) -> HypergraphNode:
        """Convert caselaw case node to core hypergraph node"""
        return HypergraphNode(
            id=caselaw_node.id,
            node_type="case",
            properties={
                "name": caselaw_node.properties.get("name"),
                "jurisdiction": caselaw_node.properties.get("jurisdiction"),
                "decision_date": caselaw_node.properties.get("decision_date"),
                "court": caselaw_node.properties.get("court"),
                "precedential_value": self._calculate_precedential_value(caselaw_node),
                "legal_concepts": self._extract_legal_concepts(caselaw_node),
                "provenance_id": caselaw_node.provenance_id
            },
            created_at=caselaw_node.created_at,
            source_plugin=self.store.plugin_id
        )
    
    def _convert_relationship_to_edge(self, relationship: CaseRelationship) -> HypergraphEdge:
        """Convert case relationship to hypergraph edge"""
        return HypergraphEdge(
            id=relationship.id,
            relation=relationship.relationship_type,
            heads=[relationship.target_case_id],
            tails=[relationship.source_case_id],
            properties={
                "confidence": relationship.confidence,
                "evidence_spans": relationship.evidence_spans,
                "temporal_validity": relationship.temporal_evaluation,
                "jurisdictional_validity": relationship.jurisdictional_evaluation,
                "provenance_id": relationship.provenance_id
            },
            created_at=relationship.created_at,
            source_plugin=self.store.plugin_id
        )
    
    def _translate_filters(self, core_filters: Dict[str, Any]) -> Dict[str, Any]:
        """Translate core system filters to caselaw-specific format"""
        caselaw_filters = {}
        
        filter_mappings = {
            "jurisdiction": "jurisdiction",
            "date_range": "decision_date_range", 
            "court_level": "court.authority_level",
            "legal_concepts": "extracted_concepts",
            "precedential_strength": "precedential_value"
        }
        
        for core_key, value in core_filters.items():
            if core_key in filter_mappings:
                caselaw_key = filter_mappings[core_key]
                caselaw_filters[caselaw_key] = value
        
        return caselaw_filters
```

## 🔄 Cross-Plugin Enhancement

### Employment Law Plugin Integration

```python
# plugins/caselaw/integration/employment_law_enhancer.py
from typing import Dict, List, Any, Optional
from core.reasoning import ReasoningContext, LegalAnalysis
from ..api import CaselawQueryAPI
from ..models import PrecedentQuery, PrecedentAnalysis

class EmploymentLawEnhancer:
    """Enhance employment law analysis with relevant case law precedents"""
    
    def __init__(self, caselaw_api: CaselawQueryAPI):
        self.caselaw_api = caselaw_api
        self.employment_concept_mapping = {
            "discrimination": [
                "employment_discrimination", "disparate_treatment", "disparate_impact",
                "protected_class", "title_vii", "ada_discrimination"
            ],
            "harassment": [
                "sexual_harassment", "hostile_work_environment", "quid_pro_quo",
                "supervisor_liability", "employer_liability"
            ],
            "wrongful_termination": [
                "at_will_employment", "constructive_discharge", "retaliatory_discharge",
                "breach_of_contract", "good_faith_and_fair_dealing"
            ],
            "wage_and_hour": [
                "flsa_violations", "overtime_pay", "minimum_wage", "exempt_employee",
                "meal_breaks", "rest_periods"
            ]
        }
    
    def enhance_employment_analysis(self, 
                                  analysis: LegalAnalysis,
                                  context: ReasoningContext) -> Dict[str, Any]:
        """Enhance employment law analysis with case law precedents"""
        
        enhancements = {
            "supporting_precedents": [],
            "contrary_precedents": [],
            "authority_hierarchy": [],
            "temporal_analysis": {},
            "provenance_traces": []
        }
        
        # Extract employment law concepts from analysis
        employment_concepts = self._extract_employment_concepts(analysis)
        
        if not employment_concepts:
            return enhancements
        
        # Query relevant case law for each concept
        for concept in employment_concepts:
            precedent_query = PrecedentQuery(
                legal_concept=concept,
                jurisdiction=context.jurisdiction,
                date_range=context.temporal_scope,
                authority_level=context.required_authority_level,
                limit=10
            )
            
            # Get precedent analysis
            precedent_analysis = self.caselaw_api.query_precedents(precedent_query)
            
            if precedent_analysis:
                enhancements["supporting_precedents"].extend(
                    precedent_analysis.supporting_cases
                )
                enhancements["contrary_precedents"].extend(
                    precedent_analysis.contrary_cases
                )
                
                # Add authority hierarchy for this concept
                enhancements["authority_hierarchy"].append({
                    "concept": concept,
                    "hierarchy": precedent_analysis.authority_hierarchy
                })
                
                # Add temporal analysis
                enhancements["temporal_analysis"][concept] = {
                    "trend_analysis": precedent_analysis.temporal_trends,
                    "recent_developments": precedent_analysis.recent_developments,
                    "historical_context": precedent_analysis.historical_context
                }
        
        # Generate comprehensive provenance traces
        enhancements["provenance_traces"] = self._generate_provenance_traces(
            analysis, enhancements, context
        )
        
        return enhancements
    
    def _extract_employment_concepts(self, analysis: LegalAnalysis) -> List[str]:
        """Extract employment law concepts that can be enhanced with case law"""
        concepts = []
        
        # Check analysis text for employment law keywords
        analysis_text = f"{analysis.summary} {' '.join(analysis.key_findings)}"
        
        for concept_category, concept_terms in self.employment_concept_mapping.items():
            for term in concept_terms:
                if term.lower() in analysis_text.lower():
                    concepts.append(term)
        
        # Also check extracted legal entities
        if hasattr(analysis, 'legal_entities'):
            for entity in analysis.legal_entities:
                if entity.entity_type == "legal_concept" and entity.value in self.employment_concept_mapping:
                    concepts.extend(self.employment_concept_mapping[entity.value])
        
        return list(set(concepts))  # Remove duplicates
    
    def _generate_provenance_traces(self,
                                   analysis: LegalAnalysis,
                                   enhancements: Dict[str, Any],
                                   context: ReasoningContext) -> List[Dict[str, Any]]:
        """Generate complete provenance traces for enhanced analysis"""
        traces = []
        
        # Create trace for each supporting precedent
        for precedent in enhancements["supporting_precedents"]:
            trace = self.caselaw_api.provenance_api.trace_entity_provenance(
                precedent.case_id
            )
            
            # Add reasoning path
            trace["reasoning_path"] = {
                "original_analysis": {
                    "plugin": "employment_law",
                    "concepts": analysis.legal_concepts,
                    "confidence": analysis.confidence
                },
                "enhancement_source": {
                    "plugin": "caselaw_access_project",
                    "case_id": precedent.case_id,
                    "relevance_score": precedent.relevance_score,
                    "authority_level": precedent.authority_level
                },
                "query_context": {
                    "jurisdiction": context.jurisdiction,
                    "temporal_scope": context.temporal_scope,
                    "query_timestamp": context.query_timestamp.isoformat()
                }
            }
            
            traces.append(trace)
        
        return traces
```

### Contract Law Integration Example

```python
# plugins/caselaw/integration/contract_law_enhancer.py
class ContractLawEnhancer:
    """Enhance contract law analysis with relevant precedents"""
    
    def __init__(self, caselaw_api: CaselawQueryAPI):
        self.caselaw_api = caselaw_api
        self.contract_concepts = {
            "formation": ["offer", "acceptance", "consideration", "capacity", "legality"],
            "interpretation": ["plain_meaning", "ambiguity", "parol_evidence", "course_of_dealing"],
            "performance": ["material_breach", "substantial_performance", "perfect_tender"],
            "remedies": ["expectation_damages", "reliance_damages", "restitution", "specific_performance"]
        }
    
    def enhance_contract_analysis(self,
                                contract_analysis: LegalAnalysis,
                                context: ReasoningContext) -> Dict[str, Any]:
        """Provide contract law precedent enhancement"""
        
        # Extract contract-specific concepts
        contract_concepts = self._identify_contract_concepts(contract_analysis)
        
        enhancements = {}
        
        for concept in contract_concepts:
            # Query relevant contract law precedents
            precedents = self.caselaw_api.query_precedents(
                PrecedentQuery(
                    legal_concept=concept,
                    jurisdiction=context.jurisdiction,
                    case_types=["contract", "commercial"],
                    limit=5
                )
            )
            
            if precedents:
                enhancements[concept] = {
                    "leading_cases": precedents.leading_cases,
                    "circuit_splits": precedents.circuit_splits,
                    "recent_trends": precedents.temporal_trends
                }
        
        return enhancements
```

## 🔌 Plugin Composition Framework

### Composition Manager Integration

```python
# plugins/caselaw/integration/composition_manager.py
from typing import Dict, List, Any, Optional, Callable
from core.composition import PluginComposition, CompositionResult
from ..api import CaselawQueryAPI, CaselawProvenanceAPI

class CaselawCompositionManager:
    """Manage composition with other plugins for enhanced legal reasoning"""
    
    def __init__(self, caselaw_api: CaselawQueryAPI, provenance_api: CaselawProvenanceAPI):
        self.caselaw_api = caselaw_api
        self.provenance_api = provenance_api
        self.composition_strategies = {
            "employment_law": self._compose_with_employment_law,
            "contract_law": self._compose_with_contract_law,
            "constitutional_law": self._compose_with_constitutional_law,
            "regulatory_compliance": self._compose_with_regulatory_compliance
        }
    
    def compose_analysis(self,
                        primary_plugin: str,
                        primary_result: LegalAnalysis,
                        context: ReasoningContext,
                        requested_enhancements: List[str] = None) -> CompositionResult:
        """Compose caselaw enhancement with primary plugin analysis"""
        
        if primary_plugin not in self.composition_strategies:
            # Generic composition for unknown plugins
            return self._generic_composition(primary_result, context)
        
        # Use specialized composition strategy
        composition_func = self.composition_strategies[primary_plugin]
        caselaw_enhancement = composition_func(primary_result, context)
        
        # Create comprehensive composition result
        return CompositionResult(
            primary_plugin=primary_plugin,
            primary_result=primary_result,
            enhancements={
                "caselaw_access_project": caselaw_enhancement
            },
            composition_metadata={
                "enhancement_confidence": caselaw_enhancement.get("confidence", 0.0),
                "precedent_count": len(caselaw_enhancement.get("supporting_precedents", [])),
                "authority_levels": self._extract_authority_levels(caselaw_enhancement),
                "temporal_coverage": self._calculate_temporal_coverage(caselaw_enhancement)
            },
            provenance_trace=self._create_composition_provenance_trace(
                primary_plugin, primary_result, caselaw_enhancement, context
            )
        )
    
    def _compose_with_employment_law(self,
                                   employment_analysis: LegalAnalysis,
                                   context: ReasoningContext) -> Dict[str, Any]:
        """Specialized composition with employment law plugin"""
        
        # Extract employment-specific legal concepts
        employment_concepts = self._extract_concepts_by_domain(
            employment_analysis, "employment"
        )
        
        enhancement = {
            "supporting_precedents": [],
            "jurisdictional_analysis": {},
            "temporal_trends": {},
            "circuit_authority": {}
        }
        
        # Query precedents for each employment concept
        for concept in employment_concepts:
            # Get comprehensive precedent analysis
            precedent_analysis = self.caselaw_api.query_employment_precedents(
                concept=concept,
                jurisdiction=context.jurisdiction,
                temporal_scope=context.temporal_scope
            )
            
            if precedent_analysis:
                enhancement["supporting_precedents"].extend(
                    precedent_analysis.cases
                )
                
                # Add jurisdictional analysis
                enhancement["jurisdictional_analysis"][concept] = {
                    "binding_authority": precedent_analysis.binding_cases,
                    "persuasive_authority": precedent_analysis.persuasive_cases,
                    "conflicting_authority": precedent_analysis.conflicting_cases
                }
                
                # Add temporal trends
                enhancement["temporal_trends"][concept] = {
                    "recent_developments": precedent_analysis.recent_trends,
                    "historical_shifts": precedent_analysis.historical_analysis,
                    "emerging_issues": precedent_analysis.emerging_concepts
                }
        
        # Calculate overall enhancement confidence
        enhancement["confidence"] = self._calculate_enhancement_confidence(
            employment_analysis, enhancement
        )
        
        return enhancement
    
    def _create_composition_provenance_trace(self,
                                           primary_plugin: str,
                                           primary_result: LegalAnalysis,
                                           caselaw_enhancement: Dict[str, Any],
                                           context: ReasoningContext) -> Dict[str, Any]:
        """Create comprehensive provenance trace for plugin composition"""
        
        return {
            "composition_id": f"comp_{uuid.uuid4()}",
            "timestamp": datetime.utcnow().isoformat(),
            "primary_analysis": {
                "plugin": primary_plugin,
                "analysis_id": primary_result.analysis_id,
                "confidence": primary_result.confidence,
                "legal_concepts": primary_result.legal_concepts
            },
            "caselaw_enhancement": {
                "plugin": "caselaw_access_project",
                "precedent_count": len(caselaw_enhancement.get("supporting_precedents", [])),
                "enhancement_confidence": caselaw_enhancement.get("confidence", 0.0),
                "query_context": {
                    "jurisdiction": context.jurisdiction,
                    "temporal_scope": context.temporal_scope,
                    "authority_requirements": context.required_authority_level
                }
            },
            "reasoning_chain": self._build_reasoning_chain(
                primary_result, caselaw_enhancement
            ),
            "source_verification": {
                "primary_sources": self._extract_primary_sources(primary_result),
                "caselaw_sources": self._extract_caselaw_sources(caselaw_enhancement),
                "cross_references": self._identify_cross_references(
                    primary_result, caselaw_enhancement
                )
            }
        }
```

## 📡 API Integration Patterns

### RESTful API Integration

```python
# plugins/caselaw/integration/rest_api.py
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from ..api import CaselawQueryAPI, CaselawProvenanceAPI
from core.authentication import verify_api_key
from core.rate_limiting import rate_limit

# Integration router for external API access
caselaw_integration_router = APIRouter(
    prefix="/api/v1/plugins/caselaw",
    tags=["caselaw-integration"],
    dependencies=[Depends(verify_api_key), Depends(rate_limit)]
)

class CrossPluginEnhancementRequest(BaseModel):
    primary_plugin: str
    primary_analysis: Dict[str, Any]
    context: Dict[str, Any]
    enhancement_types: List[str] = ["precedents", "authority", "temporal"]

class EnhancementResponse(BaseModel):
    enhancement_id: str
    primary_plugin: str
    enhancements: Dict[str, Any]
    confidence: float
    provenance_trace: Dict[str, Any]

@caselaw_integration_router.post("/enhance", response_model=EnhancementResponse)
async def enhance_legal_analysis(
    request: CrossPluginEnhancementRequest,
    caselaw_api: CaselawQueryAPI = Depends()
) -> EnhancementResponse:
    """Enhance legal analysis from other plugins with caselaw precedents"""
    
    try:
        # Convert request to internal format
        primary_analysis = LegalAnalysis.from_dict(request.primary_analysis)
        context = ReasoningContext.from_dict(request.context)
        
        # Get composition manager
        composition_manager = CaselawCompositionManager(caselaw_api, caselaw_api.provenance_api)
        
        # Perform enhancement
        composition_result = composition_manager.compose_analysis(
            primary_plugin=request.primary_plugin,
            primary_result=primary_analysis,
            context=context,
            requested_enhancements=request.enhancement_types
        )
        
        return EnhancementResponse(
            enhancement_id=composition_result.composition_id,
            primary_plugin=request.primary_plugin,
            enhancements=composition_result.enhancements["caselaw_access_project"],
            confidence=composition_result.composition_metadata["enhancement_confidence"],
            provenance_trace=composition_result.provenance_trace
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enhancement failed: {str(e)}")

@caselaw_integration_router.get("/precedents/bulk")
async def bulk_precedent_lookup(
    concepts: List[str] = Query(...),
    jurisdiction: str = Query("US"),
    limit_per_concept: int = Query(5, le=20),
    caselaw_api: CaselawQueryAPI = Depends()
) -> Dict[str, List[Dict[str, Any]]]:
    """Bulk precedent lookup for multiple legal concepts"""
    
    results = {}
    
    for concept in concepts:
        try:
            precedent_query = PrecedentQuery(
                legal_concept=concept,
                jurisdiction=jurisdiction,
                limit=limit_per_concept
            )
            
            precedent_analysis = await caselaw_api.query_precedents(precedent_query)
            
            results[concept] = [
                {
                    "case_id": case.case_id,
                    "citation": case.citation,
                    "relevance_score": case.relevance_score,
                    "authority_level": case.authority_level,
                    "decision_date": case.decision_date.isoformat() if case.decision_date else None
                }
                for case in precedent_analysis.supporting_cases
            ]
            
        except Exception as e:
            results[concept] = {"error": str(e)}
    
    return results
```

### GraphQL Integration

```python
# plugins/caselaw/integration/graphql_schema.py
import graphene
from graphene import ObjectType, String, List, Float, Field, Argument
from typing import Optional, List as ListType
from ..models import CaselawNode, CaseRelationship

class CaseType(ObjectType):
    """GraphQL type for legal cases"""
    id = String(required=True)
    name = String(required=True)
    jurisdiction = String(required=True)
    decision_date = String()
    court = String()
    citations = List(String)
    precedential_value = Float()
    
    def resolve_citations(self, info):
        # Resolve citations for this case
        return self.properties.get("citations", [])
    
    def resolve_precedential_value(self, info):
        # Calculate precedential value based on authority and citations
        return self.properties.get("precedential_value", 0.0)

class CaseRelationshipType(ObjectType):
    """GraphQL type for case relationships"""
    id = String(required=True)
    source_case = Field(CaseType)
    target_case = Field(CaseType)
    relationship_type = String(required=True)
    confidence = Float()
    evidence_spans = List(String)
    
    def resolve_source_case(self, info):
        # Resolve source case from relationship
        case_store = info.context["case_store"]
        return case_store.get_case(self.source_case_id)
    
    def resolve_target_case(self, info):
        # Resolve target case from relationship
        case_store = info.context["case_store"]
        return case_store.get_case(self.target_case_id)

class PrecedentAnalysisType(ObjectType):
    """GraphQL type for precedent analysis results"""
    concept = String(required=True)
    supporting_cases = List(CaseType)
    contrary_cases = List(CaseType)
    authority_hierarchy = List(String)
    confidence = Float()

class CaselawQuery(ObjectType):
    """GraphQL query interface for caselaw plugin"""
    
    case = Field(
        CaseType,
        id=Argument(String, required=True),
        description="Get case by ID"
    )
    
    cases_by_citation = Field(
        List(CaseType),
        citation=Argument(String, required=True),
        description="Find cases by citation"
    )
    
    precedent_analysis = Field(
        PrecedentAnalysisType,
        concept=Argument(String, required=True),
        jurisdiction=Argument(String, default_value="US"),
        description="Analyze precedents for legal concept"
    )
    
    case_relationships = Field(
        List(CaseRelationshipType),
        case_id=Argument(String, required=True),
        relationship_types=Argument(List(String)),
        description="Get relationships for a case"
    )
    
    def resolve_case(self, info, id):
        case_store = info.context["case_store"]
        return case_store.get_case(id)
    
    def resolve_cases_by_citation(self, info, citation):
        citation_resolver = info.context["citation_resolver"]
        return citation_resolver.resolve_citation(citation)
    
    def resolve_precedent_analysis(self, info, concept, jurisdiction):
        caselaw_api = info.context["caselaw_api"]
        query = PrecedentQuery(
            legal_concept=concept,
            jurisdiction=jurisdiction,
            limit=10
        )
        return caselaw_api.query_precedents(query)
    
    def resolve_case_relationships(self, info, case_id, relationship_types=None):
        hypergraph_store = info.context["hypergraph_store"]
        return hypergraph_store.get_case_relationships(case_id, relationship_types)

# Integration with main GraphQL schema
def extend_schema_with_caselaw(base_schema):
    """Extend the main OpenLaw GraphQL schema with caselaw types"""
    
    class ExtendedQuery(base_schema.Query, CaselawQuery):
        pass
    
    return graphene.Schema(
        query=ExtendedQuery,
        types=[CaseType, CaseRelationshipType, PrecedentAnalysisType]
    )
```

## 🔄 Event-Driven Integration

### Event Publishing

```python
# plugins/caselaw/integration/events.py
from typing import Dict, Any, List
from core.events import EventPublisher, Event, EventType
from ..models import CaselawNode, CaseRelationship

class CaselawEventPublisher:
    """Publish caselaw-related events for other plugins to consume"""
    
    def __init__(self, event_publisher: EventPublisher):
        self.publisher = event_publisher
        self.plugin_id = "caselaw_access_project"
    
    def publish_case_ingested(self, case: CaselawNode):
        """Publish event when new case is ingested"""
        event = Event(
            event_type=EventType.ENTITY_CREATED,
            source_plugin=self.plugin_id,
            entity_type="case",
            entity_id=case.id,
            data={
                "case_name": case.properties.get("name"),
                "jurisdiction": case.properties.get("jurisdiction"),
                "decision_date": case.properties.get("decision_date"),
                "legal_concepts": case.properties.get("extracted_concepts", []),
                "precedential_value": case.properties.get("precedential_value", 0.0)
            },
            metadata={
                "provenance_id": case.provenance_id,
                "processing_timestamp": case.created_at.isoformat()
            }
        )
        
        self.publisher.publish(event)
    
    def publish_relationship_discovered(self, relationship: CaseRelationship):
        """Publish event when new case relationship is discovered"""
        event = Event(
            event_type=EventType.RELATIONSHIP_CREATED,
            source_plugin=self.plugin_id,
            entity_type="case_relationship",
            entity_id=relationship.id,
            data={
                "source_case_id": relationship.source_case_id,
                "target_case_id": relationship.target_case_id,
                "relationship_type": relationship.relationship_type,
                "confidence": relationship.confidence,
                "evidence_spans": relationship.evidence_spans
            },
            metadata={
                "provenance_id": relationship.provenance_id,
                "extraction_method": relationship.extraction_method
            }
        )
        
        self.publisher.publish(event)
    
    def publish_precedent_query_executed(self, 
                                       query: PrecedentQuery,
                                       results: PrecedentAnalysis):
        """Publish event when precedent query is executed (for analytics)"""
        event = Event(
            event_type=EventType.QUERY_EXECUTED,
            source_plugin=self.plugin_id,
            entity_type="precedent_query",
            entity_id=f"query_{uuid.uuid4()}",
            data={
                "legal_concept": query.legal_concept,
                "jurisdiction": query.jurisdiction,
                "result_count": len(results.supporting_cases),
                "confidence": results.overall_confidence
            },
            metadata={
                "query_timestamp": datetime.utcnow().isoformat(),
                "execution_time_ms": results.execution_time_ms
            }
        )
        
        self.publisher.publish(event)

class CaselawEventSubscriber:
    """Subscribe to events from other plugins for potential enhancement"""
    
    def __init__(self, caselaw_api: CaselawQueryAPI):
        self.caselaw_api = caselaw_api
        self.plugin_id = "caselaw_access_project"
    
    def handle_legal_analysis_completed(self, event: Event):
        """Handle completion of legal analysis from other plugins"""
        if event.source_plugin == self.plugin_id:
            return  # Don't enhance our own events
        
        # Check if analysis could benefit from caselaw enhancement
        analysis_data = event.data
        legal_concepts = analysis_data.get("legal_concepts", [])
        
        if self._should_enhance_with_caselaw(legal_concepts):
            # Queue for asynchronous enhancement
            self._queue_enhancement_task(event)
    
    def handle_document_analyzed(self, event: Event):
        """Handle document analysis events for potential citation extraction"""
        if event.entity_type != "legal_document":
            return
        
        document_text = event.data.get("text", "")
        
        # Check if document contains legal citations
        if self._contains_legal_citations(document_text):
            # Extract and resolve citations
            self._extract_citations_async(event.entity_id, document_text)
    
    def _should_enhance_with_caselaw(self, legal_concepts: List[str]) -> bool:
        """Determine if legal concepts warrant caselaw enhancement"""
        enhanceable_concepts = {
            "discrimination", "harassment", "wrongful_termination",
            "contract_breach", "constitutional_violation", "due_process",
            "equal_protection", "first_amendment", "fourth_amendment"
        }
        
        return any(concept in enhanceable_concepts for concept in legal_concepts)
    
    def _queue_enhancement_task(self, event: Event):
        """Queue asynchronous enhancement task"""
        # Implementation would use task queue (Celery, RQ, etc.)
        pass
    
    def _contains_legal_citations(self, text: str) -> bool:
        """Quick check if text contains legal citations"""
        citation_patterns = [
            r'\d+\s+U\.S\.\s+\d+',  # U.S. citations
            r'\d+\s+F\.\d+d\s+\d+',  # Federal citations
            r'\d+\s+U\.S\.C\.\s+§\s+\d+',  # USC citations
        ]
        
        import re
        for pattern in citation_patterns:
            if re.search(pattern, text):
                return True
        return False
```

This comprehensive integration guide provides the framework for seamlessly connecting the CAP caselaw plugin with the OpenLaw core system and other domain-specific plugins, enabling powerful cross-plugin legal reasoning with complete provenance tracking.