# TradingAgents/graph/trading_graph.py

import os
from pathlib import Path
import json
from datetime import date
from typing import Dict, Any, Tuple, List, Optional

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

from langgraph.prebuilt import ToolNode

# Import enhanced configuration manager
from tradingagents.config.enhanced_gemini_config import enhanced_gemini_config

from tradingagents.agents import *
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.agents.utils.memory import FinancialSituationMemory

# 导入统一日志系统
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('trading_graph')
from tradingagents.agents.utils.agent_states import (
    AgentState,
    InvestDebateState,
    RiskDebateState,
)
from tradingagents.dataflows.interface import set_config

from .conditional_logic import ConditionalLogic
from .setup import GraphSetup
from .propagation import Propagator
from .reflection import Reflector
from .signal_processing import SignalProcessor


class TradingAgentsGraph:
    """Main class that orchestrates the trading agents framework."""
    
    def _get_gemini_model_params(self, model_name: str, is_deep_thinking: bool = True) -> Dict[str, Any]:
        """Get model-specific parameters for Gemini models.
        
        Args:
            model_name: The Gemini model name (e.g., 'gemini-2.5-pro', 'gemini-2.0-flash')
            is_deep_thinking: Whether this is for deep thinking tasks (affects parameters)
            
        Returns:
            Dictionary of model parameters optimized for the specific model
        """
        model_name_lower = model_name.lower()
        
        # Gemini 2.5 Pro models - optimized for comprehensive analysis
        if "2.5-pro" in model_name_lower or "gemini-2.5-pro" in model_name_lower:
            if is_deep_thinking:
                return {
                    "temperature": 0.3,  # Higher temperature for more comprehensive analysis
                    "max_tokens": 8000,  # Much higher token limit for complete analysis
                    "top_p": 0.8,       # Allow for more diverse reasoning paths
                }
            else:
                return {
                    "temperature": 0.2,  # Moderate temperature for quick tasks
                    "max_tokens": 4000,  # Higher than default but less than deep thinking
                    "top_p": 0.7,
                }
        
        # Gemini 2.0 Flash models - optimized for speed and efficiency
        elif "2.0-flash" in model_name_lower or "gemini-2.0-flash" in model_name_lower:
            if is_deep_thinking:
                return {
                    "temperature": 0.2,  # Balanced temperature
                    "max_tokens": 4000,  # Adequate for most analysis tasks
                    "top_p": 0.7,
                }
            else:
                return {
                    "temperature": 0.1,  # Lower temperature for quick, focused responses
                    "max_tokens": 2000,  # Standard limit for quick tasks
                    "top_p": 0.6,
                }
        
        # Gemini 1.5 Pro models
        elif "1.5-pro" in model_name_lower or "gemini-1.5-pro" in model_name_lower:
            if is_deep_thinking:
                return {
                    "temperature": 0.25,
                    "max_tokens": 6000,
                    "top_p": 0.75,
                }
            else:
                return {
                    "temperature": 0.15,
                    "max_tokens": 3000,
                    "top_p": 0.65,
                }
        
        # Gemini 1.5 Flash models
        elif "1.5-flash" in model_name_lower or "gemini-1.5-flash" in model_name_lower:
            if is_deep_thinking:
                return {
                    "temperature": 0.2,
                    "max_tokens": 4000,
                    "top_p": 0.7,
                }
            else:
                return {
                    "temperature": 0.1,
                    "max_tokens": 2000,
                    "top_p": 0.6,
                }
        
        # Legacy Gemini Pro models (fallback)
        elif "gemini-pro" in model_name_lower:
            if is_deep_thinking:
                return {
                    "temperature": 0.2,
                    "max_tokens": 3000,
                    "top_p": 0.7,
                }
            else:
                return {
                    "temperature": 0.1,
                    "max_tokens": 2000,
                    "top_p": 0.6,
                }
        
        # Default parameters for unknown Gemini models
        else:
            logger.warning(f"⚠️ Unknown Gemini model '{model_name}', using default parameters")
            if is_deep_thinking:
                return {
                    "temperature": 0.2,
                    "max_tokens": 4000,
                    "top_p": 0.7,
                }
            else:
                return {
                    "temperature": 0.1,
                    "max_tokens": 2000,
                    "top_p": 0.6,
                }

    def __init__(
        self,
        selected_analysts=["market", "social", "news", "fundamentals"],
        debug=False,
        config: Dict[str, Any] = None,
    ):
        """Initialize the trading agents graph and components.

        Args:
            selected_analysts: List of analyst types to include
            debug: Whether to run in debug mode
            config: Configuration dictionary. If None, uses default config
        """
        self.debug = debug
        self.config = config or DEFAULT_CONFIG

        # Update the interface's config
        set_config(self.config)

        # Create necessary directories
        os.makedirs(
            os.path.join(self.config["project_dir"], "dataflows/data_cache"),
            exist_ok=True,
        )

        # Initialize LLMs
        if self.config["llm_provider"].lower() == "openai":
            self.deep_thinking_llm = ChatOpenAI(model=self.config["deep_think_llm"], base_url=self.config["backend_url"])
            self.quick_thinking_llm = ChatOpenAI(model=self.config["quick_think_llm"], base_url=self.config["backend_url"])
        elif self.config["llm_provider"] == "openrouter":
            # OpenRouter支持：优先使用OPENROUTER_API_KEY，否则使用OPENAI_API_KEY
            openrouter_api_key = os.getenv('OPENROUTER_API_KEY') or os.getenv('OPENAI_API_KEY')
            if not openrouter_api_key:
                raise ValueError("使用OpenRouter需要设置OPENROUTER_API_KEY或OPENAI_API_KEY环境变量")

            logger.info(f"🌐 [OpenRouter] 使用API密钥: {openrouter_api_key[:20]}...")

            self.deep_thinking_llm = ChatOpenAI(
                model=self.config["deep_think_llm"],
                base_url=self.config["backend_url"],
                api_key=openrouter_api_key
            )
            self.quick_thinking_llm = ChatOpenAI(
                model=self.config["quick_think_llm"],
                base_url=self.config["backend_url"],
                api_key=openrouter_api_key
            )
        elif self.config["llm_provider"] == "ollama":
            self.deep_thinking_llm = ChatOpenAI(model=self.config["deep_think_llm"], base_url=self.config["backend_url"])
            self.quick_thinking_llm = ChatOpenAI(model=self.config["quick_think_llm"], base_url=self.config["backend_url"])
        elif self.config["llm_provider"].lower() == "anthropic":
            self.deep_thinking_llm = ChatAnthropic(model=self.config["deep_think_llm"], base_url=self.config["backend_url"])
            self.quick_thinking_llm = ChatAnthropic(model=self.config["quick_think_llm"], base_url=self.config["backend_url"])
        elif self.config["llm_provider"].lower() == "google":
            from tradingagents.utils.api_key_utils import get_google_api_key, validate_api_key, mask_api_key
            google_api_key = validate_api_key(get_google_api_key(), "Google AI")
            logger.info(f"🔧 [Google AI] 使用API密钥: {mask_api_key(google_api_key)}")
            
            # Use enhanced configuration manager for optimal parameters with cost controls
            try:
                deep_think_params = enhanced_gemini_config.get_optimal_parameters(
                    self.config["deep_think_llm"],
                    task_type="stock_analysis",
                    complexity_level="high"
                )
                quick_think_params = enhanced_gemini_config.get_optimal_parameters(
                    self.config["quick_think_llm"],
                    task_type="stock_analysis", 
                    complexity_level="medium"
                )
                
                # Clean parameters for API call (remove monitoring metadata)
                deep_think_clean = {k: v for k, v in deep_think_params.items() if not k.startswith('_')}
                quick_think_clean = {k: v for k, v in quick_think_params.items() if not k.startswith('_')}
                
                logger.info(f"🔧 [Enhanced Google AI] 深度思考模型: {self.config['deep_think_llm']}")
                logger.info(f"   参数: {deep_think_clean}")
                if '_cost_monitoring' in deep_think_params:
                    cost_info = deep_think_params['_cost_monitoring']
                    logger.info(f"   估算成本: ${cost_info.get('estimated_cost_usd', 0):.4f}, 预算余量: {cost_info.get('remaining_budget_pct', 100):.1f}%")
                
                logger.info(f"🔧 [Enhanced Google AI] 快速思考模型: {self.config['quick_think_llm']}")
                logger.info(f"   参数: {quick_think_clean}")
                if '_cost_monitoring' in quick_think_params:
                    cost_info = quick_think_params['_cost_monitoring']
                    logger.info(f"   估算成本: ${cost_info.get('estimated_cost_usd', 0):.4f}, 预算余量: {cost_info.get('remaining_budget_pct', 100):.1f}%")
                
            except Exception as e:
                logger.warning(f"⚠️ Enhanced config failed, falling back to legacy parameters: {e}")
                # Fallback to legacy method
                deep_think_clean = self._get_gemini_model_params(self.config["deep_think_llm"], is_deep_thinking=True)
                quick_think_clean = self._get_gemini_model_params(self.config["quick_think_llm"], is_deep_thinking=False)
            
            self.deep_thinking_llm = ChatGoogleGenerativeAI(
                model=self.config["deep_think_llm"],
                google_api_key=google_api_key,
                **deep_think_clean
            )
            self.quick_thinking_llm = ChatGoogleGenerativeAI(
                model=self.config["quick_think_llm"],
                google_api_key=google_api_key,
                **quick_think_clean
            )
        # DashScope/阿里百炼 已废弃，不再支持
        elif self.config["llm_provider"].lower() == "siliconflow":
            # SiliconFlow 聚合平台（OpenAI 兼容）
            import os as _os
            siliconflow_api_key = _os.getenv('SILICONFLOW_API_KEY')
            if not siliconflow_api_key:
                raise ValueError("使用SiliconFlow需要设置SILICONFLOW_API_KEY环境变量")

            base_url = self.config.get("backend_url") or _os.getenv('SILICONFLOW_BASE_URL', 'https://api.siliconflow.cn/v1')

            # 直接使用OpenAI兼容的LangChain客户端
            self.deep_thinking_llm = ChatOpenAI(
                model=self.config["deep_think_llm"],
                base_url=base_url,
                api_key=siliconflow_api_key,
            )
            self.quick_thinking_llm = ChatOpenAI(
                model=self.config["quick_think_llm"],
                base_url=base_url,
                api_key=siliconflow_api_key,
            )
            logger.info("✅ [SiliconFlow] 已启用OpenAI兼容客户端")

        elif (self.config["llm_provider"].lower() == "deepseek" or
              "deepseek" in self.config["llm_provider"].lower()):
            # DeepSeek V3配置 - 使用支持token统计的适配器
            from tradingagents.llm_adapters.deepseek_adapter import ChatDeepSeek


            deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
            if not deepseek_api_key:
                raise ValueError("使用DeepSeek需要设置DEEPSEEK_API_KEY环境变量")

            deepseek_base_url = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')

            # 使用支持token统计的DeepSeek适配器
            self.deep_thinking_llm = ChatDeepSeek(
                model=self.config["deep_think_llm"],
                api_key=deepseek_api_key,
                base_url=deepseek_base_url,
                temperature=0.1,
                max_tokens=2000
            )
            self.quick_thinking_llm = ChatDeepSeek(
                model=self.config["quick_think_llm"],
                api_key=deepseek_api_key,
                base_url=deepseek_base_url,
                temperature=0.1,
                max_tokens=2000
                )

            logger.info(f"✅ [DeepSeek] 已启用token统计功能")
        else:
            raise ValueError(f"Unsupported LLM provider: {self.config['llm_provider']}")
        
        self.toolkit = Toolkit(config=self.config)

        # Initialize memories (如果启用)
        memory_enabled = self.config.get("memory_enabled", True)
        if memory_enabled:
            # 使用单例ChromaDB管理器，避免并发创建冲突
            self.bull_memory = FinancialSituationMemory("bull_memory", self.config)
            self.bear_memory = FinancialSituationMemory("bear_memory", self.config)
            self.trader_memory = FinancialSituationMemory("trader_memory", self.config)
            self.invest_judge_memory = FinancialSituationMemory("invest_judge_memory", self.config)
            self.risk_manager_memory = FinancialSituationMemory("risk_manager_memory", self.config)
        else:
            # 创建空的内存对象
            self.bull_memory = None
            self.bear_memory = None
            self.trader_memory = None
            self.invest_judge_memory = None
            self.risk_manager_memory = None

        # Create tool nodes
        self.tool_nodes = self._create_tool_nodes()

        # Initialize components
        self.conditional_logic = ConditionalLogic()
        self.graph_setup = GraphSetup(
            self.quick_thinking_llm,
            self.deep_thinking_llm,
            self.toolkit,
            self.tool_nodes,
            self.bull_memory,
            self.bear_memory,
            self.trader_memory,
            self.invest_judge_memory,
            self.risk_manager_memory,
            self.conditional_logic,
            self.config,
            getattr(self, 'react_llm', None),
        )

        self.propagator = Propagator()
        self.reflector = Reflector(self.quick_thinking_llm)
        self.signal_processor = SignalProcessor(self.quick_thinking_llm)

        # State tracking
        self.curr_state = None
        self.ticker = None
        self.log_states_dict = {}  # date to full state dict

        # Set up the graph
        self.graph = self.graph_setup.setup_graph(selected_analysts)

        # Initialize multi-model extension
        try:
            from .multi_model_extension import MultiModelExtension
            self.multi_model_extension = MultiModelExtension(self)
            logger.info("多模型协作扩展已启用")
        except Exception as e:
            logger.warning(f"多模型扩展初始化失败: {e}")
            self.multi_model_extension = None

    def _create_tool_nodes(self) -> Dict[str, ToolNode]:
        """Create tool nodes for different data sources."""
        return {
            "market": ToolNode(
                [
                    # 统一工具
                    self.toolkit.get_stock_market_data_unified,
                    # online tools
                    self.toolkit.get_YFin_data_online,
                    self.toolkit.get_stockstats_indicators_report_online,
                    # offline tools
                    self.toolkit.get_YFin_data,
                    self.toolkit.get_stockstats_indicators_report,
                ]
            ),
            "social": ToolNode(
                [
                    # online tools
                    self.toolkit.get_stock_news_openai,
                    # offline tools
                    self.toolkit.get_reddit_stock_info,
                ]
            ),
            "news": ToolNode(
                [
                    # online tools
                    self.toolkit.get_global_news_openai,
                    self.toolkit.get_google_news,
                    # offline tools
                    self.toolkit.get_finnhub_news,
                    self.toolkit.get_reddit_news,
                ]
            ),
            "fundamentals": ToolNode(
                [
                    # 统一工具
                    self.toolkit.get_stock_fundamentals_unified,
                    # offline tools
                    self.toolkit.get_finnhub_company_insider_sentiment,
                    self.toolkit.get_finnhub_company_insider_transactions,
                    self.toolkit.get_simfin_balance_sheet,
                    self.toolkit.get_simfin_cashflow,
                    self.toolkit.get_simfin_income_stmt,
                ]
            ),
        }

    def propagate(self, company_name, trade_date):
        """Run the trading agents graph for a company on a specific date."""

        # 添加详细的接收日志
        logger.debug(f"🔍 [GRAPH DEBUG] ===== TradingAgentsGraph.propagate 接收参数 =====")
        logger.debug(f"🔍 [GRAPH DEBUG] 接收到的company_name: '{company_name}' (类型: {type(company_name)})")
        logger.debug(f"🔍 [GRAPH DEBUG] 接收到的trade_date: '{trade_date}' (类型: {type(trade_date)})")

        self.ticker = company_name
        logger.debug(f"🔍 [GRAPH DEBUG] 设置self.ticker: '{self.ticker}'")

        # Initialize state
        logger.debug(f"🔍 [GRAPH DEBUG] 创建初始状态，传递参数: company_name='{company_name}', trade_date='{trade_date}'")
        init_agent_state = self.propagator.create_initial_state(
            company_name, trade_date
        )
        logger.debug(f"🔍 [GRAPH DEBUG] 初始状态中的company_of_interest: '{init_agent_state.get('company_of_interest', 'NOT_FOUND')}'")
        logger.debug(f"🔍 [GRAPH DEBUG] 初始状态中的trade_date: '{init_agent_state.get('trade_date', 'NOT_FOUND')}'")
        args = self.propagator.get_graph_args()

        if self.debug:
            # Debug mode with tracing
            trace = []
            for chunk in self.graph.stream(init_agent_state, **args):
                if len(chunk["messages"]) == 0:
                    pass
                else:
                    chunk["messages"][-1].pretty_print()
                    trace.append(chunk)

            final_state = trace[-1]
        else:
            # Standard mode without tracing
            final_state = self.graph.invoke(init_agent_state, **args)

        # Store current state for reflection
        self.curr_state = final_state

        # Log state
        self._log_state(trade_date, final_state)

        # Return decision and processed signal
        return final_state, self.process_signal(final_state["final_trade_decision"], company_name)

    def _log_state(self, trade_date, final_state):
        """Log the final state to a JSON file."""
        self.log_states_dict[str(trade_date)] = {
            "company_of_interest": final_state["company_of_interest"],
            "trade_date": final_state["trade_date"],
            "market_report": final_state["market_report"],
            "sentiment_report": final_state["sentiment_report"],
            "news_report": final_state["news_report"],
            "fundamentals_report": final_state["fundamentals_report"],
            "investment_debate_state": {
                "bull_history": final_state["investment_debate_state"]["bull_history"],
                "bear_history": final_state["investment_debate_state"]["bear_history"],
                "history": final_state["investment_debate_state"]["history"],
                "current_response": final_state["investment_debate_state"][
                    "current_response"
                ],
                "judge_decision": final_state["investment_debate_state"][
                    "judge_decision"
                ],
            },
            "trader_investment_decision": final_state["trader_investment_plan"],
            "risk_debate_state": {
                "risky_history": final_state["risk_debate_state"]["risky_history"],
                "safe_history": final_state["risk_debate_state"]["safe_history"],
                "neutral_history": final_state["risk_debate_state"]["neutral_history"],
                "history": final_state["risk_debate_state"]["history"],
                "judge_decision": final_state["risk_debate_state"]["judge_decision"],
            },
            "investment_plan": final_state["investment_plan"],
            "final_trade_decision": final_state["final_trade_decision"],
        }

        # Save to file
        directory = Path(f"eval_results/{self.ticker}/TradingAgentsStrategy_logs/")
        directory.mkdir(parents=True, exist_ok=True)

        with open(
            f"eval_results/{self.ticker}/TradingAgentsStrategy_logs/full_states_log.json",
            "w",
        ) as f:
            json.dump(self.log_states_dict, f, indent=4)

    def reflect_and_remember(self, returns_losses):
        """Reflect on decisions and update memory based on returns."""
        self.reflector.reflect_bull_researcher(
            self.curr_state, returns_losses, self.bull_memory
        )
        self.reflector.reflect_bear_researcher(
            self.curr_state, returns_losses, self.bear_memory
        )
        self.reflector.reflect_trader(
            self.curr_state, returns_losses, self.trader_memory
        )
        self.reflector.reflect_invest_judge(
            self.curr_state, returns_losses, self.invest_judge_memory
        )
        self.reflector.reflect_risk_manager(
            self.curr_state, returns_losses, self.risk_manager_memory
        )

    def process_signal(self, full_signal, stock_symbol=None):
        """Process a signal to extract the core decision."""
        return self.signal_processor.process_signal(full_signal, stock_symbol)

    # Multi-Model Collaboration Methods
    
    def analyze_with_collaboration(self, 
                                 company_name: str, 
                                 trade_date: str,
                                 collaboration_mode: str = "sequential",
                                 selected_agents: List[str] = None) -> Dict[str, Any]:
        """
        使用多模型协作进行分析
        
        Args:
            company_name: 公司名称
            trade_date: 交易日期
            collaboration_mode: 协作模式 (sequential/parallel/debate)
            selected_agents: 选择的智能体列表
            
        Returns:
            Dict[str, Any]: 协作分析结果
        """
        if not self.multi_model_extension:
            logger.warning("多模型扩展未启用，使用传统分析模式")
            return self._traditional_analysis_wrapper(company_name, trade_date)
        
        return self.multi_model_extension.execute_collaborative_analysis(
            company_name=company_name,
            trade_date=trade_date,
            collaboration_mode=collaboration_mode,
            selected_agents=selected_agents
        )
    
    def _traditional_analysis_wrapper(self, company_name: str, trade_date: str) -> Dict[str, Any]:
        """传统分析的包装器，统一返回格式"""
        try:
            traditional_result, signal = self.propagate(company_name, trade_date)
            return {
                'company_name': company_name,
                'trade_date': trade_date,
                'collaboration_mode': 'traditional',
                'final_decision': traditional_result.get('final_trade_decision', '无决策'),
                'confidence_score': 0.7,  # 默认置信度
                'traditional_result': traditional_result,
                'signal': signal,
                'multi_model_enabled': False
            }
        except Exception as e:
            logger.error(f"传统分析失败: {e}")
            return {
                'company_name': company_name,
                'trade_date': trade_date,
                'error': str(e),
                'multi_model_enabled': False
            }
    
    def get_available_collaboration_modes(self) -> List[str]:
        """获取可用的协作模式"""
        if self.multi_model_extension:
            return list(self.multi_model_extension.collaboration_modes.keys())
        return ['traditional']
    
    def get_available_agents(self) -> List[str]:
        """获取可用的专业智能体"""
        if self.multi_model_extension:
            return list(self.multi_model_extension.specialized_agents.keys())
        return []
    
    def get_multi_model_status(self) -> Dict[str, Any]:
        """获取多模型系统状态"""
        if self.multi_model_extension:
            return self.multi_model_extension.get_multi_model_status()
        return {
            'multi_model_enabled': False,
            'available_agents': [],
            'collaboration_modes': ['traditional'],
            'reason': '多模型扩展未启用'
        }
    
    def enable_smart_analysis(self) -> bool:
        """
        启用智能分析模式（自动选择最佳协作模式）
        
        Returns:
            bool: 是否成功启用
        """
        if self.multi_model_extension:
            self.config['smart_analysis_enabled'] = True
            logger.info("智能分析模式已启用")
            return True
        else:
            logger.warning("多模型扩展不可用，无法启用智能分析模式")
            return False
    
    def smart_analyze(self, company_name: str, trade_date: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        智能分析 - 自动选择最佳的协作模式和智能体组合
        
        Args:
            company_name: 公司名称
            trade_date: 交易日期
            context: 额外上下文信息
            
        Returns:
            Dict[str, Any]: 分析结果
        """
        if not self.multi_model_extension:
            return self._traditional_analysis_wrapper(company_name, trade_date)
        
        context = context or {}
        
        # 智能选择协作模式和智能体
        if context.get('urgency') == 'high':
            # 紧急情况使用并行模式，选择关键智能体
            collaboration_mode = 'parallel'
            selected_agents = ['news_hunter', 'risk_manager', 'chief_decision_officer']
        elif context.get('complexity') == 'high':
            # 复杂分析使用辩论模式，包含多个专家
            collaboration_mode = 'debate'
            selected_agents = ['fundamental_expert', 'technical_analyst', 'risk_manager', 'chief_decision_officer']
        else:
            # 默认使用序列模式，全面分析
            collaboration_mode = 'sequential'
            selected_agents = ['news_hunter', 'fundamental_expert', 'technical_analyst', 'sentiment_analyst', 'risk_manager']
        
        logger.info(f"智能分析选择: 模式={collaboration_mode}, 智能体={selected_agents}")
        
        return self.analyze_with_collaboration(
            company_name=company_name,
            trade_date=trade_date,
            collaboration_mode=collaboration_mode,
            selected_agents=selected_agents
        )
