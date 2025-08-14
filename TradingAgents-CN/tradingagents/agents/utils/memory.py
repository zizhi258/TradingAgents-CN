import chromadb
from chromadb.config import Settings
from openai import OpenAI
import os
import threading
from typing import Dict, Optional

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger
logger = get_logger("agents.utils.memory")


class ChromaDBManager:
    """单例ChromaDB管理器，避免并发创建集合的冲突"""

    _instance = None
    _lock = threading.Lock()
    _collections: Dict[str, any] = {}
    _client = None

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ChromaDBManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            try:
                # 自动检测操作系统版本并使用最优配置
                import platform
                system = platform.system()
                
                if system == "Windows":
                    # 使用改进的Windows 11检测
                    from .chromadb_win11_config import is_windows_11
                    if is_windows_11():
                        # Windows 11 或更新版本，使用优化配置
                        from .chromadb_win11_config import get_win11_chromadb_client
                        self._client = get_win11_chromadb_client()
                        logger.info(f"📚 [ChromaDB] Windows 11优化配置初始化完成 (构建号: {platform.version()})")
                    else:
                        # Windows 10 或更老版本，使用兼容配置
                        from .chromadb_win10_config import get_win10_chromadb_client
                        self._client = get_win10_chromadb_client()
                        logger.info(f"📚 [ChromaDB] Windows 10兼容配置初始化完成")
                else:
                    # 非Windows系统，使用标准配置
                    settings = Settings(
                        allow_reset=True,
                        anonymized_telemetry=False,
                        is_persistent=False
                    )
                    self._client = chromadb.Client(settings)
                    logger.info(f"📚 [ChromaDB] {system}标准配置初始化完成")
                
                self._initialized = True
            except Exception as e:
                logger.error(f"❌ [ChromaDB] 初始化失败: {e}")
                # 使用最简单的配置作为备用
                try:
                    settings = Settings(
                        allow_reset=True,
                        anonymized_telemetry=False,  # 关键：禁用遥测
                        is_persistent=False
                    )
                    self._client = chromadb.Client(settings)
                    logger.info(f"📚 [ChromaDB] 使用备用配置初始化完成")
                except Exception as backup_error:
                    # 最后的备用方案
                    self._client = chromadb.Client()
                    logger.warning(f"⚠️ [ChromaDB] 使用最简配置初始化: {backup_error}")
                self._initialized = True

    def get_or_create_collection(self, name: str):
        """线程安全地获取或创建集合"""
        with self._lock:
            if name in self._collections:
                logger.info(f"📚 [ChromaDB] 使用缓存集合: {name}")
                return self._collections[name]

            try:
                # 尝试获取现有集合
                collection = self._client.get_collection(name=name)
                logger.info(f"📚 [ChromaDB] 获取现有集合: {name}")
            except Exception:
                try:
                    # 创建新集合
                    collection = self._client.create_collection(name=name)
                    logger.info(f"📚 [ChromaDB] 创建新集合: {name}")
                except Exception as e:
                    # 可能是并发创建，再次尝试获取
                    try:
                        collection = self._client.get_collection(name=name)
                        logger.info(f"📚 [ChromaDB] 并发创建后获取集合: {name}")
                    except Exception as final_error:
                        logger.error(f"❌ [ChromaDB] 集合操作失败: {name}, 错误: {final_error}")
                        raise final_error

            # 缓存集合
            self._collections[name] = collection
            return collection


