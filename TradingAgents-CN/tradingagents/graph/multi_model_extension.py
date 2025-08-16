"""
Multi-Model Trading Graph Extension
扩展现有的TradingGraph以支持多模型协作功能
"""

import os
import yaml
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

# 导入多模型组件
from tradingagents.core.multi_model_manager import MultiModelManager
from tradingagents.agents.specialized import (
    NewsHunter, FundamentalExpert, TechnicalAnalyst, SentimentAnalyst, 
    RiskManager, ChiefDecisionOfficer, ChiefWriter
)
from tradingagents.agents.specialized.charting_artist import ChartingArtist
from tradingagents.agents.specialized.base_specialized_agent import AgentAnalysisResult

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger
logger = get_logger('multi_model_trading_graph')


class MultiModelExtension:
    """TradingGraph的多模型协作扩展"""
    
    def __init__(self, trading_graph_instance):
        """
        初始化多模型扩展
        
        Args:
            trading_graph_instance: TradingGraph实例
        """
        self.trading_graph = trading_graph_instance
        self.config = trading_graph_instance.config
        
        # 加载多模型配置
        self.multi_model_config = self._load_multi_model_config()
        self.agent_roles_config = self._load_agent_roles_config()
        
        # 初始化多模型管理器
        self.multi_model_manager = None
        self.specialized_agents = {}
        
        # 协作模式配置
        self.collaboration_modes = {
            'sequential': self._execute_sequential_collaboration,
            'parallel': self._execute_parallel_collaboration,
            'debate': self._execute_debate_collaboration
        }
        
        # 启用标志
        self.multi_model_enabled = self._check_multi_model_availability()
        
        if self.multi_model_enabled:
            self._initialize_multi_model_components()
            logger.info("多模型协作扩展初始化成功")
        else:
            logger.warning("多模型功能不可用，将使用传统单模型模式")
    
    def _load_multi_model_config(self) -> Dict[str, Any]:
        """加载多模型配置"""
        try:
            config_path = Path(__file__).parent.parent.parent / "config" / "multi_model_config.yaml"
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"加载多模型配置失败: {e}")
        
        # 返回默认配置
        return {
            'providers': {
                'siliconflow': {'enabled': False},
                'google': {'enabled': False}
            }
        }
    
    def _load_agent_roles_config(self) -> Dict[str, Any]:
        """加载智能体角色配置"""
        try:
            config_path = Path(__file__).parent.parent.parent / "config" / "agent_roles.yaml"
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"加载智能体角色配置失败: {e}")
        
        return {'agent_roles': {}}
    
    def _check_multi_model_availability(self) -> bool:
        """检查多模型功能是否可用"""
        # 检查必要的API密钥 - 支持多种环境变量名
        siliconflow_key = os.getenv('SILICONFLOW_API_KEY')
        google_key = (
            os.getenv('GOOGLE_AI_API_KEY')
            or os.getenv('GOOGLE_API_KEY')
            or os.getenv('GEMINI_API_KEY')
        )
        
        # 检查配置 - 修正配置路径，使用 'google_ai' 而不是 'google'
        siliconflow_enabled = self.multi_model_config.get('providers', {}).get('siliconflow', {}).get('enabled', False)
        google_enabled = self.multi_model_config.get('providers', {}).get('google_ai', {}).get('enabled', False)
        gemini_api_enabled = self.multi_model_config.get('providers', {}).get('gemini_api', {}).get('enabled', False)
        deepseek_enabled = self.multi_model_config.get('providers', {}).get('deepseek', {}).get('enabled', False)
        
        deepseek_key = os.getenv('DEEPSEEK_API_KEY')
        
        gemini_api_key = os.getenv('GEMINI_API_COMPAT_API_KEY') or os.getenv('OPENAI_API_KEY')
        has_provider = (
            (siliconflow_key and siliconflow_enabled)
            or (google_key and google_enabled)
            or (deepseek_key and deepseek_enabled)
            or (gemini_api_key and gemini_api_enabled)
        )
        
        if not has_provider:
            logger.info(f"多模型检查: SiliconFlow={bool(siliconflow_key)}/{siliconflow_enabled}, Google={bool(google_key)}/{google_enabled}, DeepSeek={bool(deepseek_key)}/{deepseek_enabled}")
            logger.info("未检测到多模型API配置，多模型功能将被禁用")
            return False
        
        return True
    
    def _initialize_multi_model_components(self) -> None:
        """初始化多模型组件"""
        try:
            # 准备API配置
            api_configs = {}
            
            # SiliconFlow配置
            if (os.getenv('SILICONFLOW_API_KEY') and 
                self.multi_model_config.get('providers', {}).get('siliconflow', {}).get('enabled', False)):
                api_configs['siliconflow'] = {
                    'enabled': True,
                    'api_key': os.getenv('SILICONFLOW_API_KEY'),
                    'base_url': self.multi_model_config['providers']['siliconflow'].get('base_url', 'https://api.siliconflow.cn/v1'),
                    'timeout': self.multi_model_config['providers']['siliconflow'].get('timeout', 60)
                }
            
            # Google AI配置 - 支持多种环境变量检查
            google_key = (
                os.getenv('GOOGLE_AI_API_KEY')
                or os.getenv('GOOGLE_API_KEY')
                or os.getenv('GEMINI_API_KEY')
            )
            if (google_key and 
                self.multi_model_config.get('providers', {}).get('google_ai', {}).get('enabled', False)):
                api_configs['google_ai'] = {
                    'enabled': True,
                    'api_key': google_key,
                    'timeout': self.multi_model_config['providers']['google_ai'].get('timeout', 60)
                }

            # Gemini-API 兼容（OpenAI协议反代）
            gapi_cfg = self.multi_model_config.get('providers', {}).get('gemini_api', {})
            gapi_key = os.getenv('GEMINI_API_COMPAT_API_KEY') or os.getenv('OPENAI_API_KEY')
            if gapi_key and gapi_cfg.get('enabled', False):
                api_configs['gemini_api'] = {
                    'enabled': True,
                    'api_key': gapi_key,
                    'base_url': gapi_cfg.get('base_url', os.getenv('GEMINI_API_COMPAT_BASE_URL', 'http://localhost:8080/v1')),
                    'default_model': gapi_cfg.get('default_model', 'gemini-2.5-pro'),
                    'timeout': gapi_cfg.get('timeout', 60),
                }
            
            # DeepSeek配置
            if (os.getenv('DEEPSEEK_API_KEY') and 
                self.multi_model_config.get('providers', {}).get('deepseek', {}).get('enabled', False)):
                api_configs['deepseek'] = {
                    'enabled': True,
                    'api_key': os.getenv('DEEPSEEK_API_KEY'),
                    'base_url': self.multi_model_config['providers']['deepseek'].get('base_url', 'https://api.deepseek.com'),
                    'timeout': self.multi_model_config['providers']['deepseek'].get('timeout', 60)
                }
            
            # 添加系统配置
            system_config = self.multi_model_config.get('system', {})
            api_configs.update(system_config)

            # 传递策略/绑定/目录到多模型管理器
            api_configs['agent_bindings'] = self.multi_model_config.get('agent_bindings', {})
            api_configs['task_bindings'] = self.multi_model_config.get('task_bindings', {})
            api_configs['intra_pool_weights'] = self.multi_model_config.get('intra_pool_weights', {})
            api_configs['model_catalog'] = self.multi_model_config.get('model_catalog', {})
            api_configs['runtime_overrides'] = self.multi_model_config.get('runtime_overrides', {})
            
            # 初始化多模型管理器
            self.multi_model_manager = MultiModelManager(api_configs)
            
            # 初始化专业智能体
            self._initialize_specialized_agents()
            
        except Exception as e:
            logger.error(f"多模型组件初始化失败: {e}")
            self.multi_model_enabled = False
            raise
    
    def _initialize_specialized_agents(self) -> None:
        """初始化专业智能体"""
        agent_classes = {
            'news_hunter': NewsHunter,
            'fundamental_expert': FundamentalExpert,
            'technical_analyst': TechnicalAnalyst,
            'sentiment_analyst': SentimentAnalyst,
            'risk_manager': RiskManager,
            'chief_decision_officer': ChiefDecisionOfficer,
            'chief_writer': ChiefWriter,
            'charting_artist': ChartingArtist,  # 新增绘图师智能体
        }
        
        for role, agent_class in agent_classes.items():
            try:
                agent_config = self.agent_roles_config.get('agent_roles', {}).get(role, {})
                self.specialized_agents[role] = agent_class(
                    multi_model_manager=self.multi_model_manager,
                    config=agent_config
                )
                logger.debug(f"初始化专业智能体: {role}")
            except Exception as e:
                logger.error(f"初始化{role}智能体失败: {e}")
    
    def execute_collaborative_analysis(self,
                                     company_name: str,
                                     trade_date: str,
                                     collaboration_mode: str = "sequential",
                                     selected_agents: List[str] = None,
                                     context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        执行协作分析
        
        Args:
            company_name: 公司名称
            trade_date: 交易日期
            collaboration_mode: 协作模式 (sequential/parallel/debate)
            selected_agents: 选择的智能体列表
            context: 上下文信息
            
        Returns:
            Dict[str, Any]: 协作分析结果
        """
        if not self.multi_model_enabled:
            logger.warning("多模型功能未启用，无法执行协作分析")
            return self._fallback_to_traditional_analysis(company_name, trade_date)
        
        # 默认智能体选择
        if selected_agents is None:
            selected_agents = ['news_hunter', 'fundamental_expert', 'technical_analyst', 'risk_manager']
        
        # 构建上下文
        analysis_context = {
            'company_name': company_name,
            'trade_date': trade_date,
            'session_id': f"collab_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'collaboration_mode': collaboration_mode,
            'traditional_data': self._prepare_traditional_data(company_name, trade_date)
        }
        if context:
            analysis_context.update(context)
        
        try:
            # 执行协作分析
            if collaboration_mode in self.collaboration_modes:
                collaboration_result = self.collaboration_modes[collaboration_mode](
                    selected_agents, analysis_context
                )
            else:
                raise ValueError(f"不支持的协作模式: {collaboration_mode}")
            
            # 生成最终决策
            final_decision = self._generate_final_decision(
                collaboration_result, analysis_context
            )
            
            # 整合结果
            integrated_result = self._integrate_with_traditional_output(
                final_decision, collaboration_result, company_name, trade_date
            )
            
            logger.info(f"协作分析完成: {company_name}, 模式: {collaboration_mode}")
            
            return integrated_result
            
        except Exception as e:
            logger.error(f"协作分析失败: {e}", exc_info=True)
            return self._fallback_to_traditional_analysis(company_name, trade_date)
    
    def _prepare_traditional_data(self, company_name: str, trade_date: str) -> Dict[str, Any]:
        """准备传统分析的数据"""
        try:
            # 使用现有的数据获取功能
            traditional_data = {}
            
            # 如果trading_graph有数据获取方法，调用它们
            if hasattr(self.trading_graph, 'toolkit'):
                # 获取股票数据
                traditional_data['stock_data'] = "使用现有数据获取工具"
                # 可以在这里调用现有的数据获取工具
            
            return traditional_data
            
        except Exception as e:
            logger.warning(f"准备传统数据失败: {e}")
            return {}
    
    def _execute_sequential_collaboration(self, 
                                        selected_agents: List[str], 
                                        context: Dict[str, Any]) -> Dict[str, Any]:
        """执行序列协作分析"""
        results = []
        accumulated_context = context.copy()
        
        for agent_role in selected_agents:
            if agent_role not in self.specialized_agents:
                logger.warning(f"智能体 {agent_role} 不可用，跳过")
                continue
            
            # 特殊处理：检查ChartingArtist是否启用
            if agent_role == 'charting_artist':
                charting_enabled = os.getenv('CHARTING_ARTIST_ENABLED', 'false').lower() == 'true'
                if not charting_enabled:
                    logger.info("ChartingArtist未启用，跳过绘图师分析")
                    continue
            
            try:
                agent = self.specialized_agents[agent_role]
                
                # 构建输入数据
                input_data = self._prepare_agent_input(agent_role, accumulated_context)
                
                # 执行分析
                result = agent.analyze(
                    input_data=input_data,
                    context=accumulated_context,
                    complexity_level="medium"
                )
                
                results.append(result)
                
                # 更新累积上下文
                accumulated_context[f'{agent_role}_result'] = result.analysis_content
                accumulated_context[f'{agent_role}_confidence'] = result.confidence_score
                
                logger.info(f"序列协作完成: {agent_role}")
                
            except Exception as e:
                logger.error(f"智能体 {agent_role} 执行失败: {e}")
        
        return {
            'mode': 'sequential',
            'results': results,
            'final_context': accumulated_context
        }
    
    def _execute_parallel_collaboration(self, 
                                      selected_agents: List[str], 
                                      context: Dict[str, Any]) -> Dict[str, Any]:
        """执行并行协作分析"""
        results = []
        
        for agent_role in selected_agents:
            if agent_role not in self.specialized_agents:
                logger.warning(f"智能体 {agent_role} 不可用，跳过")
                continue
            
            # 特殊处理：检查ChartingArtist是否启用
            if agent_role == 'charting_artist':
                charting_enabled = os.getenv('CHARTING_ARTIST_ENABLED', 'false').lower() == 'true'
                if not charting_enabled:
                    logger.info("ChartingArtist未启用，跳过绘图师分析")
                    continue
            
            try:
                agent = self.specialized_agents[agent_role]
                
                # 构建输入数据
                input_data = self._prepare_agent_input(agent_role, context)
                
                # 执行分析
                result = agent.analyze(
                    input_data=input_data,
                    context=context,
                    complexity_level="medium"
                )
                
                results.append(result)
                logger.info(f"并行协作完成: {agent_role}")
                
            except Exception as e:
                logger.error(f"智能体 {agent_role} 执行失败: {e}")
        
        return {
            'mode': 'parallel',
            'results': results,
            'final_context': context
        }
    
    def _execute_debate_collaboration(self, 
                                    selected_agents: List[str], 
                                    context: Dict[str, Any]) -> Dict[str, Any]:
        """执行辩论协作分析"""
        if len(selected_agents) < 2:
            logger.warning("辩论模式需要至少2个智能体，回退到并行模式")
            return self._execute_parallel_collaboration(selected_agents, context)
        
        max_rounds = 2  # 简化版本，减少轮次
        debate_history = []
        
        # 第一轮：初始观点
        initial_results = []
        for agent_role in selected_agents:
            if agent_role not in self.specialized_agents:
                continue
            
            # 特殊处理：检查ChartingArtist是否启用
            if agent_role == 'charting_artist':
                charting_enabled = os.getenv('CHARTING_ARTIST_ENABLED', 'false').lower() == 'true'
                if not charting_enabled:
                    logger.info("ChartingArtist未启用，跳过绘图师分析")
                    continue
            
            try:
                agent = self.specialized_agents[agent_role]
                input_data = self._prepare_agent_input(agent_role, context)
                input_data['debate_instruction'] = "请提出你的初始分析观点"
                
                result = agent.analyze(input_data=input_data, context=context)
                initial_results.append(result)
                debate_history.append({
                    'round': 1,
                    'agent': agent_role,
                    'position': result.analysis_content
                })
                
            except Exception as e:
                logger.error(f"辩论首轮失败 {agent_role}: {e}")
        
        # 第二轮：回应和调整
        if len(initial_results) > 1:
            final_results = []
            for i, agent_role in enumerate(selected_agents):
                if agent_role not in self.specialized_agents:
                    continue
                
                try:
                    agent = self.specialized_agents[agent_role]
                    
                    # 收集其他智能体的观点
                    other_positions = [
                        entry["position"] for entry in debate_history
                        if entry["agent"] != agent_role
                    ]
                    
                    input_data = self._prepare_agent_input(agent_role, context)
                    input_data['other_opinions'] = other_positions[:2]  # 最多考虑2个其他观点
                    input_data['debate_instruction'] = "基于其他专家的观点，请调整或坚持你的分析"
                    
                    result = agent.analyze(input_data=input_data, context=context)
                    final_results.append(result)
                    
                    debate_history.append({
                        'round': 2,
                        'agent': agent_role,
                        'position': result.analysis_content
                    })
                    
                except Exception as e:
                    logger.error(f"辩论第二轮失败 {agent_role}: {e}")
                    # 使用第一轮结果
                    if i < len(initial_results):
                        final_results.append(initial_results[i])
        else:
            final_results = initial_results
        
        return {
            'mode': 'debate',
            'results': final_results,
            'debate_history': debate_history,
            'final_context': context
        }
    
    def _prepare_agent_input(self, agent_role: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """为特定智能体准备输入数据"""
        base_input = {
            'company_name': context['company_name'],
            'trade_date': context['trade_date'],
            'analysis_request': f"请作为{agent_role}分析股票{context['company_name']}"
        }
        
        # 根据智能体类型添加特定数据
        if agent_role == 'news_hunter':
            base_input['news_content'] = f"关于{context['company_name']}的最新新闻分析请求"
        elif agent_role == 'fundamental_expert':
            base_input['financial_data'] = {"company": context['company_name'], "basic_info": "需要分析"}
        elif agent_role == 'technical_analyst':
            base_input['price_data'] = {"company": context['company_name'], "chart_data": "需要分析"}
        elif agent_role == 'sentiment_analyst':
            base_input['sentiment_data'] = {"company": context['company_name'], "market_sentiment": "需要分析"}
        elif agent_role == 'risk_manager':
            base_input['investment_proposal'] = f"投资{context['company_name']}的风险评估请求"
        
        # 添加辩论特定字段
        if 'debate_instruction' in context:
            base_input['debate_instruction'] = context['debate_instruction']
        if 'other_opinions' in context:
            base_input['other_opinions'] = context['other_opinions']
        
        return base_input
    
    def _generate_final_decision(self, 
                               collaboration_result: Dict[str, Any], 
                               context: Dict[str, Any]) -> AgentAnalysisResult:
        """生成最终决策"""
        if 'chief_decision_officer' not in self.specialized_agents:
            # 如果没有首席决策官，使用简单的结果合成
            return self._synthesize_simple_decision(collaboration_result)
        
        try:
            cdo = self.specialized_agents['chief_decision_officer']
            
            # 准备专家分析数据
            expert_analyses = []
            for result in collaboration_result.get('results', []):
                expert_analyses.append({
                    'agent_role': result.agent_role,
                    'analysis_content': result.analysis_content,
                    'confidence_score': result.confidence_score,
                    'key_points': result.key_points,
                    'risk_factors': result.risk_factors,
                    'recommendations': result.recommendations
                })
            
            # 执行最终决策
            decision_input = {
                'expert_analyses': expert_analyses,
                'market_context': context.get('traditional_data', {}),
                'collaboration_metadata': {
                    'mode': collaboration_result.get('mode'),
                    'total_experts': len(expert_analyses)
                }
            }
            
            final_decision = cdo.analyze(
                input_data=decision_input,
                context=context,
                complexity_level="high"
            )
            
            # 调用主笔人生成规整长文（吸收各方观点）
            try:
                if 'chief_writer' in self.specialized_agents:
                    writer_input = {
                        'expert_analyses': expert_analyses,
                        'final_decision_brief': final_decision.analysis_content,
                        'market_context': context.get('traditional_data', {}),
                        'collaboration_mode': collaboration_result.get('mode'),
                    }
                    writer = self.specialized_agents['chief_writer']
                    final_article = writer.analyze(
                        input_data=writer_input,
                        context={**context, 'priority': 'quality_first'},
                        complexity_level="high",
                    )
                    # 将长文放入 context 以便后续导出
                    context['final_article'] = final_article.analysis_content
                    context['final_article_metrics'] = final_article.supporting_data
            except Exception as e:
                logger.error(f"主笔人生成长文失败: {e}")
            
            return final_decision
            
        except Exception as e:
            logger.error(f"最终决策生成失败: {e}")
            return self._synthesize_simple_decision(collaboration_result)
    
    def _synthesize_simple_decision(self, collaboration_result: Dict[str, Any]) -> AgentAnalysisResult:
        """简单的决策合成"""
        results = collaboration_result.get('results', [])
        
        if not results:
            return self._create_fallback_result()
        
        # 计算平均置信度
        avg_confidence = sum(r.confidence_score for r in results) / len(results)
        
        # 合并关键点
        all_key_points = []
        all_risks = []
        all_recommendations = []
        
        for result in results:
            all_key_points.extend(result.key_points[:2])  # 每个智能体最多取2个关键点
            all_risks.extend(result.risk_factors[:2])
            all_recommendations.extend(result.recommendations[:1])
        
        # 生成综合分析内容
        synthesis_content = self._generate_synthesis_content(results)
        
        return AgentAnalysisResult(
            agent_role="collaborative_synthesis",
            analysis_content=synthesis_content,
            confidence_score=avg_confidence,
            key_points=all_key_points[:5],  # 最多5个关键点
            risk_factors=all_risks[:3],     # 最多3个风险
            recommendations=all_recommendations[:3],  # 最多3个建议
            supporting_data={'synthesis_method': 'simple_average'},
            timestamp=datetime.now(),
            model_used='multi_agent_synthesis',
            execution_time=0
        )
    
    def _generate_synthesis_content(self, results: List[AgentAnalysisResult]) -> str:
        """生成综合分析内容"""
        content = "## 多智能体协作分析综合报告\n\n"
        
        content += "### 各专家观点摘要\n"
        for i, result in enumerate(results, 1):
            content += f"**{i}. {result.agent_role}** (置信度: {result.confidence_score:.1%})\n"
            if result.key_points:
                content += f"   核心观点: {result.key_points[0]}\n"
            content += "\n"
        
        # 简单的共识分析
        confidence_scores = [r.confidence_score for r in results]
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
        consensus_level = "高" if max(confidence_scores) - min(confidence_scores) < 0.2 else "中等" if max(confidence_scores) - min(confidence_scores) < 0.4 else "低"
        
        content += f"### 综合评估\n"
        content += f"- 平均信心度: {avg_confidence:.1%}\n"
        content += f"- 专家共识度: {consensus_level}\n"
        content += f"- 参与专家数量: {len(results)}\n"
        
        return content
    
    def _create_fallback_result(self) -> AgentAnalysisResult:
        """创建回退结果"""
        return AgentAnalysisResult(
            agent_role="fallback",
            analysis_content="协作分析失败，无法提供有效分析结果",
            confidence_score=0.1,
            key_points=[],
            risk_factors=["协作分析系统异常"],
            recommendations=["建议使用传统分析模式"],
            supporting_data={},
            timestamp=datetime.now(),
            model_used='fallback',
            execution_time=0
        )
    
    def _integrate_with_traditional_output(self, 
                                         final_decision: AgentAnalysisResult,
                                         collaboration_result: Dict[str, Any],
                                         company_name: str,
                                         trade_date: str) -> Dict[str, Any]:
        """与传统输出格式集成"""
        integrated_result = {
            'company_name': company_name,
            'trade_date': trade_date,
            'collaboration_mode': collaboration_result.get('mode', 'unknown'),
            'final_decision': final_decision.analysis_content,
            'final_article': collaboration_result.get('final_article'),
            'final_article_metrics': collaboration_result.get('final_article_metrics', {}),
            'confidence_score': final_decision.confidence_score,
            'key_insights': final_decision.key_points,
            'risk_factors': final_decision.risk_factors,
            'recommendations': final_decision.recommendations,
            'expert_results': [result.to_dict() for result in collaboration_result.get('results', [])],
            'synthesis_metadata': {
                'total_experts': len(collaboration_result.get('results', [])),
                'execution_time': sum(r.execution_time for r in collaboration_result.get('results', [])),
                'models_used': list(set(r.model_used for r in collaboration_result.get('results', []) if r.model_used))
            },
            'multi_model_enabled': True
        }
        
        # 检查是否有ChartingArtist的可视化结果，并集成到输出中
        analysis_results = {result.agent_role: result for result in collaboration_result.get('results', [])}
        if 'charting_artist' in analysis_results:
            charting_result = analysis_results['charting_artist']
            if charting_result.supporting_data and 'visualizations' in charting_result.supporting_data:
                integrated_result['visualizations'] = charting_result.supporting_data['visualizations']
                logger.info("已集成ChartingArtist的可视化结果到输出中")
        
        return integrated_result
    
    def _fallback_to_traditional_analysis(self, company_name: str, trade_date: str) -> Dict[str, Any]:
        """回退到传统分析模式"""
        try:
            # 调用原始的TradingGraph分析方法
            logger.info("回退到传统单模型分析")
            traditional_result, signal = self.trading_graph.propagate(company_name, trade_date)
            
            return {
                'company_name': company_name,
                'trade_date': trade_date,
                'collaboration_mode': 'traditional_fallback',
                'final_decision': traditional_result.get('final_trade_decision', '无决策'),
                'confidence_score': 0.5,  # 传统模式使用默认置信度
                'traditional_result': traditional_result,
                'signal': signal,
                'multi_model_enabled': False,
                'fallback_reason': '多模型功能不可用或执行失败'
            }
        except Exception as e:
            logger.error(f"传统分析也失败: {e}")
            return {
                'company_name': company_name,
                'trade_date': trade_date,
                'error': str(e),
                'multi_model_enabled': False
            }
    
    def get_multi_model_status(self) -> Dict[str, Any]:
        """获取多模型系统状态"""
        status = {
            'multi_model_enabled': self.multi_model_enabled,
            'available_agents': list(self.specialized_agents.keys()),
            'collaboration_modes': list(self.collaboration_modes.keys()),
        }
        
        if self.multi_model_enabled and self.multi_model_manager:
            status.update(self.multi_model_manager.get_system_status())
        
        return status
