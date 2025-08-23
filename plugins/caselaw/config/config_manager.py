"""
Configuration Manager for CAP Caselaw Plugin
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel, Field, validator
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class StorageConfig:
    """Storage configuration"""
    use_mock: bool = False
    neo4j_enabled: bool = True
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: Optional[str] = None
    redis_enabled: bool = True
    redis_url: str = "redis://localhost:6379"
    redis_db: int = 0
    elasticsearch_enabled: bool = True
    elasticsearch_hosts: list = Field(default_factory=lambda: ["localhost:9200"])
    elasticsearch_index_prefix: str = "caselaw"


@dataclass
class IngestionConfig:
    """Ingestion configuration"""
    auto_start_ingestion: bool = False
    enable_background_ingestion: bool = True
    ingestion_batch_size: int = 1000
    ingestion_max_workers: int = 10
    dataset_name: str = "harvard-lil/cap-us-court-opinions"
    checkpoint_frequency: int = 1000


@dataclass
class ExtractionConfig:
    """Extraction configuration"""
    enable_ml_citation_extraction: bool = True
    citation_confidence_threshold: float = 0.7
    relationship_confidence_threshold: float = 0.6
    enable_spacy_models: bool = True


@dataclass
class ReasoningConfig:
    """Reasoning configuration"""
    temporal_analysis_enabled: bool = True
    jurisdictional_analysis_enabled: bool = True
    precedent_strength_threshold: float = 0.5
    authority_confidence_threshold: float = 0.7


@dataclass
class APIConfig:
    """API configuration"""
    enable_query_api: bool = True
    enable_provenance_api: bool = True
    max_search_results: int = 100
    query_timeout: int = 30


@dataclass
class LoggingConfig:
    """Logging configuration"""
    log_level: str = "INFO"
    enable_performance_logging: bool = False
    enable_audit_logging: bool = True


class CaselawConfig(BaseModel):
    """Complete Caselaw Plugin Configuration"""
    
    storage: StorageConfig = Field(default_factory=StorageConfig)
    ingestion: IngestionConfig = Field(default_factory=IngestionConfig)
    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)
    reasoning: ReasoningConfig = Field(default_factory=ReasoningConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    @validator('storage')
    def validate_storage_config(cls, v):
        """Validate storage configuration"""
        if isinstance(v, dict):
            return StorageConfig(**v)
        return v
    
    @validator('ingestion')
    def validate_ingestion_config(cls, v):
        """Validate ingestion configuration"""
        if isinstance(v, dict):
            return IngestionConfig(**v)
        return v
    
    @validator('extraction')
    def validate_extraction_config(cls, v):
        """Validate extraction configuration"""
        if isinstance(v, dict):
            return ExtractionConfig(**v)
        return v
    
    @validator('reasoning')
    def validate_reasoning_config(cls, v):
        """Validate reasoning configuration"""
        if isinstance(v, dict):
            return ReasoningConfig(**v)
        return v
    
    @validator('api')
    def validate_api_config(cls, v):
        """Validate API configuration"""
        if isinstance(v, dict):
            return APIConfig(**v)
        return v
    
    @validator('logging')
    def validate_logging_config(cls, v):
        """Validate logging configuration"""
        if isinstance(v, dict):
            return LoggingConfig(**v)
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "storage": self.storage.__dict__,
            "ingestion": self.ingestion.__dict__,
            "extraction": self.extraction.__dict__,
            "reasoning": self.reasoning.__dict__,
            "api": self.api.__dict__,
            "logging": self.logging.__dict__
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'CaselawConfig':
        """Create configuration from dictionary"""
        return cls(**config_dict)


class ConfigManager:
    """
    Manages configuration loading, validation, and environment variable substitution
    """
    
    def __init__(self, plugin_dir: Optional[Path] = None):
        """
        Initialize configuration manager
        
        Args:
            plugin_dir: Path to plugin directory
        """
        self.plugin_dir = plugin_dir or Path(__file__).parent.parent
        self.config_file = self.plugin_dir / "plugin.yaml"
        self.config: Optional[CaselawConfig] = None
        
    def load_config(self, config_path: Optional[Path] = None,
                   override_config: Optional[Dict[str, Any]] = None) -> CaselawConfig:
        """
        Load configuration from file and environment
        
        Args:
            config_path: Path to configuration file (optional)
            override_config: Configuration overrides (optional)
            
        Returns:
            Loaded and validated configuration
        """
        try:
            # Load from file
            file_config = self._load_config_file(config_path)
            
            # Apply environment variable overrides
            env_config = self._load_environment_config()
            
            # Merge configurations (env overrides file, override_config overrides all)
            merged_config = self._merge_configs(file_config, env_config, override_config or {})
            
            # Extract configuration section
            config_section = merged_config.get("configuration", {})
            
            # Validate and create configuration object
            self.config = CaselawConfig.from_dict(config_section)
            
            logger.info("Configuration loaded successfully")
            return self.config
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            # Return default configuration
            self.config = CaselawConfig()
            return self.config
    
    def _load_config_file(self, config_path: Optional[Path] = None) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        file_path = config_path or self.config_file
        
        if not file_path.exists():
            logger.warning(f"Configuration file not found: {file_path}")
            return {}
        
        try:
            with open(file_path, 'r') as f:
                config = yaml.safe_load(f)
            return config or {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML configuration: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error reading configuration file: {e}")
            return {}
    
    def _load_environment_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        env_config = {}
        
        # Define environment variable mappings
        env_mappings = {
            # Storage
            "CASELAW_STORAGE_USE_MOCK": ("storage", "use_mock", bool),
            "CASELAW_NEO4J_ENABLED": ("storage", "neo4j_enabled", bool),
            "CASELAW_NEO4J_URI": ("storage", "neo4j_uri", str),
            "CASELAW_NEO4J_USER": ("storage", "neo4j_user", str),
            "CASELAW_NEO4J_PASSWORD": ("storage", "neo4j_password", str),
            "CASELAW_REDIS_ENABLED": ("storage", "redis_enabled", bool),
            "CASELAW_REDIS_URL": ("storage", "redis_url", str),
            "CASELAW_ELASTICSEARCH_ENABLED": ("storage", "elasticsearch_enabled", bool),
            
            # Ingestion
            "CASELAW_AUTO_START_INGESTION": ("ingestion", "auto_start_ingestion", bool),
            "CASELAW_BACKGROUND_INGESTION": ("ingestion", "enable_background_ingestion", bool),
            "CASELAW_BATCH_SIZE": ("ingestion", "ingestion_batch_size", int),
            "CASELAW_MAX_WORKERS": ("ingestion", "ingestion_max_workers", int),
            "CASELAW_DATASET_NAME": ("ingestion", "dataset_name", str),
            
            # Extraction
            "CASELAW_ML_EXTRACTION": ("extraction", "enable_ml_citation_extraction", bool),
            "CASELAW_CITATION_THRESHOLD": ("extraction", "citation_confidence_threshold", float),
            "CASELAW_RELATIONSHIP_THRESHOLD": ("extraction", "relationship_confidence_threshold", float),
            
            # Reasoning
            "CASELAW_TEMPORAL_ANALYSIS": ("reasoning", "temporal_analysis_enabled", bool),
            "CASELAW_JURISDICTIONAL_ANALYSIS": ("reasoning", "jurisdictional_analysis_enabled", bool),
            "CASELAW_PRECEDENT_THRESHOLD": ("reasoning", "precedent_strength_threshold", float),
            
            # API
            "CASELAW_QUERY_API": ("api", "enable_query_api", bool),
            "CASELAW_PROVENANCE_API": ("api", "enable_provenance_api", bool),
            "CASELAW_MAX_RESULTS": ("api", "max_search_results", int),
            "CASELAW_QUERY_TIMEOUT": ("api", "query_timeout", int),
            
            # Logging
            "CASELAW_LOG_LEVEL": ("logging", "log_level", str),
            "CASELAW_PERFORMANCE_LOGGING": ("logging", "enable_performance_logging", bool),
            "CASELAW_AUDIT_LOGGING": ("logging", "enable_audit_logging", bool),
        }
        
        for env_var, (section, key, value_type) in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                try:
                    # Convert value to appropriate type
                    if value_type == bool:
                        converted_value = env_value.lower() in ('true', '1', 'yes', 'on')
                    elif value_type == int:
                        converted_value = int(env_value)
                    elif value_type == float:
                        converted_value = float(env_value)
                    else:
                        converted_value = env_value
                    
                    # Set in configuration
                    if section not in env_config:
                        env_config[section] = {}
                    env_config[section][key] = converted_value
                    
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid environment variable value {env_var}={env_value}: {e}")
        
        return {"configuration": env_config} if env_config else {}
    
    def _merge_configs(self, file_config: Dict[str, Any], 
                      env_config: Dict[str, Any], 
                      override_config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge multiple configuration sources"""
        result = file_config.copy()
        
        # Merge environment config
        self._deep_merge(result, env_config)
        
        # Merge override config
        if override_config:
            override_wrapped = {"configuration": override_config}
            self._deep_merge(result, override_wrapped)
        
        return result
    
    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]):
        """Deep merge two dictionaries"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def get_config(self) -> CaselawConfig:
        """Get current configuration"""
        if self.config is None:
            return self.load_config()
        return self.config
    
    def reload_config(self, config_path: Optional[Path] = None,
                     override_config: Optional[Dict[str, Any]] = None) -> CaselawConfig:
        """Reload configuration"""
        return self.load_config(config_path, override_config)
    
    def validate_config(self, config: Optional[CaselawConfig] = None) -> bool:
        """Validate configuration"""
        config_to_validate = config or self.config
        
        if config_to_validate is None:
            logger.error("No configuration to validate")
            return False
        
        try:
            # Pydantic validation happens during creation
            # Additional custom validation can be added here
            
            # Validate storage dependencies
            if config_to_validate.storage.neo4j_enabled and not config_to_validate.storage.neo4j_password:
                logger.warning("Neo4j enabled but no password provided")
            
            # Validate ingestion settings
            if config_to_validate.ingestion.ingestion_batch_size <= 0:
                logger.error("Ingestion batch size must be positive")
                return False
            
            if config_to_validate.ingestion.ingestion_max_workers <= 0:
                logger.error("Ingestion max workers must be positive")
                return False
            
            # Validate confidence thresholds
            if not (0.0 <= config_to_validate.extraction.citation_confidence_threshold <= 1.0):
                logger.error("Citation confidence threshold must be between 0.0 and 1.0")
                return False
            
            if not (0.0 <= config_to_validate.reasoning.precedent_strength_threshold <= 1.0):
                logger.error("Precedent strength threshold must be between 0.0 and 1.0")
                return False
            
            logger.info("Configuration validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False
    
    def save_config(self, config: CaselawConfig, output_path: Optional[Path] = None):
        """Save configuration to file"""
        output_file = output_path or (self.plugin_dir / "config_output.yaml")
        
        try:
            config_dict = {"configuration": config.to_dict()}
            
            with open(output_file, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False, indent=2)
            
            logger.info(f"Configuration saved to {output_file}")
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise
    
    def get_environment_template(self) -> str:
        """Generate environment variable template"""
        template = """
