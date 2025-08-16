"""
Gemini OpenAI-Compatible Client
通过 OpenAI 兼容协议访问自建 Gemini 反代服务（如：Gemini-API-服务介绍.md）。

特性：
- 使用 openai>=1 的官方 SDK，通过自定义 base_url + api_key 调用
- 支持流式与非流式输出
- 与 BaseMultiModelAdapter 统一接口，便于与多模型路由集成
"""

from __future__ import annotations

import os
import time
import json
from typing import Dict, Any, List

try:
    from openai import OpenAI  # type: ignore
    OPENAI_AVAILABLE = True
except Exception:
    OPENAI_AVAILABLE = False
    OpenAI = None  # type: ignore

from ..core.base_multi_model_adapter import (
    BaseMultiModelAdapter,
    ModelProvider,
    ModelSpec,
    TaskSpec,
    TaskResult,
)
from tradingagents.utils.logging_init import get_logger

logger = get_logger("gemini_openai_compat_client")


class GeminiOpenAICompatClient(BaseMultiModelAdapter):
    """Gemini 兼容 OpenAI 协议的客户端（自建反代渠道）。"""

    # 依据常见可用模型列举（与 Google 官方命名一致，便于前端认知）
    SUPPORTED_MODELS: Dict[str, Dict[str, Any]] = {
        # 无前缀（与 Google 官方命名一致）
        "gemini-2.5-pro": {
            "type": "premium",
            "cost_per_1k": 0.0125,
            "max_tokens": 65536,
            "context_window": 1048576,
            "description": "Gemini 2.5 Pro (OpenAI兼容渠道)",
        },
        # 带渠道前缀的别名，便于在策略/角色中区分渠道
        "gemini-api/gemini-2.5-pro": {
            "type": "premium",
            "cost_per_1k": 0.0125,
            "max_tokens": 65536,
            "context_window": 1048576,
            "description": "Gemini 2.5 Pro (Gemini-API 兼容渠道)",
        },
        "gemini-2.0-flash": {
            "type": "speed",
            "cost_per_1k": 0.0020,
            "max_tokens": 8192,
            "context_window": 1048576,
            "description": "Gemini 2.0 Flash (OpenAI兼容渠道)",
        },
        "gemini-api/gemini-2.0-flash": {
            "type": "speed",
            "cost_per_1k": 0.0020,
            "max_tokens": 8192,
            "context_window": 1048576,
            "description": "Gemini 2.0 Flash (Gemini-API 兼容渠道)",
        },
        "gemini-1.5-pro": {
            "type": "general",
            "cost_per_1k": 0.0075,
            "max_tokens": 8192,
            "context_window": 2097152,
            "description": "Gemini 1.5 Pro (OpenAI兼容渠道)",
        },
        "gemini-api/gemini-1.5-pro": {
            "type": "general",
            "cost_per_1k": 0.0075,
            "max_tokens": 8192,
            "context_window": 2097152,
            "description": "Gemini 1.5 Pro (Gemini-API 兼容渠道)",
        },
        "gemini-1.5-flash": {
            "type": "speed",
            "cost_per_1k": 0.0015,
            "max_tokens": 8192,
            "context_window": 1048576,
            "description": "Gemini 1.5 Flash (OpenAI兼容渠道)",
        },
        "gemini-api/gemini-1.5-flash": {
            "type": "speed",
            "cost_per_1k": 0.0015,
            "max_tokens": 8192,
            "context_window": 1048576,
            "description": "Gemini 1.5 Flash (Gemini-API 兼容渠道)",
        },
    }

    def __init__(self, config: Dict[str, Any]):
        super().__init__(ModelProvider.OPENAI, config)  # 使用 OPENAI 表示协议兼容

        if not OPENAI_AVAILABLE:
            raise ImportError("openai SDK 未安装。请运行: pip install openai>=1.0.0")

        # 读取密钥与端点（优先 config，再读环境变量）
        self.api_key = (
            config.get("api_key")
            or os.getenv("GEMINI_API_COMPAT_API_KEY")
            or os.getenv("OPENAI_API_KEY")
        )
        self.base_url = (
            config.get("base_url")
            or os.getenv("GEMINI_API_COMPAT_BASE_URL")
            or "http://localhost:8080/v1"
        )
        self.default_model = config.get("default_model", "gemini-2.5-pro")
        self.timeout = int(config.get("timeout", 60))

        if not self.api_key:
            raise ValueError("Gemini-API(兼容) 未配置 API Key: 设置 GEMINI_API_COMPAT_API_KEY 或 OPENAI_API_KEY")

        self.initialize_client()

    def initialize_client(self) -> None:
        # 初始化 OpenAI 客户端（指向自建反代）
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        # 初始化模型规格
        self._supported_models = {}
        for model_name, info in self.SUPPORTED_MODELS.items():
            self._supported_models[model_name] = ModelSpec(
                name=model_name,
                provider=ModelProvider.OPENAI,  # 协议为 OpenAI 兼容
                model_type=info["type"],
                cost_per_1k_tokens=info["cost_per_1k"],
                max_tokens=info["max_tokens"],
                context_window=info["context_window"],
                supports_streaming=True,
            )
        logger.info(
            f"Gemini-API(兼容) 客户端初始化完成，base_url={self.base_url}, 支持 {len(self._supported_models)} 个模型"
        )

    def get_supported_models(self) -> Dict[str, ModelSpec]:
        return self._supported_models.copy()

    def execute_task(self, model_name: str, prompt: str, task_spec: TaskSpec, **kwargs) -> TaskResult:
        start = time.time()
        try:
            if model_name not in self._supported_models:
                raise ValueError(f"不支持的模型: {model_name}")

            model_spec = self._supported_models[model_name]
            max_out = min(model_spec.max_tokens, int(kwargs.get("max_tokens", 4096)))
            temperature = float(kwargs.get("temperature", 0.2))
            top_p = float(kwargs.get("top_p", 0.9))
            streaming = bool(kwargs.get("stream", False))
            on_token = kwargs.get("on_token")

            invoke_model = model_name.split('/', 1)[1] if model_name.startswith('gemini-api/') else model_name

            if streaming and callable(on_token):
                resp = self.client.chat.completions.create(
                    model=invoke_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_out,
                    temperature=temperature,
                    top_p=top_p,
                    stream=True,
                    timeout=self.timeout,
                )
                full_text = ""
                usage = {}
                for chunk in resp:
                    try:
                        delta = chunk.choices[0].delta.content or ""
                    except Exception:
                        delta = ""
                    if delta:
                        full_text += delta
                        try:
                            on_token(delta)
                        except Exception:
                            pass
                    # usage 仅在非流式/结束后可用；此处保留空，后续估算
                exec_ms = int((time.time() - start) * 1000)
                if not full_text:
                    return TaskResult(
                        result="",
                        model_used=model_spec,
                        execution_time=exec_ms,
                        actual_cost=0.0,
                        token_usage={},
                        success=False,
                        error_message="流式响应为空",
                    )
                # 估算用量与成本（保守）
                approx_in = max(1, int(len(prompt) / 2))
                approx_out = int(len(full_text) / 2)
                usage = {
                    "prompt_tokens": approx_in,
                    "completion_tokens": approx_out,
                    "total_tokens": approx_in + approx_out,
                }
                cost = (usage["total_tokens"] / 1000.0) * model_spec.cost_per_1k_tokens
                return TaskResult(
                    result=full_text,
                    model_used=model_spec,
                    execution_time=exec_ms,
                    actual_cost=cost,
                    token_usage=usage,
                    success=True,
                )

            # 非流式
            resp = self.client.chat.completions.create(
                model=invoke_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_out,
                temperature=temperature,
                top_p=top_p,
                timeout=self.timeout,
            )
            exec_ms = int((time.time() - start) * 1000)
            text = (resp.choices[0].message.content or "") if getattr(resp, "choices", None) else ""
            usage_meta = getattr(resp, "usage", None)
            if not text:
                return TaskResult(
                    result="",
                    model_used=model_spec,
                    execution_time=exec_ms,
                    actual_cost=0.0,
                    token_usage={},
                    success=False,
                    error_message="模型返回空响应",
                )
            if usage_meta:
                usage = {
                    "prompt_tokens": int(getattr(usage_meta, "prompt_tokens", 0) or 0),
                    "completion_tokens": int(getattr(usage_meta, "completion_tokens", 0) or 0),
                    "total_tokens": int(getattr(usage_meta, "total_tokens", 0) or 0),
                }
            else:
                # 估算
                approx_in = max(1, int(len(prompt) / 2))
                approx_out = int(len(text) / 2)
                usage = {
                    "prompt_tokens": approx_in,
                    "completion_tokens": approx_out,
                    "total_tokens": approx_in + approx_out,
                }
            cost = (usage["total_tokens"] / 1000.0) * model_spec.cost_per_1k_tokens
            return TaskResult(
                result=text,
                model_used=model_spec,
                execution_time=exec_ms,
                actual_cost=cost,
                token_usage=usage,
                success=True,
            )

        except Exception as e:
            exec_ms = int((time.time() - start) * 1000)
            logger.error(f"Gemini-API(兼容) 调用失败: {e}")
            return TaskResult(
                result="",
                model_used=self._supported_models.get(model_name),
                execution_time=exec_ms,
                actual_cost=0.0,
                token_usage={},
                success=False,
                error_message=str(e),
            )

    def estimate_cost(self, model_name: str, estimated_tokens: int) -> float:
        if model_name not in self._supported_models:
            return 0.0
        spec = self._supported_models[model_name]
        return (estimated_tokens / 1000.0) * spec.cost_per_1k_tokens

    def health_check(self) -> bool:
        # 使用最短调用验证端点可用
        try:
            invoke_model = self.default_model.split('/', 1)[1] if self.default_model.startswith('gemini-api/') else self.default_model
            resp = self.client.chat.completions.create(
                model=invoke_model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=4,
                temperature=0.0,
                timeout=10,
            )
            ok = bool(getattr(resp, "id", None))
            if ok:
                logger.info("Gemini-API(兼容) 健康检查通过")
            else:
                logger.warning("Gemini-API(兼容) 健康检查失败：无ID")
            return ok
        except Exception as e:
            logger.warning(f"Gemini-API(兼容) 健康检查异常: {e}")
            return False
