# Legal Hypergraph Analysis System - Examples

This guide provides practical examples demonstrating the capabilities of the Legal Hypergraph Analysis System.

## 🚀 Getting Started Examples

### Basic Document Analysis

```bash
# Analyze an ADA accommodation request
python cli_driver.py analyze --file test_documents/employment_law/ada_accommodation_request.txt

# Get detailed analysis with reasoning
python cli_driver.py analyze --file test_documents/employment_law/ada_accommodation_request.txt --format detailed

# Export results as JSON for integration
python cli_driver.py analyze --file test_documents/employment_law/ada_accommodation_request.txt --format json > results.json
```

### Interactive Demo

```bash
# Launch interactive demo
python cli_driver.py demo

# Example session:
# 📄 AVAILABLE TEST DOCUMENTS
# 1. workers_comp_claim.txt
# 2. flsa_overtime_complaint.txt  
# 3. ada_accommodation_request.txt
# 4. wrongful_termination_incident.txt
# 
# Enter document number to analyze (or 'q' to quit): 3
```

### Batch Processing

```bash
# Process all documents in employment law directory
python cli_driver.py batch --directory test_documents/employment_law/

# Save batch results to file
python cli_driver.py batch --directory test_documents/employment_law/ --output-file batch_results.json
```

## 📋 Employment Law Analysis Examples

### 1. ADA Accommodation Analysis

**Input Document**: `ada_accommodation_request.txt`
```
EMPLOYMENT LAW ACCOMMODATION REQUEST

Employee: Sarah Martinez
Department: Marketing
Date: March 15, 2024

REQUEST FOR REASONABLE ACCOMMODATION

I am writing to request reasonable accommodation under the ADA
for my mobility disability. Due to a chronic joint condition affecting
my ability to walk long distances and stand for extended periods...

REQUESTED ACCOMMODATION:
1. Ergonomic chair with lumbar support
2. Modified work schedule to accommodate medical appointments...

This request is made pursuant to 42 U.S.C. § 12112.
```

**Analysis Output**:
```
🔍 Analyzing document: ada_accommodation_request.txt
📄 Document length: 2,416 characters
⚖️  Jurisdiction: US

📊 ANALYSIS SUMMARY
============================================================
🏷️  Entities Extracted: 13 total
   • ADA_REQUEST: 7
   • DISABILITY: 2  
   • REASONABLE_ACCOMMODATION: 3
   • INTERACTIVE_PROCESS: 1

📚 Legal Citations: 1
   • 42 U.S.C. § 12112

⚖️  Legal Conclusions: 1
   • ADA_VIOLATION: Employer may be required to provide reasonable accommodation
     Legal Basis: 42 U.S.C. § 12112(b)(5)(A)
     Confidence: 85.0%
```

**Legal Reasoning Chain**:
1. **Fact Extraction**: Employee has mobility disability → `employee_has_disability`
2. **Fact Extraction**: Can perform essential functions with accommodation → `can_perform_essential_functions_with_accommodation`
3. **Rule Application**: ADA Rule #1 (42 U.S.C. § 12112) → `reasonable_accommodation_required`
4. **Conclusion**: ADA violation likely if accommodation not provided

### 2. FLSA Overtime Analysis

**Input Document**: `flsa_overtime_complaint.txt`
```
FAIR LABOR STANDARDS ACT COMPLAINT

Employee: Michael Johnson
Position: Warehouse Associate
Pay Period: January 1-31, 2024

OVERTIME VIOLATION COMPLAINT

During the pay period of January 1-31, 2024, I worked the following hours:
Week 1: 45 hours
Week 2: 52 hours  
Week 3: 48 hours
Week 4: 50 hours

My regular hourly rate is $18.00. However, I was only paid straight time
for all hours worked, receiving no overtime compensation as required by
29 U.S.C. § 207...
```

**Analysis Output**:
```
🔍 Analyzing document: flsa_overtime_complaint.txt

📊 ANALYSIS SUMMARY
============================================================
🏷️  Entities Extracted: 17 total
   • FLSA_VIOLATION: 8
   • OVERTIME: 5
   • WAGE_RATE: 3
   • RETALIATION: 1

📚 Legal Citations: 1
   • 29 U.S.C. § 207

⚖️  Legal Conclusions: 1
   • FLSA_VIOLATION: Employee entitled to overtime compensation
     Legal Basis: 29 U.S.C. § 207
     Confidence: 90.0%
```

