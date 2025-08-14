"""
Web Multi-Model Collaboration Manager
专为Web界面设计的多模型协作管理器
"""

import os
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from tradingagents.core.multi_model_manager import MultiModelManager
from tradingagents.agents.specialized import (
    NewsHunter, FundamentalExpert, TechnicalAnalyst, 
    SentimentAnalyst, RiskManager, ChiefDecisionOfficer, ChiefWriter
)

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('web_multi_model_manager')


class WebMultiModelCollaborationManager:
    """专为Web界面设计的多模型协作管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化Web多模型协作管理器
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.collaboration_mode = config.get('collaboration_mode', 'sequential')
        self.selected_agents = config.get('selected_agents', [])
        self.use_smart_routing = config.get('use_smart_routing', True)
        
        # 初始化多模型管理器
        self.multi_model_manager = MultiModelManager(config)
        
        # 初始化专业智能体
        self.agents = {}
        self._initialize_agents()
        
        logger.info("Web多模型协作管理器初始化完成")
    
    def _initialize_agents(self):
        """初始化专业智能体"""
        try:
            agent_classes = {
                'news_hunter': NewsHunter,
                'fundamental_expert': FundamentalExpert,
                'technical_analyst': TechnicalAnalyst,
                'sentiment_analyst': SentimentAnalyst,
                'risk_manager': RiskManager,
                'chief_decision_officer': ChiefDecisionOfficer
            }
            
            for agent_type in self.selected_agents:
                if agent_type in agent_classes:
                    try:
                        self.agents[agent_type] = agent_classes[agent_type](
                            multi_model_manager=self.multi_model_manager,
                            config=self.config
                        )
                        logger.info(f"✅ 初始化智能体: {agent_type}")
                    except Exception as e:
                        logger.warning(f"⚠️ 智能体初始化失败 {agent_type}: {e}")
                        
        except Exception as e:
            logger.error(f"智能体初始化失败: {e}")
    
    def run_collaboration_analysis(
        self,
        stock_symbol: str,
        market_type: str = 'A股',
        analysis_date: str = None,
        research_depth: int = 3,
        custom_requirements: str = '',
        show_process_details: bool = True,
        progress_callback=None
    ) -> Dict[str, Any]:
        """
        运行协作分析
        
        Args:
            stock_symbol: 股票代码
            market_type: 市场类型
            analysis_date: 分析日期
            research_depth: 研究深度
            custom_requirements: 自定义要求
            show_process_details: 显示过程详情
            
        Returns:
            分析结果字典
        """
        try:
            logger.info(f"🚀 开始多模型协作分析: {stock_symbol}")
            
            # 准备分析数据
            analysis_data = {
                'stock_symbol': stock_symbol,
                'market_type': market_type,
                'analysis_date': analysis_date or datetime.now().isoformat(),
                'research_depth': research_depth,
                'custom_requirements': custom_requirements
            }
            
            # 根据协作模式执行分析
            if self.collaboration_mode == 'sequential':
                results = self._run_sequential_analysis(analysis_data, progress_callback)
            elif self.collaboration_mode == 'parallel':
                results = self._run_parallel_analysis(analysis_data, progress_callback)
            elif self.collaboration_mode == 'debate':
                results = self._run_debate_analysis(analysis_data, progress_callback)
            else:
                raise ValueError(f"未支持的协作模式: {self.collaboration_mode}")
            
            # 主笔人生成规整长文
            if progress_callback:
                try:
                    progress_callback({'stage': 'chief_writer_prepare', 'message': '准备生成主笔人长文'})
                except Exception:
                    pass
            final_article, article_metrics = self._compose_final_article(results, analysis_data)
            if progress_callback:
                try:
                    progress_callback({'stage': 'chief_writer_done', 'percent': 95, 'message': '主笔人长文生成完成'})
                except Exception:
                    pass

            logger.info("✅ 多模型协作分析完成")
            return {
                'status': 'success',
                'collaboration_mode': self.collaboration_mode,
                'agents_used': list(self.selected_agents),
                'analysis_data': analysis_data,
                'results': results,
                'final_article': final_article,
                'final_article_metrics': article_metrics,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ 协作分析失败: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _run_sequential_analysis(self, analysis_data: Dict[str, Any], progress_callback=None) -> Dict[str, Any]:
        """运行串行协作分析"""
        results = {}
        previous_results = []
        
        for agent_type in self.selected_agents:
            try:
                logger.info(f"🤖 运行智能体: {agent_type}")
                if progress_callback:
                    try:
                        progress_callback({'stage': 'agent_start', 'agent': agent_type, 'message': f'{agent_type} 开始分析'})
                    except Exception:
                        pass
                
                # 准备智能体输入数据
                agent_input = {
                    **analysis_data,
                    'previous_analyses': previous_results
                }
                
                # 真正执行AI分析
                try:
                    # 构建智能体任务提示词（支持角色库自定义）
                    task_prompt = self._build_prompt_for_role(agent_type, analysis_data, previous_results)
                    
                    # 使用多模型管理器执行任务
                    task_result = self.multi_model_manager.execute_task(
                        agent_role=agent_type,
                        task_prompt=task_prompt,
                        task_type=self._get_task_type_for_agent(agent_type),
                        complexity_level="medium" if analysis_data.get('research_depth', 3) <= 3 else "high",
                        context={
                            'session_id': f"web_multi_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                            'market_type': analysis_data.get('market_type', 'A股'),
                            'stock_symbol': analysis_data['stock_symbol'],
                            # 透传模型参数，启用流式与token回调
                            'model_params': {
                                'stream': True,
                                'on_token': (lambda t, agent=agent_type: progress_callback({'stage': 'token', 'agent': agent, 'delta': t}) if progress_callback else None)
                            }
                        }
                    )
                    
                    if task_result.success:
                        agent_result = {
                            'agent_type': agent_type,
                            'analysis': task_result.result,
                            'confidence': 0.85,
                            'recommendations': self._extract_recommendations(task_result.result),
                            'timestamp': datetime.now().isoformat(),
                            'model_used': task_result.model_used.name if task_result.model_used else 'unknown',
                            'execution_time': task_result.execution_time,
                            'token_usage': task_result.token_usage
                        }
                    else:
                        # 如果AI调用失败，回退到模拟结果
                        agent_result = {
                            'agent_type': agent_type,
                            'analysis': f"分析失败: {task_result.error_message}",
                            'confidence': 0.0,
                            'recommendations': "暂无建议",
                            'timestamp': datetime.now().isoformat(),
                            'error': task_result.error_message
                        }
                except Exception as ai_error:
                    logger.warning(f"AI分析失败，使用模拟结果: {ai_error}")
                    # 回退到模拟结果
                    agent_result = {
                        'agent_type': agent_type,
                        'analysis': f"这是 {agent_type} 对 {analysis_data['stock_symbol']} 的分析结果（模拟）",
                        'confidence': 0.85,
                        'recommendations': f"{agent_type} 的投资建议",
                        'timestamp': datetime.now().isoformat()
                    }
                
                results[agent_type] = agent_result
                previous_results.append(agent_result)
                
                logger.info(f"✅ {agent_type} 分析完成")
                if progress_callback:
                    try:
                        progress_callback({'stage': 'agent_done', 'agent': agent_type, 'message': f'{agent_type} 分析完成'})
                    except Exception:
                        pass
                
            except Exception as e:
                logger.error(f"❌ {agent_type} 分析失败: {e}")
                results[agent_type] = {
                    'error': str(e),
                    'status': 'failed'
                }
        
        return results
    
    def _run_parallel_analysis(self, analysis_data: Dict[str, Any], progress_callback=None) -> Dict[str, Any]:
        """运行并行协作分析"""
        results = {}
        
        # 并行执行分析
        for agent_type in self.selected_agents:
            try:
                logger.info(f"🤖 并行运行智能体: {agent_type}")
                if progress_callback:
                    try:
                        progress_callback({'stage': 'agent_start', 'agent': agent_type, 'message': f'{agent_type} 开始分析'})
                    except Exception:
                        pass
                
                # 构建智能体任务提示词（支持角色库自定义）
                task_prompt = self._build_prompt_for_role(agent_type, analysis_data)
                
                # 使用多模型管理器执行任务
                task_result = self.multi_model_manager.execute_task(
                    agent_role=agent_type,
                    task_prompt=task_prompt,
                    task_type=self._get_task_type_for_agent(agent_type),
                    complexity_level="medium" if analysis_data.get('research_depth', 3) <= 3 else "high",
                    context={
                        'session_id': f"web_multi_parallel_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        'market_type': analysis_data.get('market_type', 'A股'),
                        'stock_symbol': analysis_data['stock_symbol'],
                        'model_params': {
                            'stream': True,
                            'on_token': (lambda t, agent=agent_type: progress_callback({'stage': 'token', 'agent': agent, 'delta': t}) if progress_callback else None)
                        }
                    }
                )
                
                if task_result.success:
                    agent_result = {
                        'agent_type': agent_type,
                        'analysis': task_result.result,
                        'confidence': 0.80,
                        'recommendations': self._extract_recommendations(task_result.result),
                        'timestamp': datetime.now().isoformat(),
                        'model_used': task_result.model_used.name if task_result.model_used else 'unknown'
                    }
                else:
                    agent_result = {
                        'agent_type': agent_type,
                        'analysis': f"分析失败: {task_result.error_message}",
                        'confidence': 0.0,
                        'recommendations': "暂无建议",
                        'timestamp': datetime.now().isoformat()
                    }
                
                results[agent_type] = agent_result
                logger.info(f"✅ {agent_type} 并行分析完成")
                if progress_callback:
                    try:
                        progress_callback({'stage': 'agent_done', 'agent': agent_type, 'message': f'{agent_type} 分析完成'})
                    except Exception:
                        pass
                
            except Exception as e:
                logger.error(f"❌ {agent_type} 并行分析失败: {e}")
                results[agent_type] = {
                    'error': str(e),
                    'status': 'failed'
                }
        
        # 整合并行分析结果
        results['summary'] = self._integrate_parallel_results(results)
        
        return results
    
    def _run_debate_analysis(self, analysis_data: Dict[str, Any], progress_callback=None) -> Dict[str, Any]:
        """运行辩论协作分析"""
        results = {}
        
        # 第一轮：各智能体独立分析
        independent_results = {}
        for agent_type in self.selected_agents:
            try:
                logger.info(f"🤖 辩论第1轮 - {agent_type}")
                if progress_callback:
                    try:
                        progress_callback({'stage': 'debate_round1', 'agent': agent_type, 'message': f'{agent_type} 提交初始观点'})
                    except Exception:
                        pass
                
                agent_result = {
                    'agent_type': agent_type,
                    'analysis': f"{agent_type} 对 {analysis_data['stock_symbol']} 的初始观点（模拟）",
                    'stance': 'bullish' if agent_type in ['fundamental_expert', 'news_hunter'] else 'bearish',
                    'confidence': 0.75,
                    'timestamp': datetime.now().isoformat()
                }
                
                independent_results[agent_type] = agent_result
                
            except Exception as e:
                logger.error(f"❌ {agent_type} 辩论分析失败: {e}")
                independent_results[agent_type] = {
                    'error': str(e),
                    'status': 'failed'
                }
        
        # 第二轮：辩论和共识
        consensus_result = self._generate_consensus(independent_results, analysis_data)
        if progress_callback:
            try:
                progress_callback({'stage': 'debate_consensus', 'message': '辩论共识生成完成'})
            except Exception:
                pass
        
        results['independent_analyses'] = independent_results
        results['consensus'] = consensus_result
        
        return results
    
    def _integrate_parallel_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """整合并行分析结果"""
        return {
            'integration_method': 'weighted_average',
            'overall_recommendation': '基于多智能体并行分析的综合建议（模拟）',
            'confidence_score': 0.82,
            'risk_level': 'medium',
            'timestamp': datetime.now().isoformat()
        }

    def _compose_final_article(self, results: Dict[str, Any], analysis_data: Dict[str, Any]) -> (str, Dict[str, Any]):
        """使用主笔人（Gemini-2.5-Pro）生成规整长文"""
        try:
            # 准备专家分析列表（兼容顺序/并行结果字典）
            expert_analyses: List[Dict[str, Any]] = []
            for key, value in results.items():
                if isinstance(value, dict) and 'analysis' in value:
                    expert_analyses.append({
                        'agent_role': value.get('agent_type', key),
                        'analysis_content': value.get('analysis', ''),
                        'confidence_score': value.get('confidence', 0.7),
                        'recommendations': value.get('recommendations', []),
                        'key_points': [],
                        'risk_factors': [],
                    })

            if not expert_analyses:
                return "", {}

            # 初始化或复用主笔人
            writer = self.agents.get('chief_writer')
            if writer is None:
                try:
                    writer = ChiefWriter(self.multi_model_manager, config=self.config)
                    self.agents['chief_writer'] = writer
                except Exception:
                    return "", {}

            writer_input = {
                'expert_analyses': expert_analyses,
                'market_context': {
                    'market_type': analysis_data.get('market_type'),
                    'stock_symbol': analysis_data.get('stock_symbol'),
                    'analysis_date': analysis_data.get('analysis_date'),
                },
                'collaboration_mode': self.collaboration_mode,
            }

            article_result = writer.analyze(
                input_data=writer_input,
                context={'priority': 'quality_first'},
                complexity_level='high',
            )

            return article_result.analysis_content, article_result.supporting_data
        except Exception as e:
            logger.error(f"主笔人生成长文失败: {e}")
            return "", {}
    
    def _generate_consensus(self, independent_results: Dict[str, Any], analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成辩论共识"""
        return {
            'consensus_method': 'debate_resolution',
            'final_recommendation': f"经过多轮辩论，对 {analysis_data['stock_symbol']} 的最终共识（模拟）",
            'agreement_level': 0.78,
            'dissenting_opinions': ['部分智能体持保留意见'],
            'timestamp': datetime.now().isoformat()
        }
    
    def _build_agent_prompt(self, agent_type: str, analysis_data: Dict[str, Any], 
                          previous_results: List[Dict[str, Any]] = None) -> str:
        """构建智能体的任务提示词"""
        stock_symbol = analysis_data.get('stock_symbol', '')
        market_type = analysis_data.get('market_type', 'A股')
        analysis_date = analysis_data.get('analysis_date', datetime.now().strftime('%Y-%m-%d'))
        custom_requirements = analysis_data.get('custom_requirements', '')
        
        base_prompt = f"""请作为{self._get_agent_chinese_name(agent_type)}分析{market_type}股票 {stock_symbol}。
分析日期：{analysis_date}

请提供专业、深入的分析，包括：
1. 从你的专业角度分析这只股票
2. 给出具体的投资建议
3. 评估相关风险和机会
"""
        
        if custom_requirements:
            base_prompt += f"\n特别要求：{custom_requirements}\n"
        
        if previous_results and agent_type != 'news_hunter':  # 第一个智能体不需要前置结果
            base_prompt += "\n前面的分析结果：\n"
            for prev in previous_results[-2:]:  # 只包含最近2个分析
                base_prompt += f"- {prev['agent_type']}: {prev.get('analysis', '')[:200]}...\n"
        
        return base_prompt

    def _build_prompt_for_role(self, agent_type: str, analysis_data: Dict[str, Any], 
                              previous_results: List[Dict[str, Any]] = None) -> str:
        """优先使用角色库模板生成提示，否则回退到通用提示。"""
        try:
            from tradingagents.config.role_library import get_prompt, format_prompt
            sys_tpl = get_prompt(agent_type, 'system_prompt')
            if sys_tpl:
                ctx = {
                    'ticker': analysis_data.get('stock_symbol', ''),
                    'company_name': analysis_data.get('stock_symbol', ''),
                    'market_type': analysis_data.get('market_type', ''),
                    'current_date': analysis_data.get('analysis_date', ''),
                    'custom_requirements': analysis_data.get('custom_requirements', ''),
                    'previous_results': previous_results or [],
                }
                return format_prompt(sys_tpl, ctx)
        except Exception:
            pass
        return self._build_agent_prompt(agent_type, analysis_data, previous_results)
    
    def _get_task_type_for_agent(self, agent_type: str) -> str:
        """获取智能体对应的任务类型"""
        # 先尝试角色库覆盖
        try:
            from tradingagents.config.provider_models import model_provider_manager
            custom = model_provider_manager.role_task_types.get(agent_type)
            if isinstance(custom, str) and custom:
                return custom
        except Exception:
            pass
        task_mapping = {
            'news_hunter': 'news_analysis',
            'fundamental_expert': 'fundamental_analysis',
            'technical_analyst': 'technical_analysis',
            'sentiment_analyst': 'sentiment_analysis',
            'risk_manager': 'risk_assessment',
            'policy_researcher': 'policy_analysis',
            'tool_engineer': 'technical_analysis',
            'compliance_officer': 'compliance_check',
            'chief_decision_officer': 'decision_making'
        }
        return task_mapping.get(agent_type, 'general')
    
    def _get_agent_chinese_name(self, agent_type: str) -> str:
        """获取智能体的中文名称"""
        try:
            from tradingagents.config.provider_models import model_provider_manager
            cfg = model_provider_manager.role_definitions.get(agent_type)
            if cfg and cfg.name:
                return cfg.name
        except Exception:
            pass
        name_mapping = {
            'news_hunter': '快讯猎手',
            'fundamental_expert': '基本面专家',
            'technical_analyst': '技术分析师',
            'sentiment_analyst': '情绪分析师',
            'risk_manager': '风控经理',
            'policy_researcher': '政策研究员',
            'tool_engineer': '工具工程师',
            'compliance_officer': '合规官',
            'chief_decision_officer': '首席决策官'
        }
        return name_mapping.get(agent_type, agent_type)
    
    def _extract_recommendations(self, analysis_text: str) -> str:
        """从分析文本中提取投资建议"""
        # 简单的关键词提取逻辑
        if '建议买入' in analysis_text or '强烈推荐' in analysis_text:
            return "买入建议"
        elif '建议卖出' in analysis_text or '建议减持' in analysis_text:
            return "卖出建议"
        elif '建议持有' in analysis_text or '观望' in analysis_text:
            return "持有建议"
        else:
            # 尝试提取包含"建议"的句子
            import re
            matches = re.findall(r'[^。]*建议[^。]*。', analysis_text)
            if matches:
                return matches[0]
            return "请参考详细分析"
