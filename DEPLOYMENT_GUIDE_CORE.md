# OpenLaw Legal Hypergraph System - Complete Deployment Guide

## Overview

Comprehensive deployment guide for the OpenLaw legal hypergraph system. This guide covers development, staging, and production deployments with the employment law plugin. The caselaw plugin is currently held for future release.

## Table of Contents

- [System Requirements](#system-requirements)
- [Quick Start](#quick-start)
- [Development Deployment](#development-deployment)
- [Production Deployment](#production-deployment)
- [Docker Deployment](#docker-deployment)
- [Environment Configuration](#environment-configuration)
- [Performance Tuning](#performance-tuning)
- [Monitoring & Maintenance](#monitoring--maintenance)
- [Security Considerations](#security-considerations)
- [Troubleshooting](#troubleshooting)

## System Requirements

### Minimum Requirements

| Component | Specification |
|-----------|---------------|
| **Python** | 3.9+ (3.11 recommended) |
| **Memory** | 4GB RAM |
| **Storage** | 2GB available space |
| **CPU** | 2 cores |
| **OS** | Linux, macOS, Windows |

### Recommended Production

| Component | Specification |
|-----------|---------------|
| **Python** | 3.11+ |
| **Memory** | 8-16GB RAM |
| **Storage** | 50GB+ SSD |
| **CPU** | 4-8 cores |
| **OS** | Ubuntu 20.04+ or RHEL 8+ |

### Dependencies

**Core System:**
- pydantic>=2.0.0
- sqlitedict>=2.1.0
- pyyaml>=6.0
- click>=8.0.0
- python-dateutil>=2.8.0

**NLP Components:**
- transformers>=4.21.0
- torch>=1.12.0
- spacy>=3.4.0
- scikit-learn>=1.1.0

## Quick Start

### Automated Installation

```bash
# One-command setup with automated script
git clone <repository-url>
cd openlaw
./setup.sh

# Activate environment and start
source openlaw-env/bin/activate
python3 cli_driver.py demo --domain employment_law
```

### Manual Installation

```bash
# 1. Create virtual environment
python3 -m venv openlaw-env

# 2. Activate virtual environment
# Linux/Mac:
source openlaw-env/bin/activate
# Windows (Command Prompt):
# openlaw-env\Scripts\activate.bat
# Windows (PowerShell):
# openlaw-env\Scripts\Activate.ps1

# 3. Upgrade pip and install dependencies
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# 4. Verify installation
python3 -c "import plugins.employment_law.plugin; print('✅ System ready')"

# 5. Test functionality
python3 cli_driver.py demo --domain employment_law
```

## Development Deployment

### Local Development Setup

```bash
# Clone repository
git clone <repository-url>
cd openlaw

# Create development environment
python3 -m venv openlaw-dev
source openlaw-dev/bin/activate

# Install with development dependencies
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install -e ".[dev,test]"

# Set development environment variables
export OPENLAW_ENV=development
export OPENLAW_LOG_LEVEL=DEBUG
export OPENLAW_STORAGE_TYPE=memory

# Run tests
pytest tests/ -v

# Format code
black .
isort .

# Start development
python3 cli_driver.py demo --domain employment_law
```

### Development Configuration

```bash
# .env file for development
cat > .env << 'EOF'
OPENLAW_ENV=development
OPENLAW_LOG_LEVEL=DEBUG
OPENLAW_STORAGE_TYPE=memory
OPENLAW_CACHE_ENABLED=true
OPENLAW_SKIP_NLP=false
PYTHONPATH=.
EOF

# Load environment
set -a; source .env; set +a
```

### VS Code Setup

```json
// .vscode/settings.json
{
    "python.defaultInterpreterPath": "./openlaw-env/bin/python",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/"],
    "python.formatting.provider": "black",
    "python.sortImports.args": ["--profile", "black"],
    "editor.formatOnSave": true,
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true
}
```

## Production Deployment

### System Preparation

```bash
# Ubuntu/Debian production server setup
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
sudo apt install python3.11 python3.11-venv python3.11-dev python3-pip

# Install system dependencies
sudo apt install build-essential git curl

# Create system user
sudo useradd -m -s /bin/bash openlaw
sudo mkdir -p /opt/openlaw /var/log/openlaw /var/lib/openlaw
sudo chown -R openlaw:openlaw /opt/openlaw /var/log/openlaw /var/lib/openlaw
```

### Production Installation

```bash
# Switch to openlaw user
sudo su - openlaw

# Clone and setup
cd /opt/openlaw
git clone <repository-url> .

# Create production environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# Set production configuration
cat > /opt/openlaw/.env << 'EOF'
OPENLAW_ENV=production
OPENLAW_LOG_LEVEL=WARNING
OPENLAW_STORAGE_TYPE=sqlite
OPENLAW_STORAGE_PATH=/var/lib/openlaw/openlaw.db
OPENLAW_DATA_DIR=/var/lib/openlaw
OPENLAW_LOG_FILE=/var/log/openlaw/app.log
OPENLAW_CACHE_ENABLED=true
OPENLAW_CACHE_SIZE=5000
EOF

# Test installation
source .env
python3 cli_driver.py --help
python3 -c "import plugins.employment_law.plugin; print('✅ Production installation complete')"
```

### Systemd Service

```bash
# Create systemd service file
sudo tee /etc/systemd/system/openlaw.service << 'EOF'
[Unit]
Description=OpenLaw Legal Hypergraph System
After=network.target

[Service]
Type=simple
User=openlaw
Group=openlaw
WorkingDirectory=/opt/openlaw
Environment=PATH=/opt/openlaw/venv/bin
EnvironmentFile=/opt/openlaw/.env
ExecStart=/opt/openlaw/venv/bin/python3 cli_driver.py demo --domain employment_law
Restart=always
RestartSec=10

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/openlaw /var/log/openlaw

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable openlaw
sudo systemctl start openlaw
sudo systemctl status openlaw
```

### Nginx Configuration (Optional)

```nginx
# /etc/nginx/sites-available/openlaw
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Static files
    location /static/ {
        alias /opt/openlaw/static/;
        expires 30d;
    }
    
    # Logs
    access_log /var/log/nginx/openlaw_access.log;
    error_log /var/log/nginx/openlaw_error.log;
}
```

## Docker Deployment

### Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OPENLAW_ENV=production

# Create app user
RUN groupadd -r openlaw && useradd -r -g openlaw openlaw

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create directories
RUN mkdir -p /app /var/log/openlaw /var/lib/openlaw
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Change ownership
RUN chown -R openlaw:openlaw /app /var/log/openlaw /var/lib/openlaw

# Switch to app user
USER openlaw

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import plugins.employment_law.plugin" || exit 1

# Default command
CMD ["python3", "cli_driver.py", "demo", "--domain", "employment_law"]
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  openlaw:
    build: .
    container_name: openlaw-app
    restart: unless-stopped
    environment:
      - OPENLAW_ENV=production
      - OPENLAW_LOG_LEVEL=INFO
      - OPENLAW_STORAGE_TYPE=sqlite
      - OPENLAW_STORAGE_PATH=/var/lib/openlaw/openlaw.db
      - OPENLAW_CACHE_ENABLED=true
    volumes:
      - openlaw_data:/var/lib/openlaw
      - openlaw_logs:/var/log/openlaw
      - ./documents:/app/documents:ro
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "python3", "-c", "import plugins.employment_law.plugin"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Optional: Database for future expansion
  # postgres:
  #   image: postgres:13
  #   container_name: openlaw-db
  #   restart: unless-stopped
  #   environment:
  #     POSTGRES_DB: openlaw
  #     POSTGRES_USER: openlaw
  #     POSTGRES_PASSWORD: ${DB_PASSWORD}
  #   volumes:
  #     - postgres_data:/var/lib/postgresql/data

volumes:
  openlaw_data:
  openlaw_logs:
  # postgres_data:

networks:
  default:
    name: openlaw-network
```

### Docker Deployment Commands

```bash
# Build and run with Docker Compose
git clone <repository-url>
cd openlaw

# Production deployment
docker-compose up -d

# View logs
docker-compose logs -f openlaw

# Scale services (future)
docker-compose up -d --scale openlaw=3

# Backup data
docker run --rm -v openlaw_openlaw_data:/source -v $(pwd):/backup \
  alpine tar czf /backup/openlaw-backup-$(date +%Y%m%d).tar.gz -C /source .
```

## Environment Configuration

### Production Environment Variables

```bash
# Core configuration
export OPENLAW_ENV=production
export OPENLAW_LOG_LEVEL=WARNING
export OPENLAW_DATA_DIR=/var/lib/openlaw

# Storage configuration
export OPENLAW_STORAGE_TYPE=sqlite
export OPENLAW_STORAGE_PATH=/var/lib/openlaw/openlaw.db

# Performance configuration
export OPENLAW_CACHE_ENABLED=true
export OPENLAW_CACHE_SIZE=5000
export OPENLAW_MAX_CONCURRENT_ANALYSES=4

# Security configuration
export OPENLAW_INPUT_VALIDATION=true
export OPENLAW_SANITIZE_OUTPUT=true
```

### Configuration File Template

```yaml
# config/production.yaml
environment: production

logging:
  level: WARNING
  file: "/var/log/openlaw/app.log"
  rotation:
    max_size: "100MB"
    backup_count: 5

storage:
  type: sqlite
  path: "/var/lib/openlaw/openlaw.db"
  cache:
    enabled: true
    size: 5000

plugins:
  employment_law:
    enabled: true
    confidence_threshold: 0.8

analysis:
  max_document_size: 2097152  # 2MB
  timeout: 120
  confidence_threshold: 0.75

performance:
  max_concurrent_analyses: 4
  memory_limit: "4GB"

security:
  input_validation: true
  sanitize_output: true
```

## Performance Tuning

### Memory Optimization

```bash
# Memory-efficient configuration
export OPENLAW_CACHE_SIZE=1000
export OPENLAW_MAX_ENTITIES=1000
export OPENLAW_NLP_BATCH_SIZE=8

# For low-memory systems
export OPENLAW_STORAGE_TYPE=memory  # For testing only
export OPENLAW_SKIP_NLP=true       # Disable NLP temporarily
```

### CPU Optimization

```bash
# Multi-core processing
export OPENLAW_MAX_CONCURRENT_ANALYSES=4
export OPENLAW_WORKER_PROCESSES=2

# Analysis timeouts
export OPENLAW_ANALYSIS_TIMEOUT=60
export OPENLAW_PLUGIN_TIMEOUT=30
```

### Storage Optimization

```bash
# SQLite performance tuning
export OPENLAW_SQLITE_CACHE_SIZE=64000  # 64MB
export OPENLAW_SQLITE_JOURNAL_MODE=WAL
export OPENLAW_SQLITE_SYNCHRONOUS=NORMAL
```

## Monitoring & Maintenance

### Log Management

```bash
# Log rotation setup
sudo tee /etc/logrotate.d/openlaw << 'EOF'
/var/log/openlaw/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 openlaw openlaw
    postrotate
        systemctl reload openlaw
    endscript
}
EOF
```

### Health Checks

```bash
#!/bin/bash
# health_check.sh
set -e

echo "=== OpenLaw Health Check ==="

# Check service status
if systemctl is-active --quiet openlaw; then
    echo "✅ Service running"
else
    echo "❌ Service not running"
    exit 1
fi

# Check plugin loading
if python3 -c "import plugins.employment_law.plugin" 2>/dev/null; then
    echo "✅ Plugin loading"
else
    echo "❌ Plugin loading failed"
    exit 1
fi

# Check storage
if [ -f "/var/lib/openlaw/openlaw.db" ]; then
    echo "✅ Database accessible"
else
    echo "⚠️ Database file not found"
fi

# Check disk space
DISK_USAGE=$(df /var/lib/openlaw | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -lt 90 ]; then
    echo "✅ Disk usage: ${DISK_USAGE}%"
else
    echo "⚠️ High disk usage: ${DISK_USAGE}%"
fi

echo "Health check complete"
```

### Backup Strategy

```bash
#!/bin/bash
# backup.sh
BACKUP_DIR="/opt/backups/openlaw"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Backup database
cp /var/lib/openlaw/openlaw.db "$BACKUP_DIR/openlaw_${DATE}.db"

# Backup configuration
tar czf "$BACKUP_DIR/config_${DATE}.tar.gz" -C /opt/openlaw .env config/

# Backup logs (last 7 days)
find /var/log/openlaw -name "*.log" -mtime -7 -exec cp {} "$BACKUP_DIR/" \;

# Cleanup old backups (keep 30 days)
find "$BACKUP_DIR" -name "*.db" -mtime +30 -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR"
```

## Security Considerations

### File Permissions

```bash
# Set secure file permissions
sudo chmod 755 /opt/openlaw
sudo chmod 640 /opt/openlaw/.env
sudo chmod 644 /opt/openlaw/requirements.txt
sudo chmod 755 /opt/openlaw/cli_driver.py

# Database security
sudo chmod 600 /var/lib/openlaw/openlaw.db
sudo chown openlaw:openlaw /var/lib/openlaw/openlaw.db
```

### Firewall Configuration

```bash
# UFW firewall rules
sudo ufw allow ssh
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable

# For development only
# sudo ufw allow 8000/tcp
```

### Input Validation

```bash
# Enable security features
export OPENLAW_INPUT_VALIDATION=true
export OPENLAW_SANITIZE_OUTPUT=true
export OPENLAW_MAX_FILE_SIZE=10485760  # 10MB
```

## Troubleshooting

### Common Issues

1. **Service won't start:**
   ```bash
   sudo systemctl status openlaw
   sudo journalctl -u openlaw -f
   ```

2. **Permission errors:**
   ```bash
   sudo chown -R openlaw:openlaw /var/lib/openlaw /var/log/openlaw
   ```

3. **Database locked:**
   ```bash
   sudo systemctl stop openlaw
   rm -f /var/lib/openlaw/openlaw.db-lock
   sudo systemctl start openlaw
   ```

4. **Memory issues:**
   ```bash
   # Reduce cache size
   export OPENLAW_CACHE_SIZE=100
   sudo systemctl restart openlaw
   ```

### Log Analysis

```bash
# Check recent errors
sudo tail -100 /var/log/openlaw/app.log | grep ERROR

# Monitor real-time logs
sudo tail -f /var/log/openlaw/app.log

# System resource usage
htop
iotop
```

### Getting Help

- **Documentation**: [`docs/`](docs/)
- **Troubleshooting**: [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md)
- **Configuration**: [`docs/CONFIGURATION_REFERENCE.md`](docs/CONFIGURATION_REFERENCE.md)
- **Issues**: [GitHub Issues](../../issues)

## Deployment Checklist

### Pre-Deployment

- [ ] System requirements verified
- [ ] Python 3.9+ installed
- [ ] Dependencies listed and compatible
- [ ] Security considerations reviewed
- [ ] Backup strategy planned

### Development

- [ ] Virtual environment created
- [ ] Dependencies installed
- [ ] Tests passing
- [ ] Code formatted and linted
- [ ] Configuration tested

### Production

- [ ] Production server prepared
- [ ] System user created
- [ ] Application installed
- [ ] Configuration set
- [ ] Service configured
- [ ] Monitoring setup
- [ ] Backups scheduled
- [ ] Security hardened
- [ ] Health checks working

### Post-Deployment

- [ ] Functionality verified
- [ ] Performance monitored
- [ ] Logs reviewed
- [ ] Documentation updated
- [ ] Team trained

This deployment guide provides comprehensive instructions for deploying the OpenLaw system in various environments. For specific issues, consult the troubleshooting guide or contact support.

## Core Components

### Working Components ✅

1. **Employment Law Plugin**
   - NER for employment law entities
   - Rules for ADA, FLSA, at-will employment, workers' comp
   - Complete CLI integration

2. **Core System**
   - Hypergraph storage (`core/storage.py`)
   - Rule engine (`core/reasoning.py`)
   - Provenance tracking (`core/model.py`)

3. **CLI Interface**
   - Document analysis: `python3 cli_driver.py analyze --file document.txt`
   - Interactive demo: `python3 cli_driver.py demo --domain employment_law`
   - Batch processing: `python3 cli_driver.py batch --directory path/`

### On Hold Components 🔄

1. **Caselaw Plugin**
   - Currently disabled to maintain system modularity
   - Will be enabled after core system stabilization

## Directory Structure

```
openlaw/
├── requirements.txt           # Core dependencies
├── pyproject.toml            # Project configuration
├── cli_driver.py             # Main CLI interface
├── core/                     # Core hypergraph system
│   ├── __init__.py
│   ├── model.py              # Data models and provenance
│   ├── storage.py            # Graph storage
│   ├── reasoning.py          # Rule engine
│   └── rules.py              # Legal rules framework
├── sdk/                      # Plugin SDK
│   └── plugin.py             # Plugin interfaces
├── plugins/
│   ├── employment_law/       # ✅ Working plugin
│   │   ├── plugin.py         # Main plugin class
│   │   ├── ner.py           # Employment law NER
│   │   └── rules.py         # Employment law rules
│   └── caselaw/             # 🔄 On hold
└── tests/                   # Test suites
```

## Testing the System

### Employment Law Analysis

Create a test document:

```bash
# Create test document
cat > test_ada_case.txt << 'EOF'
John Smith has been employed as a software engineer for 3 years. He recently developed a visual impairment that affects his ability to read standard computer screens. John requested a larger monitor and screen reader software as reasonable accommodations. The company has 150 employees and annual revenue of $50 million. John can perform all essential job functions with these accommodations.
EOF

# Analyze the document
python3 cli_driver.py analyze --file test_ada_case.txt --format detailed
```

Expected output:
- Entity extraction (DISABILITY, REASONABLE_ACCOMMODATION)
- Legal citations detection
- ADA rule application
- Conclusion: "Employer may be required to provide reasonable accommodation"

### Interactive Demo

```bash
python3 cli_driver.py demo --domain employment_law
```

This will show:
- Available employment law rules (ADA, FLSA, at-will, workers' comp)
- Interactive document selection (if test documents exist)
- Complete analysis with legal reasoning

## Configuration

### Environment Variables

```bash
# Optional: Set custom configuration
export OPENLAW_ENV=development
export OPENLAW_LOG_LEVEL=INFO
```

### Storage Configuration

The system uses SQLite by default for simplicity:
- Database file: `:memory:` (in-memory for demos)
- Production: Can be configured to use persistent SQLite files

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure you're in the project root directory
   cd /path/to/openlaw
   
   # Verify Python path
   export PYTHONPATH=$PYTHONPATH:.
   ```

2. **Missing Dependencies**
   ```bash
   # Reinstall requirements
   pip install -r requirements.txt --force-reinstall
   ```

3. **Demo Not Working**
   ```bash
   # Check if in correct directory
   python3 -c "import plugins.employment_law.plugin; print('✅ Employment law plugin loaded')"
   ```

### Dependency Issues

If you encounter issues with PyTorch or transformers:

```bash
# Install CPU-only PyTorch (lighter)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Alternative: Skip NLP features temporarily
export OPENLAW_SKIP_NLP=true
```

## Production Considerations

### Performance

- SQLite storage suitable for < 10k documents
- In-memory analysis good for < 1MB documents
- For larger deployments, consider PostgreSQL backend

### Security

- Input validation enabled by default
- No external network calls in core system
- All ML models run locally

### Monitoring

Basic logging available:
```python
import logging
logging.basicConfig(level=logging.INFO)
```

## Next Steps

1. **Test Core System**: Verify employment law plugin works completely
2. **Create Sample Documents**: Build test document library
3. **Performance Testing**: Test with larger documents
4. **Caselaw Integration**: Re-enable caselaw plugin after core stabilization

## Support

For issues:
1. Check this deployment guide
2. Run with `--debug` flag for verbose output
3. Check test suite: `pytest tests/ -v`

## Changelog

- v0.1.0: Core system with employment law plugin
- Caselaw plugin temporarily disabled for stability