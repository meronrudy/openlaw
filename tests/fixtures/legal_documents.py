"""
Test Fixtures: Legal Documents for End-to-End Testing

Contains realistic legal document text for testing various employment law scenarios.
These documents are designed to trigger specific legal rules and reasoning chains.
"""

class TestDocuments:
    """Collection of test legal documents for various employment law scenarios"""
    
    ADA_ACCOMMODATION_REQUEST = """
    Employee Jane Smith, who has been diagnosed with a visual impairment that substantially 
    limits her ability to see, works as a data analyst for Acme Corporation, which employs 
    over 200 people. Jane submitted a written request to HR on February 1, 2024, asking 
    for a reasonable accommodation in the form of screen reading software (JAWS) and 
    adjustable lighting at her workstation. 
    
    Jane is otherwise qualified to perform the essential functions of her position and has 
    received satisfactory performance reviews for the past three years. She holds a 
    Bachelor's degree in Computer Science and has completed all required certifications 
    for her role.
    
    The requested accommodations would cost approximately $2,500 to implement and would not 
    fundamentally alter the nature of Jane's job duties. Acme Corporation's annual revenue 
    exceeds $50 million, and the company has previously provided accommodations for other 
    employees with disabilities.
    
    Under the Americans with Disabilities Act (ADA), 42 U.S.C. § 12112(b)(5)(A), covered 
    employers must provide reasonable accommodations to qualified individuals with 
    disabilities unless doing so would impose an undue hardship.
    """
    
    ADA_UNDUE_HARDSHIP_SCENARIO = """
    Mary Johnson, an employee with mobility limitations requiring a wheelchair, works for 
    Small Tech Startup, a company with 18 employees. Mary has requested that the company 
    install an elevator to access the second-floor offices where her team is located.
    
    The building is a historic structure, and installing an elevator would require 
    significant structural modifications costing approximately $150,000. Small Tech 
    Startup's annual revenue is $200,000, and the company is currently operating at a loss.
    
    The accommodation would represent 75% of the company's annual revenue and would require 
    taking on substantial debt. Alternative accommodations such as relocating Mary's team 
    to the first floor have been offered but would significantly disrupt operations and 
    require relocating 12 other employees.
    
    Under 42 U.S.C. § 12112(b)(5)(A), employers must provide reasonable accommodations 
    unless they constitute an undue hardship considering the employer's size, financial 
    resources, and the nature of the accommodation.
    """
    
    FLSA_OVERTIME_SCENARIO = """
    John Martinez works as a non-exempt warehouse associate for Global Logistics Inc., 
    a company engaged in interstate commerce. During the week of March 4-10, 2024, 
    John worked the following hours:

    Monday: 9 hours
    Tuesday: 10 hours  
    Wednesday: 8 hours
    Thursday: 12 hours
    Friday: 9 hours
    Saturday: 6 hours

    Total: 54 hours

    John's regular hourly rate is $18.00 per hour. He was paid his regular rate for 
    all 54 hours worked, receiving $972.00 for the week. However, he received no 
    overtime premium for the 14 hours worked over 40 hours in the workweek.
    
    Under the Fair Labor Standards Act (FLSA), 29 U.S.C. § 207(a)(1), non-exempt 
    employees must be paid overtime compensation at a rate of not less than one and 
    one-half times their regular rate for all hours worked over 40 in a workweek.
    
    John should have received $18.00 for the first 40 hours ($720.00) plus $27.00 
    per hour for the 14 overtime hours ($378.00), for a total of $1,098.00.
    """
    
    AT_WILL_RETALIATION_SCENARIO = """
    Sarah Johnson was employed as a sales manager at TechStart Inc., an at-will employer 
    located in Texas, for three years. On April 15, 2024, Sarah reported to HR that her 
    supervisor, Mike Davis, had been making inappropriate comments about her appearance 
    and had suggested that her performance reviews would improve if she agreed to have 
    dinner with him outside of work.
    
    Sarah documented these incidents in writing and provided specific dates and witnesses. 
    HR acknowledged receipt of her complaint and indicated they would investigate the matter.
    
    Two weeks after filing the complaint, on April 29, 2024, Sarah received a termination 
    notice stating that her position was being eliminated due to "restructuring and budget 
    constraints." However, Sarah observed that a male colleague, Tom Wilson, with lower 
    sales numbers and less experience was promoted to a similar sales manager role the 
    following month.
    
    While Texas is an at-will employment state, termination in retaliation for filing 
    a sexual harassment complaint may violate Title VII of the Civil Rights Act of 1964, 
    42 U.S.C. § 2000e-3(a), which prohibits retaliation against employees who oppose 
    unlawful employment practices.
    """
    
    WORKERS_COMP_SCENARIO = """
    On May 3, 2024, construction worker Carlos Rodriguez was injured while operating 
    a forklift at the Riverside Construction site. Carlos had completed mandatory 
    safety training two months prior and was wearing all required protective equipment, 
    including a hard hat, safety vest, and steel-toed boots.
    
    While moving materials from the loading dock to the construction area, a defective 
    hydraulic line in the forklift burst without warning, causing the forklift to tip 
    and pin Carlos's left leg. The incident was witnessed by two coworkers and recorded 
    on the site's security cameras.
    
    Carlos was immediately transported to Metro General Hospital where he underwent 
    emergency surgery for a compound fracture of his left tibia and fibula. Medical 
    records indicate he will require 8-12 weeks of recovery and extensive physical 
    therapy before returning to work.
    
    Carlos has been employed by Riverside Construction for 18 months as a full-time 
    employee and has no prior workplace injury claims. The forklift had last been 
    inspected six months ago and was due for its next scheduled maintenance inspection.
    
    Post-incident investigation revealed that the hydraulic line failure was due to 
    normal wear and tear rather than operator error or safety violations.
    """
    
    MULTI_DOMAIN_SCENARIO = """
    Lisa Chen, an employee with hearing impairment who is deaf, works as a software 
    engineer for DataCorp, a technology company with 150 employees. Lisa uses American 
    Sign Language (ASL) as her primary language and has requested an ASL interpreter 
    for team meetings and presentations as a reasonable accommodation under the ADA.
    
    During the week of June 10-16, 2024, Lisa worked the following hours due to a 
    critical project deadline:
    
    Monday: 11 hours
    Tuesday: 12 hours
    Wednesday: 10 hours
    Thursday: 13 hours
    Friday: 10 hours
    
    Total: 56 hours
    
    Lisa's regular salary is equivalent to $25.00 per hour for a 40-hour work week. 
    As a non-exempt employee under the FLSA, she is entitled to overtime compensation 
    for the 16 hours worked over 40 hours.
    
    DataCorp has provided the ASL interpreter for some meetings but has refused to 
    provide interpretation for "informal team discussions" citing cost concerns. The 
    company also failed to pay Lisa overtime compensation for her extra hours, stating 
    that project deadlines justified the additional work without extra pay.
    
    This scenario involves both ADA accommodation requirements under 42 U.S.C. § 12112 
    and FLSA overtime obligations under 29 U.S.C. § 207(a)(1).
    """
    
    CITATION_HEAVY_DOCUMENT = """
    The legal framework governing employment discrimination is established by multiple 
    federal statutes. Title VII of the Civil Rights Act of 1964, 42 U.S.C. § 2000e et seq., 
    prohibits employment discrimination based on race, color, religion, sex, or national origin.
    
    The Americans with Disabilities Act, 42 U.S.C. § 12112, extends protection to qualified 
    individuals with disabilities. In McDonnell Douglas Corp. v. Green, 411 U.S. 792 (1973), 
    the Supreme Court established the burden-shifting framework for discrimination claims.
    
    The Equal Employment Opportunity Commission (EEOC) has issued guidance on reasonable 
    accommodations in 29 C.F.R. § 1630.2(o). Recent circuit court decisions, including 
    EEOC v. Abercrombie & Fitch Stores, Inc., 575 U.S. 768 (2015), have clarified the 
    scope of religious accommodation requirements.
    
    State laws may provide additional protections. For example, the California Fair 
    Employment and Housing Act (FEHA), Cal. Gov. Code § 12900 et seq., provides broader 
    coverage than federal law in some areas.
    """
    
    COMPLEX_LEGAL_REASONING = """
    ABC Manufacturing, a company with 75 employees, implemented a new attendance policy 
    requiring all employees to work mandatory overtime during peak production periods. 
    The policy states that failure to work required overtime may result in termination.
    
    Employee Maria Santos, who has Type 1 diabetes, submitted medical documentation 
    indicating that working more than 10 hours per day causes dangerous fluctuations 
    in her blood sugar levels. She requested an accommodation to be exempt from 
    mandatory overtime exceeding 10 hours per day.
    
    ABC Manufacturing denied the request, stating that all employees must be treated 
    equally and that the overtime policy is essential for meeting customer demands. 
    The company terminated Maria when she refused to work a scheduled 12-hour shift.
    
    Analysis must consider: (1) whether Type 1 diabetes constitutes a disability under 
    the ADA; (2) whether the requested accommodation is reasonable; (3) whether 
    equal treatment policies can override ADA accommodation requirements; (4) whether 
    the termination constitutes disability discrimination; and (5) potential defenses 
    such as undue hardship or essential functions.
    
    Relevant authorities include 42 U.S.C. § 12112, 29 C.F.R. § 1630.2, and cases 
    such as US Airways, Inc. v. Barnett, 535 U.S. 391 (2002).
    """


