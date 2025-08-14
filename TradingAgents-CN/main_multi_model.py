#!/usr/bin/env python3
"""
Multi-Model Trading Agents Main Entry Point
多模型协作交易智能体主入口
"""

import sys
import os
from pathlib import Path
import argparse
from datetime import datetime
from typing import Dict, Any, List

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tradingagents.graph.trading_graph import TradingAgentsGraph

# 尝试导入多模型扩展
try:
    from tradingagents.graph.multi_model_extension import MultiModelExtension
    MULTI_MODEL_AVAILABLE = True
    print("✅ 多模型协作扩展加载成功")
except ImportError as e:
    MULTI_MODEL_AVAILABLE = False
    print(f"⚠️ 多模型协作扩展不可用: {e}")
    print("📝 将使用标准单模型分析")

# 导入日志系统
from tradingagents.utils.logging_init import get_logger
logger = get_logger('main_multi_model')


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="TradingAgents-CN 多模型协作分析")
    
    parser.add_argument('stock_symbol', nargs='?', default='AAPL', 
                       help='股票代码 (默认: AAPL)')
    parser.add_argument('analysis_date', nargs='?', 
                       default=datetime.now().strftime('%Y-%m-%d'),
                       help='分析日期 (默认: 今天)')
    parser.add_argument('collaboration_mode', nargs='?', default='sequential',
                       choices=['sequential', 'parallel', 'debate'],
                       help='协作模式 (默认: sequential)')
    
    parser.add_argument('--agents', nargs='+', 
                       default=['news_hunter', 'fundamental_expert', 'technical_analyst', 'risk_manager'],
                       help='参与的智能体列表')
    parser.add_argument('--cost-optimization', choices=['cost_first', 'balanced', 'quality_first'],
                       default='balanced', help='成本优化策略')
    parser.add_argument('--research-depth', type=int, choices=[1,2,3,4,5], default=3,
                       help='研究深度 (1-5, 默认: 3)')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    parser.add_argument('--single-model', action='store_true', help='强制使用单模型模式')
    
    return parser.parse_args()


def create_default_config():
    """创建默认配置"""
    return {
        'project_dir': str(project_root),
        'llm_provider': 'google',
        'llm_model': 'gemini-2.0-flash',
        'deep_think_llm': 'gemini-2.5-pro',
        'quick_think_llm': 'gemini-2.0-flash',
        'backend_url': 'https://generativelanguage.googleapis.com/v1',
        'data_sources': {
            'news': True,
            'financial': True, 
            'social': True
        },
        'analysis': {
            'enable_caching': True,
            'timeout': 300
        }
    }


