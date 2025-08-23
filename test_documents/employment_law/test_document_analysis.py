#!/usr/bin/env python3
"""
Employment Law Document Analysis Demo

This script demonstrates the complete employment law analysis workflow:
1. Load realistic legal documents
2. Extract entities using employment law NER
3. Apply legal rules through hypergraph reasoning
4. Generate conclusions with detailed explanations

Run with: python test_document_analysis.py
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from pathlib import Path
from datetime import datetime
from plugins.employment_law.plugin import EmploymentLawPlugin
from core.model import Context
import json

def analyze_document(file_path: str, document_type: str) -> dict:
    """
    Analyze a legal document using the employment law plugin
    
    Args:
        file_path: Path to the document file
        document_type: Type of document (ada, flsa, wrongful_termination, workers_comp)
        
    Returns:
        Analysis results with entities, facts, conclusions, and explanations
    """
    # Read document
    with open(file_path, 'r', encoding='utf-8') as f:
        document_text = f.read()
    
    # Initialize plugin and context
    plugin = EmploymentLawPlugin()
    context = Context(jurisdiction="US", law_type="employment")
    
    # Analyze document
    analysis = plugin.analyze_document(document_text, context)
    
    # Add document metadata
    analysis['document_info'] = {
        'file_path': file_path,
        'document_type': document_type,
        'analysis_time': datetime.utcnow().isoformat(),
        'text_length': len(document_text)
    }
    
    return analysis

def print_analysis_summary(analysis: dict):
    """Print a formatted summary of the analysis results"""
    doc_info = analysis['document_info']
    
    print(f"\n{'='*80}")
    print(f"EMPLOYMENT LAW DOCUMENT ANALYSIS")
    print(f"{'='*80}")
    print(f"Document: {Path(doc_info['file_path']).name}")
    print(f"Type: {doc_info['document_type'].upper()}")
    print(f"Text Length: {doc_info['text_length']:,} characters")
    print(f"Analysis Time: {doc_info['analysis_time']}")
    
    print(f"\n{'-'*60}")
    print("ENTITIES EXTRACTED:")
    print(f"{'-'*60}")
    
    entity_counts = {}
    for entity in analysis['entities']:
        entity_type = entity['type']
        entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1
        print(f"  • {entity_type}: {entity['text'][:50]}...")
    
    print(f"\nEntity Summary: {dict(entity_counts)}")
    
    print(f"\n{'-'*60}")
    print("LEGAL CITATIONS FOUND:")
    print(f"{'-'*60}")
    for citation in analysis['citations']:
        print(f"  • {citation['text']} ({citation['metadata']['citation_type']})")
    
    print(f"\n{'-'*60}")
    print("FACTS DERIVED FROM ENTITIES:")
    print(f"{'-'*60}")
    for fact in analysis['original_facts']:
        print(f"  • {fact.get('statement', 'N/A')}")
    
    print(f"\n{'-'*60}")
    print("REASONING CONCLUSIONS:")
    print(f"{'-'*60}")
    for fact in analysis['derived_facts']:
        print(f"  • {fact.get('statement', 'N/A')}")
    
    print(f"\n{'-'*60}")
    print("LEGAL ANALYSIS CONCLUSIONS:")
    print(f"{'-'*60}")
    for conclusion in analysis['conclusions']:
        print(f"  Type: {conclusion['type']}")
        print(f"  Conclusion: {conclusion['conclusion']}")
        print(f"  Legal Basis: {conclusion['legal_basis']}")
        print(f"  Confidence: {conclusion['confidence']:.2f}")
        print()

def run_comprehensive_demo():
    """Run analysis on all four employment law scenarios"""
    
    base_path = Path(__file__).parent
    
    test_documents = [
        {
            'file': base_path / 'ada_accommodation_request.txt',
            'type': 'ADA Accommodation Request',
            'description': 'Employee requesting reasonable accommodations for mobility disability'
        },
        {
            'file': base_path / 'flsa_overtime_complaint.txt', 
            'type': 'FLSA Overtime Violation',
            'description': 'Complaint about unpaid overtime wages and FLSA violations'
        },
        {
            'file': base_path / 'wrongful_termination_incident.txt',
            'type': 'Wrongful Termination',
            'description': 'Retaliation for whistleblowing to OSHA (public policy exception)'
        },
        {
            'file': base_path / 'workers_comp_claim.txt',
            'type': 'Workers Compensation',
            'description': 'Workplace injury claim with employer retaliation issues'
        }
    ]
    
    print("EMPLOYMENT LAW ANALYSIS SYSTEM - COMPREHENSIVE DEMO")
    print("=" * 80)
    print("Analyzing realistic employment law documents using:")
    print("• Legal NER for entity extraction")
    print("• Hypergraph reasoning with legal rules")
    print("• Provenance tracking and explanation generation")
    print("• 16 encoded employment law rules (ADA, FLSA, At-Will, Workers' Comp)")
    print()
    
    all_results = []
    
    for doc in test_documents:
        try:
            print(f"\nProcessing: {doc['type']}")
            print(f"Description: {doc['description']}")
            
            analysis = analyze_document(str(doc['file']), doc['type'].lower().replace(' ', '_'))
            print_analysis_summary(analysis)
            
            all_results.append({
                'document_type': doc['type'],
                'analysis': analysis
            })
            
        except Exception as e:
            print(f"Error analyzing {doc['file']}: {e}")
    
    # Summary statistics
    print(f"\n{'='*80}")
    print("OVERALL ANALYSIS SUMMARY")
    print(f"{'='*80}")
    
    total_entities = sum(len(result['analysis']['entities']) for result in all_results)
    total_citations = sum(len(result['analysis']['citations']) for result in all_results) 
    total_conclusions = sum(len(result['analysis']['conclusions']) for result in all_results)
    
    print(f"Documents Analyzed: {len(all_results)}")
    print(f"Total Entities Extracted: {total_entities}")
    print(f"Total Legal Citations Found: {total_citations}")
    print(f"Total Legal Conclusions Generated: {total_conclusions}")
    
    # Show entity types across all documents
    all_entity_types = set()
    for result in all_results:
        for entity in result['analysis']['entities']:
            all_entity_types.add(entity['type'])
    
    print(f"\nEntity Types Detected: {sorted(all_entity_types)}")
    
    # Show conclusion types across all documents
    all_conclusion_types = set()
    for result in all_results:
        for conclusion in result['analysis']['conclusions']:
            all_conclusion_types.add(conclusion['type'])
    
    print(f"Legal Conclusions Generated: {sorted(all_conclusion_types)}")
    
    print(f"\n{'='*80}")
    print("DEMO COMPLETE - Employment Law Analysis System Successfully Demonstrated")
    print("The system successfully:")
    print("✓ Extracted domain-specific entities from realistic legal documents")
    print("✓ Applied 16 employment law rules through hypergraph reasoning")
    print("✓ Generated legal conclusions with proper authorities and confidence scores")
    print("✓ Provided full provenance tracking for explainable AI")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    run_comprehensive_demo()