# CAP Caselaw Plugin - Deployment Guide

## Overview

This document provides comprehensive deployment instructions for the CAP caselaw plugin in production environments, including infrastructure setup, scaling considerations, and operational procedures.

## 🚀 Production Architecture

### Infrastructure Overview

```mermaid
graph TB
    subgraph "Load Balancer Layer"
        LB[Application Load Balancer<br/>AWS ALB / GCP GLB]
    end
    
    subgraph "Application Layer"
        API1[OpenLaw API<br/>Instance 1]
        API2[OpenLaw API<br/>Instance 2]
        API3[OpenLaw API<br/>Instance 3]
    end
    
    subgraph "Caselaw Plugin Layer"
        CP1[Caselaw Plugin<br/>Instance 1]
        CP2[Caselaw Plugin<br/>Instance 2]
        CP3[Caselaw Plugin<br/>Instance 3]
    end
    
    subgraph "Data Layer"
        PG[(PostgreSQL<br/>Primary + Read Replicas)]
        REDIS[(Redis Cluster<br/>Cache + Sessions)]
        S3[(Object Storage<br/>S3 / GCS)]
        ES[(Elasticsearch<br/>Search Index)]
    end
    
    subgraph "Processing Layer"
        WORKER1[ETL Worker 1]
        WORKER2[ETL Worker 2]
        WORKER3[ETL Worker 3]
        QUEUE[(Message Queue<br/>RabbitMQ / SQS)]
    end
    
    LB --> API1
    LB --> API2
    LB --> API3
    
    API1 --> CP1
    API2 --> CP2
    API3 --> CP3
    
    CP1 --> PG
    CP1 --> REDIS
    CP1 --> S3
    CP1 --> ES
    
    CP1 --> QUEUE
    QUEUE --> WORKER1
    QUEUE --> WORKER2
    QUEUE --> WORKER3
    
    WORKER1 --> PG
    WORKER1 --> S3
```

## ☸️ Kubernetes Deployment

### Namespace Configuration

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: openlaw-caselaw
  labels:
    app: openlaw
    component: caselaw-plugin
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: caselaw-quota
  namespace: openlaw-caselaw
spec:
  hard:
    requests.cpu: "50"
    requests.memory: 200Gi
    limits.cpu: "100"
    limits.memory: 400Gi
    persistentvolumeclaims: "20"
```

### Application Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: caselaw-plugin
  namespace: openlaw-caselaw
  labels:
    app: openlaw
    component: caselaw-plugin
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: openlaw
      component: caselaw-plugin
  template:
    metadata:
      labels:
        app: openlaw
        component: caselaw-plugin
    spec:
      containers:
      - name: caselaw-plugin
        image: openlaw/caselaw-plugin:v1.0.0
        ports:
        - containerPort: 8080
          name: http
        - containerPort: 8090
          name: metrics
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: caselaw-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: caselaw-secrets
              key: redis-url
        - name: ELASTICSEARCH_URL
          valueFrom:
            secretKeyRef:
              name: caselaw-secrets
              key: elasticsearch-url
        - name: S3_BUCKET
          valueFrom:
            configMapKeyRef:
              name: caselaw-config
              key: s3-bucket
        - name: AWS_REGION
          valueFrom:
            configMapKeyRef:
              name: caselaw-config
              key: aws-region
        resources:
          requests:
            cpu: 2000m
            memory: 8Gi
          limits:
            cpu: 4000m
            memory: 16Gi
        livenessProbe:
          httpGet:
            path: /health
            port: http
          initialDelaySeconds: 60
          periodSeconds: 30
          timeoutSeconds: 10
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            Port: http
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        volumeMounts:
        - name: plugin-config
          mountPath: /app/config
          readOnly: true
        - name: temp-storage
          mountPath: /tmp/caselaw
      volumes:
      - name: plugin-config
        configMap:
          name: caselaw-config
      - name: temp-storage
        emptyDir:
          sizeLimit: 10Gi
---
apiVersion: v1
kind: Service
metadata:
  name: caselaw-plugin-service
  namespace: openlaw-caselaw
  labels:
    app: openlaw
    component: caselaw-plugin
spec:
  selector:
    app: openlaw
    component: caselaw-plugin
  ports:
  - name: http
    port: 80
    targetPort: 8080
  - name: metrics
    port: 8090
    targetPort: 8090
  type: ClusterIP
```

### ETL Worker Deployment