def run_single_model_analysis(stock_symbol: str, analysis_date: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """运行单模型分析"""
    logger.info(f"🔄 开始单模型分析: {stock_symbol} ({analysis_date})")
    
    try:
        # 创建标准交易图
        ta = TradingAgentsGraph(debug=config.get('debug', False), config=config)
        
        # 执行分析
        graph_result, decision = ta.propagate(stock_symbol, analysis_date)
        
        logger.info("✅ 单模型分析完成")
        
        return {
            'mode': 'single_model',
            'stock_symbol': stock_symbol,
            'analysis_date': analysis_date,
            'graph_result': graph_result,
            'decision': decision,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 单模型分析失败: {e}")
        return {
            'mode': 'single_model',
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


def run_multi_model_analysis(stock_symbol: str, analysis_date: str, 
                            collaboration_mode: str, agents: List[str],
                            cost_optimization: str, research_depth: int,
                            config: Dict[str, Any]) -> Dict[str, Any]:
    """运行多模型协作分析"""
    logger.info(f"🚀 开始多模型协作分析: {stock_symbol} ({analysis_date})")
    logger.info(f"📊 协作模式: {collaboration_mode}, 智能体: {agents}")
    
    try:
        # 创建标准交易图
        ta = TradingAgentsGraph(debug=config.get('debug', False), config=config)
        
        # 创建多模型扩展
        mm_extension = MultiModelExtension(ta)
        
        # 检查多模型是否可用
        if not mm_extension.multi_model_enabled:
            logger.warning("⚠️ 多模型功能未启用，回退到单模型分析")
            return run_single_model_analysis(stock_symbol, analysis_date, config)
        
        # 执行多模型协作分析
        result = mm_extension.execute_collaborative_analysis(
            company_name=stock_symbol,
            trade_date=analysis_date,
            collaboration_mode=collaboration_mode,
            selected_agents=agents,
            context={
                'research_depth': research_depth,
                'cost_optimization': cost_optimization
            }
        )
        
        logger.info("✅ 多模型协作分析完成")
        
        return {
            'mode': 'multi_model',
            'collaboration_mode': collaboration_mode,
            'agents_used': agents,
            'cost_optimization': cost_optimization,
            'research_depth': research_depth,
            'result': result,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 多模型协作分析失败: {e}")
        logger.warning("🔄 回退到单模型分析")
        return run_single_model_analysis(stock_symbol, analysis_date, config)


def print_results(results: Dict[str, Any]):
    """打印分析结果"""
    print("\n" + "="*80)
    print(f"📊 TradingAgents-CN 分析结果")
    print("="*80)
    
    mode = results.get('mode', 'unknown')
    
    if mode == 'single_model':
        print(f"🔧 分析模式: 单模型分析")
        if 'decision' in results:
            decision = results['decision']
            print(f"📈 股票: {results.get('stock_symbol', 'N/A')}")
            print(f"📅 日期: {results.get('analysis_date', 'N/A')}")
            print(f"💡 决策: {decision.get('decision', 'N/A')}")
            print(f"📊 置信度: {decision.get('confidence', 'N/A')}")
            
    elif mode == 'multi_model':
        print(f"🤖 分析模式: 多模型协作分析")
        print(f"🔄 协作模式: {results.get('collaboration_mode', 'N/A')}")
        print(f"👥 参与智能体: {', '.join(results.get('agents_used', []))}")
        print(f"💰 成本优化: {results.get('cost_optimization', 'N/A')}")
        print(f"🔍 研究深度: {results.get('research_depth', 'N/A')}")
        
        result = results.get('result', {})
        if isinstance(result, dict):
            if result.get('status') == 'success':
                print("✅ 分析状态: 成功完成")
                collab_result = result.get('collaboration_result', {})
                if collab_result:
                    print(f"💡 最终建议: {collab_result.get('final_result', 'N/A')[:200]}...")
                    print(f"💵 总成本: ${collab_result.get('total_cost', 0):.4f}")
                    print(f"⏱️ 总用时: {collab_result.get('total_time', 0)}秒")
            else:
                print(f"❌ 分析状态: {result.get('error', '未知错误')}")
    
    if 'error' in results:
        print(f"❌ 错误信息: {results['error']}")
    
    print(f"🕒 完成时间: {results.get('timestamp', 'N/A')}")
    print("="*80)


def main():
    """主函数"""
    args = parse_arguments()
    
    print("🤖 TradingAgents-CN 多模型协作系统")
    print(f"📊 分析股票: {args.stock_symbol}")
    print(f"📅 分析日期: {args.analysis_date}")
    
    # 创建配置
    config = create_default_config()
    config['debug'] = args.debug
    
    # 根据参数决定分析模式
    if args.single_model or not MULTI_MODEL_AVAILABLE:
        if args.single_model:
            print("🔧 用户选择单模型模式")
        else:
            print("⚠️ 多模型扩展不可用，使用单模型模式")
            
        results = run_single_model_analysis(args.stock_symbol, args.analysis_date, config)
    else:
        print(f"🚀 启动多模型协作分析 ({args.collaboration_mode} 模式)")
        results = run_multi_model_analysis(
            args.stock_symbol, args.analysis_date,
            args.collaboration_mode, args.agents,
            args.cost_optimization, args.research_depth,
            config
        )
    
    # 打印结果
    print_results(results)
    
    # 返回状态码
    if results.get('status') == 'error' or 'error' in results:
        return 1
    else:
        return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断分析")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 程序异常退出: {e}")
        print(f"❌ 程序异常退出: {e}")
        sys.exit(1)