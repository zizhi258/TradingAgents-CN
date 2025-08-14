import os

DEFAULT_CONFIG = {
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", "./results"),
    "data_dir": os.path.join(os.path.expanduser("~"), "Documents", "TradingAgents", "data"),
    "data_cache_dir": os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
        "dataflows/data_cache",
    ),
    
    # ========================================
    # 方法层配置 (Method Level)
    # ========================================
    
    # 分析模式
    "analysis_mode": "single",  # single | multi
    "collaboration_mode": "sequential",  # sequential | parallel | debate
    "routing_strategy": "balanced",  # quality_first | cost_first | latency_first | balanced
    
    # LLM设置（单模型默认配置）
    "llm_provider": "openai",
    "deep_think_llm": "o4-mini",
    "quick_think_llm": "gpt-4o-mini",
    "backend_url": "https://api.openai.com/v1",
    
    # 多模型配置（当analysis_mode为multi时生效）
    "role_model_policies": {},  # 角色-模型策略，由前端或配置文件提供
    "fallback_models": [],  # 回退模型列表
    
    # 辩论和讨论设置
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "max_recur_limit": 100,
    
    # 工具设置
    "online_tools": True,
    
    # 性能和成本限制
    "max_budget": 2.0,
    "max_concurrent_tasks": 5,
    "enable_caching": True,
    
    # ========================================
    # 业务层配置 (Business Level)
    # ========================================
    
    # 市场和目标（由前端提供）
    "market_type": None,  # A股 | 美股 | 港股 | 全球
    "targets": [],  # 股票代码列表
    "analysis_date": None,
    "research_depth": 3,  # 1-5级深度

    # Note: Database and cache configuration is now managed by .env file and config.database_manager
    # No database/cache settings in default config to avoid configuration conflicts
}
