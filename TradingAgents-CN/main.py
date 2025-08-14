from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

# 导入统一日志系统
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('main')


# Create a custom config
config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "google"  # Use Google AI
config["backend_url"] = "https://generativelanguage.googleapis.com/v1"  # Google AI API endpoint
config["deep_think_llm"] = "gemini-2.5-pro"  # Use Gemini 2.5 Pro for deep analysis
config["quick_think_llm"] = "gemini-2.5-pro"  # Use Gemini 2.5 Pro for all tasks
config["max_debate_rounds"] = 1  # Increase debate rounds
config["online_tools"] = True  # Enable online tools

# Initialize with custom config
ta = TradingAgentsGraph(debug=True, config=config)

# forward propagate
_, decision = ta.propagate("NVDA", "2024-05-10")
print(decision)

# Memorize mistakes and reflect
# ta.reflect_and_remember(1000) # parameter is the position returns
