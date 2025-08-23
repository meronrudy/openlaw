"""
Configuration Validator for CAP Caselaw Plugin
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import re

from .config_manager import CaselawConfig

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Configuration validation error"""
    pass


class ConfigValidator:
    """
    Validates caselaw plugin configuration for correctness and compatibility
    """
    
    def __init__(self):
        """Initialize configuration validator"""
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate(self, config: CaselawConfig) -> Tuple[bool, List[str], List[str]]:
        """
        Validate complete configuration
        
        Args:
            config: Configuration to validate
            
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []
        
        try:
            # Validate each configuration section
            self._validate_storage_config(config.storage)
            self._validate_ingestion_config(config.ingestion)
            self._validate_extraction_config(config.extraction)
            self._validate_reasoning_config(config.reasoning)
            self._validate_api_config(config.api)
            self._validate_logging_config(config.logging)
            
            # Cross-section validation
            self._validate_cross_dependencies(config)
            
            is_valid = len(self.errors) == 0
            
            if is_valid:
                logger.info("Configuration validation passed")
            else:
                logger.error(f"Configuration validation failed with {len(self.errors)} errors")
            
            if self.warnings:
                logger.warning(f"Configuration validation completed with {len(self.warnings)} warnings")
            
            return is_valid, self.errors, self.warnings
            
        except Exception as e:
            error_msg = f"Validation process failed: {str(e)}"
            self.errors.append(error_msg)
            logger.error(error_msg)
            return False, self.errors, self.warnings
    
    def _validate_storage_config(self, storage_config):
        """Validate storage configuration"""
        # Neo4j validation
        if storage_config.neo4j_enabled:
            if not storage_config.neo4j_uri:
                self.errors.append("Neo4j enabled but no URI provided")
            else:
                if not self._validate_neo4j_uri(storage_config.neo4j_uri):
                    self.errors.append(f"Invalid Neo4j URI format: {storage_config.neo4j_uri}")
            
            if not storage_config.neo4j_user:
                self.errors.append("Neo4j enabled but no username provided")
            
            if not storage_config.neo4j_password:
                self.warnings.append("Neo4j enabled but no password provided - using empty password")
        
        # Redis validation
        if storage_config.redis_enabled:
            if not storage_config.redis_url:
                self.errors.append("Redis enabled but no URL provided")
            else:
                if not self._validate_redis_url(storage_config.redis_url):
                    self.errors.append(f"Invalid Redis URL format: {storage_config.redis_url}")
            
            if not isinstance(storage_config.redis_db, int) or storage_config.redis_db < 0:
                self.errors.append("Redis database number must be a non-negative integer")
        
        # Elasticsearch validation
        if storage_config.elasticsearch_enabled:
            if not storage_config.elasticsearch_hosts:
                self.errors.append("Elasticsearch enabled but no hosts provided")
            else:
                for host in storage_config.elasticsearch_hosts:
                    if not self._validate_elasticsearch_host(host):
                        self.errors.append(f"Invalid Elasticsearch host format: {host}")
            
            if not storage_config.elasticsearch_index_prefix:
                self.errors.append("Elasticsearch index prefix cannot be empty")
            elif not self._validate_index_name(storage_config.elasticsearch_index_prefix):
                self.errors.append(f"Invalid Elasticsearch index prefix: {storage_config.elasticsearch_index_prefix}")
        
        # Mock storage validation
        if storage_config.use_mock:
            if storage_config.neo4j_enabled or storage_config.redis_enabled or storage_config.elasticsearch_enabled:
                self.warnings.append("Mock storage enabled - real storage backends will be bypassed")
    
    def _validate_ingestion_config(self, ingestion_config):
        """Validate ingestion configuration"""
        if ingestion_config.ingestion_batch_size <= 0:
            self.errors.append("Ingestion batch size must be positive")
        elif ingestion_config.ingestion_batch_size > 10000:
            self.warnings.append("Large ingestion batch size may cause memory issues")
        
        if ingestion_config.ingestion_max_workers <= 0:
            self.errors.append("Ingestion max workers must be positive")
        elif ingestion_config.ingestion_max_workers > 50:
            self.warnings.append("High number of ingestion workers may overwhelm system resources")
        
        if not ingestion_config.dataset_name:
            self.errors.append("Dataset name cannot be empty")
        elif not self._validate_huggingface_dataset_name(ingestion_config.dataset_name):
            self.warnings.append(f"Dataset name format may be invalid: {ingestion_config.dataset_name}")
        
        if ingestion_config.checkpoint_frequency <= 0:
            self.errors.append("Checkpoint frequency must be positive")
        elif ingestion_config.checkpoint_frequency < 100:
            self.warnings.append("Very frequent checkpointing may impact performance")
        
        # Cross-validation with storage
        if ingestion_config.auto_start_ingestion and not ingestion_config.enable_background_ingestion:
            self.warnings.append("Auto-start ingestion enabled but background ingestion disabled")
    
    def _validate_extraction_config(self, extraction_config):
        """Validate extraction configuration"""
        if not (0.0 <= extraction_config.citation_confidence_threshold <= 1.0):
            self.errors.append("Citation confidence threshold must be between 0.0 and 1.0")
        elif extraction_config.citation_confidence_threshold < 0.3:
            self.warnings.append("Very low citation confidence threshold may include many false positives")
        elif extraction_config.citation_confidence_threshold > 0.95:
            self.warnings.append("Very high citation confidence threshold may miss valid citations")
        
        if not (0.0 <= extraction_config.relationship_confidence_threshold <= 1.0):
            self.errors.append("Relationship confidence threshold must be between 0.0 and 1.0")
        elif extraction_config.relationship_confidence_threshold < 0.3:
            self.warnings.append("Very low relationship confidence threshold may include many false positives")
        
        if not extraction_config.enable_ml_citation_extraction and not extraction_config.enable_spacy_models:
            self.warnings.append("Both ML citation extraction and spaCy models disabled - extraction quality may be poor")
    
    def _validate_reasoning_config(self, reasoning_config):
        """Validate reasoning configuration"""
        if not (0.0 <= reasoning_config.precedent_strength_threshold <= 1.0):
            self.errors.append("Precedent strength threshold must be between 0.0 and 1.0")
        
        if not (0.0 <= reasoning_config.authority_confidence_threshold <= 1.0):
            self.errors.append("Authority confidence threshold must be between 0.0 and 1.0")
        
        if not reasoning_config.temporal_analysis_enabled and not reasoning_config.jurisdictional_analysis_enabled:
            self.warnings.append("Both temporal and jurisdictional analysis disabled - reasoning capabilities will be limited")
    
    def _validate_api_config(self, api_config):
        """Validate API configuration"""
        if api_config.max_search_results <= 0:
            self.errors.append("Max search results must be positive")
        elif api_config.max_search_results > 10000:
            self.warnings.append("Very high max search results may impact performance")
        
        if api_config.query_timeout <= 0:
            self.errors.append("Query timeout must be positive")
        elif api_config.query_timeout < 5:
            self.warnings.append("Very short query timeout may cause queries to fail")
        elif api_config.query_timeout > 300:
            self.warnings.append("Very long query timeout may cause client timeouts")
        
        if not api_config.enable_query_api and not api_config.enable_provenance_api:
            self.warnings.append("Both query and provenance APIs disabled - plugin will have limited functionality")
    
    def _validate_logging_config(self, logging_config):
        """Validate logging configuration"""
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if logging_config.log_level not in valid_log_levels:
            self.errors.append(f"Invalid log level: {logging_config.log_level}. Must be one of {valid_log_levels}")
        
        if logging_config.enable_performance_logging:
            self.warnings.append("Performance logging enabled - may impact performance and generate large logs")
    
    def _validate_cross_dependencies(self, config: CaselawConfig):
        """Validate cross-section dependencies"""
        # Storage and ingestion dependencies
        if config.ingestion.enable_background_ingestion:
            if not config.storage.neo4j_enabled and not config.storage.use_mock:
                self.errors.append("Background ingestion requires Neo4j storage or mock storage")
        
        # Extraction and reasoning dependencies
        if config.reasoning.temporal_analysis_enabled or config.reasoning.jurisdictional_analysis_enabled:
            if not config.extraction.enable_ml_citation_extraction and not config.extraction.enable_spacy_models:
                self.warnings.append("Reasoning analysis enabled but extraction capabilities limited")
        
        # API and storage dependencies
        if config.api.enable_query_api:
            if not config.storage.elasticsearch_enabled and not config.storage.use_mock:
                self.warnings.append("Query API enabled but Elasticsearch disabled - search performance may be poor")
        
        if config.api.enable_provenance_api:
            if not config.storage.neo4j_enabled and not config.storage.use_mock:
                self.errors.append("Provenance API requires Neo4j storage or mock storage")
    
    def _validate_neo4j_uri(self, uri: str) -> bool:
        """Validate Neo4j URI format"""
        neo4j_pattern = r'^(bolt|bolt\+s|bolt\+ssc|neo4j|neo4j\+s|neo4j\+ssc)://[^:]+:\d+$'
        return bool(re.match(neo4j_pattern, uri))
    
    def _validate_redis_url(self, url: str) -> bool:
        """Validate Redis URL format"""
        redis_pattern = r'^redis://([^:]+:\d+|[^:]+)(\?\S*)?$'
        return bool(re.match(redis_pattern, url))
    
    def _validate_elasticsearch_host(self, host: str) -> bool:
        """Validate Elasticsearch host format"""
        host_pattern = r'^[^:]+:\d+$'
        return bool(re.match(host_pattern, host))
    
    def _validate_index_name(self, name: str) -> bool:
        """Validate Elasticsearch index name"""
        # Elasticsearch index name rules: lowercase, no spaces, certain special chars
        index_pattern = r'^[a-z0-9][a-z0-9._-]*$'
        return bool(re.match(index_pattern, name))
    
    def _validate_huggingface_dataset_name(self, name: str) -> bool:
        """Validate HuggingFace dataset name format"""
        dataset_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?/[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?$'
        return bool(re.match(dataset_pattern, name))
    
    def validate_environment_variables(self, env_vars: Dict[str, str]) -> Tuple[bool, List[str], List[str]]:
        """
        Validate environment variables
        
        Args:
            env_vars: Dictionary of environment variables
            
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        errors = []
        warnings = []
        
        # Check for required environment variables in production
        production_required = [
            "CASELAW_NEO4J_PASSWORD",
        ]
        
        for var in production_required:
            if var not in env_vars or not env_vars[var]:
                warnings.append(f"Production environment variable not set: {var}")
        
        # Validate specific environment variable formats
        if "CASELAW_NEO4J_URI" in env_vars:
            if not self._validate_neo4j_uri(env_vars["CASELAW_NEO4J_URI"]):
                errors.append(f"Invalid NEO4J_URI format: {env_vars['CASELAW_NEO4J_URI']}")
        
        if "CASELAW_REDIS_URL" in env_vars:
            if not self._validate_redis_url(env_vars["CASELAW_REDIS_URL"]):
                errors.append(f"Invalid REDIS_URL format: {env_vars['CASELAW_REDIS_URL']}")
        
        # Validate numeric environment variables
        numeric_vars = {
            "CASELAW_BATCH_SIZE": (1, 10000),
            "CASELAW_MAX_WORKERS": (1, 50),
            "CASELAW_MAX_RESULTS": (1, 10000),
            "CASELAW_QUERY_TIMEOUT": (1, 300)
        }
        
        for var, (min_val, max_val) in numeric_vars.items():
            if var in env_vars:
                try:
                    value = int(env_vars[var])
                    if not (min_val <= value <= max_val):
                        errors.append(f"{var} must be between {min_val} and {max_val}")
                except ValueError:
                    errors.append(f"{var} must be a valid integer")
        
        # Validate float environment variables
        float_vars = {
            "CASELAW_CITATION_THRESHOLD": (0.0, 1.0),
            "CASELAW_RELATIONSHIP_THRESHOLD": (0.0, 1.0),
            "CASELAW_PRECEDENT_THRESHOLD": (0.0, 1.0)
        }
        
        for var, (min_val, max_val) in float_vars.items():
            if var in env_vars:
                try:
                    value = float(env_vars[var])
                    if not (min_val <= value <= max_val):
                        errors.append(f"{var} must be between {min_val} and {max_val}")
                except ValueError:
                    errors.append(f"{var} must be a valid float")
        
        # Validate log level
        if "CASELAW_LOG_LEVEL" in env_vars:
            valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            if env_vars["CASELAW_LOG_LEVEL"] not in valid_levels:
                errors.append(f"CASELAW_LOG_LEVEL must be one of {valid_levels}")
        
        is_valid = len(errors) == 0
        return is_valid, errors, warnings
    
    def generate_validation_report(self, config: CaselawConfig) -> str:
        """
        Generate a comprehensive validation report
        
        Args:
            config: Configuration to validate
            
        Returns:
            Formatted validation report
        """
        is_valid, errors, warnings = self.validate(config)
        
        report = ["=" * 50]
        report.append("CAP CASELAW PLUGIN CONFIGURATION VALIDATION REPORT")
        report.append("=" * 50)
        report.append("")
        
        # Summary
        status = "PASS" if is_valid else "FAIL"
        report.append(f"Overall Status: {status}")
        report.append(f"Errors: {len(errors)}")
        report.append(f"Warnings: {len(warnings)}")
        report.append("")
        
        # Errors
        if errors:
            report.append("ERRORS:")
            report.append("-" * 20)
            for i, error in enumerate(errors, 1):
                report.append(f"{i:2d}. {error}")
            report.append("")
        
        # Warnings
        if warnings:
            report.append("WARNINGS:")
            report.append("-" * 20)
            for i, warning in enumerate(warnings, 1):
                report.append(f"{i:2d}. {warning}")
            report.append("")
        
        # Configuration summary
        report.append("CONFIGURATION SUMMARY:")
        report.append("-" * 20)
        report.append(f"Storage Backend: {'Mock' if config.storage.use_mock else 'Production'}")
        report.append(f"Neo4j: {'Enabled' if config.storage.neo4j_enabled else 'Disabled'}")
        report.append(f"Redis: {'Enabled' if config.storage.redis_enabled else 'Disabled'}")
        report.append(f"Elasticsearch: {'Enabled' if config.storage.elasticsearch_enabled else 'Disabled'}")
        report.append(f"Background Ingestion: {'Enabled' if config.ingestion.enable_background_ingestion else 'Disabled'}")
        report.append(f"ML Citation Extraction: {'Enabled' if config.extraction.enable_ml_citation_extraction else 'Disabled'}")
        report.append(f"Temporal Analysis: {'Enabled' if config.reasoning.temporal_analysis_enabled else 'Disabled'}")
        report.append(f"Query API: {'Enabled' if config.api.enable_query_api else 'Disabled'}")
        report.append(f"Provenance API: {'Enabled' if config.api.enable_provenance_api else 'Disabled'}")
        report.append("")
        
        report.append("=" * 50)
        
        return "\n".join(report)