**Legal Analysis**:
- **Hours Worked**: 45, 52, 48, 50 hours (all exceed 40-hour threshold)
- **Overtime Owed**: 
  - Week 1: 5 hours @ $27.00 = $135.00
  - Week 2: 12 hours @ $27.00 = $324.00
  - Week 3: 8 hours @ $27.00 = $216.00
  - Week 4: 10 hours @ $27.00 = $270.00
  - **Total**: $945.00 in unpaid overtime

### 3. Wrongful Termination Analysis

**Input Document**: `wrongful_termination_incident.txt`
```
WRONGFUL TERMINATION INCIDENT REPORT

Employee: Jennifer Adams
Department: Safety & Compliance
Termination Date: February 20, 2024

CIRCUMSTANCES OF TERMINATION

On February 15, 2024, I filed a complaint with OSHA regarding unsafe
working conditions in the manufacturing facility, specifically the lack
of proper ventilation systems and inadequate personal protective equipment...

Five days after filing the OSHA complaint, I was terminated for alleged
"performance issues" despite having received satisfactory performance
reviews for the past three years...
```

**Analysis Output**:
```
🔍 Analyzing document: wrongful_termination_incident.txt

📊 ANALYSIS SUMMARY
============================================================
🏷️  Entities Extracted: 27 total
   • WRONGFUL_TERMINATION: 5
   • WHISTLEBLOWING: 8
   • RETALIATION: 6
   • PUBLIC_POLICY_EXCEPTION: 2
   • AT_WILL_EMPLOYMENT: 5

⚖️  Legal Conclusions: 1
   • WRONGFUL_TERMINATION: Potential wrongful termination claim under public policy exception
     Legal Basis: State common law public policy exception
     Confidence: 80.0%
```

**Legal Analysis**:
- **Protected Activity**: OSHA complaint filing
- **Temporal Proximity**: Termination 5 days after complaint
- **Pretext**: Alleged performance issues contradicted by review history
- **Legal Theory**: Public policy exception to at-will employment

### 4. Workers' Compensation Analysis

**Input Document**: `workers_comp_claim.txt`
```
WORKERS' COMPENSATION CLAIM

Employee: Robert Chen
Department: Manufacturing
Injury Date: January 8, 2024

WORKPLACE INJURY REPORT

On January 8, 2024, while operating machinery in the manufacturing facility,
I sustained a severe back injury when a hydraulic lift malfunctioned.
The injury occurred during the course and scope of my employment...

MEDICAL TREATMENT:
- Emergency room visit on January 8, 2024
- MRI scan revealing herniated disc at L4-L5
- Physical therapy sessions (ongoing)
- Orthopedic specialist consultations...

LOST WAGES:
Unable to work from January 9, 2024 to present.
Average weekly wage: $950.00...

After filing this claim, my supervisor has made several threatening
statements about my job security and has denied previously approved
accommodations...
```

**Analysis Output**:
```
🔍 Analyzing document: workers_comp_claim.txt

📊 ANALYSIS SUMMARY
============================================================
🏷️  Entities Extracted: 30 total
   • WORKERS_COMP_CLAIM: 6
   • MEDICAL_TREATMENT: 5
   • LOST_WAGES: 4
   • RETALIATION: 15

⚖️  Legal Conclusions: 2
   • WORKERS_COMP_ENTITLEMENT: Valid workers' compensation claim
     Legal Basis: State workers' compensation statute
     Confidence: 95.0%
   • RETALIATION_VIOLATION: Employer retaliation prohibited
     Legal Basis: Workers' compensation anti-retaliation provisions
     Confidence: 80.0%
```

## 🔧 Advanced Usage Examples

### Custom Analysis Workflows

#### 1. Multi-Document Comparative Analysis

```bash
# Analyze multiple similar cases
for file in test_documents/employment_law/ada_*.txt; do
    echo "Analyzing: $file"
    python cli_driver.py analyze --file "$file" --format json >> ada_analysis.jsonl
done

# Process results with jq for comparison
jq '.analysis_results.conclusions[0].confidence' ada_analysis.jsonl
```

#### 2. Confidence Threshold Filtering