# CAP Caselaw Plugin Environment Variables

# Storage Configuration
CASELAW_STORAGE_USE_MOCK=false
CASELAW_NEO4J_ENABLED=true
CASELAW_NEO4J_URI=bolt://localhost:7687
CASELAW_NEO4J_USER=neo4j
CASELAW_NEO4J_PASSWORD=your_password_here
CASELAW_REDIS_ENABLED=true
CASELAW_REDIS_URL=redis://localhost:6379
CASELAW_ELASTICSEARCH_ENABLED=true

# Ingestion Configuration
CASELAW_AUTO_START_INGESTION=false
CASELAW_BACKGROUND_INGESTION=true
CASELAW_BATCH_SIZE=1000
CASELAW_MAX_WORKERS=10
CASELAW_DATASET_NAME=harvard-lil/cap-us-court-opinions

# Extraction Configuration
CASELAW_ML_EXTRACTION=true
CASELAW_CITATION_THRESHOLD=0.7
CASELAW_RELATIONSHIP_THRESHOLD=0.6

# Reasoning Configuration
CASELAW_TEMPORAL_ANALYSIS=true
CASELAW_JURISDICTIONAL_ANALYSIS=true
CASELAW_PRECEDENT_THRESHOLD=0.5

# API Configuration
CASELAW_QUERY_API=true
CASELAW_PROVENANCE_API=true
CASELAW_MAX_RESULTS=100
CASELAW_QUERY_TIMEOUT=30

# Logging Configuration
CASELAW_LOG_LEVEL=INFO
CASELAW_PERFORMANCE_LOGGING=false
CASELAW_AUDIT_LOGGING=true
"""
        return template.strip()