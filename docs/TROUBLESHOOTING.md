# Troubleshooting Guide

Comprehensive troubleshooting guide for the OpenLaw Legal Hypergraph System.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Installation Issues](#installation-issues)
- [Plugin Issues](#plugin-issues)
- [Analysis Issues](#analysis-issues)
- [Performance Issues](#performance-issues)
- [Storage Issues](#storage-issues)
- [Configuration Issues](#configuration-issues)
- [CLI Issues](#cli-issues)
- [Development Issues](#development-issues)
- [Common Error Messages](#common-error-messages)

## Quick Diagnostics

### System Health Check

Run this quick diagnostic to identify common issues:

```bash
# Check Python version
python3 --version | grep -E "3\.(9|10|11|12)" || echo "❌ Python 3.9+ required"

# Check core dependencies
python3 -c "import pydantic, sqlitedict, yaml, click; print('✅ Core dependencies OK')" 2>/dev/null || echo "❌ Missing core dependencies"

# Check plugin loading
python3 -c "import plugins.employment_law.plugin; print('✅ Employment law plugin OK')" 2>/dev/null || echo "❌ Plugin loading failed"

# Check CLI functionality
python3 cli_driver.py --help > /dev/null && echo "✅ CLI working" || echo "❌ CLI issues"

# Check current directory
[ -f "cli_driver.py" ] && echo "✅ In project root" || echo "❌ Not in project root directory"
```

### Environment Information

```bash
# Gather environment information for bug reports
echo "=== OpenLaw Environment Information ==="
echo "Python Version: $(python3 --version)"
echo "Working Directory: $(pwd)"
echo "PYTHONPATH: ${PYTHONPATH:-'Not set'}"
echo "Virtual Environment: ${VIRTUAL_ENV:-'Not activated'}"
echo ""
echo "OpenLaw Environment Variables:"
env | grep OPENLAW || echo "No OpenLaw environment variables set"
echo ""
echo "Project Files:"
ls -la cli_driver.py requirements.txt setup.sh 2>/dev/null || echo "Missing project files"
```

## Installation Issues

### Issue: `python3: command not found`

**Symptoms:**
```bash
bash: python3: command not found
```

**Solutions:**

**macOS:**
```bash
# Install Python via Homebrew
brew install python3

# Or use system Python
alias python3=python
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

**Windows:**
```bash
# Download Python from python.org
# Or use Windows Package Manager
winget install Python.Python.3.11
```

### Issue: `pip install` Fails

**Symptoms:**
```bash
ERROR: Could not install packages due to an EnvironmentError
```

**Solutions:**

1. **Upgrade pip:**
   ```bash
   python3 -m pip install --upgrade pip setuptools wheel
   ```

2. **Use virtual environment:**
   ```bash
   python3 -m venv openlaw-env
   source openlaw-env/bin/activate
   pip install -r requirements.txt
   ```

3. **Install with user flag:**
   ```bash
   pip install --user -r requirements.txt
   ```

4. **Clear pip cache:**
   ```bash
   pip cache purge
   pip install -r requirements.txt
   ```

### Issue: Virtual Environment Not Working

**Symptoms:**
```bash
bash: source: command not found
# or
(openlaw-env) not appearing in prompt
```

**Solutions:**

**Linux/macOS:**
```bash
# Create virtual environment
python3 -m venv openlaw-env

# Activate (bash/zsh)
source openlaw-env/bin/activate

# Activate (fish shell)
source openlaw-env/bin/activate.fish

# Verify activation
which python3
```

**Windows:**
```bash
# Create virtual environment
python -m venv openlaw-env

# Activate (Command Prompt)
openlaw-env\Scripts\activate.bat

# Activate (PowerShell)
openlaw-env\Scripts\Activate.ps1
```

### Issue: PyTorch Installation Problems

**Symptoms:**
```bash
ERROR: Could not find a version that satisfies the requirement torch
```

**Solutions:**

1. **CPU-only PyTorch:**
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
   ```

2. **Skip NLP temporarily:**
   ```bash
   export OPENLAW_SKIP_NLP=true
   python3 cli_driver.py demo --domain employment_law
   ```

3. **Alternative: Use minimal requirements:**
   ```bash
   # Create minimal requirements file
   cat > requirements-minimal.txt << EOF
   pydantic>=2.0.0
   sqlitedict>=2.1.0
   pyyaml>=6.0
   click>=8.0.0
   python-dateutil>=2.8.0
   EOF
   
   pip install -r requirements-minimal.txt
   ```

## Plugin Issues

### Issue: Plugin Import Errors

**Symptoms:**
```bash
ModuleNotFoundError: No module named 'plugins.employment_law'
```

**Solutions:**

1. **Check working directory:**
   ```bash
   pwd
   ls -la plugins/employment_law/
   ```

2. **Add to Python path:**
   ```bash
   export PYTHONPATH=$PYTHONPATH:$(pwd)
   python3 -c "import plugins.employment_law.plugin"
   ```

3. **Install in development mode:**
   ```bash
   pip install -e .
   ```

### Issue: Plugin Not Found

**Symptoms:**
```bash
❌ Demo domain 'employment_law' not supported. Available: 
```

**Solutions:**

1. **Verify plugin files exist:**
   ```bash
   ls -la plugins/employment_law/
   # Should show: __init__.py, plugin.py, ner.py, rules.py
   ```

2. **Check plugin initialization:**
   ```bash
   python3 -c "
   import sys
   sys.path.append('.')
   from plugins.employment_law.plugin import EmploymentLawPlugin
   plugin = EmploymentLawPlugin()
   print(f'Plugin: {plugin.name} v{plugin.version}')
   "
   ```

3. **Debug plugin loading:**
   ```bash
   export OPENLAW_LOG_LEVEL=DEBUG
   python3 cli_driver.py demo --domain employment_law
   ```

### Issue: Plugin Rules Not Loading

**Symptoms:**
```bash
⚖️  LEGAL RULES LOADED: 0 total
```

**Solutions:**

1. **Check rule definitions:**
   ```bash
   python3 -c "
   from plugins.employment_law.rules import EmploymentLawRules
   rules = EmploymentLawRules()
   print(f'Rules loaded: {len(rules.get_all_rules())}')
   for rule in rules.get_all_rules()[:3]:
       print(f'- {rule.id}: {rule.name}')
   "
   ```

2. **Verify rule format:**
   ```bash
   python3 -c "
   from plugins.employment_law.rules import EmploymentLawRules
   rules = EmploymentLawRules()
   rule = rules.get_all_rules()[0]
   print(f'Rule: {rule.id}')
   print(f'Conditions: {rule.conditions}')
   print(f'Conclusion: {rule.conclusion}')
   "
   ```

## Analysis Issues

### Issue: No Entities Extracted

**Symptoms:**
```bash
🏷️  Entities Extracted: 0 total
```

**Solutions:**

1. **Check document content:**
   ```bash
   # Verify document has content
   wc -c test_document.txt
   head test_document.txt
   ```

2. **Test with known working document:**
   ```bash
   cat > test_ada.txt << 'EOF'
   Employee has a visual impairment and requested screen reader software 
   as reasonable accommodation. The company has 150 employees.
   EOF
   
   python3 cli_driver.py analyze --file test_ada.txt --format detailed
   ```

3. **Debug NER processing:**
   ```bash
   python3 -c "
   from plugins.employment_law.ner import EmploymentNER
   ner = EmploymentNER()
   text = 'Employee has visual impairment and needs accommodation.'
   entities = ner.extract_entities(text)
   print(f'Entities found: {len(entities)}')
   for entity in entities:
       print(f'- {entity[\"type\"]}: {entity[\"text\"]}')
   "
   ```

### Issue: No Legal Conclusions

**Symptoms:**
```bash
⚖️  Legal Conclusions: 0
```

**Solutions:**

1. **Check if facts are generated:**
   ```bash
   python3 cli_driver.py analyze --file test_document.txt --format detailed --show-reasoning
   # Look for "Original Facts" and "Derived Facts" sections
   ```

2. **Test reasoning engine:**
   ```bash
   python3 -c "
   from plugins.employment_law.plugin import EmploymentLawPlugin
   from core.model import Context
   
   plugin = EmploymentLawPlugin()
   context = Context(jurisdiction='US', law_type='employment')
   
   text = '''Employee has disability and can perform job with accommodation.
   Company has 150 employees and provides reasonable accommodation.'''
   
   results = plugin.analyze_document(text, context)
   print(f'Original facts: {len(results[\"original_facts\"])}')
   print(f'Derived facts: {len(results[\"derived_facts\"])}') 
   print(f'Conclusions: {len(results[\"conclusions\"])}')
   "
   ```

3. **Check rule conditions:**
   ```bash
   python3 -c "
   from plugins.employment_law.rules import EmploymentLawRules
   rules = EmploymentLawRules()
   for rule in rules.get_all_rules():
       print(f'{rule.id}: {rule.conditions} -> {rule.conclusion}')
   "
   ```

### Issue: Low Confidence Scores

**Symptoms:**
```bash
Confidence: 45.0%  # Very low confidence
```

**Solutions:**

1. **Check confidence threshold:**
   ```bash
   export OPENLAW_CONFIDENCE_THRESHOLD=0.5
   python3 cli_driver.py analyze --file document.txt
   ```

2. **Review entity patterns:**
   ```bash
   # Check if document matches expected patterns
   grep -i "disability\|accommodation\|ada" document.txt
   grep -i "overtime\|40 hours\|flsa" document.txt
   ```

3. **Improve document quality:**
   ```bash
   # Use clearer legal language
   cat > improved_doc.txt << 'EOF'
   John Smith is an employee with a visual disability. He requested 
   reasonable accommodations including a screen reader. The employer 
   has over 15 employees and must provide accommodation under the ADA.
   EOF
   ```

## Performance Issues

### Issue: Slow Analysis

**Symptoms:**
- Analysis takes >30 seconds for small documents
- System becomes unresponsive

**Solutions:**

1. **Check system resources:**
   ```bash
   # Monitor CPU and memory usage
   top -p $(pgrep -f python3)
   
   # Check disk space
   df -h
   ```

2. **Reduce document size:**
   ```bash
   # Check document size
   wc -c document.txt
   
   # Limit document size
   export OPENLAW_MAX_DOCUMENT_SIZE=1048576  # 1MB
   ```

3. **Optimize for development:**
   ```bash
   export OPENLAW_STORAGE_TYPE=memory
   export OPENLAW_CACHE_ENABLED=true
   export OPENLAW_SKIP_NLP=true  # Temporarily skip NLP
   ```

4. **Use CPU-only mode:**
   ```bash
   export OPENLAW_NLP_DEVICE=cpu
   export OPENLAW_NLP_BATCH_SIZE=1
   ```

### Issue: Memory Errors

**Symptoms:**
```bash
MemoryError: Unable to allocate memory
```

**Solutions:**

1. **Reduce memory usage:**
   ```bash
   export OPENLAW_CACHE_SIZE=100
   export OPENLAW_MAX_ENTITIES=500
   export OPENLAW_NLP_MAX_MEMORY=1G
   ```

2. **Use smaller models:**
   ```bash
   # In plugin configuration
   export OPENLAW_NLP_MODEL=distilbert-base-uncased
   ```

3. **Process documents individually:**
   ```bash
   # Avoid batch processing large documents
   for file in documents/*.txt; do
       python3 cli_driver.py analyze --file "$file"
   done
   ```

## Storage Issues

### Issue: Database Locked

**Symptoms:**
```bash
sqlite3.OperationalError: database is locked
```

**Solutions:**

1. **Use in-memory storage:**
   ```bash
   export OPENLAW_STORAGE_TYPE=memory
   ```

2. **Check for zombie processes:**
   ```bash
   ps aux | grep python3
   # Kill any hanging processes
   pkill -f "python3 cli_driver.py"
   ```

3. **Remove lock file:**
   ```bash
   rm -f /path/to/database.db-lock
   ```

4. **Use unique database file:**
   ```bash
   export OPENLAW_STORAGE_PATH="/tmp/openlaw_$(date +%s).db"
   ```

### Issue: Permission Denied

**Symptoms:**
```bash
PermissionError: [Errno 13] Permission denied: '/var/lib/openlaw/openlaw.db'
```

**Solutions:**

1. **Use user directory:**
   ```bash
   export OPENLAW_DATA_DIR="$HOME/.openlaw"
   mkdir -p "$OPENLAW_DATA_DIR"
   export OPENLAW_STORAGE_PATH="$OPENLAW_DATA_DIR/openlaw.db"
   ```

2. **Fix permissions:**
   ```bash
   sudo chown -R $USER:$USER /var/lib/openlaw/
   sudo chmod -R 755 /var/lib/openlaw/
   ```

3. **Use temporary directory:**
   ```bash
   export OPENLAW_DATA_DIR=/tmp/openlaw
   mkdir -p $OPENLAW_DATA_DIR
   ```

## Configuration Issues

### Issue: Environment Variables Not Working

**Symptoms:**
- Settings not taking effect
- Default values always used

**Solutions:**

1. **Check variable names:**
   ```bash
   # Correct variable names (note the prefix)
   export OPENLAW_ENV=development
   export OPENLAW_LOG_LEVEL=DEBUG
   
   # Verify they're set
   env | grep OPENLAW
   ```

2. **Use configuration file:**
   ```bash
   # Create config file
   cat > config.yaml << 'EOF'
   environment: development
   logging:
     level: DEBUG
   storage:
     type: memory
   EOF
   
   export OPENLAW_CONFIG_PATH=config.yaml
   ```

3. **Check shell environment:**
   ```bash
   # Make sure variables persist
   echo "export OPENLAW_ENV=development" >> ~/.bashrc
   source ~/.bashrc
   ```

### Issue: Invalid Configuration Values

**Symptoms:**
```bash
ValueError: Invalid configuration value
```

**Solutions:**

1. **Check valid values:**
   ```bash
   # Valid environments
   export OPENLAW_ENV=development  # or production, testing
   
   # Valid log levels  
   export OPENLAW_LOG_LEVEL=DEBUG  # or INFO, WARNING, ERROR
   
   # Valid storage types
   export OPENLAW_STORAGE_TYPE=memory  # or sqlite, postgresql
   ```

2. **Validate configuration:**
   ```bash
   python3 -c "
   import os
   print('Environment:', os.getenv('OPENLAW_ENV', 'default'))
   print('Log Level:', os.getenv('OPENLAW_LOG_LEVEL', 'default'))
   print('Storage:', os.getenv('OPENLAW_STORAGE_TYPE', 'default'))
   "
   ```

## CLI Issues

### Issue: Command Not Found

**Symptoms:**
```bash
python3: can't open file 'cli_driver.py': [Errno 2] No such file or directory
```

**Solutions:**

1. **Navigate to project root:**
   ```bash
   # Find project directory
   find ~ -name "cli_driver.py" 2>/dev/null
   
   # Change to project directory
   cd /path/to/openlaw
   ```

2. **Verify project structure:**
   ```bash
   ls -la
   # Should see: cli_driver.py, requirements.txt, setup.sh, core/, plugins/
   ```

### Issue: Demo Not Starting

**Symptoms:**
```bash
❌ Demo domain 'employment_law' not supported
```

**Solutions:**

1. **Check plugin imports:**
   ```bash
   python3 -c "
   import sys
   sys.path.append('.')
   try:
       from plugins.employment_law.plugin import EmploymentLawPlugin
       print('✅ Plugin imports successfully')
   except Exception as e:
       print(f'❌ Plugin import failed: {e}')
   "
   ```

2. **Verify CLI implementation:**
   ```bash
   python3 -c "
   from cli_driver import LegalAnalysisCLI
   cli = LegalAnalysisCLI()
   print(f'CLI initialized: {type(cli.plugin).__name__}')
   "
   ```

### Issue: Argument Parsing Errors

**Symptoms:**
```bash
error: the following arguments are required: --file/-f
```

**Solutions:**

1. **Check command syntax:**
   ```bash
   # Correct syntax
   python3 cli_driver.py analyze --file document.txt
   python3 cli_driver.py demo --domain employment_law
   python3 cli_driver.py batch --directory documents/
   ```

2. **Get help:**
   ```bash
   python3 cli_driver.py --help
   python3 cli_driver.py analyze --help
   python3 cli_driver.py demo --help
   ```

## Development Issues

### Issue: Import Errors in Development

**Symptoms:**
```bash
ModuleNotFoundError: No module named 'core'
```

**Solutions:**

1. **Set up development environment:**
   ```bash
   # Install in development mode
   pip install -e .
   
   # Or add to Python path
   export PYTHONPATH=$PYTHONPATH:$(pwd)
   ```

2. **Check project structure:**
   ```bash
   tree -I "__pycache__|*.pyc" -L 3
   # Should show core/, plugins/, sdk/ directories
   ```

### Issue: Test Failures

**Symptoms:**
```bash
FAILED tests/test_employment_law.py::test_ada_analysis
```

**Solutions:**

1. **Run tests with verbose output:**
   ```bash
   pytest tests/ -v --tb=long
   ```

2. **Run specific test:**
   ```bash
   pytest tests/test_employment_law.py::test_ada_analysis -v
   ```

3. **Check test dependencies:**
   ```bash
   pip install -e ".[test]"
   ```

4. **Update test data:**
   ```bash
   # Ensure test documents exist
   ls -la tests/data/
   ```

### Issue: Code Style Errors

**Symptoms:**
```bash
black would reformat file.py
```

**Solutions:**

1. **Format code:**
   ```bash
   black .
   isort .
   ```

2. **Check code style:**
   ```bash
   black --check .
   flake8 .
   mypy .
   ```

## Common Error Messages

### `FileNotFoundError: [Errno 2] No such file or directory`

**Cause:** File path is incorrect or file doesn't exist.

**Solutions:**
```bash
# Check file exists
ls -la document.txt

# Use absolute path
python3 cli_driver.py analyze --file /full/path/to/document.txt

# Check working directory
pwd
```

### `ModuleNotFoundError: No module named 'plugins'`

**Cause:** Python can't find the plugins directory.

**Solutions:**
```bash
# Check you're in project root
ls -la plugins/

# Add to Python path
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Install in development mode
pip install -e .
```

### `ImportError: cannot import name 'EmploymentLawPlugin'`

**Cause:** Plugin class not properly defined or imported.

**Solutions:**
```bash
# Check plugin file exists
ls -la plugins/employment_law/plugin.py

# Check class definition
grep "class EmploymentLawPlugin" plugins/employment_law/plugin.py

# Check __init__.py files
find plugins/ -name "__init__.py" -exec ls -la {} \;
```

### `sqlite3.OperationalError: no such table`

**Cause:** Database schema not initialized.

**Solutions:**
```bash
# Use in-memory database
export OPENLAW_STORAGE_TYPE=memory

# Delete and recreate database
rm -f openlaw.db
python3 cli_driver.py demo --domain employment_law
```

### `AttributeError: 'NoneType' object has no attribute`

**Cause:** Null value in analysis results.

**Solutions:**
```bash
# Enable debug logging
export OPENLAW_LOG_LEVEL=DEBUG
python3 cli_driver.py analyze --file document.txt --format detailed

# Check document content
cat document.txt | head -5
```

### `ValueError: Invalid jurisdiction`

**Cause:** Unsupported jurisdiction specified.

**Solutions:**
```bash
# Use supported jurisdictions
python3 cli_driver.py analyze --file document.txt --jurisdiction US

# Check supported values
python3 -c "
from core.model import Context
try:
    ctx = Context(jurisdiction='INVALID')
except Exception as e:
    print(f'Error: {e}')
"
```

### `TimeoutError: Analysis timeout`

**Cause:** Document too large or analysis taking too long.

**Solutions:**
```bash
# Increase timeout
export OPENLAW_ANALYSIS_TIMEOUT=120

# Reduce document size
head -100 large_document.txt > smaller_document.txt

# Use memory storage
export OPENLAW_STORAGE_TYPE=memory
```

## Getting Additional Help

### Enable Debug Logging

For any issue, start by enabling detailed logging:

```bash
export OPENLAW_LOG_LEVEL=DEBUG
python3 cli_driver.py [your command] 2>&1 | tee debug.log
```

### Collect System Information

```bash
#!/bin/bash
# save as debug_info.sh
echo "=== OpenLaw Debug Information ==="
echo "Date: $(date)"
echo "Python: $(python3 --version)"
echo "OS: $(uname -a)"
echo "Working Directory: $(pwd)"
echo "Virtual Environment: ${VIRTUAL_ENV:-'None'}"
echo ""

echo "=== Environment Variables ==="
env | grep OPENLAW | sort

echo ""
echo "=== Project Structure ==="
find . -name "*.py" | head -20

echo ""
echo "=== Dependencies ==="
pip list | grep -E "(pydantic|torch|transformers|sqlitedict)"

echo ""
echo "=== Recent Logs ==="
tail -20 debug.log 2>/dev/null || echo "No debug.log found"
```

### Create Bug Reports

When reporting issues, include:

1. **System Information:**
   ```bash
   python3 --version
   pip list
   uname -a
   ```

2. **Complete Error Message:**
   ```bash
   python3 cli_driver.py [command] 2>&1 | tee error.log
   ```

3. **Steps to Reproduce:**
   - Exact commands run
   - Input files used
   - Expected vs actual behavior

4. **Environment Details:**
   ```bash
   env | grep OPENLAW
   pwd
   ls -la
   ```

### Community Resources

- **Documentation**: [docs/](../README.md)
- **Examples**: [plugins/employment_law/](../../plugins/employment_law/)
- **Issues**: [GitHub Issues](../../issues)
- **Discussions**: [GitHub Discussions](../../discussions)

### Professional Support

For production deployments or complex issues:

1. **Performance Optimization**: Contact for scaling guidance
2. **Custom Plugin Development**: Professional plugin development services
3. **Enterprise Support**: Priority support and custom features

## Prevention Tips

### Regular Maintenance

```bash
# Weekly maintenance script
#!/bin/bash

# Update dependencies
pip list --outdated

# Clean cache
pip cache purge
find . -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Run tests
pytest tests/ -q

# Check disk space
df -h

echo "✅ Maintenance complete"
```

### Best Practices

1. **Always use virtual environments**
2. **Pin dependency versions for production**
3. **Regular backups of analysis data**
4. **Monitor log files for warnings**
5. **Test with sample documents before processing large batches**

### Development Environment

```bash
# .envrc file for direnv
export OPENLAW_ENV=development
export OPENLAW_LOG_LEVEL=DEBUG
export OPENLAW_STORAGE_TYPE=memory
export PYTHONPATH=$PWD

# Development aliases
alias ol-demo="python3 cli_driver.py demo --domain employment_law"
alias ol-test="pytest tests/ -v"
alias ol-format="black . && isort ."
```

This troubleshooting guide should help resolve most common issues. For problems not covered here, please check the latest documentation or file an issue on the project repository.