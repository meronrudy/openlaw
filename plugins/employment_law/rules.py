"""
Employment Law Rules Implementation

Implements legal rules for employment law reasoning including:
- ADA reasonable accommodation requirements and undue hardship analysis
- FLSA overtime calculations and exemption classifications
- At-will employment exceptions for wrongful termination claims
- Workers' compensation coverage and exclusivity principles

Rules are encoded as LegalRule objects for hypergraph reasoning.
"""

from typing import List, Dict, Any
from datetime import datetime

from core.rules import LegalRule
from core.model import Context


class EmploymentLawRules:
    """
    Employment law rule provider implementing domain-specific legal rules
    
    Provides rules for ADA, FLSA, at-will employment, and workers' compensation
    analysis using the hypergraph reasoning system.
    """
    
    def __init__(self):
        """Initialize employment law rules provider"""
        pass
    
    def get_ada_rules(self) -> List[LegalRule]:
        """
        Get ADA (Americans with Disabilities Act) rules
        
        Returns:
            List of ADA legal rules for reasonable accommodation analysis
        """
        rules = []
        
        # ADA Reasonable Accommodation Required
        rules.append(LegalRule(
            id="ada_accommodation_required",
            rule_type="statutory",
            priority=100,
            authority="42 U.S.C. § 12112(b)(5)(A)",
            jurisdiction=Context(
                jurisdiction="US",
                law_type="civil_rights",
                authority_level="federal"
            ),
            premises=[
                "employee_has_disability",
                "can_perform_essential_functions_with_accommodation"
            ],
            conclusions=["reasonable_accommodation_required"],
            rule_text="Employer must provide reasonable accommodation to qualified individual with disability unless it would impose undue hardship",
            exceptions=["undue_hardship"],
            confidence=0.95
        ))
        
        # ADA Undue Hardship Defense
        rules.append(LegalRule(
            id="ada_undue_hardship_defense",
            rule_type="statutory", 
            priority=90,
            authority="42 U.S.C. § 12112(b)(5)(A)",
            jurisdiction=Context(
                jurisdiction="US",
                law_type="civil_rights",
                authority_level="federal"
            ),
            premises=[
                "accommodation_causes_significant_difficulty",
                "accommodation_causes_significant_expense"
            ],
            conclusions=["undue_hardship"],
            rule_text="Accommodation that causes significant difficulty or expense relative to employer resources constitutes undue hardship",
            confidence=0.90
        ))
        
        # ADA Interactive Process Requirement
        rules.append(LegalRule(
            id="ada_interactive_process",
            rule_type="statutory",
            priority=95,
            authority="42 U.S.C. § 12112; 29 C.F.R. § 1630.2(o)",
            jurisdiction=Context(
                jurisdiction="US",
                law_type="civil_rights", 
                authority_level="federal"
            ),
            premises=[
                "employee_requests_accommodation",
                "employer_aware_of_disability"
            ],
            conclusions=["interactive_process_required"],
            rule_text="Employer must engage in interactive process to identify reasonable accommodation",
            confidence=0.92
        ))
        
        # ADA Qualified Individual Requirement
        rules.append(LegalRule(
            id="ada_qualified_individual",
            rule_type="statutory",
            priority=100,
            authority="42 U.S.C. § 12111(8)",
            jurisdiction=Context(
                jurisdiction="US",
                law_type="civil_rights",
                authority_level="federal"
            ),
            premises=[
                "employee_has_disability",
                "can_perform_essential_functions"
            ],
            conclusions=["qualified_individual_with_disability"],
            rule_text="Individual with disability who can perform essential job functions with or without reasonable accommodation",
            confidence=0.95
        ))
        
        return rules
    
    def get_flsa_rules(self) -> List[LegalRule]:
        """
        Get FLSA (Fair Labor Standards Act) rules
        
        Returns:
            List of FLSA legal rules for wage and hour analysis
        """
        rules = []
        
        # FLSA Overtime Required
        rules.append(LegalRule(
            id="flsa_overtime_required",
            rule_type="statutory",
            priority=100,
            authority="29 U.S.C. § 207(a)(1)",
            jurisdiction=Context(
                jurisdiction="US",
                law_type="labor",
                authority_level="federal"
            ),
            premises=[
                "worked_over_40_hours",
                "employee_non_exempt"
            ],
            conclusions=["overtime_pay_required"],
            rule_text="Employee shall receive overtime compensation at rate of not less than time and one-half for hours worked over 40 in workweek",
            confidence=0.98
        ))
        
        # FLSA Time and Half Rate
        rules.append(LegalRule(
            id="flsa_time_and_half",
            rule_type="statutory",
            priority=95,
            authority="29 U.S.C. § 207(a)(1)",
            jurisdiction=Context(
                jurisdiction="US",
                law_type="labor",
                authority_level="federal"
            ),
            premises=[
                "overtime_pay_required",
                "regular_hourly_rate_established"
            ],
            conclusions=["overtime_rate_time_and_half"],
            rule_text="Overtime rate shall be computed at time and one-half the regular rate of pay",
            confidence=0.98
        ))
        
        # FLSA Exempt Employee Exception
        rules.append(LegalRule(
            id="flsa_exempt_employee",
            rule_type="statutory",
            priority=90,
            authority="29 U.S.C. § 213(a)(1); 29 C.F.R. § 541",
            jurisdiction=Context(
                jurisdiction="US",
                law_type="labor",
                authority_level="federal"
            ),
            premises=[
                "employee_executive_duties",
                "salary_basis_payment",
                "salary_exceeds_minimum_threshold"
            ],
            conclusions=["employee_exempt_from_overtime"],
            rule_text="Executive, administrative, and professional employees paid on salary basis exceeding threshold are exempt from overtime",
            exceptions=["highly_compensated_employee"],
            confidence=0.85
        ))
        
        # FLSA Minimum Wage Requirement
        rules.append(LegalRule(
            id="flsa_minimum_wage",
            rule_type="statutory",
            priority=100,
            authority="29 U.S.C. § 206(a)(1)",
            jurisdiction=Context(
                jurisdiction="US",
                law_type="labor",
                authority_level="federal"
            ),
            premises=[
                "employee_covered_by_flsa",
                "hours_worked_established"
            ],
            conclusions=["minimum_wage_required"],
            rule_text="Covered employee shall receive not less than federal minimum wage for all hours worked",
            confidence=0.98
        ))
        
        return rules
    
    def get_at_will_rules(self) -> List[LegalRule]:
        """
        Get at-will employment rules
        
        Returns:
            List of at-will employment rules including exceptions
        """
        rules = []
        
        # At-Will General Rule
        rules.append(LegalRule(
            id="at_will_general_rule",
            rule_type="common_law",
            priority=70,
            authority="Restatement (Third) of Employment Law § 2.01",
            jurisdiction=Context(
                law_type="employment",
                authority_level="state"
            ),
            premises=[
                "at_will_employment",
                "no_specified_contract_term"
            ],
            conclusions=["termination_permitted_any_reason"],
            rule_text="Employment at will may be terminated by either party at any time for any reason or no reason",
            exceptions=["public_policy_exception", "implied_contract_exception"],
            confidence=0.85
        ))
        
        # Public Policy Exception
        rules.append(LegalRule(
            id="public_policy_exception",
            rule_type="common_law",
            priority=85,
            authority="Petermann v. International Brotherhood of Teamsters (Cal. 1959)",
            jurisdiction=Context(
                law_type="employment",
                authority_level="state"
            ),
            premises=[
                "at_will_employment",
                "terminated_for_protected_activity"
            ],
            conclusions=["wrongful_termination_claim_viable"],
            rule_text="Termination violates public policy when employee terminated for exercising legal rights or fulfilling legal obligations",
            confidence=0.80
        ))
        
        # Implied Contract Exception
        rules.append(LegalRule(
            id="implied_contract_exception",
            rule_type="common_law",
            priority=75,
            authority="Toussaint v. Blue Cross & Blue Shield (Mich. 1980)",
            jurisdiction=Context(
                law_type="employment",
                authority_level="state"
            ),
            premises=[
                "at_will_employment",
                "employer_promised_job_security",
                "employee_reasonably_relied_on_promise"
            ],
            conclusions=["implied_contract_for_cause_termination"],
            rule_text="Employer statements or policies may create implied contract limiting termination to just cause",
            confidence=0.70
        ))
        
        # Whistleblower Protection
        rules.append(LegalRule(
            id="whistleblower_protection",
            rule_type="statutory",
            priority=90,
            authority="Various state whistleblower statutes",
            jurisdiction=Context(
                law_type="employment",
                authority_level="state"
            ),
            premises=[
                "employee_reported_illegal_activity",
                "termination_following_report"
            ],
            conclusions=["wrongful_termination_claim_viable"],
            rule_text="Termination in retaliation for reporting illegal activity violates whistleblower protection",
            confidence=0.85
        ))
        
        return rules
    
    def get_workers_comp_rules(self) -> List[LegalRule]:
        """
        Get workers' compensation rules
        
        Returns:
            List of workers' compensation coverage and exclusivity rules
        """
        rules = []
        
        # Workers' Compensation Coverage
        rules.append(LegalRule(
            id="workers_comp_coverage",
            rule_type="statutory",
            priority=95,
            authority="State Workers' Compensation Statutes",
            jurisdiction=Context(
                law_type="workers_compensation",
                authority_level="state"
            ),
            premises=[
                "injury_in_course_of_employment",
                "injury_arising_out_of_employment"
            ],
            conclusions=["workers_comp_benefits_available"],
            rule_text="Employee injured in course and scope of employment entitled to workers' compensation benefits",
            confidence=0.90
        ))
        
        # Course of Employment Test
        rules.append(LegalRule(
            id="course_of_employment",
            rule_type="statutory",
            priority=90,
            authority="State Workers' Compensation Statutes",
            jurisdiction=Context(
                law_type="workers_compensation",
                authority_level="state"
            ),
            premises=[
                "injury_during_work_hours",
                "injury_at_work_location",
                "injury_performing_work_duties"
            ],
            conclusions=["injury_in_course_of_employment"],
            rule_text="Injury occurs in course of employment when sustained during work hours while performing work duties",
            confidence=0.85
        ))
        
        # Workers' Compensation Exclusivity
        rules.append(LegalRule(
            id="workers_comp_exclusivity",
            rule_type="statutory",
            priority=85,
            authority="State Workers' Compensation Statutes",
            jurisdiction=Context(
                law_type="workers_compensation",
                authority_level="state"
            ),
            premises=[
                "workers_comp_benefits_available",
                "injury_covered_by_workers_comp"
            ],
            conclusions=["tort_lawsuit_barred"],
            rule_text="Workers' compensation is exclusive remedy for covered workplace injuries, barring tort lawsuits",
            exceptions=["intentional_tort_by_employer"],
            confidence=0.90
        ))
        
        # Retaliation Protection
        rules.append(LegalRule(
            id="workers_comp_retaliation",
            rule_type="statutory",
            priority=88,
            authority="State Workers' Compensation Statutes",
            jurisdiction=Context(
                law_type="workers_compensation",
                authority_level="state"
            ),
            premises=[
                "filed_workers_comp_claim",
                "adverse_employment_action_following_claim"
            ],
            conclusions=["workers_comp_retaliation_claim"],
            rule_text="Employer prohibited from retaliating against employee for filing workers' compensation claim",
            confidence=0.92
        ))
        
        return rules
    
    def get_all_rules(self) -> List[LegalRule]:
        """
        Get all employment law rules
        
        Returns:
            Combined list of all employment law rules
        """
        all_rules = []
        all_rules.extend(self.get_ada_rules())
        all_rules.extend(self.get_flsa_rules())
        all_rules.extend(self.get_at_will_rules())
        all_rules.extend(self.get_workers_comp_rules())
        return all_rules
    
    def get_rules_by_domain(self, domain: str) -> List[LegalRule]:
        """
        Get rules for specific employment law domain
        
        Args:
            domain: Employment law domain (ada, flsa, at_will, workers_comp)
            
        Returns:
            List of rules for the specified domain
        """
        domain_map = {
            "ada": self.get_ada_rules,
            "flsa": self.get_flsa_rules,
            "at_will": self.get_at_will_rules,
            "workers_comp": self.get_workers_comp_rules
        }
        
        if domain in domain_map:
            return domain_map[domain]()
        else:
            raise ValueError(f"Unknown employment law domain: {domain}")