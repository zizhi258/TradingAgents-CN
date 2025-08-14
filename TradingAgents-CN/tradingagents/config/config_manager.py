#!/usr/bin/env python3
"""
配置管理器
管理API密钥、模型配置、费率设置等
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from dotenv import load_dotenv

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('agents')

try:
    from .mongodb_storage import MongoDBStorage
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    MongoDBStorage = None


@dataclass
class ModelConfig:
    """模型配置"""
    provider: str  # 供应商：deepseek, google, siliconflow, etc.
    model_name: str  # 模型名称
    api_key: str  # API密钥
    base_url: Optional[str] = None  # 自定义API地址
    max_tokens: int = 32000  # 最大token数
    temperature: float = 0.7  # 温度参数
    enabled: bool = True  # 是否启用


@dataclass
class PricingConfig:
    """定价配置"""
    provider: str  # 供应商
    model_name: str  # 模型名称
    input_price_per_1k: float  # 输入token价格（每1000个token）
    output_price_per_1k: float  # 输出token价格（每1000个token）
    currency: str = "CNY"  # 货币单位


@dataclass
class UsageRecord:
    """使用记录"""
    timestamp: str  # 时间戳
    provider: str  # 供应商
    model_name: str  # 模型名称
    input_tokens: int  # 输入token数
    output_tokens: int  # 输出token数
    cost: float  # 成本
    session_id: str  # 会话ID
    analysis_type: str  # 分析类型


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)

        self.models_file = self.config_dir / "models.json"
        self.pricing_file = self.config_dir / "pricing.json"
        self.usage_file = self.config_dir / "usage.json"
        self.settings_file = self.config_dir / "settings.json"

        # 加载.env文件（保持向后兼容）
        self._load_env_file()

        # 初始化MongoDB存储（如果可用）
        self.mongodb_storage = None
        self._init_mongodb_storage()

        self._init_default_configs()

    def _load_env_file(self):
        """加载.env文件（保持向后兼容）"""
        # 尝试从项目根目录加载.env文件
        project_root = Path(__file__).parent.parent.parent
        env_file = project_root / ".env"

        if env_file.exists():
            load_dotenv(env_file, override=True)

    def _get_env_api_key(self, provider: str) -> str:
        """从环境变量获取API密钥"""
        env_key_map = {
            "deepseek": "DEEPSEEK_API_KEY",
            "google": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],  # 支持多个环境变量名
            "siliconflow": "SILICONFLOW_API_KEY"
        }

        env_key = env_key_map.get(provider.lower())
        if env_key:
            # 处理多个环境变量名的情况（如Google）
            if isinstance(env_key, list):
                for key in env_key:
                    value = os.getenv(key)
                    if value:
                        return value
                return ""
            else:
                return os.getenv(env_key, "")
        return ""
    
    def _init_mongodb_storage(self):
        """初始化MongoDB存储"""
        if not MONGODB_AVAILABLE:
            return
        
        # 检查是否启用MongoDB存储
        use_mongodb = os.getenv("USE_MONGODB_STORAGE", "false").lower() == "true"
        if not use_mongodb:
            return
        
        try:
            connection_string = os.getenv("MONGODB_CONNECTION_STRING")
            database_name = os.getenv("MONGODB_DATABASE_NAME", "tradingagents")
            
            self.mongodb_storage = MongoDBStorage(
                connection_string=connection_string,
                database_name=database_name
            )
            
            if self.mongodb_storage.is_connected():
                logger.info("✅ MongoDB存储已启用")
            else:
                self.mongodb_storage = None
                logger.warning("⚠️ MongoDB连接失败，将使用JSON文件存储")

        except Exception as e:
            logger.error(f"❌ MongoDB初始化失败: {e}", exc_info=True)
            self.mongodb_storage = None

    def _init_default_configs(self):
        """初始化默认配置"""
        # 默认模型配置
        if not self.models_file.exists():
            default_models = [
                ModelConfig(
                    provider="deepseek",
                    model_name="deepseek-chat",
                    api_key="",
                    max_tokens=32000,  # DeepSeek V3: 64K上下文，32K默认输出
                    temperature=0.7,
                    enabled=True  # 默认启用
                ),
                ModelConfig(
                    provider="deepseek",
                    model_name="deepseek-reasoner",
                    api_key="",
                    max_tokens=32000,  # R1推理模型，包含思维链输出
                    temperature=0.3,  # 推理模型使用低温度
                    enabled=True  # 默认启用
                ),
                ModelConfig(
                    provider="google",
                    model_name="gemini-2.5-flash",
                    api_key="",
                    max_tokens=65536,  # Gemini 2.5 Flash 最大输出
                    temperature=0.7,
                    enabled=True  # 默认启用
                ),
                ModelConfig(
                    provider="google",
                    model_name="gemini-2.5-pro",
                    api_key="",
                    max_tokens=65536,  # Gemini 2.5 Pro 最大输出
                    temperature=0.3,
                    enabled=True  # 默认启用
                ),
                # SiliconFlow Models
                ModelConfig(
                    provider="siliconflow",
                    model_name="deepseek-ai/DeepSeek-R1",
                    api_key="",
                    base_url="https://api.siliconflow.cn/v1",
                    max_tokens=16384,  # DeepSeek R1 推理模型最大输出
                    temperature=0.6,
                    enabled=True  # 默认启用
                ),
                ModelConfig(
                    provider="siliconflow",
                    model_name="deepseek-ai/DeepSeek-V3",
                    api_key="",
                    base_url="https://api.siliconflow.cn/v1",
                    max_tokens=8192,  # DeepSeek V3 通用模型
                    temperature=0.7,
                    enabled=True  # 默认启用
                ),
                ModelConfig(
                    provider="siliconflow",
                    model_name="zai-org/GLM-4.5",
                    api_key="",
                    base_url="https://api.siliconflow.cn/v1",
                    max_tokens=8192,  # GLM-4.5 最大输出
                    temperature=0.7,
                    enabled=True  # 默认启用
                ),
                ModelConfig(
                    provider="siliconflow",
                    model_name="Qwen/Qwen3-Coder-480B-A35B-Instruct",
                    api_key="",
                    base_url="https://api.siliconflow.cn/v1",
                    max_tokens=8192,  # Qwen3 Coder超大规模模型
                    temperature=0.3,  # 代码生成使用低温度
                    enabled=True  # 默认启用
                ),
                ModelConfig(
                    provider="siliconflow",
                    model_name="moonshotai/Kimi-K2-Instruct",
                    api_key="",
                    base_url="https://api.siliconflow.cn/v1",
                    max_tokens=8192,  # Kimi K2 最大输出
                    temperature=0.7,
                    enabled=True  # 默认启用
                ),
                ModelConfig(
                    provider="siliconflow",
                    model_name="Qwen/Qwen3-235B-A22B-Thinking-2507",
                    api_key="",
                    base_url="https://api.siliconflow.cn/v1",
                    max_tokens=8192,  # Qwen3 推理增强模型
                    temperature=0.5,  # 推理模型使用中等温度
                    enabled=True  # 默认启用
                ),
                ModelConfig(
                    provider="siliconflow",
                    model_name="Qwen/Qwen3-235B-A22B-Instruct-2507",
                    api_key="",
                    base_url="https://api.siliconflow.cn/v1",
                    max_tokens=8192,  # Qwen3 超大指令模型
                    temperature=0.7,
                    enabled=True  # 默认启用
                ),
                # SiliconFlow Embedding and Rerank Models
                ModelConfig(
                    provider="siliconflow",
                    model_name="Qwen/Qwen3-Embedding-8B",
                    api_key="",
                    base_url="https://api.siliconflow.cn/v1",
                    max_tokens=512,  # Embedding模型通常输出较短
                    temperature=0.0,  # Embedding不需要随机性
                    enabled=True  # 默认启用
                ),
                ModelConfig(
                    provider="siliconflow",
                    model_name="Qwen/Qwen3-Reranker-8B",
                    api_key="",
                    base_url="https://api.siliconflow.cn/v1",
                    max_tokens=512,  # Reranker模型输出较短
                    temperature=0.0,  # Reranker不需要随机性
                    enabled=True  # 默认启用
                ),
            ]
            self.save_models(default_models)
        
        # 默认定价配置
        if not self.pricing_file.exists():
            default_pricing = [
                # DeepSeek官方定价 (人民币) - 2025年最新价格
                PricingConfig("deepseek", "deepseek-chat", 0.0014, 0.0028, "CNY"),      # V3通用对话模型
                PricingConfig("deepseek", "deepseek-reasoner", 0.0055, 0.0195, "CNY"),  # R1推理模型

                # Google Gemini 2.5 定价 (美元) - 2025年最新官方定价
                PricingConfig("google", "gemini-2.5-flash", 0.000125, 0.0005, "USD"),  # Flash: $0.125/$0.50 per 1M tokens
                PricingConfig("google", "gemini-2.5-pro", 0.0125, 0.05, "USD"),  # Pro: $12.5/$50 per 1M tokens
                
                # SiliconFlow Models Pricing (人民币) - 2025年官方定价
                PricingConfig("siliconflow", "deepseek-ai/DeepSeek-R1", 0.004, 0.016, "CNY"),  # ¥4/¥16 per 1M tokens
                PricingConfig("siliconflow", "deepseek-ai/DeepSeek-V3", 0.002, 0.008, "CNY"),  # ¥2/¥8 per 1M tokens
                PricingConfig("siliconflow", "zai-org/GLM-4.5", 0.002, 0.008, "CNY"),  # GLM-4.5预估定价
                PricingConfig("siliconflow", "Qwen/Qwen3-Coder-480B-A35B-Instruct", 0.006, 0.024, "CNY"),  # 超大模型预估
                PricingConfig("siliconflow", "moonshotai/Kimi-K2-Instruct", 0.003, 0.012, "CNY"),  # Kimi预估定价
                PricingConfig("siliconflow", "Qwen/Qwen3-235B-A22B-Thinking-2507", 0.005, 0.020, "CNY"),  # 推理模型
                PricingConfig("siliconflow", "Qwen/Qwen3-235B-A22B-Instruct-2507", 0.005, 0.020, "CNY"),  # 超大指令模型
                PricingConfig("siliconflow", "Qwen/Qwen3-Embedding-8B", 0.0005, 0.0005, "CNY"),  # Embedding固定价格
                PricingConfig("siliconflow", "Qwen/Qwen3-Reranker-8B", 0.0008, 0.0008, "CNY"),  # Reranker固定价格
            ]
            self.save_pricing(default_pricing)
        
        # 默认设置
        if not self.settings_file.exists():
            # 导入默认数据目录配置
            import os
            default_data_dir = os.path.join(os.path.expanduser("~"), "Documents", "TradingAgents", "data")
            
            default_settings = {
                "default_provider": "deepseek",
                "default_model": "deepseek-chat",
                "enable_cost_tracking": True,
                "cost_alert_threshold": 100.0,  # 成本警告阈值
                "currency_preference": "CNY",
                "auto_save_usage": True,
                "max_usage_records": 10000,
                "data_dir": default_data_dir,  # 数据目录配置
                "cache_dir": os.path.join(default_data_dir, "cache"),  # 缓存目录
                "results_dir": os.path.join(os.path.expanduser("~"), "Documents", "TradingAgents", "results"),  # 结果目录
                "auto_create_dirs": True,  # 自动创建目录
                "email_schedules": {  # 邮件调度配置
                    "daily": {
                        "enabled": False,
                        "hour": 18,
                        "minute": 0
                    },
                    "weekly": {
                        "enabled": False,
                        "weekday": [1],  # 周一(0=Monday, 6=Sunday)
                        "hour": 9,
                        "minute": 0
                    }
                }
            }
            self.save_settings(default_settings)
    
    def load_models(self) -> List[ModelConfig]:
        """加载模型配置，优先使用.env中的API密钥"""
        try:
            with open(self.models_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                models = [ModelConfig(**item) for item in data]

                # 合并.env中的API密钥（优先级更高）
                for model in models:
                    env_api_key = self._get_env_api_key(model.provider)
                    if env_api_key:
                        model.api_key = env_api_key
                        # 如果.env中有API密钥，自动启用该模型
                        if not model.enabled:
                            model.enabled = True

                return models
        except Exception as e:
            logger.error(f"加载模型配置失败: {e}")
            return []
    
    def save_models(self, models: List[ModelConfig]):
        """保存模型配置"""
        try:
            data = [asdict(model) for model in models]
            with open(self.models_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存模型配置失败: {e}")
    
    def load_pricing(self) -> List[PricingConfig]:
        """加载定价配置"""
        try:
            with open(self.pricing_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return [PricingConfig(**item) for item in data]
        except Exception as e:
            logger.error(f"加载定价配置失败: {e}")
            return []
    
    def save_pricing(self, pricing: List[PricingConfig]):
        """保存定价配置"""
        try:
            data = [asdict(price) for price in pricing]
            with open(self.pricing_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存定价配置失败: {e}")
    
    def load_usage_records(self) -> List[UsageRecord]:
        """加载使用记录"""
        try:
            if not self.usage_file.exists():
                return []
            with open(self.usage_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [UsageRecord(**item) for item in data]
        except Exception as e:
            logger.error(f"加载使用记录失败: {e}")
            return []
    
    def save_usage_records(self, records: List[UsageRecord]):
        """保存使用记录"""
        try:
            data = [asdict(record) for record in records]
            with open(self.usage_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存使用记录失败: {e}")
    
    def add_usage_record(self, provider: str, model_name: str, input_tokens: int,
                        output_tokens: int, session_id: str, analysis_type: str = "stock_analysis"):
        """添加使用记录"""
        # 计算成本
        cost = self.calculate_cost(provider, model_name, input_tokens, output_tokens)
        
        record = UsageRecord(
            timestamp=datetime.now().isoformat(),
            provider=provider,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            session_id=session_id,
            analysis_type=analysis_type
        )
        
        # 优先使用MongoDB存储
        if self.mongodb_storage and self.mongodb_storage.is_connected():
            success = self.mongodb_storage.save_usage_record(record)
            if success:
                return record
            else:
                logger.error(f"⚠️ MongoDB保存失败，回退到JSON文件存储")
        
        # 回退到JSON文件存储
        records = self.load_usage_records()
        records.append(record)
        
        # 限制记录数量
        settings = self.load_settings()
        max_records = settings.get("max_usage_records", 10000)
        if len(records) > max_records:
            records = records[-max_records:]
        
        self.save_usage_records(records)
        return record
    
    def calculate_cost(self, provider: str, model_name: str, input_tokens: int, output_tokens: int) -> float:
        """计算使用成本"""
        pricing_configs = self.load_pricing()

        for pricing in pricing_configs:
            if pricing.provider == provider and pricing.model_name == model_name:
                input_cost = (input_tokens / 1000) * pricing.input_price_per_1k
                output_cost = (output_tokens / 1000) * pricing.output_price_per_1k
                total_cost = input_cost + output_cost
                return round(total_cost, 6)

        # 只在找不到配置时输出调试信息
        logger.warning(f"⚠️ [calculate_cost] 未找到匹配的定价配置: {provider}/{model_name}")
        logger.debug(f"⚠️ [calculate_cost] 可用的配置:")
        for pricing in pricing_configs:
            logger.debug(f"⚠️ [calculate_cost]   - {pricing.provider}/{pricing.model_name}")

        return 0.0
    
    def load_settings(self) -> Dict[str, Any]:
        """加载设置，合并.env中的配置"""
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
        except Exception as e:
            logger.error(f"加载设置失败: {e}")
            settings = {}

        # 合并.env中的其他配置
        env_settings = {
            "finnhub_api_key": os.getenv("FINNHUB_API_KEY", ""),
            "reddit_client_id": os.getenv("REDDIT_CLIENT_ID", ""),
            "reddit_client_secret": os.getenv("REDDIT_CLIENT_SECRET", ""),
            "reddit_user_agent": os.getenv("REDDIT_USER_AGENT", ""),
            "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", ""),
            "log_level": os.getenv("TRADINGAGENTS_LOG_LEVEL", "INFO"),
            "data_dir": os.getenv("TRADINGAGENTS_DATA_DIR", ""),  # 数据目录环境变量
            "cache_dir": os.getenv("TRADINGAGENTS_CACHE_DIR", ""),  # 缓存目录环境变量
        }

        # 只有当环境变量存在且不为空时才覆盖
        for key, value in env_settings.items():
            if value:
                settings[key] = value

        return settings

    def get_env_config_status(self) -> Dict[str, Any]:
        """获取.env配置状态"""
        return {
            "env_file_exists": (Path(__file__).parent.parent.parent / ".env").exists(),
            "api_keys": {
                "deepseek": bool(os.getenv("DEEPSEEK_API_KEY")),
                "google": bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")),
                "siliconflow": bool(os.getenv("SILICONFLOW_API_KEY")),
                "finnhub": bool(os.getenv("FINNHUB_API_KEY")),
            },
            "other_configs": {
                "reddit_configured": bool(os.getenv("REDDIT_CLIENT_ID") and os.getenv("REDDIT_CLIENT_SECRET")),
                "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", "./results"),
                "log_level": os.getenv("TRADINGAGENTS_LOG_LEVEL", "INFO"),
            }
        }

    def save_settings(self, settings: Dict[str, Any]):
        """保存设置"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存设置失败: {e}")
    
    def get_enabled_models(self) -> List[ModelConfig]:
        """获取启用的模型"""
        models = self.load_models()
        return [model for model in models if model.enabled and model.api_key]
    
    def get_model_by_name(self, provider: str, model_name: str) -> Optional[ModelConfig]:
        """根据名称获取模型配置"""
        models = self.load_models()
        for model in models:
            if model.provider == provider and model.model_name == model_name:
                return model
        return None
    
    def get_usage_statistics(self, days: int = 30) -> Dict[str, Any]:
        """获取使用统计"""
        # 优先使用MongoDB获取统计
        if self.mongodb_storage and self.mongodb_storage.is_connected():
            try:
                # 从MongoDB获取基础统计
                stats = self.mongodb_storage.get_usage_statistics(days)
                # 获取供应商统计
                provider_stats = self.mongodb_storage.get_provider_statistics(days)
                
                if stats:
                    stats["provider_stats"] = provider_stats
                    stats["records_count"] = stats.get("total_requests", 0)
                    return stats
            except Exception as e:
                logger.error(f"⚠️ MongoDB统计获取失败，回退到JSON文件: {e}")
        
        # 回退到JSON文件统计
        records = self.load_usage_records()
        
        # 过滤最近N天的记录
        from datetime import datetime, timedelta

        cutoff_date = datetime.now() - timedelta(days=days)
        
        recent_records = []
        for record in records:
            try:
                record_date = datetime.fromisoformat(record.timestamp)
                if record_date >= cutoff_date:
                    recent_records.append(record)
            except:
                continue
        
        # 统计数据
        total_cost = sum(record.cost for record in recent_records)
        total_input_tokens = sum(record.input_tokens for record in recent_records)
        total_output_tokens = sum(record.output_tokens for record in recent_records)
        
        # 按供应商统计
        provider_stats = {}
        for record in recent_records:
            if record.provider not in provider_stats:
                provider_stats[record.provider] = {
                    "cost": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "requests": 0
                }
            provider_stats[record.provider]["cost"] += record.cost
            provider_stats[record.provider]["input_tokens"] += record.input_tokens
            provider_stats[record.provider]["output_tokens"] += record.output_tokens
            provider_stats[record.provider]["requests"] += 1
        
        return {
            "period_days": days,
            "total_cost": round(total_cost, 4),
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_requests": len(recent_records),
            "provider_stats": provider_stats,
            "records_count": len(recent_records)
        }
    
    def get_data_dir(self) -> str:
        """获取数据目录路径"""
        settings = self.load_settings()
        data_dir = settings.get("data_dir")
        if not data_dir:
            # 如果没有配置，使用默认路径
            data_dir = os.path.join(os.path.expanduser("~"), "Documents", "TradingAgents", "data")
        return data_dir

    def set_data_dir(self, data_dir: str):
        """设置数据目录路径"""
        settings = self.load_settings()
        settings["data_dir"] = data_dir
        # 同时更新缓存目录
        settings["cache_dir"] = os.path.join(data_dir, "cache")
        self.save_settings(settings)
        
        # 如果启用自动创建目录，则创建目录
        if settings.get("auto_create_dirs", True):
            self.ensure_directories_exist()

    def ensure_directories_exist(self):
        """确保必要的目录存在"""
        settings = self.load_settings()
        
        directories = [
            settings.get("data_dir"),
            settings.get("cache_dir"),
            settings.get("results_dir"),
            os.path.join(settings.get("data_dir", ""), "finnhub_data"),
            os.path.join(settings.get("data_dir", ""), "finnhub_data", "news_data"),
            os.path.join(settings.get("data_dir", ""), "finnhub_data", "insider_sentiment"),
            os.path.join(settings.get("data_dir", ""), "finnhub_data", "insider_transactions")
        ]
        
        for directory in directories:
            if directory and not os.path.exists(directory):
                try:
                    os.makedirs(directory, exist_ok=True)
                    logger.info(f"✅ 创建目录: {directory}")
                except Exception as e:
                    logger.error(f"❌ 创建目录失败 {directory}: {e}")


