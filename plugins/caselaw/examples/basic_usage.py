"""
Basic Usage Examples for CAP Caselaw Plugin
"""

import asyncio
from pathlib import Path
from datetime import datetime

# Import OpenLaw core components
from core.model import Context

# Import plugin components
from plugins.caselaw.plugin import CaselawPlugin
from plugins.caselaw.config.config_manager import ConfigManager


async def basic_document_analysis():
    """
    Example: Basic document analysis with citation extraction
    """
    print("=== Basic Document Analysis ===")
    
    # Initialize plugin with test configuration
    config = {
        "storage": {
            "use_mock": True,  # Use mock storage for testing
            "neo4j_enabled": False,
            "redis_enabled": False,
            "elasticsearch_enabled": False
        },
        "extraction": {
            "enable_ml_citation_extraction": True,
            "citation_confidence_threshold": 0.7
        }
    }
    
    plugin = CaselawPlugin(config=config)
    await plugin.initialize()
    
    # Sample legal text with citations
    legal_text = """
    In Brown v. Board of Education, 347 U.S. 483 (1954), the Supreme Court
    held that separate educational facilities are inherently unequal.
    This landmark decision overruled Plessy v. Ferguson, 163 U.S. 537 (1896),
    which had established the "separate but equal" doctrine.
    
    The Court's reasoning was later cited in Miranda v. Arizona, 384 U.S. 436 (1966),
    where the Court established procedural safeguards for criminal suspects.
    See also 42 U.S.C. § 1983 (civil rights enforcement).
    """
    
    # Create analysis context
    context = Context(
        domain="constitutional_law",
        jurisdiction="federal",
        user_id="example_user",
        session_id="basic_example"
    )
    
    # Analyze the document
    result = await plugin.analyze_document(legal_text, context)
    
    # Display results
    print(f"Document ID: {result['document_id']}")
    print(f"Citations found: {len(result['citations'])}")
    print(f"Relationships found: {len(result['relationships'])}")
    print(f"Conclusions: {len(result['conclusions'])}")
    
    # Show extracted citations
    print("\nExtracted Citations:")
    for i, citation in enumerate(result['citations'], 1):
        print(f"  {i}. {citation.get('full_citation', 'N/A')} (confidence: {citation.get('confidence', 0):.2f})")
    
    # Show case relationships
    print("\nCase Relationships:")
    for i, relationship in enumerate(result['relationships'], 1):
        rel_type = relationship.get('relationship_type', 'unknown')
        confidence = relationship.get('confidence', 0)
        print(f"  {i}. {rel_type} (confidence: {confidence:.2f})")
    
    await plugin.shutdown()


async def precedent_search_example():
    """
    Example: Searching for legal precedents
    """
    print("\n=== Precedent Search ===")
    
    config = {
        "storage": {"use_mock": True},
        "api": {"enable_query_api": True, "max_search_results": 10}
    }
    
    plugin = CaselawPlugin(config=config)
    await plugin.initialize()
    
    # Search for precedents on constitutional due process
    legal_issue = "constitutional due process requirements"
    jurisdiction = "federal"
    date_range = {"start": "1950-01-01", "end": "2023-12-31"}
    
    try:
        precedents = await plugin.query_precedents(
            legal_issue=legal_issue,
            jurisdiction=jurisdiction,
            date_range=date_range
        )
        
        print(f"Found precedents for '{legal_issue}':")
        print(f"Results: {len(precedents.get('results', []))}")
        
        # Display sample results (if any)
        for i, precedent in enumerate(precedents.get('results', [])[:3], 1):
            case_name = precedent.get('case_name', 'Unknown Case')
            relevance = precedent.get('relevance_score', 0)
            print(f"  {i}. {case_name} (relevance: {relevance:.2f})")
    
    except Exception as e:
        print(f"Search completed (mock mode): {e}")
    
    await plugin.shutdown()


async def provenance_tracing_example():
    """
    Example: Tracing provenance of legal conclusions
    """
    print("\n=== Provenance Tracing ===")
    
    config = {
        "storage": {"use_mock": True},
        "api": {"enable_provenance_api": True}
    }
    
    plugin = CaselawPlugin(config=config)
    await plugin.initialize()
    
    # Trace provenance of a legal conclusion
    conclusion = "Separate educational facilities are inherently unequal"
    context = {"domain": "constitutional_law", "jurisdiction": "federal"}
    
    try:
        provenance_chain = await plugin.trace_provenance(conclusion, context)
        
        print(f"Provenance chain for: '{conclusion}'")
        print(f"Primary sources: {len(provenance_chain.get('primary_sources', []))}")
        print(f"Reasoning steps: {len(provenance_chain.get('reasoning_steps', []))}")
        print(f"Confidence: {provenance_chain.get('confidence', 0):.2f}")
        
        # Show audit trail
        audit_trail = provenance_chain.get('complete_audit_trail', [])
        print(f"Audit trail entries: {len(audit_trail)}")
    
    except Exception as e:
        print(f"Provenance tracing completed (mock mode): {e}")
    
    await plugin.shutdown()


