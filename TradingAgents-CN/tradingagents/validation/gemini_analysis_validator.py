#!/usr/bin/env python3
"""
Gemini Analysis Validator
Validates that Gemini 2.5 Pro model parameters actually fix incomplete analysis issues
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path

from langchain_google_genai import ChatGoogleGenerativeAI

from tradingagents.utils.logging_manager import get_logger
from tradingagents.config.config_manager import config_manager, token_tracker

logger = get_logger('validation')


@dataclass
class ValidationTestCase:
    """A test case for validating analysis completeness"""
    name: str
    description: str
    input_prompt: str
    expected_keywords: List[str]  # Keywords that should appear in complete analysis
    min_response_length: int
    max_acceptable_cost: float  # Maximum acceptable cost in USD


@dataclass
class ValidationResult:
    """Result of a validation test"""
    test_case_name: str
    success: bool
    response_length: int
    contains_keywords: List[str]
    missing_keywords: List[str]
    response_time_seconds: float
    token_usage: Dict[str, int]
    estimated_cost: float
    error_message: Optional[str] = None


class GeminiAnalysisValidator:
    """Validates Gemini model analysis completeness and cost effectiveness"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.test_cases = self._create_test_cases()
        self.results_dir = Path("validation_results")
        self.results_dir.mkdir(exist_ok=True)
        
    def _create_test_cases(self) -> List[ValidationTestCase]:
        """Create comprehensive test cases for validation"""
        return [
            ValidationTestCase(
                name="basic_stock_analysis",
                description="Basic stock analysis completeness test",
                input_prompt="""
                Analyze NVDA stock for investment decision. Provide a comprehensive analysis including:
                1. Current market position and trends
                2. Financial health assessment
                3. Risk factors
                4. Investment recommendation with reasoning
                5. Price targets and timeline
                
                Be thorough and provide specific details for each section.
                """,
                expected_keywords=[
                    "financial", "revenue", "profit", "market", "competition", 
                    "risk", "recommendation", "price target", "growth", "valuation"
                ],
                min_response_length=1500,
                max_acceptable_cost=0.50  # $0.50 USD
            ),
            ValidationTestCase(
                name="complex_market_analysis",
                description="Complex multi-factor market analysis test",
                input_prompt="""
                Conduct a detailed analysis of the semiconductor sector focusing on:
                1. Market dynamics and competitive landscape
                2. Technology trends (AI, 5G, autonomous vehicles)
                3. Supply chain considerations
                4. Regulatory environment and geopolitical factors
                5. Investment opportunities and risks
                6. Sector outlook for next 12-24 months
                
                Provide specific companies, data points, and actionable insights.
                """,
                expected_keywords=[
                    "semiconductor", "AI", "supply chain", "competition", "technology",
                    "regulatory", "geopolitical", "investment", "outlook", "companies",
                    "data", "insights", "trends", "opportunities"
                ],
                min_response_length=2000,
                max_acceptable_cost=0.75  # $0.75 USD
            ),
            ValidationTestCase(
                name="risk_assessment",
                description="Comprehensive risk assessment test",
                input_prompt="""
                Perform a comprehensive risk assessment for a technology stock portfolio including:
                1. Market risk factors and volatility analysis
                2. Sector-specific risks and dependencies
                3. Economic indicators and their impact
                4. Regulatory and compliance risks
                5. Operational and execution risks
                6. Risk mitigation strategies
                7. Portfolio diversification recommendations
                
                Include quantitative metrics where applicable.
                """,
                expected_keywords=[
                    "risk", "volatility", "market", "sector", "economic", "regulatory",
                    "operational", "mitigation", "diversification", "quantitative",
                    "metrics", "portfolio", "assessment", "impact"
                ],
                min_response_length=1800,
                max_acceptable_cost=0.60  # $0.60 USD
            )
        ]
    
    def validate_model_parameters(
        self, 
        model_name: str,
        parameters: Dict[str, Any],
        baseline_parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Validate model parameters against test cases
        
        Args:
            model_name: Gemini model name
            parameters: Model parameters to test
            baseline_parameters: Optional baseline parameters for comparison
            
        Returns:
            Comprehensive validation report
        """
        logger.info(f"🧪 Starting validation for {model_name} with parameters: {parameters}")
        
        # Test current parameters
        current_results = self._run_test_suite(model_name, parameters)
        
        # Test baseline parameters if provided
        baseline_results = None
        if baseline_parameters:
            logger.info(f"🔄 Running baseline tests with parameters: {baseline_parameters}")
            baseline_results = self._run_test_suite(model_name, baseline_parameters, is_baseline=True)
        
        # Generate comprehensive report
        report = self._generate_validation_report(
            model_name, parameters, current_results, 
            baseline_parameters, baseline_results
        )
        
        # Save results
        self._save_validation_results(report)
        
        return report
    
    def _run_test_suite(
        self, 
        model_name: str, 
        parameters: Dict[str, Any],
        is_baseline: bool = False
    ) -> List[ValidationResult]:
        """Run all test cases with given parameters"""
        results = []
        test_prefix = "baseline" if is_baseline else "current"
        
        logger.info(f"🎯 Running {test_prefix} test suite with {len(self.test_cases)} test cases")
        
        for i, test_case in enumerate(self.test_cases, 1):
            logger.info(f"📋 Running test {i}/{len(self.test_cases)}: {test_case.name}")
            
            try:
                result = self._run_single_test(model_name, parameters, test_case)
                results.append(result)
                
                # Log immediate result
                status = "✅ PASS" if result.success else "❌ FAIL"
                logger.info(
                    f"{status} {test_case.name}: "
                    f"Length={result.response_length}, "
                    f"Keywords={len(result.contains_keywords)}/{len(test_case.expected_keywords)}, "
                    f"Cost=${result.estimated_cost:.4f}, "
                    f"Time={result.response_time_seconds:.1f}s"
                )
                
            except Exception as e:
                logger.error(f"❌ Test {test_case.name} failed with error: {e}")
                results.append(ValidationResult(
                    test_case_name=test_case.name,
                    success=False,
                    response_length=0,
                    contains_keywords=[],
                    missing_keywords=test_case.expected_keywords,
                    response_time_seconds=0,
                    token_usage={"input": 0, "output": 0},
                    estimated_cost=0.0,
                    error_message=str(e)
                ))
        
        return results
    
    def _run_single_test(
        self, 
        model_name: str, 
        parameters: Dict[str, Any], 
        test_case: ValidationTestCase
    ) -> ValidationResult:
        """Run a single test case"""
        google_api_key = os.getenv('GOOGLE_API_KEY')
        if not google_api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required")
        
        # Create model with test parameters
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=google_api_key,
            **parameters
        )
        
        # Measure response time
        start_time = time.time()
        
        # Make the API call
        response = llm.invoke(test_case.input_prompt)
        
        end_time = time.time()
        response_time = end_time - start_time
        
        # Extract response content
        response_content = response.content if hasattr(response, 'content') else str(response)
        
        # Calculate token usage (estimated)
        input_tokens = self._estimate_tokens(test_case.input_prompt)
        output_tokens = self._estimate_tokens(response_content)
        
        # Calculate cost
        estimated_cost = self._calculate_cost(model_name, input_tokens, output_tokens)
        
        # Track token usage
        if hasattr(response, 'usage_metadata'):
            actual_input_tokens = getattr(response.usage_metadata, 'input_tokens', input_tokens)
            actual_output_tokens = getattr(response.usage_metadata, 'output_tokens', output_tokens)
            
            # Record actual usage if available
            token_tracker.track_usage(
                provider="google",
                model_name=model_name,
                input_tokens=actual_input_tokens,
                output_tokens=actual_output_tokens,
                session_id=f"validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                analysis_type="validation_test"
            )
        
        # Check keyword presence
        response_lower = response_content.lower()
        contains_keywords = [kw for kw in test_case.expected_keywords if kw.lower() in response_lower]
        missing_keywords = [kw for kw in test_case.expected_keywords if kw.lower() not in response_lower]
        
        # Determine success
        success = (
            len(response_content) >= test_case.min_response_length and
            len(contains_keywords) >= len(test_case.expected_keywords) * 0.7 and  # 70% keyword coverage
            estimated_cost <= test_case.max_acceptable_cost
        )
        
        return ValidationResult(
            test_case_name=test_case.name,
            success=success,
            response_length=len(response_content),
            contains_keywords=contains_keywords,
            missing_keywords=missing_keywords,
            response_time_seconds=response_time,
            token_usage={"input": input_tokens, "output": output_tokens},
            estimated_cost=estimated_cost
        )
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation)"""
        return max(1, len(text.split()) * 1.3)  # Rough estimate: ~1.3 tokens per word
    
    def _calculate_cost(self, model_name: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate estimated cost based on current pricing"""
        cost = config_manager.calculate_cost("google", model_name, input_tokens, output_tokens)
        if cost == 0.0:
            # Fallback pricing if not found in config
            if "2.5-pro" in model_name.lower():
                cost = (input_tokens / 1000 * 0.0125) + (output_tokens / 1000 * 0.05)
            elif "2.0-flash" in model_name.lower():
                cost = (input_tokens / 1000 * 0.000075) + (output_tokens / 1000 * 0.0003)
            else:
                cost = (input_tokens / 1000 * 0.00025) + (output_tokens / 1000 * 0.0005)
        
        return cost
    
    def _generate_validation_report(
        self,
        model_name: str,
        parameters: Dict[str, Any],
        current_results: List[ValidationResult],
        baseline_parameters: Optional[Dict[str, Any]],
        baseline_results: Optional[List[ValidationResult]]
    ) -> Dict[str, Any]:
        """Generate comprehensive validation report"""
        
        # Calculate current metrics
        current_metrics = self._calculate_metrics(current_results)
        
        # Calculate baseline metrics if available
        baseline_metrics = None
        improvement_analysis = None
        if baseline_results:
            baseline_metrics = self._calculate_metrics(baseline_results)
            improvement_analysis = self._analyze_improvements(current_metrics, baseline_metrics)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            current_results, current_metrics, improvement_analysis
        )
        
        report = {
            "validation_timestamp": datetime.now().isoformat(),
            "model_name": model_name,
            "test_parameters": parameters,
            "baseline_parameters": baseline_parameters,
            "current_results": {
                "metrics": current_metrics,
                "detailed_results": [self._result_to_dict(r) for r in current_results]
            },
            "baseline_results": {
                "metrics": baseline_metrics,
                "detailed_results": [self._result_to_dict(r) for r in baseline_results] if baseline_results else []
            } if baseline_results else None,
            "improvement_analysis": improvement_analysis,
            "recommendations": recommendations,
            "overall_assessment": self._assess_overall_performance(current_metrics, improvement_analysis)
        }
        
        return report
    
    def _calculate_metrics(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """Calculate aggregate metrics from results"""
        if not results:
            return {}
        
        successful_tests = [r for r in results if r.success]
        total_cost = sum(r.estimated_cost for r in results)
        total_tokens = sum(r.token_usage.get("input", 0) + r.token_usage.get("output", 0) for r in results)
        avg_response_length = sum(r.response_length for r in results) / len(results)
        avg_response_time = sum(r.response_time_seconds for r in results) / len(results)
        
        keyword_coverage_rates = []
        for result in results:
            test_case = next(tc for tc in self.test_cases if tc.name == result.test_case_name)
            coverage = len(result.contains_keywords) / len(test_case.expected_keywords) if test_case.expected_keywords else 0
            keyword_coverage_rates.append(coverage)
        
        avg_keyword_coverage = sum(keyword_coverage_rates) / len(keyword_coverage_rates) if keyword_coverage_rates else 0
        
        return {
            "total_tests": len(results),
            "successful_tests": len(successful_tests),
            "success_rate": len(successful_tests) / len(results),
            "total_cost_usd": total_cost,
            "avg_cost_per_test": total_cost / len(results),
            "total_tokens": total_tokens,
            "avg_tokens_per_test": total_tokens / len(results),
            "avg_response_length": avg_response_length,
            "avg_response_time_seconds": avg_response_time,
            "avg_keyword_coverage": avg_keyword_coverage,
            "cost_efficiency": avg_response_length / total_cost if total_cost > 0 else 0  # chars per dollar
        }
    
    def _analyze_improvements(self, current: Dict[str, Any], baseline: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze improvements between current and baseline"""
        improvements = {}
        
        for key in ["success_rate", "avg_response_length", "avg_keyword_coverage", "cost_efficiency"]:
            if key in current and key in baseline:
                current_val = current[key]
                baseline_val = baseline[key]
                if baseline_val > 0:
                    improvement_pct = ((current_val - baseline_val) / baseline_val) * 100
                    improvements[f"{key}_improvement_pct"] = improvement_pct
                    improvements[f"{key}_improved"] = improvement_pct > 0
        
        # Cost analysis
        cost_increase_pct = 0
        if "avg_cost_per_test" in current and "avg_cost_per_test" in baseline:
            if baseline["avg_cost_per_test"] > 0:
                cost_increase_pct = ((current["avg_cost_per_test"] - baseline["avg_cost_per_test"]) / baseline["avg_cost_per_test"]) * 100
        
        improvements["cost_increase_pct"] = cost_increase_pct
        improvements["cost_acceptable"] = cost_increase_pct <= 100  # No more than 100% increase
        
        return improvements
    
    def _generate_recommendations(
        self, 
        results: List[ValidationResult], 
        metrics: Dict[str, Any],
        improvement_analysis: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Generate recommendations based on validation results"""
        recommendations = []
        
        # Success rate recommendations
        if metrics.get("success_rate", 0) < 0.8:
            recommendations.append("❌ Success rate below 80% - consider adjusting parameters")
        elif metrics.get("success_rate", 0) >= 0.9:
            recommendations.append("✅ Excellent success rate - parameters are well-tuned")
        
        # Cost recommendations
        if metrics.get("avg_cost_per_test", 0) > 1.0:
            recommendations.append("💰 Average cost per test exceeds $1.00 - consider cost optimization")
        
        # Response quality recommendations
        if metrics.get("avg_keyword_coverage", 0) < 0.7:
            recommendations.append("📝 Low keyword coverage - responses may be incomplete")
        
        # Improvement analysis recommendations
        if improvement_analysis:
            if improvement_analysis.get("cost_increase_pct", 0) > 100:
                recommendations.append("⚠️ Cost increased by >100% - validate if benefits justify the expense")
            
            if not improvement_analysis.get("success_rate_improved", False):
                recommendations.append("⚠️ Success rate did not improve - current parameters may not be effective")
        
        # Parameter-specific recommendations
        if not recommendations:
            recommendations.append("✅ All metrics within acceptable ranges - parameters appear optimal")
        
        return recommendations
    
    def _assess_overall_performance(
        self, 
        metrics: Dict[str, Any], 
        improvement_analysis: Optional[Dict[str, Any]]
    ) -> str:
        """Assess overall performance and provide verdict"""
        success_rate = metrics.get("success_rate", 0)
        avg_cost = metrics.get("avg_cost_per_test", 0)
        keyword_coverage = metrics.get("avg_keyword_coverage", 0)
        
        if improvement_analysis:
            cost_increase = improvement_analysis.get("cost_increase_pct", 0)
            success_improved = improvement_analysis.get("success_rate_improved", False)
            
            if success_rate >= 0.8 and keyword_coverage >= 0.7 and success_improved and cost_increase <= 100:
                return "EXCELLENT - Parameters provide significant improvement with acceptable cost"
            elif success_rate >= 0.7 and success_improved:
                return "GOOD - Parameters show improvement but may need further optimization"
            elif cost_increase > 100 and not success_improved:
                return "POOR - High cost increase without corresponding improvement"
            else:
                return "ACCEPTABLE - Parameters provide modest improvement"
        else:
            if success_rate >= 0.8 and keyword_coverage >= 0.7 and avg_cost <= 1.0:
                return "EXCELLENT - Parameters provide good performance at reasonable cost"
            elif success_rate >= 0.7 and avg_cost <= 1.5:
                return "GOOD - Parameters provide adequate performance"
            else:
                return "NEEDS_IMPROVEMENT - Consider parameter adjustment"
    
    def _result_to_dict(self, result: ValidationResult) -> Dict[str, Any]:
        """Convert ValidationResult to dictionary"""
        return {
            "test_case_name": result.test_case_name,
            "success": result.success,
            "response_length": result.response_length,
            "contains_keywords": result.contains_keywords,
            "missing_keywords": result.missing_keywords,
            "response_time_seconds": result.response_time_seconds,
            "token_usage": result.token_usage,
            "estimated_cost": result.estimated_cost,
            "error_message": result.error_message
        }
    
    def _save_validation_results(self, report: Dict[str, Any]):
        """Save validation results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"gemini_validation_{report['model_name'].replace('-', '_')}_{timestamp}.json"
        filepath = self.results_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Validation results saved to {filepath}")
    
    def run_automated_validation(self) -> Dict[str, Any]:
        """Run automated validation with current and baseline parameters"""
        logger.info("🚀 Starting automated Gemini validation")
        
        # Current parameters (from the fix)
        current_params = {
            "temperature": 0.3,
            "max_tokens": 8000,  # The 100% increase
            "top_p": 0.8
        }
        
        # Baseline parameters (original)
        baseline_params = {
            "temperature": 0.7,
            "max_tokens": 4000,  # Original limit
            "top_p": 0.9
        }
        
        return self.validate_model_parameters(
            model_name="gemini-2.5-pro",
            parameters=current_params,
            baseline_parameters=baseline_params
        )


def run_validation_suite():
    """Run the complete validation suite"""
    validator = GeminiAnalysisValidator()
    return validator.run_automated_validation()


if __name__ == "__main__":
    # Run validation if executed directly
    results = run_validation_suite()
    
    print("\n" + "="*80)
    print("GEMINI 2.5 PRO VALIDATION RESULTS")
    print("="*80)
    
    print(f"\nOverall Assessment: {results['overall_assessment']}")
    
    current_metrics = results['current_results']['metrics']
    print(f"\nCurrent Parameters Performance:")
    print(f"  Success Rate: {current_metrics['success_rate']:.1%}")
    print(f"  Average Cost: ${current_metrics['avg_cost_per_test']:.4f}")
    print(f"  Keyword Coverage: {current_metrics['avg_keyword_coverage']:.1%}")
    
    if results['baseline_results']:
        baseline_metrics = results['baseline_results']['metrics']
        print(f"\nBaseline Parameters Performance:")
        print(f"  Success Rate: {baseline_metrics['success_rate']:.1%}")
        print(f"  Average Cost: ${baseline_metrics['avg_cost_per_test']:.4f}")
        print(f"  Keyword Coverage: {baseline_metrics['avg_keyword_coverage']:.1%}")
        
        improvement = results['improvement_analysis']
        print(f"\nImprovement Analysis:")
        print(f"  Cost Increase: {improvement['cost_increase_pct']:.1f}%")
        print(f"  Success Rate Improved: {improvement.get('success_rate_improved', False)}")
    
    print(f"\nRecommendations:")
    for rec in results['recommendations']:
        print(f"  • {rec}")
    
    print("\n" + "="*80)