class TestLegalFactPatterns:
    """Specific legal fact patterns for targeted rule testing"""
    
    ADA_ESSENTIAL_FUNCTIONS = """
    Robert Kim works as a delivery driver for QuickShip Express. Due to a recent back 
    injury, Robert can no longer lift packages weighing more than 25 pounds. His job 
    description requires lifting packages up to 70 pounds. Robert has requested 
    accommodation to have a coworker assist with heavy packages or to be reassigned 
    to lighter delivery routes.
    """
    
    FLSA_EXEMPT_EMPLOYEE = """
    Dr. Amanda Foster works as a licensed physician for City Medical Center. She is 
    classified as an exempt employee and receives an annual salary of $180,000. 
    Last month, Dr. Foster worked 65 hours per week due to emergency surgeries and 
    patient care responsibilities. She is requesting overtime compensation for hours 
    worked over 40 per week.
    """
    
    PREGNANCY_DISCRIMINATION = """
    Jennifer Walsh, a marketing coordinator at Premier Agency, informed her supervisor 
    that she is pregnant and will need time off for prenatal appointments. Two weeks 
    later, she was demoted to a lower-paying administrative assistant position. Her 
    supervisor stated that the company needs someone "more reliable" in the marketing 
    coordinator role.
    """
    
    RELIGIOUS_ACCOMMODATION = """
    Ahmed Hassan, a practicing Muslim, works as a cashier at Downtown Grocery. He has 
    requested time off on Fridays from 12:00-1:30 PM to attend Jummah (Friday prayer). 
    The store manager refused, stating that Friday afternoons are the busiest time and 
    all cashiers must be available. Ahmed was written up for leaving his shift to 
    attend prayer.
    """


