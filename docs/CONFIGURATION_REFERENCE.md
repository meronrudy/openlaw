# Configuration Reference

Complete configuration options for the OpenLaw Legal Hypergraph System.

## Table of Contents

- [Overview](#overview)
- [Environment Variables](#environment-variables)
- [Configuration Files](#configuration-files)
- [Storage Configuration](#storage-configuration)
- [Plugin Configuration](#plugin-configuration)
- [Logging Configuration](#logging-configuration)
- [Performance Tuning](#performance-tuning)
- [Security Settings](#security-settings)
- [Development Settings](#development-settings)

## Overview

The OpenLaw system uses a combination of:
- **Environment variables** for runtime configuration
- **Configuration files** for complex settings (optional)
- **Reasonable defaults** for minimal setup requirements

### Configuration Priority

1. Environment variables (highest priority)
2. Configuration files
3. Default values (lowest priority)

## Native Legal Configuration (quick reference)

- Courts and clause weights (+ optional hierarchy/overrides): [config/courts.yaml](config/courts.yaml:1)
- Authority multipliers (recency, jurisdiction alignment, court levels, treatment modifiers): [config/precedent_weights.yaml](config/precedent_weights.yaml:1)
- Statutory interpretation preferences (styles: textualism, purposivism, lenity): [config/statutory_prefs.yaml](config/statutory_prefs.yaml:1)
- Export redaction rules (labels_blocklist etc.): [config/compliance/redaction_rules.yml](config/compliance/redaction_rules.yml:1)

Validation and strict mode
- The native adapter validates these configs on startup; enable fail-fast by passing strict_mode=True to [NativeLegalBridge.__init__()](core/adapters/native_bridge.py:55)
  - Courts validator: [_validate_courts_cfg()](core/adapters/native_bridge.py:127)
  - Precedent weights validator: [_validate_precedent_cfg()](core/adapters/native_bridge.py:158)
  - Statutory prefs validator: [_validate_statutory_prefs_cfg()](core/adapters/native_bridge.py:181)

How the configuration is used
- Clause-class weights (controlling/persuasive/contrary) are selected and tuned in [build_rules_for_claim_native()](core/rules_native/native_legal_builder.py:373)
- Authority multipliers are computed from graph metadata and [precedent_weights.yaml](config/precedent_weights.yaml:1) in [_compute_authority_multipliers()](core/adapters/native_bridge.py:325) and applied to the top-level support rule in [build_rules_for_claim()](core/adapters/native_bridge.py:450)
- Exports respect privacy profiles and redaction policies via [Interpretation.export()](core/native/interpretation.py:127) and [export_interpretation()](core/adapters/native_bridge.py:536)

## Environment Variables

### Core System

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `OPENLAW_ENV` | string | `development` | Environment mode: `development`, `production`, `testing` |
| `OPENLAW_LOG_LEVEL` | string | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `OPENLAW_CONFIG_PATH` | string | `None` | Path to configuration file |
| `OPENLAW_DATA_DIR` | string | `./data` | Data directory for storage |
| `PYTHONPATH` | string | `None` | Python path (add project root) |

**Example:**
```bash
export OPENLAW_ENV=production
export OPENLAW_LOG_LEVEL=WARNING
export OPENLAW_DATA_DIR=/var/lib/openlaw
```

### Storage Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `OPENLAW_STORAGE_TYPE` | string | `sqlite` | Storage backend: `sqlite`, `memory`, `postgresql` |
| `OPENLAW_STORAGE_PATH` | string | `:memory:` | SQLite database path |
| `OPENLAW_STORAGE_URL` | string | `None` | Database connection URL |
| `OPENLAW_CACHE_ENABLED` | boolean | `true` | Enable in-memory caching |
| `OPENLAW_CACHE_SIZE` | integer | `1000` | Maximum cache entries |

**Examples:**

```bash
# In-memory storage (development)
export OPENLAW_STORAGE_TYPE=memory

# File-based SQLite (production)
export OPENLAW_STORAGE_TYPE=sqlite
export OPENLAW_STORAGE_PATH=/var/lib/openlaw/openlaw.db

# PostgreSQL (enterprise)
export OPENLAW_STORAGE_TYPE=postgresql
export OPENLAW_STORAGE_URL=postgresql://user:pass@localhost:5432/openlaw
```

### Plugin Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `OPENLAW_PLUGINS_DIR` | string | `./plugins` | Plugin directory path |
| `OPENLAW_PLUGIN_TIMEOUT` | integer | `30` | Plugin operation timeout (seconds) |
| `OPENLAW_SKIP_NLP` | boolean | `false` | Skip NLP components (for testing) |
| `OPENLAW_EMPLOYMENT_LAW_ENABLED` | boolean | `true` | Enable employment law plugin |
| `OPENLAW_CASELAW_ENABLED` | boolean | `false` | Enable caselaw plugin |

### Analysis Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `OPENLAW_MAX_DOCUMENT_SIZE` | integer | `1048576` | Maximum document size (bytes) |
| `OPENLAW_ANALYSIS_TIMEOUT` | integer | `60` | Analysis timeout (seconds) |
| `OPENLAW_CONFIDENCE_THRESHOLD` | float | `0.7` | Minimum confidence for conclusions |
| `OPENLAW_MAX_ENTITIES` | integer | `1000` | Maximum entities per document |

## Configuration Files

### YAML Configuration

Create a YAML configuration file for complex settings:

```yaml
# config/production.yaml
environment: production

logging:
  level: WARNING
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "/var/log/openlaw/app.log"
  rotation:
    enabled: true
    max_size: "100MB"
    backup_count: 5

storage:
  type: sqlite
  path: "/var/lib/openlaw/openlaw.db"
  cache:
    enabled: true
    size: 5000
    ttl: 3600
  
  # PostgreSQL configuration (alternative)
  # type: postgresql
  # url: "postgresql://openlaw:password@localhost:5432/openlaw"
  # pool_size: 20
  # max_overflow: 30

plugins:
  directory: "/opt/openlaw/plugins"
  timeout: 30
  
  employment_law:
    enabled: true
    confidence_threshold: 0.8
    rules:
      ada_enabled: true
      flsa_enabled: true
      at_will_enabled: true
      workers_comp_enabled: true
  
  caselaw:
    enabled: false  # Disabled in production until stable
    # hf_cache_dir: "/var/cache/openlaw/hf"
    # max_documents: 10000

analysis:
  max_document_size: 2097152  # 2MB
  timeout: 120
  confidence_threshold: 0.75
  
  nlp:
    model_cache_dir: "/var/cache/openlaw/models"
    max_memory_usage: "2GB"
    device: "cpu"  # or "cuda" for GPU

security:
  input_validation: true
  sanitize_output: true
  rate_limiting:
    enabled: true
    requests_per_minute: 100
  
performance:
  max_concurrent_analyses: 4
  worker_processes: 2
  memory_limit: "4GB"
```

### Loading Configuration

```python
import yaml
import os

def load_config():
    config_path = os.getenv('OPENLAW_CONFIG_PATH')
    if config_path and os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    return {}

# Usage
config = load_config()
log_level = config.get('logging', {}).get('level', 'INFO')
```

## Storage Configuration

### SQLite Configuration

**Development (In-Memory):**
```bash
export OPENLAW_STORAGE_TYPE=memory
```

**Production (File-Based):**
```bash
export OPENLAW_STORAGE_TYPE=sqlite
export OPENLAW_STORAGE_PATH=/var/lib/openlaw/openlaw.db
```

**Performance Tuning:**
```python
# SQLite optimizations in code
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = -64000;  # 64MB cache
PRAGMA temp_store = memory;
```

### PostgreSQL Configuration

**Environment Variables:**
```bash
export OPENLAW_STORAGE_TYPE=postgresql
export OPENLAW_STORAGE_URL=postgresql://user:pass@host:5432/openlaw
```

**Connection Pool Settings:**
```yaml
storage:
  type: postgresql
  url: "postgresql://openlaw:password@localhost:5432/openlaw"
  pool_size: 20
  max_overflow: 30
  pool_timeout: 30
  pool_recycle: 3600
```

### Cache Configuration

```bash
# Enable caching
export OPENLAW_CACHE_ENABLED=true
export OPENLAW_CACHE_SIZE=5000

# Cache TTL (time-to-live) in seconds
export OPENLAW_CACHE_TTL=3600
```

## Plugin Configuration

### Employment Law Plugin

```yaml
plugins:
  employment_law:
    enabled: true
    confidence_threshold: 0.8
    
    rules:
      ada_enabled: true
      flsa_enabled: true
      at_will_enabled: true
      workers_comp_enabled: true
    
    nlp:
      model_name: "distilbert-base-uncased"
      max_sequence_length: 512
      batch_size: 16
```

### Caselaw Plugin (When Enabled)

```yaml
plugins:
  caselaw:
    enabled: false  # Currently disabled
    
    # Future configuration options:
    # huggingface:
    #   dataset: "harvard-lil/cap"
    #   cache_dir: "/var/cache/openlaw/hf"
    #   max_documents: 50000
    # 
    # storage:
    #   neo4j_url: "neo4j://localhost:7687"
    #   redis_url: "redis://localhost:6379"
    #   elasticsearch_url: "http://localhost:9200"
```

### Custom Plugin Configuration

```python
# plugins/custom_domain/config.py
DEFAULT_CONFIG = {
    "enabled": True,
    "confidence_threshold": 0.75,
    "custom_setting": "default_value"
}

def get_plugin_config():
    """Get plugin configuration from environment and files"""
    config = DEFAULT_CONFIG.copy()
    
    # Override from environment
    config["enabled"] = os.getenv("OPENLAW_CUSTOM_DOMAIN_ENABLED", "true").lower() == "true"
    config["confidence_threshold"] = float(os.getenv("OPENLAW_CUSTOM_DOMAIN_CONFIDENCE", "0.75"))
    
    return config
```

## Logging Configuration

### Basic Logging

```bash
# Set log level
export OPENLAW_LOG_LEVEL=DEBUG

# Enable file logging
export OPENLAW_LOG_FILE=/var/log/openlaw/app.log
```

### Advanced Logging

```yaml
logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  
  handlers:
    console:
      enabled: true
      level: INFO
    
    file:
      enabled: true
      path: "/var/log/openlaw/app.log"
      level: DEBUG
      rotation:
        max_size: "100MB"
        backup_count: 5
    
    syslog:
      enabled: false
      facility: "local0"
      address: "localhost:514"

  loggers:
    "core.reasoning":
      level: DEBUG
    "plugins.employment_law":
      level: INFO
    "plugins.caselaw":
      level: WARNING
```

### Python Logging Setup

```python
import logging
import logging.handlers
import os

def setup_logging():
    """Configure logging based on environment"""
    log_level = os.getenv('OPENLAW_LOG_LEVEL', 'INFO').upper()
    log_file = os.getenv('OPENLAW_LOG_FILE')
    
    # Create logger
    logger = logging.getLogger('openlaw')
    logger.setLevel(getattr(logging, log_level))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level))
    
    # File handler (if specified)
    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=100*1024*1024, backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger
```

## Performance Tuning

### Memory Configuration

```bash
# Memory limits
export OPENLAW_MAX_MEMORY=4G
export OPENLAW_CACHE_SIZE=1000

# Document processing limits
export OPENLAW_MAX_DOCUMENT_SIZE=2097152  # 2MB
export OPENLAW_MAX_ENTITIES=2000
```

### Concurrency Configuration

```bash
# Analysis concurrency
export OPENLAW_MAX_CONCURRENT_ANALYSES=4
export OPENLAW_WORKER_PROCESSES=2

# Plugin timeouts
export OPENLAW_PLUGIN_TIMEOUT=60
export OPENLAW_ANALYSIS_TIMEOUT=120
```

### NLP Performance

```yaml
analysis:
  nlp:
    device: "cpu"  # or "cuda" for GPU
    model_cache_dir: "/var/cache/openlaw/models"
    max_memory_usage: "2GB"
    batch_size: 16
    max_sequence_length: 512
    
    # Model-specific settings
    transformers:
      use_fast_tokenizer: true
      return_tensors: "pt"
      padding: true
      truncation: true
```

## Security Settings

### Input Validation

```bash
# Enable input validation
export OPENLAW_INPUT_VALIDATION=true
export OPENLAW_SANITIZE_OUTPUT=true

# File upload limits
export OPENLAW_MAX_FILE_SIZE=10485760  # 10MB
export OPENLAW_ALLOWED_EXTENSIONS=".txt,.pdf,.docx"
```

### Rate Limiting

```yaml
security:
  rate_limiting:
    enabled: true
    requests_per_minute: 100
    burst_limit: 10
    
  input_validation:
    max_document_size: 10485760  # 10MB
    allowed_file_types: ["txt", "pdf", "docx"]
    scan_for_malware: false
    
  output_sanitization:
    enabled: true
    remove_sensitive_data: true
    anonymize_entities: false
```

## Development Settings

### Development Environment

```bash
# Development mode
export OPENLAW_ENV=development
export OPENLAW_LOG_LEVEL=DEBUG
export OPENLAW_STORAGE_TYPE=memory

# Skip time-consuming operations
export OPENLAW_SKIP_NLP=false
export OPENLAW_MOCK_EXTERNAL_APIS=true

# Development server
export OPENLAW_DEBUG_MODE=true
export OPENLAW_AUTO_RELOAD=true
```

### Testing Configuration

```bash
# Testing environment
export OPENLAW_ENV=testing
export OPENLAW_STORAGE_TYPE=memory
export OPENLAW_LOG_LEVEL=WARNING

# Test-specific settings
export OPENLAW_SKIP_SLOW_TESTS=false
export OPENLAW_MOCK_PLUGINS=false
export OPENLAW_TEST_DATA_DIR=./tests/data
```

### Docker Configuration

```yaml
# docker-compose.yml environment
version: '3.8'
services:
  openlaw:
    image: openlaw:latest
    environment:
      - OPENLAW_ENV=production
      - OPENLAW_STORAGE_TYPE=postgresql
      - OPENLAW_STORAGE_URL=postgresql://openlaw:password@db:5432/openlaw
      - OPENLAW_LOG_LEVEL=INFO
      - OPENLAW_CACHE_ENABLED=true
    volumes:
      - ./data:/var/lib/openlaw
      - ./logs:/var/log/openlaw
    depends_on:
      - db
      
  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=openlaw
      - POSTGRES_USER=openlaw
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## Configuration Validation

### Environment Validation Script

```python
#!/usr/bin/env python3
"""Validate OpenLaw configuration"""

import os
import sys
from pathlib import Path

def validate_config():
    """Validate current configuration"""
    errors = []
    warnings = []
    
    # Check required environment
    env = os.getenv('OPENLAW_ENV', 'development')
    if env not in ['development', 'production', 'testing']:
        errors.append(f"Invalid OPENLAW_ENV: {env}")
    
    # Check storage configuration
    storage_type = os.getenv('OPENLAW_STORAGE_TYPE', 'sqlite')
    if storage_type == 'sqlite':
        storage_path = os.getenv('OPENLAW_STORAGE_PATH', ':memory:')
        if storage_path != ':memory:':
            storage_dir = Path(storage_path).parent
            if not storage_dir.exists():
                warnings.append(f"Storage directory does not exist: {storage_dir}")
    
    # Check data directory
    data_dir = Path(os.getenv('OPENLAW_DATA_DIR', './data'))
    if not data_dir.exists():
        warnings.append(f"Data directory does not exist: {data_dir}")
    
    # Check plugin directory
    plugins_dir = Path(os.getenv('OPENLAW_PLUGINS_DIR', './plugins'))
    if not plugins_dir.exists():
        errors.append(f"Plugins directory does not exist: {plugins_dir}")
    
    # Print results
    if errors:
        print("❌ Configuration errors:")
        for error in errors:
            print(f"  - {error}")
    
    if warnings:
        print("⚠️  Configuration warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    
    if not errors and not warnings:
        print("✅ Configuration is valid")
    
    return len(errors) == 0

if __name__ == "__main__":
    if not validate_config():
        sys.exit(1)
```

**Usage:**
```bash
python3 scripts/validate_config.py
```

## Quick Configuration Examples

### Minimal Development Setup

```bash
# Minimal development environment
export OPENLAW_ENV=development
export OPENLAW_STORAGE_TYPE=memory
python3 cli_driver.py demo --domain employment_law
```

### Production Setup

```bash
# Production environment
export OPENLAW_ENV=production
export OPENLAW_LOG_LEVEL=WARNING
export OPENLAW_STORAGE_TYPE=sqlite
export OPENLAW_STORAGE_PATH=/var/lib/openlaw/openlaw.db
export OPENLAW_DATA_DIR=/var/lib/openlaw
export OPENLAW_LOG_FILE=/var/log/openlaw/app.log

# Ensure directories exist
mkdir -p /var/lib/openlaw /var/log/openlaw

# Run application
python3 cli_driver.py analyze --file document.txt
```

### Docker Development

```bash
# Use Docker for development
docker run -it \
  -e OPENLAW_ENV=development \
  -e OPENLAW_STORAGE_TYPE=memory \
  -v $(pwd):/app \
  openlaw:dev \
  python3 cli_driver.py demo --domain employment_law
```

## Troubleshooting Configuration

### Common Issues

1. **Storage Path Not Accessible**
   ```bash
   # Check permissions
   ls -la /var/lib/openlaw/
   
   # Fix permissions
   sudo chown -R openlaw:openlaw /var/lib/openlaw/
   ```

2. **Plugin Loading Errors**
   ```bash
   # Check plugin directory
   export OPENLAW_LOG_LEVEL=DEBUG
   python3 -c "import plugins.employment_law.plugin"
   ```

3. **Memory Issues**
   ```bash
   # Reduce memory usage
   export OPENLAW_CACHE_SIZE=100
   export OPENLAW_MAX_ENTITIES=500
   ```

4. **Performance Issues**
   ```bash
   # Enable performance monitoring
   export OPENLAW_LOG_LEVEL=DEBUG
   export OPENLAW_PROFILE_ENABLED=true
   ```

See [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) for detailed troubleshooting guidance.