```yaml
# k8s/etl-workers.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: caselaw-etl-workers
  namespace: openlaw-caselaw
  labels:
    app: openlaw
    component: caselaw-etl
spec:
  replicas: 5
  selector:
    matchLabels:
      app: openlaw
      component: caselaw-etl
  template:
    metadata:
      labels:
        app: openlaw
        component: caselaw-etl
    spec:
      containers:
      - name: etl-worker
        image: openlaw/caselaw-etl-worker:v1.0.0
        env:
        - name: WORKER_TYPE
          value: "etl"
        - name: CONCURRENCY
          value: "4"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: caselaw-secrets
              key: database-url
        - name: QUEUE_URL
          valueFrom:
            secretKeyRef:
              name: caselaw-secrets
              key: queue-url
        - name: HF_TOKEN
          valueFrom:
            secretKeyRef:
              name: caselaw-secrets
              key: huggingface-token
        resources:
          requests:
            cpu: 1000m
            memory: 4Gi
          limits:
            cpu: 2000m
            memory: 8Gi
        volumeMounts:
        - name: worker-config
          mountPath: /app/config
          readOnly: true
        - name: processing-temp
          mountPath: /tmp/processing
      volumes:
      - name: worker-config
        configMap:
          name: caselaw-config
      - name: processing-temp
        emptyDir:
          sizeLimit: 20Gi
```

### Configuration Management

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: caselaw-config
  namespace: openlaw-caselaw
data:
  plugin.yaml: |
    name: "caselaw_access_project"
    version: "1.0.0"
    display_name: "Case Law Access Project"
    description: "Harvard Law CAP caselaw corpus with provenance tracking"
    
    # Processing configuration
    ingestion:
      batch_size: 1000
      max_parallel_workers: 10
      checkpoint_interval: 10000
      retry_failed_cases: true
      max_retries: 3
    
    # Storage configuration
    storage:
      database_pool_size: 20
      connection_timeout: 30
      query_timeout: 60
      batch_insert_size: 1000
    
    # Citation extraction configuration
    citation_extraction:
      confidence_threshold: 0.7
      max_citations_per_paragraph: 50
      enable_ml_validation: true
      ml_model_path: "/app/models/citation_model.pkl"
    
    # API configuration
    api:
      max_query_results: 1000
      query_timeout: 30
      enable_caching: true
      cache_ttl: 3600
    
    # Feature flags
    features:
      enable_cross_plugin_enhancement: true
      enable_temporal_reasoning: true
      enable_jurisdictional_reasoning: true
      enable_full_text_search: true
  
  aws-region: "us-east-1"
  s3-bucket: "openlaw-caselaw-production"
  elasticsearch-index: "caselaw-cases"
---
apiVersion: v1
kind: Secret
metadata:
  name: caselaw-secrets
  namespace: openlaw-caselaw
type: Opaque
stringData:
  database-url: "postgresql://caselaw_user:CHANGE_ME@postgres-primary:5432/openlaw_caselaw"
  redis-url: "redis://redis-cluster:6379/0"
  elasticsearch-url: "https://elasticsearch-cluster:9200"
  queue-url: "amqp://queue_user:CHANGE_ME@rabbitmq:5672/"
  huggingface-token: "hf_CHANGE_ME"
  aws-access-key-id: "CHANGE_ME"
  aws-secret-access-key: "CHANGE_ME"
```

## 🗄️ Database Setup

### PostgreSQL Configuration

```sql
-- Database setup for caselaw plugin
CREATE DATABASE openlaw_caselaw;
CREATE USER caselaw_user WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE openlaw_caselaw TO caselaw_user;

\c openlaw_caselaw;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS caselaw;
CREATE SCHEMA IF NOT EXISTS provenance;
CREATE SCHEMA IF NOT EXISTS hypergraph;

-- Grant schema permissions
GRANT ALL ON SCHEMA caselaw TO caselaw_user;
GRANT ALL ON SCHEMA provenance TO caselaw_user;
GRANT ALL ON SCHEMA hypergraph TO caselaw_user;

-- Performance tuning for large dataset
ALTER SYSTEM SET shared_buffers = '8GB';
ALTER SYSTEM SET effective_cache_size = '24GB';
ALTER SYSTEM SET maintenance_work_mem = '2GB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '64MB';
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;
ALTER SYSTEM SET max_worker_processes = 16;
ALTER SYSTEM SET max_parallel_workers_per_gather = 4;
ALTER SYSTEM SET max_parallel_workers = 16;

