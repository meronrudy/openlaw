"""
Elasticsearch Adapter for CAP Caselaw Plugin
Full-text search and document indexing for legal cases
"""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import asyncio

from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import ElasticsearchException, NotFoundError

from ..models.caselaw_node import CaselawNode, CaseNode

logger = logging.getLogger(__name__)


class ElasticsearchAdapter:
    """
    Elasticsearch adapter for full-text search and document indexing.
    Optimized for legal text analysis and citation search.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.hosts = config.get("hosts", ["localhost:9200"])
        self.username = config.get("username")
        self.password = config.get("password")
        self.use_ssl = config.get("use_ssl", False)
        self.verify_certs = config.get("verify_certs", False)
        
        # Index configuration
        self.cases_index = config.get("cases_index", "legal_cases")
        self.citations_index = config.get("citations_index", "legal_citations")
        
        # Performance settings
        self.max_retries = config.get("max_retries", 3)
        self.timeout = config.get("timeout", 30)
        self.max_concurrent_searches = config.get("max_concurrent_searches", 5)
        
        self._client: Optional[AsyncElasticsearch] = None
        self._initialized = False
        self._search_semaphore = asyncio.Semaphore(self.max_concurrent_searches)
        
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def initialize(self):
        """Initialize Elasticsearch client"""
        try:
            # Configure client
            client_config = {
                "hosts": self.hosts,
                "timeout": self.timeout,
                "max_retries": self.max_retries,
                "retry_on_timeout": True
            }
            
            if self.username and self.password:
                client_config["http_auth"] = (self.username, self.password)
            
            if self.use_ssl:
                client_config["use_ssl"] = True
                client_config["verify_certs"] = self.verify_certs
            
            self._client = AsyncElasticsearch(**client_config)
            
            # Test connection
            await self._client.ping()
            
            # Setup indices if they don't exist
            await self._setup_indices()
            
            self._initialized = True
            self.logger.info(f"Elasticsearch adapter initialized: {self.hosts}")
            
        except ElasticsearchException as e:
            self.logger.error(f"Failed to initialize Elasticsearch: {e}")
            raise
    
    async def close(self):
        """Close Elasticsearch client"""
        if self._client:
            await self._client.close()
            self._initialized = False
            self.logger.info("Elasticsearch adapter closed")
    
    def is_healthy(self) -> bool:
        """Check if Elasticsearch is healthy"""
        return self._initialized and self._client is not None
    
    async def _setup_indices(self):
        """Setup Elasticsearch indices and mappings"""
        # Check if cases index exists
        if not await self._client.indices.exists(index=self.cases_index):
            await self.create_index(self.cases_index, self._get_cases_mapping())
        
        # Check if citations index exists
        if not await self._client.indices.exists(index=self.citations_index):
            await self.create_index(self.citations_index, self._get_citations_mapping())
    
    def _get_cases_mapping(self) -> Dict[str, Any]:
        """Get mapping configuration for cases index"""
        return {
            "mappings": {
                "properties": {
                    "case_id": {"type": "keyword"},
                    "name": {
                        "type": "text",
                        "analyzer": "legal_text_analyzer",
                        "fields": {
                            "keyword": {"type": "keyword"},
                            "suggest": {"type": "completion"}
                        }
                    },
                    "name_abbreviation": {"type": "keyword"},
                    "jurisdiction": {"type": "keyword"},
                    "decision_date": {"type": "date"},
                    "court": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "keyword"},
                            "level": {"type": "keyword"},
                            "authority_level": {"type": "integer"}
                        }
                    },
                    "docket_number": {"type": "keyword"},
                    "full_text": {
                        "type": "text",
                        "analyzer": "legal_text_analyzer"
                    },
                    "paragraphs": {
                        "type": "nested",
                        "properties": {
                            "id": {"type": "keyword"},
                            "text": {
                                "type": "text",
                                "analyzer": "legal_text_analyzer"
                            },
                            "paragraph_number": {"type": "integer"}
                        }
                    },
                    "legal_concepts": {"type": "keyword"},
                    "precedential_value": {"type": "float"},
                    "citations": {
                        "type": "text",
                        "analyzer": "citation_analyzer"
                    },
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"},
                    "provenance_id": {"type": "keyword"}
                }
            },
            "settings": {
                "number_of_shards": 5,
                "number_of_replicas": 1,
                "analysis": {
                    "analyzer": {
                        "legal_text_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": [
                                "lowercase",
                                "legal_synonyms",
                                "legal_stemmer",
                                "stop"
                            ]
                        },
                        "citation_analyzer": {
                            "type": "custom",
                            "tokenizer": "keyword",
                            "filter": ["lowercase", "trim"]
                        }
                    },
                    "filter": {
                        "legal_synonyms": {
                            "type": "synonym",
                            "synonyms": [
                                "discrimination,bias,prejudice",
                                "precedent,authority,ruling",
                                "jurisdiction,venue,court",
                                "contract,agreement,covenant",
                                "tort,negligence,liability",
                                "constitutional,constitutional law,const",
                                "employment,labor,work"
                            ]
                        },
                        "legal_stemmer": {
                            "type": "stemmer",
                            "language": "english"
                        }
                    }
                }
            }
        }
    
    def _get_citations_mapping(self) -> Dict[str, Any]:
        """Get mapping configuration for citations index"""
        return {
            "mappings": {
                "properties": {
                    "citation_id": {"type": "keyword"},
                    "cite": {"type": "keyword"},
                    "normalized_cite": {"type": "keyword"},
                    "type": {"type": "keyword"},
                    "reporter": {"type": "keyword"},
                    "volume": {"type": "integer"},
                    "page": {"type": "integer"},
                    "case_id": {"type": "keyword"},
                    "created_at": {"type": "date"}
                }
            }
        }
    
    # Index management
    async def create_index(self, index_name: str, mapping: Dict[str, Any]) -> bool:
        """Create an index with mapping"""
        try:
            await self._client.indices.create(
                index=index_name,
                body=mapping
            )
            self.logger.info(f"Created Elasticsearch index: {index_name}")
            return True
            
        except ElasticsearchException as e:
            if "already exists" not in str(e):
                self.logger.error(f"Failed to create index {index_name}: {e}")
            return False
    
    async def delete_index(self, index_name: str) -> bool:
        """Delete an index"""
        try:
            await self._client.indices.delete(index=index_name)
            self.logger.info(f"Deleted Elasticsearch index: {index_name}")
            return True
            
        except ElasticsearchException as e:
            self.logger.error(f"Failed to delete index {index_name}: {e}")
            return False
    
    # Document indexing
    async def index_node(self, node: CaselawNode) -> bool:
        """Index a caselaw node"""
        try:
            if isinstance(node, CaseNode):
                return await self._index_case(node)
            else:
                # For other node types, we might index them differently
                # For now, only handle cases
                return True
                
        except ElasticsearchException as e:
            self.logger.error(f"Failed to index node {node.id}: {e}")
            return False
    
    async def _index_case(self, case: CaseNode) -> bool:
        """Index a case document"""
        try:
            doc = {
                "case_id": case.id,
                "name": case.case_name,
                "name_abbreviation": case.properties.get("name_abbreviation"),
                "jurisdiction": case.jurisdiction,
                "decision_date": case.decision_date.isoformat() if case.decision_date else None,
                "court": {
                    "name": case.court,
                    "level": case.properties.get("court_level"),
                    "authority_level": case.properties.get("authority_level", 0)
                },
                "docket_number": case.docket_number,
                "full_text": case.properties.get("full_text", ""),
                "legal_concepts": case.legal_concepts,
                "precedential_value": case.precedential_value,
                "citations": case.citations,
                "created_at": case.created_at.isoformat(),
                "updated_at": case.updated_at.isoformat(),
                "provenance_id": case.provenance_id
            }
            
            # Add paragraphs if available
            paragraphs = case.properties.get("paragraphs", [])
            if paragraphs:
                doc["paragraphs"] = paragraphs
            
            await self._client.index(
                index=self.cases_index,
                id=case.id,
                body=doc
            )
            
            return True
            
        except ElasticsearchException as e:
            self.logger.error(f"Failed to index case {case.id}: {e}")
            return False
    
    async def update_node(self, node: CaselawNode) -> bool:
        """Update an indexed node"""
        try:
            if isinstance(node, CaseNode):
                # For cases, we can do a partial update
                doc = {
                    "legal_concepts": node.legal_concepts,
                    "precedential_value": node.precedential_value,
                    "updated_at": datetime.utcnow().isoformat()
                }
                
                await self._client.update(
                    index=self.cases_index,
                    id=node.id,
                    body={"doc": doc}
                )
            
            return True
            
        except ElasticsearchException as e:
            self.logger.error(f"Failed to update node {node.id}: {e}")
            return False
    
    async def delete_node(self, node_id: str) -> bool:
        """Delete an indexed node"""
        try:
            await self._client.delete(
                index=self.cases_index,
                id=node_id
            )
            return True
            
        except NotFoundError:
            # Document doesn't exist, consider it successful
            return True
        except ElasticsearchException as e:
            self.logger.error(f"Failed to delete node {node_id}: {e}")
            return False
    
    # Batch operations
    async def index_nodes_batch(self, nodes: List[CaselawNode]) -> Dict[str, Any]:
        """Index multiple nodes in batch"""
        try:
            actions = []
            
            for node in nodes:
                if isinstance(node, CaseNode):
                    doc = {
                        "case_id": node.id,
                        "name": node.case_name,
                        "jurisdiction": node.jurisdiction,
                        "decision_date": node.decision_date.isoformat() if node.decision_date else None,
                        "court": {"name": node.court},
                        "legal_concepts": node.legal_concepts,
                        "precedential_value": node.precedential_value,
                        "citations": node.citations,
                        "created_at": node.created_at.isoformat(),
                        "provenance_id": node.provenance_id
                    }
                    
                    actions.append({
                        "_index": self.cases_index,
                        "_id": node.id,
                        "_source": doc
                    })
            
            if actions:
                from elasticsearch.helpers import async_bulk
                success_count, errors = await async_bulk(
                    self._client,
                    actions,
                    chunk_size=1000,
                    max_chunk_bytes=10 * 1024 * 1024  # 10MB chunks
                )
                
                return {
                    "success_count": success_count,
                    "total_count": len(nodes),
                    "errors": errors
                }
            
            return {"success_count": 0, "total_count": 0, "errors": []}
            
        except ElasticsearchException as e:
            self.logger.error(f"Failed to index nodes batch: {e}")
            return {"success_count": 0, "total_count": len(nodes), "errors": [str(e)]}
    
    # Search operations
    async def search(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute a search query"""
        async with self._search_semaphore:
            try:
                response = await self._client.search(**search_params)
                
                results = []
                for hit in response["hits"]["hits"]:
                    result = {
                        "id": hit["_id"],
                        "score": hit["_score"],
                        "source": hit["_source"]
                    }
                    
                    # Add highlights if available
                    if "highlight" in hit:
                        result["highlights"] = hit["highlight"]
                    
                    results.append(result)
                
                return results
                
            except ElasticsearchException as e:
                self.logger.error(f"Search failed: {e}")
                return []
    
    async def full_text_search(self,
                             query: str,
                             jurisdiction: Optional[str] = None,
                             date_range: Optional[tuple] = None,
                             limit: int = 100) -> List[Dict[str, Any]]:
        """Perform full-text search on legal cases"""
        try:
            search_body = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": [
                                        "name^3",
                                        "full_text",
                                        "legal_concepts^2",
                                        "paragraphs.text"
                                    ],
                                    "fuzziness": "AUTO",
                                    "type": "best_fields"
                                }
                            }
                        ],
                        "filter": []
                    }
                },
                "highlight": {
                    "fields": {
                        "name": {},
                        "full_text": {"fragment_size": 200, "number_of_fragments": 3},
                        "paragraphs.text": {"fragment_size": 150, "number_of_fragments": 2}
                    },
                    "pre_tags": ["<mark>"],
                    "post_tags": ["</mark>"]
                },
                "sort": [
                    {"_score": {"order": "desc"}},
                    {"precedential_value": {"order": "desc"}},
                    {"decision_date": {"order": "desc"}}
                ],
                "size": limit
            }
            
            # Add jurisdiction filter
            if jurisdiction:
                search_body["query"]["bool"]["filter"].append({
                    "term": {"jurisdiction": jurisdiction}
                })
            
            # Add date range filter
            if date_range:
                search_body["query"]["bool"]["filter"].append({
                    "range": {
                        "decision_date": {
                            "gte": date_range[0].isoformat() if date_range[0] else None,
                            "lte": date_range[1].isoformat() if date_range[1] else None
                        }
                    }
                })
            
            return await self.search({
                "index": self.cases_index,
                "body": search_body
            })
            
        except ElasticsearchException as e:
            self.logger.error(f"Full-text search failed: {e}")
            return []
    
    async def search_by_legal_concept(self,
                                    concept: str,
                                    jurisdiction: Optional[str] = None,
                                    limit: int = 50) -> List[Dict[str, Any]]:
        """Search cases by legal concept"""
        try:
            search_body = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "term": {"legal_concepts": concept}
                            }
                        ],
                        "filter": []
                    }
                },
                "sort": [
                    {"precedential_value": {"order": "desc"}},
                    {"decision_date": {"order": "desc"}}
                ],
                "size": limit
            }
            
            if jurisdiction:
                search_body["query"]["bool"]["filter"].append({
                    "term": {"jurisdiction": jurisdiction}
                })
            
            return await self.search({
                "index": self.cases_index,
                "body": search_body
            })
            
        except ElasticsearchException as e:
            self.logger.error(f"Legal concept search failed: {e}")
            return []
    
    async def suggest_case_names(self, prefix: str, limit: int = 10) -> List[str]:
        """Get case name suggestions"""
        try:
            response = await self._client.search(
                index=self.cases_index,
                body={
                    "suggest": {
                        "case_suggest": {
                            "prefix": prefix,
                            "completion": {
                                "field": "name.suggest",
                                "size": limit
                            }
                        }
                    }
                }
            )
            
            suggestions = []
            for option in response["suggest"]["case_suggest"][0]["options"]:
                suggestions.append(option["text"])
            
            return suggestions
            
        except ElasticsearchException as e:
            self.logger.error(f"Case name suggestion failed: {e}")
            return []
    
    # Analytics and aggregations
    async def get_jurisdiction_stats(self) -> Dict[str, Any]:
        """Get statistics by jurisdiction"""
        try:
            response = await self._client.search(
                index=self.cases_index,
                body={
                    "size": 0,
                    "aggs": {
                        "jurisdictions": {
                            "terms": {
                                "field": "jurisdiction",
                                "size": 100
                            },
                            "aggs": {
                                "avg_precedential_value": {
                                    "avg": {"field": "precedential_value"}
                                },
                                "decision_dates": {
                                    "date_histogram": {
                                        "field": "decision_date",
                                        "calendar_interval": "year"
                                    }
                                }
                            }
                        }
                    }
                }
            )
            
            return response["aggregations"]
            
        except ElasticsearchException as e:
            self.logger.error(f"Jurisdiction stats failed: {e}")
            return {}
    
    async def get_legal_concept_trends(self, 
                                     concept: str,
                                     start_date: Optional[datetime] = None,
                                     end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get trends for a legal concept over time"""
        try:
            query = {
                "bool": {
                    "must": [
                        {"term": {"legal_concepts": concept}}
                    ],
                    "filter": []
                }
            }
            
            if start_date or end_date:
                date_range = {}
                if start_date:
                    date_range["gte"] = start_date.isoformat()
                if end_date:
                    date_range["lte"] = end_date.isoformat()
                
                query["bool"]["filter"].append({
                    "range": {"decision_date": date_range}
                })
            
            response = await self._client.search(
                index=self.cases_index,
                body={
                    "size": 0,
                    "query": query,
                    "aggs": {
                        "cases_over_time": {
                            "date_histogram": {
                                "field": "decision_date",
                                "calendar_interval": "year"
                            },
                            "aggs": {
                                "avg_precedential_value": {
                                    "avg": {"field": "precedential_value"}
                                }
                            }
                        },
                        "top_jurisdictions": {
                            "terms": {
                                "field": "jurisdiction",
                                "size": 10
                            }
                        }
                    }
                }
            )
            
            return {
                "concept": concept,
                "timeline": response["aggregations"]["cases_over_time"]["buckets"],
                "top_jurisdictions": response["aggregations"]["top_jurisdictions"]["buckets"]
            }
            
        except ElasticsearchException as e:
            self.logger.error(f"Legal concept trends failed: {e}")
            return {}
    
    # Maintenance operations
    async def optimize_indices(self):
        """Optimize Elasticsearch indices"""
        try:
            await self._client.indices.forcemerge(
                index=[self.cases_index, self.citations_index],
                max_num_segments=1
            )
            self.logger.info("Elasticsearch indices optimized")
            
        except ElasticsearchException as e:
            self.logger.error(f"Failed to optimize indices: {e}")
    
    async def get_index_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        try:
            response = await self._client.indices.stats(
                index=[self.cases_index, self.citations_index]
            )
            return response["indices"]
            
        except ElasticsearchException as e:
            self.logger.error(f"Failed to get index stats: {e}")
            return {}
    
    async def refresh_indices(self):
        """Refresh indices to make recent changes available for search"""
        try:
            await self._client.indices.refresh(
                index=[self.cases_index, self.citations_index]
            )
            
        except ElasticsearchException as e:
            self.logger.error(f"Failed to refresh indices: {e}")