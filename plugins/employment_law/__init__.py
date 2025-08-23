"""
Employment Law Domain Plugin

Provides specialized legal knowledge for employment law analysis including:
- ADA (Americans with Disabilities Act) compliance
- FLSA (Fair Labor Standards Act) wage/hour regulations  
- At-will employment doctrine and wrongful termination
- Workers' compensation analysis

This plugin demonstrates the legal hypergraph system with real-world legal reasoning.
"""

from .plugin import EmploymentLawPlugin
from .rules import EmploymentLawRules
from .ner import EmploymentNER

__all__ = ["EmploymentLawPlugin", "EmploymentLawRules", "EmploymentNER"]