async def why_from_where_examples():
    """
    Example: Answering "why" and "from where" questions
    """
    print("\n=== Why/From Where Questions ===")
    
    config = {
        "storage": {"use_mock": True},
        "api": {"enable_provenance_api": True}
    }
    
    plugin = CaselawPlugin(config=config)
    await plugin.initialize()
    
    # Answer a "why" question
    why_question = "Why are separate educational facilities considered unequal?"
    context = {"domain": "constitutional_law"}
    
    try:
        why_answer = await plugin.answer_why_question(why_question, context)
        
        print(f"Question: {why_question}")
        print(f"Answer: {why_answer.get('answer', 'No answer available')}")
        print(f"Legal basis: {len(why_answer.get('legal_basis', []))} sources")
        print(f"Confidence: {why_answer.get('confidence', 0):.2f}")
    
    except Exception as e:
        print(f"Why question answered (mock mode): {e}")
    
    # Answer a "from where" question
    from_where_question = "From where does the principle of equal protection originate?"
    target_claim = "Equal protection under the law"
    
    try:
        from_where_answer = await plugin.answer_from_where_question(
            from_where_question, target_claim, context
        )
        
        print(f"\nQuestion: {from_where_question}")
        print(f"Original sources: {len(from_where_answer.get('original_sources', []))}")
        print(f"Citation chain: {len(from_where_answer.get('citation_chain', []))}")
        print(f"Verification: {from_where_answer.get('verification_status', 'unknown')}")
    
    except Exception as e:
        print(f"From where question answered (mock mode): {e}")
    
    await plugin.shutdown()


async def claim_verification_example():
    """
    Example: Verifying legal claims against sources
    """
    print("\n=== Legal Claim Verification ===")
    
    config = {
        "storage": {"use_mock": True},
        "api": {"enable_provenance_api": True}
    }
    
    plugin = CaselawPlugin(config=config)
    await plugin.initialize()
    
    # Verify a legal claim
    claim = "The Supreme Court established that separate educational facilities are inherently unequal"
    sources = ["cap:brown_v_board_1954", "cap:plessy_v_ferguson_1896"]
    context = {"verification_type": "constitutional_principle"}
    
    try:
        verification = await plugin.verify_legal_claim(claim, sources, context)
        
        print(f"Claim: {claim}")
        print(f"Verified: {verification.get('verified', False)}")
        print(f"Confidence: {verification.get('confidence', 0):.2f}")
        print(f"Supporting evidence: {len(verification.get('supporting_evidence', []))}")
        print(f"Contradicting evidence: {len(verification.get('contradicting_evidence', []))}")
    
    except Exception as e:
        print(f"Claim verification completed (mock mode): {e}")
    
    await plugin.shutdown()


async def configuration_example():
    """
    Example: Working with plugin configuration
    """
    print("\n=== Configuration Management ===")
    
    # Load configuration from file
    config_manager = ConfigManager()
    config = config_manager.load_config()
    
    print("Plugin Configuration:")
    print(f"  Storage backend: {'Mock' if config.storage.use_mock else 'Production'}")
    print(f"  Neo4j enabled: {config.storage.neo4j_enabled}")
    print(f"  Redis enabled: {config.storage.redis_enabled}")
    print(f"  Elasticsearch enabled: {config.storage.elasticsearch_enabled}")
    print(f"  ML extraction: {config.extraction.enable_ml_citation_extraction}")
    print(f"  Background ingestion: {config.ingestion.enable_background_ingestion}")
    print(f"  Batch size: {config.ingestion.ingestion_batch_size}")
    
    # Validate configuration
    is_valid = config_manager.validate_config(config)
    print(f"Configuration valid: {is_valid}")
    
    # Get environment template
    env_template = config_manager.get_environment_template()
    print(f"Environment template length: {len(env_template)} characters")


async def health_check_example():
    """
    Example: Plugin health checking
    """
    print("\n=== Health Check ===")
    
    config = {"storage": {"use_mock": True}}
    plugin = CaselawPlugin(config=config)
    
    # Check health before initialization
    health = await plugin.health_check()
    print(f"Health before init: {health['status']}")
    
    # Initialize and check again
    await plugin.initialize()
    health = await plugin.health_check()
    
    print(f"Plugin: {health['plugin_name']} v{health['version']}")
    print(f"Status: {health['status']}")
    print(f"Initialized: {health['initialized']}")
    print(f"Supported domains: {len(health['supported_domains'])}")
    
    # Show plugin capabilities
    plugin_info = plugin.get_plugin_info()
    print(f"Capabilities: {len(plugin_info['capabilities'])}")
    
    for capability, enabled in plugin_info['capabilities'].items():
        print(f"  - {capability}: {'✓' if enabled else '✗'}")
    
    await plugin.shutdown()


async def run_all_examples():
    """
    Run all usage examples
    """
    print("CAP Caselaw Plugin - Usage Examples")
    print("=" * 50)
    
    examples = [
        basic_document_analysis,
        precedent_search_example,
        provenance_tracing_example,
        why_from_where_examples,
        claim_verification_example,
        configuration_example,
        health_check_example
    ]
    
    for example in examples:
        try:
            await example()
        except Exception as e:
            print(f"Example error: {e}")
        print()  # Add spacing between examples
    
    print("All examples completed!")


if __name__ == "__main__":
    # Run examples
    asyncio.run(run_all_examples())