class TestDocumentMetadata:
    """Metadata for test documents to support various testing scenarios"""
    
    DOCUMENT_CLASSIFICATIONS = {
        'ADA_ACCOMMODATION_REQUEST': {
            'legal_domains': ['employment', 'disability_rights', 'civil_rights'],
            'expected_entities': ['Employee', 'Employer', 'Disability', 'AccommodationRequest'],
            'expected_obligations': ['provide_reasonable_accommodation'],
            'legal_authorities': ['42 U.S.C. § 12112'],
            'complexity_level': 'medium',
            'jurisdiction': 'federal'
        },
        'FLSA_OVERTIME_SCENARIO': {
            'legal_domains': ['employment', 'wage_hour'],
            'expected_entities': ['Employee', 'Employer', 'WorkHours', 'Wage'],
            'expected_obligations': ['pay_overtime_compensation'],
            'legal_authorities': ['29 U.S.C. § 207'],
            'complexity_level': 'low',
            'jurisdiction': 'federal'
        },
        'WORKERS_COMP_SCENARIO': {
            'legal_domains': ['employment', 'workers_compensation', 'workplace_safety'],
            'expected_entities': ['Employee', 'Employer', 'WorkplaceInjury', 'WorkplaceCondition'],
            'expected_relations': ['causation'],
            'expected_obligations': ['provide_workers_compensation'],
            'legal_authorities': ['state workers compensation statutes'],
            'complexity_level': 'high',
            'jurisdiction': 'state'
        },
        'MULTI_DOMAIN_SCENARIO': {
            'legal_domains': ['employment', 'disability_rights', 'wage_hour'],
            'expected_entities': ['Employee', 'Employer', 'Disability', 'WorkHours'],
            'expected_obligations': ['provide_reasonable_accommodation', 'pay_overtime_compensation'],
            'legal_authorities': ['42 U.S.C. § 12112', '29 U.S.C. § 207'],
            'complexity_level': 'high',
            'jurisdiction': 'federal'
        }
    }
    
    @classmethod
    def get_metadata(cls, document_name: str) -> dict:
        """Get metadata for a specific test document"""
        return cls.DOCUMENT_CLASSIFICATIONS.get(document_name, {})
    
    @classmethod
    def get_expected_entities(cls, document_name: str) -> list:
        """Get expected entity types for a document"""
        return cls.get_metadata(document_name).get('expected_entities', [])
    
    @classmethod
    def get_expected_obligations(cls, document_name: str) -> list:
        """Get expected legal obligations for a document"""
        return cls.get_metadata(document_name).get('expected_obligations', [])
    
    @classmethod
    def get_legal_authorities(cls, document_name: str) -> list:
        """Get expected legal authorities cited in analysis"""
        return cls.get_metadata(document_name).get('legal_authorities', [])


class TestRulePatterns:
    """Test patterns for specific legal rule testing"""
    
    ADA_RULE_PATTERN = {
        'rule_id': 'ada_reasonable_accommodation',
        'premises': [
            {'type': 'Employee', 'conditions': {'qualified': True}},
            {'type': 'Disability', 'conditions': {'substantially_limits': True}},
            {'type': 'AccommodationRequest', 'conditions': {'reasonable': True}},
            {'type': 'Employer', 'conditions': {'size': '>=15_employees'}}
        ],
        'conclusions': [
            {'type': 'Obligation', 'action': 'provide_reasonable_accommodation'}
        ],
        'exceptions': [
            {'type': 'UndueHardship', 'effect': 'overrides_obligation'}
        ]
    }
    
    FLSA_RULE_PATTERN = {
        'rule_id': 'flsa_overtime_obligation',
        'premises': [
            {'type': 'Employee', 'conditions': {'exempt': False}},
            {'type': 'WorkHours', 'conditions': {'weekly_total': '>40'}},
            {'type': 'Employer', 'conditions': {'covered': True}}
        ],
        'conclusions': [
            {'type': 'Obligation', 'action': 'pay_overtime_compensation', 'rate': '1.5x'}
        ]
    }