-- Reload configuration
SELECT pg_reload_conf();
```

### Database Migration Scripts

```python
# migrations/001_initial_schema.py
"""Initial schema migration for caselaw plugin"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Provenance tables
    op.create_table(
        'provenance_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('entity_id', sa.String(255), nullable=False, index=True),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('operation', sa.String(50), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, default=sa.text('NOW()')),
        sa.Column('source_system', sa.String(100), nullable=False),
        sa.Column('source_version', sa.String(50), nullable=False),
        sa.Column('metadata', postgresql.JSONB, nullable=True),
        sa.Column('checksum', sa.String(64), nullable=False),
        schema='provenance'
    )
    
    # Hypergraph nodes
    op.create_table(
        'nodes',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('node_type', sa.String(50), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, default=sa.text('NOW()')),
        sa.Column('properties', postgresql.JSONB, nullable=False, default=sa.text("'{}'")),
        sa.Column('provenance_id', postgresql.UUID(as_uuid=True), 
                 sa.ForeignKey('provenance.provenance_records.id'), nullable=False),
        schema='hypergraph'
    )
    
    # Hypergraph edges
    op.create_table(
        'hyperedges',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('relation', sa.String(100), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=sa.text('NOW()')),
        sa.Column('properties', postgresql.JSONB, nullable=False, default=sa.text("'{}'")),
        sa.Column('provenance_id', postgresql.UUID(as_uuid=True), 
                 sa.ForeignKey('provenance.provenance_records.id'), nullable=False),
        schema='hypergraph'
    )
    
    # Edge connections (many-to-many)
    op.create_table(
        'hyperedge_connections',
        sa.Column('hyperedge_id', postgresql.UUID(as_uuid=True), 
                 sa.ForeignKey('hypergraph.hyperedges.id'), nullable=False),
        sa.Column('node_id', sa.String(255), 
                 sa.ForeignKey('hypergraph.nodes.id'), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),
        sa.PrimaryKeyConstraint('hyperedge_id', 'node_id', 'role'),
        schema='hypergraph'
    )
    
    # Case-specific tables
    op.create_table(
        'cases',
        sa.Column('id', sa.String(255), primary_key=True),  # cap:{numeric_id}
        sa.Column('name', sa.Text, nullable=False),
        sa.Column('name_abbreviation', sa.String(500), nullable=True),
        sa.Column('decision_date', sa.Date, nullable=True, index=True),
        sa.Column('court_id', sa.String(255), nullable=True),
        sa.Column('jurisdiction', sa.String(50), nullable=False, index=True),
        sa.Column('docket_number', sa.String(100), nullable=True),
        sa.Column('first_page', sa.Integer, nullable=True),
        sa.Column('last_page', sa.Integer, nullable=True),
        sa.Column('frontend_url', sa.Text, nullable=True),
        sa.Column('frontend_pdf_url', sa.Text, nullable=True),
        sa.Column('analysis', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, default=sa.text('NOW()')),
        schema='caselaw'
    )
    
    # Optimize for common query patterns
    op.create_index('idx_cases_jurisdiction_date', 'cases', ['jurisdiction', 'decision_date'], schema='caselaw')
    op.create_index('idx_cases_name_trgm', 'cases', ['name'], postgresql_using='gin', 
                   postgresql_ops={'name': 'gin_trgm_ops'}, schema='caselaw')
    
    # Citations table
    op.create_table(
        'citations',
        sa.Column('id', sa.String(255), primary_key=True),  # reporter:vol:page format
        sa.Column('case_id', sa.String(255), 
                 sa.ForeignKey('caselaw.cases.id'), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('cite', sa.String(500), nullable=False),
        sa.Column('normalized_cite', sa.String(500), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=sa.text('NOW()')),
        schema='caselaw'
    )

def downgrade():
    op.drop_table('citations', schema='caselaw')
    op.drop_table('cases', schema='caselaw')
    op.drop_table('hyperedge_connections', schema='hypergraph')
    op.drop_table('hyperedges', schema='hypergraph')
    op.drop_table('nodes', schema='hypergraph')
    op.drop_table('provenance_records', schema='provenance')
```

## 📊 Elasticsearch Setup

### Index Configuration

```json
{
  "settings": {
    "number_of_shards": 10,
    "number_of_replicas": 1,
    "index": {
      "max_result_window": 50000,
      "refresh_interval": "30s"
    },
    "analysis": {
      "analyzer": {
        "legal_text_analyzer": {
          "type": "custom",
          "tokenizer": "standard",
          "filter": [
            "lowercase",
            "legal_synonyms",
            "legal_stemmer"
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
          "synonyms_path": "analysis/legal_synonyms.txt"
        },
        "legal_stemmer": {
          "type": "stemmer",
          "language": "english"
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "case_id": {
        "type": "keyword"
      },
      "name": {
        "type": "text",
        "analyzer": "legal_text_analyzer",
        "fields": {
          "keyword": {
            "type": "keyword",
            "ignore_above": 256
          }
        }
      },
      "court": {
        "type": "keyword"
      },
      "jurisdiction": {
        "type": "keyword"
      },
      "decision_date": {
        "type": "date"
      },
      "citations": {
        "type": "text",
        "analyzer": "citation_analyzer"
      },
      "full_text": {
        "type": "text",
        "analyzer": "legal_text_analyzer"
      },
      "paragraphs": {
        "type": "nested",
        "properties": {
          "id": {
            "type": "keyword"
          },
          "text": {
            "type": "text",
            "analyzer": "legal_text_analyzer"
          },
          "paragraph_number": {
            "type": "integer"
          }
        }
      },
      "legal_concepts": {
        "type": "keyword"
      },
      "precedential_value": {
        "type": "float"
      }
    }
  }
}
```

## 🏗️ Terraform Infrastructure

### AWS Infrastructure

```hcl
# terraform/main.tf
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# VPC and networking
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  
  name = "openlaw-caselaw-vpc"
  cidr = "10.0.0.0/16"
  
  azs             = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
  
  enable_nat_gateway = true
  enable_vpn_gateway = false
  
  tags = {
    Environment = var.environment
    Project     = "openlaw-caselaw"
  }
}

# EKS Cluster
module "eks" {
  source = "terraform-aws-modules/eks/aws"
  
  cluster_name    = "openlaw-caselaw-${var.environment}"
  cluster_version = "1.27"
  
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets
  
  enable_irsa = true
  
  eks_managed_node_groups = {
    main = {
      desired_capacity = 3
      max_capacity     = 10
      min_capacity     = 3
      
      instance_types = ["c5.2xlarge"]
      
      k8s_labels = {
        Environment = var.environment
        NodeGroup   = "main"
      }
    }
    
    workers = {
      desired_capacity = 5
      max_capacity     = 20
      min_capacity     = 5
      
      instance_types = ["c5.4xlarge"]
      
      k8s_labels = {
        Environment = var.environment
        NodeGroup   = "workers"
      }
      
      taints = [{
        key    = "workload"
        value  = "etl"
        effect = "NO_SCHEDULE"
      }]
    }
  }
  
  tags = {
    Environment = var.environment
    Project     = "openlaw-caselaw"
  }
}

# RDS PostgreSQL
resource "aws_db_subnet_group" "caselaw" {
  name       = "caselaw-${var.environment}"
  subnet_ids = module.vpc.private_subnets
  
  tags = {
    Name        = "Caselaw DB subnet group"
    Environment = var.environment
  }
}

resource "aws_db_instance" "caselaw_primary" {
  identifier = "caselaw-primary-${var.environment}"
  
  engine         = "postgres"
  engine_version = "15.3"
  instance_class = "db.r6g.2xlarge"
  
  allocated_storage     = 2000
  max_allocated_storage = 10000
  storage_type          = "gp3"
  storage_encrypted     = true
  
  db_name  = "openlaw_caselaw"
  username = "caselaw_admin"
  password = var.db_password
  
  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.caselaw.name
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  performance_insights_enabled = true
  monitoring_interval         = 60
  monitoring_role_arn        = aws_iam_role.rds_monitoring.arn
  
  skip_final_snapshot = false
  final_snapshot_identifier = "caselaw-primary-final-${var.environment}-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"
  
  tags = {
    Environment = var.environment
    Project     = "openlaw-caselaw"
  }
}

# Read replicas for scaling reads
resource "aws_db_instance" "caselaw_replica" {
  count = 2
  
  identifier = "caselaw-replica-${count.index + 1}-${var.environment}"
  
  replicate_source_db = aws_db_instance.caselaw_primary.identifier
  instance_class      = "db.r6g.xlarge"
  
  performance_insights_enabled = true
  monitoring_interval         = 60
  monitoring_role_arn        = aws_iam_role.rds_monitoring.arn
  
  tags = {
    Environment = var.environment
    Project     = "openlaw-caselaw"
  }
}

# ElastiCache Redis cluster
resource "aws_elasticache_subnet_group" "caselaw" {
  name       = "caselaw-${var.environment}"
  subnet_ids = module.vpc.private_subnets
}

resource "aws_elasticache_replication_group" "caselaw" {
  replication_group_id       = "caselaw-${var.environment}"
  description                = "Redis cluster for caselaw plugin"
  
  node_type            = "cache.r6g.xlarge"
  port                 = 6379
  parameter_group_name = "default.redis7"
  
  num_cache_clusters = 3
  
  subnet_group_name  = aws_elasticache_subnet_group.caselaw.name
  security_group_ids = [aws_security_group.redis.id]
  
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  
  tags = {
    Environment = var.environment
    Project     = "openlaw-caselaw"
  }
}

# S3 bucket for document storage
resource "aws_s3_bucket" "caselaw_documents" {
  bucket = "openlaw-caselaw-${var.environment}-${random_id.bucket_suffix.hex}"
  
  tags = {
    Environment = var.environment
    Project     = "openlaw-caselaw"
  }
}

resource "aws_s3_bucket_versioning" "caselaw_documents" {
  bucket = aws_s3_bucket.caselaw_documents.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_encryption" "caselaw_documents" {
  bucket = aws_s3_bucket.caselaw_documents.id
  
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }
}

resource "random_id" "bucket_suffix" {
  byte_length = 8
}
```

## 🔄 CI/CD Pipeline

### GitHub Actions Workflow

```yaml
# .github/workflows/caselaw-plugin-deploy.yml
name: Deploy Caselaw Plugin

on:
  push:
    branches: [main]
    paths: ['plugins/caselaw/**']
  
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to deploy to'
        required: true
        default: 'staging'
        type: choice
        options:
        - staging
        - production

env:
  AWS_REGION: us-east-1
  EKS_CLUSTER_NAME: openlaw-caselaw-production

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v3
      with:
        python-version: 3.11
    
    - name: Install dependencies
      run: |
        pip install -e .[test,nlp]
    
    - name: Run tests
      run: |
        pytest plugins/caselaw/tests/ -v --cov=plugins.caselaw
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3

  build:
    runs-on: ubuntu-latest
    needs: test
    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
      image-digest: ${{ steps.build.outputs.digest }}
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2
    
    - name: Log in to ECR
      uses: aws-actions/amazon-ecr-login@v1
    
    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v4
      with:
        images: ${{ secrets.ECR_REGISTRY }}/openlaw/caselaw-plugin
        tags: |
          type=ref,event=branch
          type=ref,event=pr
          type=sha,prefix={{branch}}-
          type=raw,value=latest,enable={{is_default_branch}}
    
    - name: Build and push
      id: build
      uses: docker/build-push-action@v4
      with:
        context: .
        file: plugins/caselaw/Dockerfile
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

  deploy:
    runs-on: ubuntu-latest
    needs: build
    environment: 
      name: ${{ github.event.inputs.environment || 'production' }}
    steps:
    - uses: actions/checkout@v3
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ${{ env.AWS_REGION }}
    
    - name: Update kubeconfig
      run: |
        aws eks update-kubeconfig --name ${{ env.EKS_CLUSTER_NAME }}
    
    - name: Deploy to Kubernetes
      run: |
        # Update deployment with new image
        kubectl set image deployment/caselaw-plugin \
          caselaw-plugin=${{ needs.build.outputs.image-tag }} \
          -n openlaw-caselaw
        
        # Wait for rollout to complete
        kubectl rollout status deployment/caselaw-plugin -n openlaw-caselaw --timeout=600s
        
        # Verify deployment
        kubectl get pods -n openlaw-caselaw -l app=openlaw,component=caselaw-plugin
    
    - name: Run health checks
      run: |
        # Wait for pods to be ready
        kubectl wait --for=condition=ready pod -l app=openlaw,component=caselaw-plugin -n openlaw-caselaw --timeout=300s
        
        # Test API endpoint
        kubectl port-forward svc/caselaw-plugin-service 8080:80 -n openlaw-caselaw &
        sleep 10
        
        curl -f http://localhost:8080/health || exit 1
        
        echo "Deployment successful!"
```

## 📈 Monitoring & Observability

### Prometheus Configuration

```yaml
# monitoring/prometheus-config.yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "caselaw_plugin_rules.yml"

scrape_configs:
  - job_name: 'caselaw-plugin'
    kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
          - openlaw-caselaw
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        action: keep
        regex: openlaw
      - source_labels: [__meta_kubernetes_pod_label_component]
        action: keep
        regex: caselaw-plugin
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
      - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
        action: replace
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:$2
        target_label: __address__
```

### Alerting Rules

```yaml
# monitoring/caselaw_plugin_rules.yml
groups:
  - name: caselaw_plugin_alerts
    rules:
    - alert: CaselawPluginDown
      expr: up{job="caselaw-plugin"} == 0
      for: 1m
      labels:
        severity: critical
      annotations:
        summary: "Caselaw plugin instance is down"
        description: "Caselaw plugin instance {{ $labels.instance }} has been down for more than 1 minute."
    
    - alert: HighCitationExtractionLatency
      expr: histogram_quantile(0.95, rate(citation_extraction_duration_seconds_bucket[5m])) > 2
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High citation extraction latency"
        description: "95th percentile citation extraction latency is {{ $value }}s"
    
    - alert: LowCitationResolutionAccuracy
      expr: citation_resolution_accuracy_ratio < 0.9
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "Low citation resolution accuracy"
        description: "Citation resolution accuracy is {{ $value }}, below 90% threshold"
    
    - alert: DatabaseConnectionPoolExhaustion
      expr: database_connections_active / database_connections_max > 0.9
      for: 2m
      labels:
        severity: critical
      annotations:
        summary: "Database connection pool nearly exhausted"
        description: "Database connection pool utilization is {{ $value }}"
```

## 🔧 Operations Procedures

### Deployment Checklist

```markdown
# Caselaw Plugin Deployment Checklist

## Pre-Deployment
- [ ] All tests passing in CI/CD pipeline
- [ ] Database migrations tested in staging
- [ ] Performance benchmarks within acceptable ranges
- [ ] Security scans completed with no critical issues
- [ ] Backup verification completed
- [ ] Monitoring and alerting configured
- [ ] Rollback plan documented and tested

## Deployment
- [ ] Maintenance window scheduled (if required)
- [ ] Database migrations applied
- [ ] Configuration updated in Kubernetes
- [ ] Application pods deployed with rolling update
- [ ] Health checks passing
- [ ] Load balancer traffic routing verified
- [ ] ETL workers scaled appropriately

## Post-Deployment
- [ ] API endpoints responding correctly
- [ ] Citation extraction accuracy within SLA
- [ ] Database performance metrics normal
- [ ] Cache hit rates optimal
- [ ] No error rate spikes in logs
- [ ] Dependent systems functioning normally
- [ ] Stakeholders notified of successful deployment

## Emergency Rollback (if needed)
- [ ] Previous deployment tagged for rollback
- [ ] Database state consistent
- [ ] Rollback executed via Kubernetes
- [ ] Health checks verified post-rollback
- [ ] Incident documentation completed
```

### Scaling Procedures

```bash
#!/bin/bash
# scripts/scale_caselaw_plugin.sh

set -e

NAMESPACE="openlaw-caselaw"
ENVIRONMENT=${1:-production}
SCALE_TARGET=${2:-5}

echo "Scaling caselaw plugin to $SCALE_TARGET replicas in $ENVIRONMENT environment..."

# Scale main application
kubectl scale deployment caselaw-plugin --replicas=$SCALE_TARGET -n $NAMESPACE

# Scale ETL workers based on workload
if [ "$SCALE_TARGET" -gt 3 ]; then
  ETL_REPLICAS=$((SCALE_TARGET * 2))
  kubectl scale deployment caselaw-etl-workers --replicas=$ETL_REPLICAS -n $NAMESPACE
fi

# Wait for scaling to complete
echo "Waiting for pods to be ready..."
kubectl wait --for=condition=ready pod -l app=openlaw,component=caselaw-plugin -n $NAMESPACE --timeout=300s

# Verify scaling
ACTUAL_REPLICAS=$(kubectl get deployment caselaw-plugin -n $NAMESPACE -o jsonpath='{.status.readyReplicas}')
echo "Scaling complete. $ACTUAL_REPLICAS replicas are ready."

# Update HPA if needed
if [ "$SCALE_TARGET" -gt 10 ]; then
  kubectl patch hpa caselaw-plugin-hpa -n $NAMESPACE -p '{"spec":{"maxReplicas":'$((SCALE_TARGET * 2))'}}'
fi

echo "Caselaw plugin scaling completed successfully!"
```

This comprehensive deployment guide provides everything needed to deploy and operate the CAP caselaw plugin in production at scale, with proper infrastructure, monitoring, and operational procedures.