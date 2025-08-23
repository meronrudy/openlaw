#!/bin/bash
# OpenLaw Core System Setup Script
# Sets up virtual environment and dependencies for deployment

set -e  # Exit on any error

echo "🚀 OpenLaw Core System Setup"
echo "============================"

# Check Python version
python3 --version | grep -E "Python 3\.(9|10|11|12)" > /dev/null || {
    echo "❌ Error: Python 3.9+ required"
    exit 1
}

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv openlaw-env

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source openlaw-env/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install core dependencies
echo "📥 Installing core dependencies..."
pip install -r requirements.txt

# Test core system
echo "🧪 Testing core system..."
python3 -c "import plugins.employment_law.plugin; print('✅ Employment law plugin loaded')" || {
    echo "❌ Core system test failed"
    exit 1
}

# Create test document if not exists
if [ ! -f "test_ada_case.txt" ]; then
    echo "📄 Creating test document..."
    cat > test_ada_case.txt << 'EOF'
John Smith has been employed as a software engineer for 3 years. He recently developed a visual impairment that affects his ability to read standard computer screens. John requested a larger monitor and screen reader software as reasonable accommodations. The company has 150 employees and annual revenue of $50 million. John can perform all essential job functions with these accommodations.
EOF
fi

# Test document analysis
echo "🔍 Testing document analysis..."
python3 cli_driver.py analyze --file test_ada_case.txt --format summary > /dev/null || {
    echo "❌ Document analysis test failed"
    exit 1
}

echo ""
echo "✅ Setup completed successfully!"
echo ""
echo "🎯 Quick Start:"
echo "   source openlaw-env/bin/activate"
echo "   python3 cli_driver.py demo --domain employment_law"
echo ""
echo "📚 Documentation: DEPLOYMENT_GUIDE_CORE.md"