```python
import json
import subprocess

def analyze_with_confidence_filter(file_path, min_confidence=0.8):
    """Analyze document and filter by confidence threshold"""
    result = subprocess.run([
        'python', 'cli_driver.py', 'analyze', 
        '--file', file_path, '--format', 'json'
    ], capture_output=True, text=True)
    
    # Parse JSON output (skip initial analysis info)
    lines = result.stdout.split('\n')
    for i, line in enumerate(lines):
        if line.strip().startswith('{'):
            json_data = json.loads('\n'.join(lines[i:]))
            break
    
    # Filter conclusions by confidence
    conclusions = json_data['analysis_results']['conclusions']
    high_confidence = [c for c in conclusions if c['confidence'] >= min_confidence]
    
    return high_confidence

# Usage
high_conf_conclusions = analyze_with_confidence_filter(
    'test_documents/employment_law/ada_accommodation_request.txt',
    min_confidence=0.85
)
```

#### 3. Legal Citation Network Analysis

```python
import json
import networkx as nx
from collections import defaultdict

def build_citation_network(directory):
    """Build network of legal citations across documents"""
    citation_graph = nx.Graph()
    doc_citations = defaultdict(list)
    
    # Analyze all documents
    for doc_file in Path(directory).glob('*.txt'):
        result = subprocess.run([
            'python', 'cli_driver.py', 'analyze',
            '--file', str(doc_file), '--format', 'json'
        ], capture_output=True, text=True)
        
        # Extract citations
        # ... (parsing logic) ...
        
    return citation_graph, doc_citations

# Usage
graph, citations = build_citation_network('test_documents/employment_law/')
```

### Integration Examples

#### 1. REST API Integration

```python
from flask import Flask, request, jsonify
import subprocess
import json
import tempfile

app = Flask(__name__)

@app.route('/analyze', methods=['POST'])
def analyze_document():
    """REST endpoint for document analysis"""
    try:
        # Get document content
        content = request.json.get('content', '')
        
        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            temp_file = f.name
        
        # Analyze document
        result = subprocess.run([
            'python', 'cli_driver.py', 'analyze',
            '--file', temp_file, '--format', 'json'
        ], capture_output=True, text=True)
        
        # Parse and return results
        lines = result.stdout.split('\n')
        for i, line in enumerate(lines):
            if line.strip().startswith('{'):
                return jsonify(json.loads('\n'.join(lines[i:])))
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
```

#### 2. Database Integration

```python
import sqlite3
import json
from datetime import datetime

class LegalAnalysisDB:
    def __init__(self, db_path='legal_analysis.db'):
        self.conn = sqlite3.connect(db_path)
        self.create_tables()
    
    def create_tables(self):
        """Create database schema"""
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY,
                document_path TEXT,
                analysis_time TIMESTAMP,
                entities_count INTEGER,
                conclusions_count INTEGER,
                analysis_data TEXT
            )
        ''')
        
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS conclusions (
                id INTEGER PRIMARY KEY,
                analysis_id INTEGER,
                conclusion_type TEXT,
                conclusion_text TEXT,
                legal_basis TEXT,
                confidence REAL,
                FOREIGN KEY (analysis_id) REFERENCES analyses (id)
            )
        ''')
    
    def store_analysis(self, document_path, analysis_results):
        """Store analysis results in database"""
        cursor = self.conn.cursor()
        
        # Insert main analysis record
        cursor.execute('''
            INSERT INTO analyses (document_path, analysis_time, entities_count, 
                                conclusions_count, analysis_data)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            document_path,
            datetime.now(),
            len(analysis_results.get('entities', [])),
            len(analysis_results.get('conclusions', [])),
            json.dumps(analysis_results)
        ))
        
        analysis_id = cursor.lastrowid
        
        # Insert conclusions
        for conclusion in analysis_results.get('conclusions', []):
            cursor.execute('''
                INSERT INTO conclusions (analysis_id, conclusion_type, 
                                       conclusion_text, legal_basis, confidence)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                analysis_id,
                conclusion['type'],
                conclusion['conclusion'],
                conclusion['legal_basis'],
                conclusion['confidence']
            ))
        
        self.conn.commit()
        return analysis_id

# Usage
db = LegalAnalysisDB()
# ... analyze document and get results ...
db.store_analysis('document.txt', analysis_results)
```

