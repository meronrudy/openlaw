"""
Storage Configuration for CAP Caselaw Plugin
Manages configuration for the hybrid storage architecture
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import os


@dataclass
class Neo4jConfig:
    """Neo4j configuration"""
    uri: str = "bolt://localhost:7687"
    username: str = "neo4j"
    password: str = "password"
    database: str = "caselaw"
    max_connection_pool_size: int = 50
    max_transaction_retry_time: int = 30
    connection_timeout: int = 30
    
    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> 'Neo4jConfig':
        """Create from dictionary configuration"""
        return cls(
            uri=config.get("uri", "bolt://localhost:7687"),
            username=config.get("username", "neo4j"),
            password=config.get("password", "password"),
            database=config.get("database", "caselaw"),
            max_connection_pool_size=config.get("max_connection_pool_size", 50),
            max_transaction_retry_time=config.get("max_transaction_retry_time", 30),
            connection_timeout=config.get("connection_timeout", 30)
        )


@dataclass
class RedisConfig:
    """Redis configuration"""
    url: str = "redis://localhost:6379"
    db: int = 0
    max_connections: int = 10
    default_ttl: int = 3600
    node_ttl: int = 7200
    relationship_ttl: int = 3600
    query_ttl: int = 1800
    
    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> 'RedisConfig':
        """Create from dictionary configuration"""
        return cls(
            url=config.get("url", "redis://localhost:6379"),
            db=config.get("db", 0),
            max_connections=config.get("max_connections", 10),
            default_ttl=config.get("default_ttl", 3600),
            node_ttl=config.get("node_ttl", 7200),
            relationship_ttl=config.get("relationship_ttl", 3600),
            query_ttl=config.get("query_ttl", 1800)
        )


@dataclass
class ElasticsearchConfig:
    """Elasticsearch configuration"""
    hosts: list = field(default_factory=lambda: ["localhost:9200"])
    username: Optional[str] = None
    password: Optional[str] = None
    use_ssl: bool = False
    verify_certs: bool = False
    cases_index: str = "legal_cases"
    citations_index: str = "legal_citations"
    max_retries: int = 3
    timeout: int = 30
    max_concurrent_searches: int = 5
    
    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> 'ElasticsearchConfig':
        """Create from dictionary configuration"""
        return cls(
            hosts=config.get("hosts", ["localhost:9200"]),
            username=config.get("username"),
            password=config.get("password"),
            use_ssl=config.get("use_ssl", False),
            verify_certs=config.get("verify_certs", False),
            cases_index=config.get("cases_index", "legal_cases"),
            citations_index=config.get("citations_index", "legal_citations"),
            max_retries=config.get("max_retries", 3),
            timeout=config.get("timeout", 30),
            max_concurrent_searches=config.get("max_concurrent_searches", 5)
        )


class StorageConfig:
    """
    Main storage configuration manager for the hybrid architecture.
    Handles environment variables, defaults, and validation.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.raw_config = config
        self._neo4j_config = None
        self._redis_config = None
        self._elasticsearch_config = None
        
        # Load configurations
        self._load_configurations()
        
        # Validate configurations
        self._validate_configurations()
    
    def _load_configurations(self):
        """Load and parse individual storage configurations"""
        
        # Neo4j configuration
        neo4j_config = self.raw_config.get("neo4j", {})
        
        # Override with environment variables if present
        neo4j_config.update({
            k.replace("NEO4J_", "").lower(): v 
            for k, v in os.environ.items() 
            if k.startswith("NEO4J_")
        })
        
        self._neo4j_config = Neo4jConfig.from_dict(neo4j_config)
        
        # Redis configuration
        redis_config = self.raw_config.get("redis", {})
        
        # Override with environment variables
        redis_config.update({
            k.replace("REDIS_", "").lower(): v
            for k, v in os.environ.items()
            if k.startswith("REDIS_")
        })
        
        self._redis_config = RedisConfig.from_dict(redis_config)
        
        # Elasticsearch configuration
        es_config = self.raw_config.get("elasticsearch", {})
        
        # Override with environment variables
        env_overrides = {}
        for k, v in os.environ.items():
            if k.startswith("ELASTICSEARCH_"):
                key = k.replace("ELASTICSEARCH_", "").lower()
                
                # Handle special cases
                if key == "hosts":
                    env_overrides[key] = v.split(",")
                elif key in ["use_ssl", "verify_certs"]:
                    env_overrides[key] = v.lower() in ("true", "1", "yes")
                elif key in ["max_retries", "timeout", "max_concurrent_searches"]:
                    env_overrides[key] = int(v)
                else:
                    env_overrides[key] = v
        
        es_config.update(env_overrides)
        self._elasticsearch_config = ElasticsearchConfig.from_dict(es_config)
    
    def _validate_configurations(self):
        """Validate storage configurations"""
        errors = []
        
        # Validate Neo4j
        if not self._neo4j_config.uri:
            errors.append("Neo4j URI is required")
        
        if not self._neo4j_config.username or not self._neo4j_config.password:
            errors.append("Neo4j username and password are required")
        
        # Validate Redis
        if not self._redis_config.url:
            errors.append("Redis URL is required")
        
        # Validate Elasticsearch
        if not self._elasticsearch_config.hosts:
            errors.append("Elasticsearch hosts are required")
        
        if errors:
            raise ValueError(f"Storage configuration errors: {', '.join(errors)}")
    
    @property
    def neo4j_config(self) -> Neo4jConfig:
        """Get Neo4j configuration"""
        return self._neo4j_config
    
    @property
    def redis_config(self) -> RedisConfig:
        """Get Redis configuration"""
        return self._redis_config
    
    @property
    def elasticsearch_config(self) -> ElasticsearchConfig:
        """Get Elasticsearch configuration"""
        return self._elasticsearch_config
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information for all storage backends"""
        return {
            "neo4j": {
                "uri": self._neo4j_config.uri,
                "database": self._neo4j_config.database,
                "pool_size": self._neo4j_config.max_connection_pool_size
            },
            "redis": {
                "url": self._redis_config.url,
                "db": self._redis_config.db,
                "max_connections": self._redis_config.max_connections
            },
            "elasticsearch": {
                "hosts": self._elasticsearch_config.hosts,
                "indices": {
                    "cases": self._elasticsearch_config.cases_index,
                    "citations": self._elasticsearch_config.citations_index
                }
            }
        }
    
    @classmethod
    def from_environment(cls) -> 'StorageConfig':
        """Create configuration from environment variables only"""
        config = {}
        
        # Group environment variables by service
        for key, value in os.environ.items():
            if key.startswith(("NEO4J_", "REDIS_", "ELASTICSEARCH_")):
                service = key.split("_")[0].lower()
                param = "_".join(key.split("_")[1:]).lower()
                
                if service not in config:
                    config[service] = {}
                
                # Type conversion for common parameters
                if param in ["port", "db", "max_connections", "timeout", "max_retries"]:
                    try:
                        value = int(value)
                    except ValueError:
                        pass
                elif param in ["use_ssl", "verify_certs"]:
                    value = value.lower() in ("true", "1", "yes")
                elif param == "hosts":
                    value = value.split(",")
                
                config[service][param] = value
        
        return cls(config)
    
    @classmethod
    def get_default_config(cls) -> 'StorageConfig':
        """Get default configuration for development"""
        return cls({
            "neo4j": {
                "uri": "bolt://localhost:7687",
                "username": "neo4j",
                "password": "password",
                "database": "caselaw"
            },
            "redis": {
                "url": "redis://localhost:6379",
                "db": 0
            },
            "elasticsearch": {
                "hosts": ["localhost:9200"],
                "cases_index": "legal_cases",
                "citations_index": "legal_citations"
            }
        })
    
    @classmethod
    def get_production_config(cls) -> 'StorageConfig':
        """Get production configuration template"""
        return cls({
            "neo4j": {
                "uri": "bolt://neo4j-cluster:7687",
                "username": "neo4j",
                "password": "${NEO4J_PASSWORD}",
                "database": "caselaw",
                "max_connection_pool_size": 100,
                "max_transaction_retry_time": 60,
                "connection_timeout": 60
            },
            "redis": {
                "url": "redis://redis-cluster:6379",
                "db": 0,
                "max_connections": 50,
                "node_ttl": 14400,  # 4 hours
                "relationship_ttl": 7200,  # 2 hours
                "query_ttl": 3600  # 1 hour
            },
            "elasticsearch": {
                "hosts": [
                    "elasticsearch-node-1:9200",
                    "elasticsearch-node-2:9200", 
                    "elasticsearch-node-3:9200"
                ],
                "username": "${ELASTICSEARCH_USERNAME}",
                "password": "${ELASTICSEARCH_PASSWORD}",
                "use_ssl": True,
                "verify_certs": True,
                "cases_index": "caselaw_cases_v1",
                "citations_index": "caselaw_citations_v1",
                "max_concurrent_searches": 20,
                "timeout": 60
            }
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "neo4j": {
                "uri": self._neo4j_config.uri,
                "username": self._neo4j_config.username,
                "password": "***",  # Masked for security
                "database": self._neo4j_config.database,
                "max_connection_pool_size": self._neo4j_config.max_connection_pool_size,
                "max_transaction_retry_time": self._neo4j_config.max_transaction_retry_time,
                "connection_timeout": self._neo4j_config.connection_timeout
            },
            "redis": {
                "url": self._redis_config.url,
                "db": self._redis_config.db,
                "max_connections": self._redis_config.max_connections,
                "default_ttl": self._redis_config.default_ttl,
                "node_ttl": self._redis_config.node_ttl,
                "relationship_ttl": self._redis_config.relationship_ttl,
                "query_ttl": self._redis_config.query_ttl
            },
            "elasticsearch": {
                "hosts": self._elasticsearch_config.hosts,
                "username": self._elasticsearch_config.username,
                "password": "***" if self._elasticsearch_config.password else None,
                "use_ssl": self._elasticsearch_config.use_ssl,
                "verify_certs": self._elasticsearch_config.verify_certs,
                "cases_index": self._elasticsearch_config.cases_index,
                "citations_index": self._elasticsearch_config.citations_index,
                "max_retries": self._elasticsearch_config.max_retries,
                "timeout": self._elasticsearch_config.timeout,
                "max_concurrent_searches": self._elasticsearch_config.max_concurrent_searches
            }
        }


# Configuration validation utilities
class ConfigValidator:
    """Utility class for validating storage configurations"""
    
    @staticmethod
    def validate_neo4j_connection(config: Neo4jConfig) -> Dict[str, Any]:
        """Validate Neo4j connection settings"""
        try:
            from neo4j import GraphDatabase
            
            driver = GraphDatabase.driver(
                config.uri,
                auth=(config.username, config.password),
                max_connection_pool_size=1  # Just for testing
            )
            
            with driver.session(database=config.database) as session:
                session.run("RETURN 1")
            
            driver.close()
            
            return {"valid": True, "message": "Neo4j connection successful"}
            
        except Exception as e:
            return {"valid": False, "message": f"Neo4j connection failed: {e}"}
    
    @staticmethod
    def validate_redis_connection(config: RedisConfig) -> Dict[str, Any]:
        """Validate Redis connection settings"""
        try:
            import redis
            
            r = redis.from_url(config.url, db=config.db)
            r.ping()
            r.close()
            
            return {"valid": True, "message": "Redis connection successful"}
            
        except Exception as e:
            return {"valid": False, "message": f"Redis connection failed: {e}"}
    
    @staticmethod
    def validate_elasticsearch_connection(config: ElasticsearchConfig) -> Dict[str, Any]:
        """Validate Elasticsearch connection settings"""
        try:
            from elasticsearch import Elasticsearch
            
            client_config = {"hosts": config.hosts}
            
            if config.username and config.password:
                client_config["http_auth"] = (config.username, config.password)
            
            if config.use_ssl:
                client_config["use_ssl"] = True
                client_config["verify_certs"] = config.verify_certs
            
            es = Elasticsearch(**client_config)
            
            if not es.ping():
                raise Exception("Elasticsearch ping failed")
            
            return {"valid": True, "message": "Elasticsearch connection successful"}
            
        except Exception as e:
            return {"valid": False, "message": f"Elasticsearch connection failed: {e}"}
    
    @classmethod
    def validate_all_connections(cls, storage_config: StorageConfig) -> Dict[str, Any]:
        """Validate all storage connections"""
        results = {
            "neo4j": cls.validate_neo4j_connection(storage_config.neo4j_config),
            "redis": cls.validate_redis_connection(storage_config.redis_config),
            "elasticsearch": cls.validate_elasticsearch_connection(storage_config.elasticsearch_config)
        }
        
        all_valid = all(result["valid"] for result in results.values())
        
        return {
            "all_valid": all_valid,
            "results": results,
            "summary": "All connections valid" if all_valid else "Some connections failed"
        }


# Configuration templates for different environments
def get_development_config() -> Dict[str, Any]:
    """Get development configuration"""
    return {
        "neo4j": {
            "uri": "bolt://localhost:7687",
            "username": "neo4j",
            "password": "password",
            "database": "caselaw_dev"
        },
        "redis": {
            "url": "redis://localhost:6379",
            "db": 1  # Use different DB for dev
        },
        "elasticsearch": {
            "hosts": ["localhost:9200"],
            "cases_index": "legal_cases_dev",
            "citations_index": "legal_citations_dev"
        }
    }


def get_test_config() -> Dict[str, Any]:
    """Get test configuration"""
    return {
        "neo4j": {
            "uri": "bolt://localhost:7687",
            "username": "neo4j",
            "password": "password",
            "database": "caselaw_test"
        },
        "redis": {
            "url": "redis://localhost:6379",
            "db": 2,  # Use different DB for tests
            "default_ttl": 60  # Short TTL for tests
        },
        "elasticsearch": {
            "hosts": ["localhost:9200"],
            "cases_index": "legal_cases_test",
            "citations_index": "legal_citations_test"
        }
    }


def get_production_config() -> Dict[str, Any]:
    """Get production configuration template"""
    return StorageConfig.get_production_config().to_dict()