class FinancialSituationMemory:
    def __init__(self, name, config):
        self.config = config
        self.llm_provider = config.get("llm_provider", "openai").lower()
        
        # ========================================
        # 统一嵌入策略：优先使用SiliconFlow的Qwen3-Embedding
        # 与现有openai_compatible_base.py架构兼容
        # ========================================
        
        # 第一优先级：SiliconFlow Qwen3-Embedding（推荐）
        siliconflow_key = os.getenv('SILICONFLOW_API_KEY')
        if siliconflow_key:
            try:
                base_url = os.getenv('SILICONFLOW_BASE_URL', 'https://api.siliconflow.cn/v1')
                self.embedding = "Qwen/Qwen3-Embedding-8B"
                self.client = OpenAI(
                    api_key=siliconflow_key,
                    base_url=base_url
                )
                self.embedding_provider = "siliconflow"
                logger.info("✅ [嵌入模型] 使用SiliconFlow Qwen/Qwen3-Embedding-8B (推荐)")
                logger.debug(f"   API地址: {base_url}")
            except Exception as e:
                logger.error(f"❌ SiliconFlow嵌入初始化失败: {e}")
                self.client = None
                self.embedding = None
                self.embedding_provider = None
        else:
            self.client = None
            self.embedding = None
            self.embedding_provider = None
        
        # 第二优先级：OpenAI text-embedding-3-small（备选）
        if self.client is None:
            openai_key = os.getenv('OPENAI_API_KEY')
            if openai_key:
                try:
                    self.embedding = "text-embedding-3-small"
                    self.client = OpenAI(
                        api_key=openai_key,
                        base_url="https://api.openai.com/v1"
                    )
                    self.embedding_provider = "openai"
                    logger.info("⚠️ [嵌入模型] 回退到OpenAI text-embedding-3-small")
                except Exception as e:
                    logger.error(f"❌ OpenAI嵌入初始化失败: {e}")
                    self.client = None
                    self.embedding = None
                    self.embedding_provider = None
        
        # 第三选项：本地Ollama（如果配置了本地服务）
        if self.client is None and config.get("backend_url") == "http://localhost:11434/v1":
            try:
                self.embedding = "nomic-embed-text"
                self.client = OpenAI(base_url=config["backend_url"])
                self.embedding_provider = "ollama"
                logger.info("💡 [嵌入模型] 使用本地Ollama nomic-embed-text")
            except Exception as e:
                logger.error(f"❌ Ollama嵌入初始化失败: {e}")
                self.client = None
                self.embedding = None
                self.embedding_provider = None
        
        # 最终降级：禁用记忆功能
        if self.client is None:
            self.client = "DISABLED"
            self.embedding_provider = "disabled"
            logger.warning("🚨 [嵌入模型] 无可用嵌入服务，记忆功能已禁用")
            logger.info("💡 提示：设置SILICONFLOW_API_KEY或OPENAI_API_KEY以启用记忆功能")

        # 使用单例ChromaDB管理器
        self.chroma_manager = ChromaDBManager()
        self.situation_collection = self.chroma_manager.get_or_create_collection(name)

    def get_embedding(self, text):
        """Get embedding for a text using the configured provider"""
        
        # 检查记忆功能是否被禁用
        if self.client == "DISABLED":
            # 内存功能已禁用，返回空向量
            logger.debug(f"⚠️ 记忆功能已禁用，返回空向量")
            return [0.0] * 1024  # 返回1024维的零向量
        
        # 使用统一的OpenAI兼容接口（SiliconFlow/OpenAI/Ollama）
        try:
            response = self.client.embeddings.create(
                model=self.embedding,
                input=text
            )
            embedding = response.data[0].embedding
            logger.debug(f"✅ [{self.embedding_provider}] 嵌入成功，维度: {len(embedding)}")
            return embedding
        
        except Exception as e:
            # 通用错误处理
            logger.error(f"❌ [{self.embedding_provider}] 嵌入失败: {str(e)}")
            logger.warning(f"⚠️ 记忆功能降级，返回空向量")
            return [0.0] * 1024  # 返回空向量而不是抛出异常

    def add_situations(self, situations_and_advice):
        """Add financial situations and their corresponding advice. Parameter is a list of tuples (situation, rec)"""

        situations = []
        advice = []
        ids = []
        embeddings = []

        offset = self.situation_collection.count()

        for i, (situation, recommendation) in enumerate(situations_and_advice):
            situations.append(situation)
            advice.append(recommendation)
            ids.append(str(offset + i))
            embeddings.append(self.get_embedding(situation))

        self.situation_collection.add(
            documents=situations,
            metadatas=[{"recommendation": rec} for rec in advice],
            embeddings=embeddings,
            ids=ids,
        )

    def get_memories(self, current_situation, n_matches=1):
        """Find matching recommendations using embeddings"""
        query_embedding = self.get_embedding(current_situation)

        # 检查是否为空向量（记忆功能被禁用）
        if all(x == 0.0 for x in query_embedding):
            logger.debug(f"⚠️ 记忆功能已禁用，返回空记忆列表")
            return []  # 返回空列表而不是查询数据库

        try:
            results = self.situation_collection.query(
                query_embeddings=[query_embedding],
                n_results=n_matches,
                include=["metadatas", "documents", "distances"],
            )

            matched_results = []
            for i in range(len(results["documents"][0])):
                matched_results.append(
                    {
                        "matched_situation": results["documents"][0][i],
                        "recommendation": results["metadatas"][0][i]["recommendation"],
                        "similarity_score": 1 - results["distances"][0][i],
                    }
                )

            return matched_results
        except Exception as e:
            logger.error(f"❌ 记忆查询失败: {e}")
            logger.warning(f"⚠️ 返回空记忆列表")
            return []  # 查询失败时返回空列表


if __name__ == "__main__":
    # Example usage
    matcher = FinancialSituationMemory()

    # Example data
    example_data = [
        (
            "High inflation rate with rising interest rates and declining consumer spending",
            "Consider defensive sectors like consumer staples and utilities. Review fixed-income portfolio duration.",
        ),
        (
            "Tech sector showing high volatility with increasing institutional selling pressure",
            "Reduce exposure to high-growth tech stocks. Look for value opportunities in established tech companies with strong cash flows.",
        ),
        (
            "Strong dollar affecting emerging markets with increasing forex volatility",
            "Hedge currency exposure in international positions. Consider reducing allocation to emerging market debt.",
        ),
        (
            "Market showing signs of sector rotation with rising yields",
            "Rebalance portfolio to maintain target allocations. Consider increasing exposure to sectors benefiting from higher rates.",
        ),
    ]

    # Add the example situations and recommendations
    matcher.add_situations(example_data)

    # Example query
    current_situation = """
    Market showing increased volatility in tech sector, with institutional investors 
    reducing positions and rising interest rates affecting growth stock valuations
    """

    try:
        recommendations = matcher.get_memories(current_situation, n_matches=2)

        for i, rec in enumerate(recommendations, 1):
            logger.info(f"\nMatch {i}:")
            logger.info(f"Similarity Score: {rec['similarity_score']:.2f}")
            logger.info(f"Matched Situation: {rec['matched_situation']}")
            logger.info(f"Recommendation: {rec['recommendation']}")

    except Exception as e:
        logger.error(f"Error during recommendation: {str(e)}")