## 📊 Performance Examples

### Benchmarking Analysis Speed

```python
import time
import statistics
from pathlib import Path

def benchmark_analysis(directory, iterations=5):
    """Benchmark analysis performance"""
    files = list(Path(directory).glob('*.txt'))
    times = []
    
    for iteration in range(iterations):
        start_time = time.time()
        
        for file_path in files:
            subprocess.run([
                'python', 'cli_driver.py', 'analyze',
                '--file', str(file_path)
            ], capture_output=True)
        
        end_time = time.time()
        times.append(end_time - start_time)
    
    return {
        'files_processed': len(files),
        'iterations': iterations,
        'avg_time': statistics.mean(times),
        'std_dev': statistics.stdev(times),
        'min_time': min(times),
        'max_time': max(times)
    }

# Usage
benchmark_results = benchmark_analysis('test_documents/employment_law/')
print(f"Average processing time: {benchmark_results['avg_time']:.2f} seconds")
print(f"Files per second: {benchmark_results['files_processed'] / benchmark_results['avg_time']:.2f}")
```

### Memory Usage Monitoring

```python
import psutil
import os

def monitor_memory_usage():
    """Monitor memory usage during analysis"""
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # Run analysis
    subprocess.run([
        'python', 'cli_driver.py', 'batch',
        '--directory', 'test_documents/employment_law/'
    ])
    
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = final_memory - initial_memory
    
    return {
        'initial_memory_mb': initial_memory,
        'final_memory_mb': final_memory,
        'memory_increase_mb': memory_increase
    }
```

## 🔍 Debugging Examples

### Verbose Analysis Output

```bash
# Enable detailed logging (if implemented)
export LEGAL_ANALYSIS_DEBUG=1
python cli_driver.py analyze --file document.txt --format detailed

# Check reasoning steps
python cli_driver.py analyze --file document.txt --show-reasoning
```

### Error Handling Examples

```python
import subprocess
import sys

def safe_analysis(file_path):
    """Safely analyze document with error handling"""
    try:
        result = subprocess.run([
            'python', 'cli_driver.py', 'analyze',
            '--file', file_path, '--format', 'json'
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            print(f"Analysis failed for {file_path}")
            print(f"Error: {result.stderr}")
            return None
        
        # Parse successful result
        lines = result.stdout.split('\n')
        for i, line in enumerate(lines):
            if line.strip().startswith('{'):
                return json.loads('\n'.join(lines[i:]))
        
    except subprocess.TimeoutExpired:
        print(f"Analysis timeout for {file_path}")
    except json.JSONDecodeError as e:
        print(f"JSON parsing error for {file_path}: {e}")
    except Exception as e:
        print(f"Unexpected error for {file_path}: {e}")
    
    return None
```

## 📝 Custom Test Document Examples

### Creating Test Documents

```python
def create_test_document(domain, scenario, entities, citations):
    """Generate realistic test documents"""
    templates = {
        'ada_accommodation': '''
REASONABLE ACCOMMODATION REQUEST

Employee: {employee_name}
Date: {date}
Department: {department}

I am requesting reasonable accommodation under the ADA for my {disability_type}.
The requested accommodations include:
{accommodations}

This request is made pursuant to {citation}.
''',
        'flsa_violation': '''
OVERTIME COMPLAINT

Employee: {employee_name}
Position: {position}
Pay Period: {pay_period}

During the specified pay period, I worked {total_hours} hours but was not
paid overtime compensation as required by {citation}.

Hours worked by week:
{weekly_hours}
''',
        # ... more templates ...
    }
    
    # Fill template with scenario data
    template = templates[scenario]
    return template.format(**entities)

# Usage
ada_doc = create_test_document(
    'employment_law', 
    'ada_accommodation',
    {
        'employee_name': 'Jane Smith',
        'date': '2024-03-15',
        'department': 'IT',
        'disability_type': 'visual impairment',
        'accommodations': '• Screen reader software\n• Large monitor\n• Adjustable desk',
        'citation': '42 U.S.C. § 12112'
    },
    ['42 U.S.C. § 12112']
)
```

---

These examples demonstrate the comprehensive capabilities of the Legal Hypergraph Analysis System. For more advanced usage scenarios, consult the API documentation and plugin development guide.