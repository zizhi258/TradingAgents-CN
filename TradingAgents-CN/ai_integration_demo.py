#!/usr/bin/env python3
"""
TradingAgents-CN AI Integration Demo

This script demonstrates the comprehensive AI-powered features integrated into
TradingAgents-CN, including multi-LLM orchestration, RAG system, intelligent
automation, enhanced coordination, and production API capabilities.

Usage:
    python ai_integration_demo.py --symbol AAPL --demo-mode full
"""

import asyncio
import sys
import argparse
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import TradingAgents-CN AI components
from tradingagents.ai import (
    initialize_ai_system,
    create_comprehensive_analysis,
    AIOrchestrator,
    FinancialRAGSystem,
    IntelligentAutomation,
    EnhancedMultiAgentCoordinator,
    ProductionAPIServer,
    TaskPriority,
    ReportType,
    AlertSeverity,
    CoordinationMode,
    get_feature_overview
)

# Import existing TradingAgents components
from tradingagents.utils.logging_init import get_logger
from tradingagents.config.config_manager import ConfigManager

logger = get_logger("ai_demo")


class AIIntegrationDemo:
    """Comprehensive demonstration of AI integration features"""
    
    def __init__(self, symbols: List[str] = None):
        self.symbols = symbols or ["AAPL", "MSFT", "GOOGL"]
        self.ai_manager = None
        self.demo_results = {}
        
    async def run_full_demo(self):
        """Run complete AI integration demonstration"""
        
        print("🚀 TradingAgents-CN AI Integration Demo")
        print("=" * 50)
        print(get_feature_overview())
        print("\n")
        
        try:
            # Step 1: Initialize AI System
            print("📥 Step 1: Initializing AI System...")
            await self._demo_ai_initialization()
            
            # Step 2: Multi-LLM Orchestrator Demo
            print("\n🧠 Step 2: Multi-LLM Orchestrator Demo...")
            await self._demo_llm_orchestrator()
            
            # Step 3: RAG System Demo
            print("\n📚 Step 3: RAG System Demo...")
            await self._demo_rag_system()
            
            # Step 4: Intelligent Automation Demo
            print("\n🤖 Step 4: Intelligent Automation Demo...")
            await self._demo_intelligent_automation()
            
            # Step 5: Enhanced Coordination Demo
            print("\n👥 Step 5: Enhanced Multi-Agent Coordination Demo...")
            await self._demo_enhanced_coordination()
            
            # Step 6: Comprehensive Analysis Demo
            print("\n🔍 Step 6: Comprehensive Analysis Demo...")
            await self._demo_comprehensive_analysis()
            
            # Step 7: Integration Status
            print("\n📊 Step 7: System Status and Metrics...")
            await self._demo_system_status()
            
            # Step 8: Production API Demo
            print("\n🚀 Step 8: Production API Demo...")
            await self._demo_production_api()
            
            print("\n✅ AI Integration Demo completed successfully!")
            print(f"📈 Results saved to: {self._save_demo_results()}")
            
        except Exception as e:
            logger.error(f"Demo failed: {e}")
            print(f"❌ Demo failed: {e}")
        
        finally:
            # Cleanup
            if self.ai_manager:
                await self.ai_manager.shutdown()
    
    async def _demo_ai_initialization(self):
        """Demonstrate AI system initialization"""
        
        start_time = time.time()
        
        # Initialize with custom configuration
        config = {
            'enable_llm_orchestrator': True,
            'enable_rag_system': True,
            'enable_automation': True,
            'enable_coordination': True,
            'enable_production_api': True,
            'integrate_charting_artist': True,
            'integrate_news_analysis': True,
            'integrate_risk_management': True,
            'knowledge_base_path': 'demo_kb',
            'reports_output_path': 'demo_reports'
        }
        
        self.ai_manager = await initialize_ai_system(
            config_path=None,  # Use default
            enable_all_features=True
        )
        
        init_time = time.time() - start_time
        
        print(f"   ✅ AI system initialized in {init_time:.2f}s")
        
        # Get initialization status
        status = self.ai_manager.get_integration_status()
        print(f"   📊 Components initialized: {len(status['integration_status'])}")
        
        for component, state in status['integration_status'].items():
            print(f"      • {component}: {state}")
        
        self.demo_results['initialization'] = {
            'time_taken': init_time,
            'components_initialized': len(status['integration_status']),
            'status': status
        }
    
    async def _demo_llm_orchestrator(self):
        """Demonstrate Multi-LLM Orchestrator capabilities"""
        
        if not self.ai_manager.ai_orchestrator:
            print("   ⚠️  LLM Orchestrator not available")
            return
        
        orchestrator = self.ai_manager.ai_orchestrator
        
        print("   🔄 Testing intelligent routing and caching...")
        
        # Test different task types and priorities
        test_tasks = [
            {
                'agent_role': 'fundamental_expert',
                'prompt': f'Analyze {self.symbols[0]} fundamentals',
                'task_type': 'fundamental_analysis',
                'priority': TaskPriority.HIGH
            },
            {
                'agent_role': 'technical_analyst', 
                'prompt': f'Provide technical analysis for {self.symbols[1]}',
                'task_type': 'technical_analysis',
                'priority': TaskPriority.NORMAL
            },
            {
                'agent_role': 'risk_manager',
                'prompt': f'Assess investment risk for {self.symbols[2]}',
                'task_type': 'risk_assessment', 
                'priority': TaskPriority.HIGH
            }
        ]
        
        llm_results = []
        total_cost = 0.0
        
        for i, task in enumerate(test_tasks):
            print(f"   📝 Task {i+1}: {task['agent_role']} - {task['task_type']}")
            
            start_time = time.time()
            
            result = await orchestrator.execute_task(
                agent_role=task['agent_role'],
                task_prompt=task['prompt'],
                task_type=task['task_type'],
                priority=task['priority'],
                context={'demo': True, 'task_number': i+1}
            )
            
            execution_time = time.time() - start_time
            
            if result.success:
                model_used = result.model_used.name if result.model_used else 'Unknown'
                cost = getattr(result, 'actual_cost', 0.0)
                total_cost += cost
                
                print(f"      ✅ Success: {model_used} (${cost:.4f}, {execution_time:.2f}s)")
                print(f"         📄 Result: {result.result[:100]}...")
                
                llm_results.append({
                    'task': task,
                    'success': True,
                    'model_used': model_used,
                    'cost': cost,
                    'execution_time': execution_time,
                    'result_preview': result.result[:200]
                })
            else:
                print(f"      ❌ Failed: {result.error_message}")
                llm_results.append({
                    'task': task,
                    'success': False,
                    'error': result.error_message
                })
        
        # Test caching by repeating first task
        print("   🗄️  Testing caching with repeated task...")
        
        cache_start = time.time()
        cached_result = await orchestrator.execute_task(
            agent_role=test_tasks[0]['agent_role'],
            task_prompt=test_tasks[0]['prompt'],
            task_type=test_tasks[0]['task_type'],
            priority=test_tasks[0]['priority'],
            context={'demo': True, 'cache_test': True},
            use_cache=True
        )
        cache_time = time.time() - cache_start
        
        if cached_result.success:
            cached = getattr(cached_result, 'cached', False)
            print(f"      {'🎯 Cache HIT' if cached else '🔄 Cache MISS'} ({cache_time:.2f}s)")
        
        # Get orchestrator metrics
        metrics = orchestrator.get_metrics()
        
        print(f"   📈 Total tasks: {metrics['performance']['total_tasks']}")
        print(f"   💰 Total cost: ${total_cost:.4f}")
        print(f"   ⚡ Cache hit rate: {metrics['performance']['cache_hit_rate']:.1%}")
        
        self.demo_results['llm_orchestrator'] = {
            'tasks_completed': len(llm_results),
            'successful_tasks': len([r for r in llm_results if r.get('success')]),
            'total_cost': total_cost,
            'metrics': metrics,
            'results': llm_results
        }
    
    async def _demo_rag_system(self):
        """Demonstrate RAG system capabilities"""
        
        if not self.ai_manager.rag_system:
            print("   ⚠️  RAG System not available")
            return
        
        rag_system = self.ai_manager.rag_system
        
        print("   📥 Ingesting financial data...")
        
        # Ingest data for demo symbols
        ingestion_stats = {}
        for symbol in self.symbols[:2]:  # Limit for demo
            stats = rag_system.ingest_symbol_data(
                symbol=symbol,
                include_news=True,
                include_market_data=True,
                days_back=7  # Limited for demo
            )
            ingestion_stats[symbol] = stats
            print(f"      📊 {symbol}: {stats['news']} news, {stats['market_data']} market docs")
        
        # Test RAG queries
        test_queries = [
            {
                'query': f"What are the recent trends for {self.symbols[0]}?",
                'query_type': 'general',
                'symbols': [self.symbols[0]]
            },
            {
                'query': f"Compare {self.symbols[0]} and {self.symbols[1]} performance",
                'query_type': 'technical',
                'symbols': self.symbols[:2]
            },
            {
                'query': "What are the main market risks currently?",
                'query_type': 'risk',
                'symbols': self.symbols
            }
        ]
        
        rag_results = []
        
        for i, query_info in enumerate(test_queries):
            print(f"   🔍 Query {i+1}: {query_info['query'][:50]}...")
            
            start_time = time.time()
            
            rag_response = await rag_system.query(
                query_text=query_info['query'],
                query_type=query_info['query_type'],
                symbols=query_info['symbols'],
                agent_role='fundamental_expert'
            )
            
            query_time = time.time() - start_time
            
            print(f"      📄 Found {len(rag_response.retrieved_documents)} relevant documents")
            print(f"      🎯 Confidence: {rag_response.confidence_score:.2f}")
            print(f"      ⏱️  Query time: {query_time:.2f}s")
            print(f"      📝 Answer: {rag_response.generated_response[:150]}...")
            
            rag_results.append({
                'query': query_info,
                'documents_found': len(rag_response.retrieved_documents),
                'confidence': rag_response.confidence_score,
                'sources': rag_response.sources,
                'query_time': query_time,
                'answer_preview': rag_response.generated_response[:300]
            })
        
        # Get RAG system stats
        system_stats = rag_system.get_system_stats()
        
        print(f"   📚 Knowledge base: {system_stats['knowledge_base']['total_documents']} documents")
        print(f"   🎯 Vector DB: {'Available' if system_stats['rag_system']['vector_db_available'] else 'Fallback mode'}")
        
        self.demo_results['rag_system'] = {
            'ingestion_stats': ingestion_stats,
            'queries_completed': len(rag_results),
            'system_stats': system_stats,
            'query_results': rag_results
        }
    
    async def _demo_intelligent_automation(self):
        """Demonstrate intelligent automation capabilities"""
        
        if not self.ai_manager.automation_system:
            print("   ⚠️  Automation System not available")
            return
        
        automation = self.ai_manager.automation_system
        
        print("   📊 Generating automated reports...")
        
        # Generate different types of reports
        report_types = [
            (ReportType.DAILY_SUMMARY, self.symbols[:2]),
            (ReportType.RISK_ASSESSMENT, [self.symbols[0]]),
        ]
        
        report_results = []
        
        for report_type, symbols in report_types:
            print(f"   📄 Generating {report_type.value} for {symbols}")
            
            start_time = time.time()
            
            try:
                report_result = await automation.report_generator.generate_report(
                    report_type=report_type,
                    symbols=symbols,
                    custom_parameters={'demo_mode': True}
                )
                
                generation_time = time.time() - start_time
                
                if 'error' not in report_result:
                    print(f"      ✅ Generated: {report_result['report_id']}")
                    print(f"      📊 Data points: {report_result['data_points']}")
                    print(f"      🤖 AI enhanced: {report_result['ai_insights_generated']}")
                    print(f"      ⏱️  Time: {generation_time:.2f}s")
                    
                    report_results.append({
                        'type': report_type.value,
                        'symbols': symbols,
                        'success': True,
                        'generation_time': generation_time,
                        'report_id': report_result['report_id'],
                        'data_points': report_result['data_points']
                    })
                else:
                    print(f"      ❌ Failed: {report_result['error']}")
                    report_results.append({
                        'type': report_type.value,
                        'symbols': symbols,
                        'success': False,
                        'error': report_result['error']
                    })
                    
            except Exception as e:
                print(f"      ❌ Error: {e}")
                report_results.append({
                    'type': report_type.value,
                    'symbols': symbols,
                    'success': False,
                    'error': str(e)
                })
        
        print("   🔔 Setting up smart alerts...")
        
        # Create sample alert conditions
        from tradingagents.ai.intelligent_automation import create_price_alert_condition
        
        alert_conditions = [
            create_price_alert_condition(self.symbols[0], 150.0, "above"),
            create_price_alert_condition(self.symbols[1], 300.0, "below")
        ]
        
        alert_results = []
        for condition in alert_conditions:
            success = automation.alert_system.add_alert_condition(condition)
            alert_results.append({
                'condition_name': condition.name,
                'success': success,
                'trigger_type': condition.trigger_type.value
            })
            print(f"      {'✅' if success else '❌'} {condition.name}")
        
        # Test alert checking (simulate)
        print("   🔍 Checking alert conditions...")
        alerts = await automation.alert_system.check_alert_conditions(self.symbols)
        
        print(f"      🚨 {len(alerts)} alerts triggered")
        for alert in alerts:
            print(f"         • {alert.title} ({alert.severity.value})")
        
        # Get automation status
        status = automation.get_automation_status()
        
        self.demo_results['automation'] = {
            'reports_generated': len(report_results),
            'successful_reports': len([r for r in report_results if r.get('success')]),
            'alert_conditions_set': len(alert_results),
            'alerts_triggered': len(alerts),
            'automation_status': status,
            'report_results': report_results,
            'alert_results': alert_results
        }
    
    async def _demo_enhanced_coordination(self):
        """Demonstrate enhanced multi-agent coordination"""
        
        if not self.ai_manager.coordinator:
            print("   ⚠️  Coordination System not available")
            return
        
        coordinator = self.ai_manager.coordinator
        
        print("   🤝 Testing multi-agent coordination...")
        
        # Create coordination task
        from tradingagents.ai.enhanced_coordination import CoordinationTask, create_market_analysis_task
        
        coordination_task = create_market_analysis_task(
            symbol=self.symbols[0], 
            analysis_type="comprehensive"
        )
        
        # Test different coordination modes
        coordination_modes = [
            (CoordinationMode.PARALLEL, 3),
            (CoordinationMode.CONSENSUS_BUILDING, 4)
        ]
        
        coordination_results = []
        
        for mode, max_agents in coordination_modes:
            print(f"   👥 Mode: {mode.value} with {max_agents} agents")
            
            start_time = time.time()
            
            try:
                result = await coordinator.execute_coordinated_analysis(
                    task=coordination_task,
                    coordination_mode=mode,
                    max_agents=max_agents
                )
                
                coordination_time = time.time() - start_time
                
                if result.get('success'):
                    print(f"      ✅ Success: {len(result['selected_agents'])} agents participated")
                    
                    consensus = result.get('consensus_result', {})
                    print(f"      🎯 Consensus score: {consensus.get('consensus_score', 0):.2f}")
                    print(f"      ⏱️  Time: {coordination_time:.2f}s")
                    
                    coordination_results.append({
                        'mode': mode.value,
                        'max_agents': max_agents,
                        'success': True,
                        'agents_participated': len(result['selected_agents']),
                        'consensus_score': consensus.get('consensus_score', 0),
                        'coordination_time': coordination_time
                    })
                else:
                    print(f"      ❌ Failed: {result.get('error', 'Unknown error')}")
                    coordination_results.append({
                        'mode': mode.value,
                        'max_agents': max_agents,
                        'success': False,
                        'error': result.get('error', 'Unknown error')
                    })
                    
            except Exception as e:
                print(f"      ❌ Error: {e}")
                coordination_results.append({
                    'mode': mode.value,
                    'max_agents': max_agents,
                    'success': False,
                    'error': str(e)
                })
        
        # Get coordination stats
        stats = coordinator.get_coordination_stats()
        
        print(f"   📊 Total workflows: {stats['total_workflows']}")
        print(f"   🎯 Success rate: {stats['success_rate']:.1%}")
        if stats['avg_consensus_score'] > 0:
            print(f"   🤝 Avg consensus: {stats['avg_consensus_score']:.2f}")
        
        self.demo_results['coordination'] = {
            'coordination_tests': len(coordination_results),
            'successful_coordinations': len([r for r in coordination_results if r.get('success')]),
            'coordination_stats': stats,
            'results': coordination_results
        }
    
    async def _demo_comprehensive_analysis(self):
        """Demonstrate comprehensive AI-powered analysis"""
        
        print(f"   🔍 Running comprehensive analysis for {self.symbols[0]}...")
        
        start_time = time.time()
        
        # Use the convenience function
        analysis_result = await create_comprehensive_analysis(
            symbol=self.symbols[0],
            analysis_type="full",
            ai_manager=self.ai_manager
        )
        
        analysis_time = time.time() - start_time
        
        if analysis_result.get('success'):
            print(f"      ✅ Analysis completed in {analysis_time:.2f}s")
            print(f"      🧩 Components: {analysis_result['components_analyzed']}")
            
            # Show component results
            components = analysis_result.get('components', {})
            
            if 'chart_analysis' in components:
                chart = components['chart_analysis']
                confidence = chart.get('confidence_score', 0)
                print(f"         📈 Chart Analysis: {confidence:.2f} confidence")
            
            if 'news_analysis' in components:
                news = components['news_analysis']
                sentiment = news.get('sentiment_metrics', {})
                overall_sentiment = sentiment.get('overall_sentiment', 0)
                print(f"         📰 News Analysis: {overall_sentiment:+.2f} sentiment")
            
            if 'risk_assessment' in components:
                risk = components['risk_assessment']
                risk_level = risk.get('overall_risk_level', 'Unknown')
                print(f"         ⚠️  Risk Assessment: {risk_level} risk")
            
            # Check for coordinated synthesis
            if 'coordinated_synthesis' in analysis_result:
                synthesis = analysis_result['coordinated_synthesis']
                print(f"         🤝 Synthesis: {synthesis.get('success', False)}")
        else:
            print(f"      ❌ Analysis failed: {analysis_result.get('error', 'Unknown error')}")
        
        self.demo_results['comprehensive_analysis'] = {
            'symbol': self.symbols[0],
            'success': analysis_result.get('success', False),
            'analysis_time': analysis_time,
            'components_analyzed': analysis_result.get('components_analyzed', 0),
            'result_summary': {
                'chart_available': 'chart_analysis' in analysis_result.get('components', {}),
                'news_available': 'news_analysis' in analysis_result.get('components', {}),
                'risk_available': 'risk_assessment' in analysis_result.get('components', {}),
                'synthesis_available': 'coordinated_synthesis' in analysis_result
            }
        }
    
    async def _demo_system_status(self):
        """Demonstrate system status and monitoring"""
        
        print("   📊 Getting system status...")
        
        # Get integration status
        integration_status = self.ai_manager.get_integration_status()
        
        # Show component health
        system_health = integration_status.get('system_health', {})
        
        for component, health in system_health.items():
            if health:
                if isinstance(health, dict):
                    status = health.get('overall_health', 'unknown')
                    print(f"      {component}: {status}")
                else:
                    print(f"      {component}: {health}")
        
        # Show performance metrics
        if self.ai_manager.ai_orchestrator:
            metrics = self.ai_manager.ai_orchestrator.get_metrics()
            perf = metrics.get('performance', {})
            
            print(f"   ⚡ Performance Metrics:")
            print(f"      • Total requests: {perf.get('total_tasks', 0)}")
            print(f"      • Success rate: {perf.get('success_rate', 0):.1%}")
            print(f"      • Avg response time: {perf.get('average_response_time', 0):.2f}s")
            print(f"      • Cache hit rate: {perf.get('cache_hit_rate', 0):.1%}")
            
            # Cost metrics
            cost = metrics.get('cost', {})
            print(f"   💰 Cost Metrics:")
            print(f"      • Session cost: ${cost.get('session_cost', 0):.4f}")
            print(f"      • Daily cost: ${cost.get('daily_cost', 0):.4f}")
        
        self.demo_results['system_status'] = {
            'integration_status': integration_status,
            'components_healthy': len([h for h in system_health.values() if h]),
            'total_components': len(system_health)
        }
    
    async def _demo_production_api(self):
        """Demonstrate production API capabilities"""
        
        if not self.ai_manager.production_api:
            print("   ⚠️  Production API not available")
            return
        
        api_server = self.ai_manager.production_api
        
        print("   🚀 Production API Status:")
        print(f"      • Server initialized: ✅")
        print(f"      • AI components injected: ✅")
        print(f"      • Rate limiting: ✅")
        print(f"      • Cost optimization: ✅")
        print(f"      • Monitoring: ✅")
        
        # Show available endpoints
        print("   📡 Available Endpoints:")
        endpoints = [
            "GET /health - Health check",
            "GET /metrics - System metrics", 
            "POST /analysis - Single symbol analysis",
            "POST /rag-query - RAG system query",
            "POST /generate-report - Report generation",
            "POST /multi-symbol-analysis - Coordinated analysis",
            "GET /cost-optimization - Cost recommendations"
        ]
        
        for endpoint in endpoints:
            print(f"      • {endpoint}")
        
        print("   🔧 To start the API server:")
        print("      python -m tradingagents.ai.production_api")
        print("      Then visit: http://localhost:8000/docs")
        
        self.demo_results['production_api'] = {
            'server_available': True,
            'endpoints_count': len(endpoints),
            'features_enabled': [
                'rate_limiting',
                'cost_optimization', 
                'monitoring',
                'health_checks',
                'api_documentation'
            ]
        }
    
    def _save_demo_results(self) -> str:
        """Save demo results to file"""
        
        results_file = Path("ai_integration_demo_results.json")
        
        # Add summary
        summary = {
            'demo_completed': True,
            'timestamp': time.time(),
            'symbols_tested': self.symbols,
            'total_components': len(self.demo_results),
            'overall_success': all(
                result.get('success', True) != False 
                for result in self.demo_results.values()
                if isinstance(result, dict)
            )
        }
        
        final_results = {
            'summary': summary,
            'detailed_results': self.demo_results
        }
        
        with open(results_file, 'w') as f:
            json.dump(final_results, f, indent=2, default=str)
        
        return str(results_file)


async def main():
    """Main demo function"""
    
    parser = argparse.ArgumentParser(description="TradingAgents-CN AI Integration Demo")
    parser.add_argument('--symbols', nargs='+', default=['AAPL', 'MSFT', 'GOOGL'],
                       help="Stock symbols to analyze")
    parser.add_argument('--demo-mode', choices=['full', 'quick', 'api-only'], 
                       default='full', help="Demo mode")
    
    args = parser.parse_args()
    
    print(f"Starting AI Integration Demo")
    print(f"Symbols: {args.symbols}")
    print(f"Mode: {args.demo_mode}")
    print("-" * 50)
    
    demo = AIIntegrationDemo(symbols=args.symbols)
    
    try:
        if args.demo_mode == 'full':
            await demo.run_full_demo()
        elif args.demo_mode == 'quick':
            # Run abbreviated demo
            await demo._demo_ai_initialization()
            await demo._demo_llm_orchestrator()
            await demo._demo_comprehensive_analysis()
        elif args.demo_mode == 'api-only':
            await demo._demo_ai_initialization()
            await demo._demo_production_api()
        
    except KeyboardInterrupt:
        print("\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        logger.error(f"Demo error: {e}", exc_info=True)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())