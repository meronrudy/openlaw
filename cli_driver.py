#!/usr/bin/env python3
"""
Legal Hypergraph Analysis CLI

Command-line interface for the provenance-first legal ontology hypergraph system.
Provides comprehensive employment law analysis with explainable AI reasoning.

Public CLI API Surface (stable)
- class LegalAnalysisCLI:
  - analyze_document(file_path: str, output_format: str = "summary", jurisdiction: str = "US",
                     show_reasoning: bool = False, viz: bool = False) -> Dict[str, Any]
  - run_demo(domain: str = "employment_law") -> None
  - batch_analyze(directory: str, output_format: str = "summary", output_file: Optional[str] = None) -> None
- main() -> None  # argparse entrypoint

Usage:
    python cli_driver.py --help
    python cli_driver.py analyze --file document.txt
    python cli_driver.py demo --domain employment_law
    python cli_driver.py batch --directory test_documents/employment_law/
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

# Import our legal analysis system
from plugins.employment_law.plugin import EmploymentLawPlugin
from core.model import Context
from core.storage import GraphStore
from core.reasoning import RuleEngine, explain
# Optional visualization (PNG via Graphviz)
try:
    from viz.graphviz_renderer import visualize_analysis
except Exception:
    visualize_analysis = None


class LegalAnalysisCLI:
    """Command-line interface for legal hypergraph analysis"""
    
    def __init__(self):
        self.plugin = EmploymentLawPlugin()
        
    def analyze_document(self, file_path: str, output_format: str = "summary",
                        jurisdiction: str = "US", show_reasoning: bool = False,
                        viz: bool = False) -> Dict[str, Any]:
        """
        Analyze a single legal document
        
        Args:
            file_path: Path to document file
            output_format: Output format (summary, detailed, json)
            jurisdiction: Legal jurisdiction for analysis
            show_reasoning: Whether to show detailed reasoning steps
            
        Returns:
            Analysis results dictionary
        """
        try:
            # Read document
            with open(file_path, 'r', encoding='utf-8') as f:
                document_text = f.read()
            
            # Set up context
            context = Context(jurisdiction=jurisdiction, law_type="employment")
            
            # Analyze document
            print(f"🔍 Analyzing document: {Path(file_path).name}")
            print(f"📄 Document length: {len(document_text):,} characters")
            print(f"⚖️  Jurisdiction: {jurisdiction}")
            print()
            
            analysis = self.plugin.analyze_document(document_text, context)
            
            # Display results based on format
            if output_format == "json":
                result = self._format_json_output(analysis, file_path)
            elif output_format == "detailed":
                result = self._format_detailed_output(analysis, file_path, show_reasoning)
            else:  # summary
                result = self._format_summary_output(analysis, file_path)

            # Optional visualization (PNG saved next to input)
            if viz:
                if visualize_analysis is None:
                    print("⚠️  Visualization requested but graphviz not available. Install python-graphviz and Graphviz binaries.")
                else:
                    try:
                        out_png = visualize_analysis(analysis, source_document_path=file_path)
                        print(f"🖼️  Visualization saved: {out_png}")
                    except Exception as ve:
                        print(f"⚠️  Visualization failed: {ve}")

            return result
                
        except FileNotFoundError:
            print(f"❌ Error: File not found: {file_path}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error analyzing document: {e}")
            sys.exit(1)
    
    def _format_summary_output(self, analysis: Dict[str, Any], file_path: str) -> Dict[str, Any]:
        """Format analysis results as summary"""
        print("📊 ANALYSIS SUMMARY")
        print("=" * 60)
        
        # Entity extraction summary
        entity_counts = {}
        for entity in analysis['entities']:
            entity_type = entity['type']
            entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1
        
        print(f"🏷️  Entities Extracted: {len(analysis['entities'])} total")
        for entity_type, count in sorted(entity_counts.items()):
            print(f"   • {entity_type}: {count}")
        print()
        
        # Legal citations
        print(f"📚 Legal Citations: {len(analysis['citations'])}")
        for citation in analysis['citations']:
            print(f"   • {citation['text']}")
        print()
        
        # Legal conclusions
        print(f"⚖️  Legal Conclusions: {len(analysis['conclusions'])}")
        for conclusion in analysis['conclusions']:
            print(f"   • {conclusion['type']}: {conclusion['conclusion']}")
            print(f"     Legal Basis: {conclusion['legal_basis']}")
            print(f"     Confidence: {conclusion['confidence']:.1%}")
        print()
        
        return analysis
    
    def _format_detailed_output(self, analysis: Dict[str, Any], file_path: str, show_reasoning: bool) -> Dict[str, Any]:
        """Format analysis results with detailed information"""
        print("📋 DETAILED ANALYSIS REPORT")
        print("=" * 80)
        print(f"Document: {Path(file_path).name}")
        print(f"Analysis Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print()
        
        # Entities with details
        print("🏷️  ENTITY EXTRACTION RESULTS")
        print("-" * 50)
        for entity in analysis['entities']:
            print(f"Type: {entity['type']}")
            print(f"Text: {entity['text']}")
            print(f"Confidence: {entity['confidence']:.1%}")
            print(f"Category: {entity['metadata']['category']}")
            print()
        
        # Citations with normalization
        print("📚 LEGAL CITATIONS FOUND")
        print("-" * 50)
        for citation in analysis['citations']:
            print(f"Citation: {citation['text']}")
            print(f"Type: {citation['metadata']['citation_type']}")
            if 'normalized' in citation['metadata']:
                print(f"Normalized: {citation['metadata']['normalized']}")
            print()
        
        # Reasoning chain
        if show_reasoning:
            print("🧠 REASONING PROCESS")
            print("-" * 50)
            print("Original Facts:")
            for fact in analysis['original_facts']:
                print(f"   • {fact.get('statement', 'N/A')}")
            print()
            
            print("Derived Facts:")
            for fact in analysis['derived_facts']:
                print(f"   • {fact.get('statement', 'N/A')}")
                if 'rule_authority' in fact:
                    print(f"     Authority: {fact['rule_authority']}")
            print()
        
        # Legal conclusions
        print("⚖️  LEGAL CONCLUSIONS")
        print("-" * 50)
        for conclusion in analysis['conclusions']:
            print(f"Type: {conclusion['type']}")
            print(f"Conclusion: {conclusion['conclusion']}")
            print(f"Legal Basis: {conclusion['legal_basis']}")
            print(f"Confidence: {conclusion['confidence']:.1%}")
            print()
        
        return analysis
    
    def _format_json_output(self, analysis: Dict[str, Any], file_path: str) -> Dict[str, Any]:
        """Format analysis results as JSON"""
        # Add metadata
        output = {
            "document_path": str(file_path),
            "analysis_time": datetime.utcnow().isoformat(),
            "analysis_results": analysis
        }
        
        print(json.dumps(output, indent=2, default=str))
        return output
    
    def run_demo(self, domain: str = "employment_law"):
        """Run interactive demo of the legal analysis system"""
        print("🎯 LEGAL HYPERGRAPH ANALYSIS SYSTEM DEMO")
        print("=" * 80)
        print("Welcome to the provenance-first legal ontology hypergraph system!")
        print("This system provides explainable AI for legal document analysis.")
        print()
        
        if domain == "employment_law":
            self._run_employment_law_demo()
        else:
            print(f"❌ Demo domain '{domain}' not supported. Available: employment_law")
    
    def _run_employment_law_demo(self):
        """Run employment law specific demo"""
        print("📚 EMPLOYMENT LAW ANALYSIS CAPABILITIES")
        print("-" * 60)
        print("Supported Areas:")
        print("• ADA (Americans with Disabilities Act) - Reasonable accommodations")
        print("• FLSA (Fair Labor Standards Act) - Overtime and wage violations")
        print("• At-Will Employment - Wrongful termination exceptions")
        print("• Workers' Compensation - Workplace injury claims")
        print()
        
        # Show rule summary
        rules = self.plugin.rules.get_all_rules()
        rule_counts = {}
        for rule in rules:
            domain = "ADA" if "ada" in rule.id else \
                    "FLSA" if "flsa" in rule.id else \
                    "At-Will" if "at_will" in rule.id or "public_policy" in rule.id or "whistleblower" in rule.id else \
                    "Workers' Comp" if "workers_comp" in rule.id else "Other"
            rule_counts[domain] = rule_counts.get(domain, 0) + 1
        
        print(f"⚖️  LEGAL RULES LOADED: {len(rules)} total")
        for domain, count in sorted(rule_counts.items()):
            print(f"   • {domain}: {count} rules")
        print()
        
        # Check for test documents
        test_docs_path = Path("test_documents/employment_law/")
        if test_docs_path.exists():
            print("📄 AVAILABLE TEST DOCUMENTS")
            print("-" * 60)
            test_files = list(test_docs_path.glob("*.txt"))
            for i, doc in enumerate(test_files, 1):
                print(f"{i}. {doc.name}")
            print()
            
            # Interactive selection
            while True:
                try:
                    choice = input("Enter document number to analyze (or 'q' to quit): ").strip()
                    if choice.lower() == 'q':
                        break
                    
                    doc_num = int(choice) - 1
                    if 0 <= doc_num < len(test_files):
                        selected_doc = test_files[doc_num]
                        print(f"\n🔍 Analyzing: {selected_doc.name}")
                        print("=" * 60)
                        self.analyze_document(str(selected_doc), output_format="summary")
                        print("\n" + "=" * 60)
                    else:
                        print("❌ Invalid selection. Please try again.")
                        
                except ValueError:
                    print("❌ Invalid input. Please enter a number.")
                except KeyboardInterrupt:
                    print("\n👋 Demo interrupted by user.")
                    break
        else:
            print("❌ Test documents not found. Run from project root directory.")
    
    def batch_analyze(self, directory: str, output_format: str = "summary", 
                     output_file: Optional[str] = None):
        """Analyze multiple documents in a directory"""
        dir_path = Path(directory)
        if not dir_path.exists():
            print(f"❌ Directory not found: {directory}")
            sys.exit(1)
        
        # Find text files
        text_files = list(dir_path.glob("*.txt"))
        if not text_files:
            print(f"❌ No .txt files found in: {directory}")
            sys.exit(1)
        
        print(f"📁 BATCH ANALYSIS: {len(text_files)} documents")
        print("=" * 60)
        
        results = []
        for i, file_path in enumerate(text_files, 1):
            print(f"\n[{i}/{len(text_files)}] Analyzing: {file_path.name}")
            print("-" * 40)
            
            try:
                analysis = self.analyze_document(str(file_path), output_format="summary")
                results.append({
                    "file": str(file_path),
                    "status": "success",
                    "analysis": analysis
                })
            except Exception as e:
                print(f"❌ Error: {e}")
                results.append({
                    "file": str(file_path),
                    "status": "error",
                    "error": str(e)
                })
        
        # Summary
        successful = len([r for r in results if r["status"] == "success"])
        print(f"\n📊 BATCH ANALYSIS COMPLETE")
        print("=" * 60)
        print(f"Total Documents: {len(text_files)}")
        print(f"Successful: {successful}")
        print(f"Failed: {len(text_files) - successful}")
        
        # Save results if requested
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"💾 Results saved to: {output_file}")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Legal Hypergraph Analysis System - Employment Law CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a single document
  python cli_driver.py analyze --file test_documents/employment_law/ada_accommodation_request.txt

  # Detailed analysis with reasoning
  python cli_driver.py analyze --file document.txt --format detailed --show-reasoning

  # JSON output for integration
  python cli_driver.py analyze --file document.txt --format json

  # Interactive demo
  python cli_driver.py demo --domain employment_law

  # Batch analysis
  python cli_driver.py batch --directory test_documents/employment_law/
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze a single legal document')
    analyze_parser.add_argument('--file', '-f', required=True, help='Path to document file')
    analyze_parser.add_argument('--format', choices=['summary', 'detailed', 'json'], 
                               default='summary', help='Output format (default: summary)')
    analyze_parser.add_argument('--jurisdiction', '-j', default='US', 
                               help='Legal jurisdiction (default: US)')
    analyze_parser.add_argument('--show-reasoning', action='store_true',
                               help='Show detailed reasoning steps')
    analyze_parser.add_argument('--viz', action='store_true',
                               help='Render PNG visualization next to input (requires Graphviz)')
    
    # Demo command
    demo_parser = subparsers.add_parser('demo', help='Run interactive demo')
    demo_parser.add_argument('--domain', choices=['employment_law'], default='employment_law',
                            help='Legal domain for demo (default: employment_law)')
    
    # Batch command
    batch_parser = subparsers.add_parser('batch', help='Analyze multiple documents')
    batch_parser.add_argument('--directory', '-d', required=True, help='Directory containing documents')
    batch_parser.add_argument('--format', choices=['summary', 'detailed', 'json'],
                             default='summary', help='Output format (default: summary)')
    batch_parser.add_argument('--output', '-o', help='Save results to file (JSON format)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Initialize CLI
    cli = LegalAnalysisCLI()
    
    # Execute command
    try:
        if args.command == 'analyze':
            cli.analyze_document(
                file_path=args.file,
                output_format=args.format,
                jurisdiction=args.jurisdiction,
                show_reasoning=args.show_reasoning,
                viz=getattr(args, "viz", False)
            )
        elif args.command == 'demo':
            cli.run_demo(domain=args.domain)
        elif args.command == 'batch':
            cli.batch_analyze(
                directory=args.directory,
                output_format=args.format,
                output_file=args.output
            )
    except KeyboardInterrupt:
        print("\n👋 Analysis interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()