class TokenTracker:
    """Token使用跟踪器"""

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager

    def track_usage(self, provider: str, model_name: str, input_tokens: int,
                   output_tokens: int, session_id: str = None, analysis_type: str = "stock_analysis"):
        """跟踪Token使用"""
        if session_id is None:
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 检查是否启用成本跟踪
        settings = self.config_manager.load_settings()
        cost_tracking_enabled = settings.get("enable_cost_tracking", True)

        if not cost_tracking_enabled:
            return None

        # 添加使用记录
        record = self.config_manager.add_usage_record(
            provider=provider,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            session_id=session_id,
            analysis_type=analysis_type
        )

        # 检查成本警告
        if record:
            self._check_cost_alert(record.cost)

        return record

    def _check_cost_alert(self, current_cost: float):
        """检查成本警告"""
        settings = self.config_manager.load_settings()
        threshold = settings.get("cost_alert_threshold", 100.0)

        # 获取今日总成本
        today_stats = self.config_manager.get_usage_statistics(1)
        total_today = today_stats["total_cost"]

        if total_today >= threshold:
            logger.warning(f"⚠️ 成本警告: 今日成本已达到 ¥{total_today:.4f}，超过阈值 ¥{threshold}",
                          extra={'cost': total_today, 'threshold': threshold, 'event_type': 'cost_alert'})

    def get_session_cost(self, session_id: str) -> float:
        """获取会话成本"""
        records = self.config_manager.load_usage_records()
        session_cost = sum(record.cost for record in records if record.session_id == session_id)
        return session_cost

    def estimate_cost(self, provider: str, model_name: str, estimated_input_tokens: int,
                     estimated_output_tokens: int) -> float:
        """估算成本"""
        return self.config_manager.calculate_cost(
            provider, model_name, estimated_input_tokens, estimated_output_tokens
        )




# 全局配置管理器实例 - 使用项目根目录的配置
def _get_project_config_dir():
    """获取项目根目录的配置目录"""
    # 从当前文件位置推断项目根目录
    current_file = Path(__file__)  # tradingagents/config/config_manager.py
    project_root = current_file.parent.parent.parent  # 向上三级到项目根目录
    return str(project_root / "config")

config_manager = ConfigManager(_get_project_config_dir())
token_tracker = TokenTracker(config_manager)
