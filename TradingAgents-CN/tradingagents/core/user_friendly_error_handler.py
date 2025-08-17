"""
用户友好的错误处理器
将技术错误信息转换为用户可理解的提示，提供解决建议
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger

logger = get_logger("error_handler")


class ErrorCategory(Enum):
    """错误类别"""

    API_KEY_MISSING = "api_key_missing"
    API_QUOTA_EXCEEDED = "api_quota_exceeded"
    NETWORK_ERROR = "network_error"
    MODEL_UNAVAILABLE = "model_unavailable"
    DATA_SOURCE_ERROR = "data_source_error"
    INVALID_INPUT = "invalid_input"
    TIMEOUT_ERROR = "timeout_error"
    SYSTEM_OVERLOAD = "system_overload"
    CONFIG_ERROR = "config_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class UserFriendlyError:
    """用户友好的错误信息"""

    category: ErrorCategory
    title: str
    message: str
    suggestion: str
    action_required: bool = False
    retry_possible: bool = True
    estimated_fix_time: str = "几分钟"
    help_url: str | None = None


class UserFriendlyErrorHandler:
    """用户友好的错误处理器"""

    def __init__(self):
        # 错误模式匹配规则
        self.error_patterns = {
            # API密钥相关错误
            ErrorCategory.API_KEY_MISSING: [
                r".*api.*key.*not.*found.*",
                r".*invalid.*api.*key.*",
                r".*authentication.*failed.*",
                r".*unauthorized.*",
                r".*401.*",
            ],
            # API配额相关错误
            ErrorCategory.API_QUOTA_EXCEEDED: [
                r".*quota.*exceeded.*",
                r".*rate.*limit.*",
                r".*too.*many.*requests.*",
                r".*429.*",
                r".*usage.*limit.*",
            ],
            # 网络连接错误
            ErrorCategory.NETWORK_ERROR: [
                r".*connection.*error.*",
                r".*network.*unreachable.*",
                r".*timeout.*",
                r".*dns.*resolution.*failed.*",
                r".*connection.*refused.*",
            ],
            # 模型不可用错误
            ErrorCategory.MODEL_UNAVAILABLE: [
                r".*model.*not.*available.*",
                r".*model.*not.*found.*",
                r".*service.*unavailable.*",
                r".*503.*",
                r".*model.*maintenance.*",
            ],
            # 数据源错误
            ErrorCategory.DATA_SOURCE_ERROR: [
                r".*stock.*data.*not.*found.*",
                r".*invalid.*stock.*code.*",
                r".*market.*data.*unavailable.*",
                r".*data.*source.*error.*",
            ],
            # 输入验证错误
            ErrorCategory.INVALID_INPUT: [
                r".*invalid.*input.*",
                r".*validation.*error.*",
                r".*format.*error.*",
                r".*parameter.*missing.*",
            ],
            # 超时错误
            ErrorCategory.TIMEOUT_ERROR: [
                r".*timeout.*",
                r".*timed.*out.*",
                r".*request.*timeout.*",
                r".*execution.*timeout.*",
            ],
            # 系统过载错误
            ErrorCategory.SYSTEM_OVERLOAD: [
                r".*system.*overload.*",
                r".*too.*busy.*",
                r".*server.*busy.*",
                r".*resource.*exhausted.*",
            ],
        }

        # 错误修复建议
        self.error_solutions = {
            ErrorCategory.API_KEY_MISSING: UserFriendlyError(
                category=ErrorCategory.API_KEY_MISSING,
                title="🔑 API密钥配置问题",
                message="系统无法验证您的API密钥，请检查配置",
                suggestion="1. 检查.env文件中的API密钥设置\n2. 确保密钥格式正确且有效\n3. 重启应用以加载新配置",
                action_required=True,
                retry_possible=False,
                estimated_fix_time="2-5分钟",
                help_url="/help/api-keys",
            ),
            ErrorCategory.API_QUOTA_EXCEEDED: UserFriendlyError(
                category=ErrorCategory.API_QUOTA_EXCEEDED,
                title="📈 API调用频率超限",
                message="您的API调用已达到限制，请稍后再试",
                suggestion="1. 等待几分钟后重试\n2. 升级您的API套餐获得更高限额\n3. 启用成本优化模式减少调用",
                action_required=False,
                retry_possible=True,
                estimated_fix_time="5-30分钟",
            ),
            ErrorCategory.NETWORK_ERROR: UserFriendlyError(
                category=ErrorCategory.NETWORK_ERROR,
                title="🌐 网络连接问题",
                message="无法连接到服务器，请检查网络连接",
                suggestion="1. 检查您的网络连接\n2. 尝试刷新页面或重试\n3. 如果使用VPN，请尝试切换节点",
                action_required=False,
                retry_possible=True,
                estimated_fix_time="立即或几分钟内",
            ),
            ErrorCategory.MODEL_UNAVAILABLE: UserFriendlyError(
                category=ErrorCategory.MODEL_UNAVAILABLE,
                title="🤖 AI模型暂时不可用",
                message="选定的AI模型正在维护中，系统将自动切换到备选模型",
                suggestion="1. 系统正在尝试备选方案\n2. 您可以手动选择其他模型\n3. 通常几分钟内会自动恢复",
                action_required=False,
                retry_possible=True,
                estimated_fix_time="3-15分钟",
            ),
            ErrorCategory.DATA_SOURCE_ERROR: UserFriendlyError(
                category=ErrorCategory.DATA_SOURCE_ERROR,
                title="📊 股票数据获取失败",
                message="无法获取指定股票的数据，请检查股票代码",
                suggestion="1. 确认股票代码正确（如：000001、AAPL）\n2. 检查选择的市场类型是否匹配\n3. 尝试选择其他交易日",
                action_required=True,
                retry_possible=True,
                estimated_fix_time="立即",
            ),
            ErrorCategory.INVALID_INPUT: UserFriendlyError(
                category=ErrorCategory.INVALID_INPUT,
                title="⚠️ 输入参数错误",
                message="您提供的信息格式不正确，请检查后重新输入",
                suggestion="1. 检查所有必填字段\n2. 确认输入格式符合要求\n3. 参考示例进行修正",
                action_required=True,
                retry_possible=True,
                estimated_fix_time="立即",
            ),
            ErrorCategory.TIMEOUT_ERROR: UserFriendlyError(
                category=ErrorCategory.TIMEOUT_ERROR,
                title="⏱️ 分析处理超时",
                message="分析处理时间过长，已自动停止。您可以尝试简化分析参数",
                suggestion="1. 降低分析深度级别\n2. 减少选择的智能体数量\n3. 稍后再次尝试",
                action_required=False,
                retry_possible=True,
                estimated_fix_time="立即重试或几分钟后",
            ),
            ErrorCategory.SYSTEM_OVERLOAD: UserFriendlyError(
                category=ErrorCategory.SYSTEM_OVERLOAD,
                title="⚡ 系统负载过高",
                message="当前系统负载较高，请稍后再试或降低分析复杂度",
                suggestion="1. 稍等几分钟后重试\n2. 选择更简单的分析模式\n3. 避开使用高峰期",
                action_required=False,
                retry_possible=True,
                estimated_fix_time="5-15分钟",
            ),
            ErrorCategory.UNKNOWN_ERROR: UserFriendlyError(
                category=ErrorCategory.UNKNOWN_ERROR,
                title="🔧 系统遇到未知问题",
                message="系统遇到意外错误，我们的技术团队将尽快解决",
                suggestion="1. 请尝试刷新页面\n2. 如果问题持续，请联系技术支持\n3. 您可以尝试使用基础分析模式",
                action_required=False,
                retry_possible=True,
                estimated_fix_time="立即重试或联系支持",
            ),
        }

        logger.info("用户友好错误处理器初始化完成")

    def handle_error(
        self,
        error: Exception,
        context: dict[str, Any] | None = None,
        user_action: str | None = None,
    ) -> UserFriendlyError:
        """
        处理错误并返回用户友好的错误信息

        Args:
            error: 原始异常对象
            context: 错误上下文信息
            user_action: 用户正在执行的操作

        Returns:
            UserFriendlyError: 用户友好的错误信息
        """
        try:
            error_str = str(error).lower()
            error_category = self._categorize_error(error_str)

            # 记录原始错误（技术日志）
            logger.error(
                f"Error handled: {error_category.value} - {error}",
                exc_info=True,
                extra={"context": context},
            )

            # 获取用户友好的错误信息
            user_error = self.error_solutions[error_category]

            # 根据上下文定制错误信息
            if context:
                user_error = self._customize_error_message(
                    user_error, context, user_action
                )

            return user_error

        except Exception as e:
            logger.error(f"Error handler itself failed: {e}", exc_info=True)
            # 返回默认错误
            return self.error_solutions[ErrorCategory.UNKNOWN_ERROR]

    def _categorize_error(self, error_message: str) -> ErrorCategory:
        """根据错误信息分类错误"""
        for category, patterns in self.error_patterns.items():
            for pattern in patterns:
                if re.search(pattern, error_message, re.IGNORECASE):
                    return category

        return ErrorCategory.UNKNOWN_ERROR

    def _customize_error_message(
        self,
        user_error: UserFriendlyError,
        context: dict[str, Any],
        user_action: str | None,
    ) -> UserFriendlyError:
        """根据上下文定制错误信息"""
        customized_error = UserFriendlyError(
            category=user_error.category,
            title=user_error.title,
            message=user_error.message,
            suggestion=user_error.suggestion,
            action_required=user_error.action_required,
            retry_possible=user_error.retry_possible,
            estimated_fix_time=user_error.estimated_fix_time,
            help_url=user_error.help_url,
        )

        # 根据用户操作定制信息
        if user_action:
            if user_action == "stock_analysis":
                customized_error.message = f"在分析股票时{customized_error.message}"
            elif user_action == "model_selection":
                customized_error.message = f"在选择AI模型时{customized_error.message}"

        # 根据上下文添加特定建议
        if context.get("stock_symbol"):
            stock = context["stock_symbol"]
            if user_error.category == ErrorCategory.DATA_SOURCE_ERROR:
                customized_error.suggestion += (
                    f"\n\n💡 当前分析股票：{stock}，请确认代码正确"
                )

        if context.get("model_name"):
            model = context["model_name"]
            if user_error.category == ErrorCategory.MODEL_UNAVAILABLE:
                customized_error.suggestion += (
                    f"\n\n🔄 受影响模型：{model}，系统将自动切换备选方案"
                )

        return customized_error

    def suggest_fallback_action(
        self, error_category: ErrorCategory, context: dict[str, Any] | None = None
    ) -> str | None:
        """
        为错误类别建议降级操作

        Args:
            error_category: 错误类别
            context: 上下文信息

        Returns:
            Optional[str]: 建议的降级操作
        """
        fallback_actions = {
            ErrorCategory.MODEL_UNAVAILABLE: "switch_to_backup_model",
            ErrorCategory.API_QUOTA_EXCEEDED: "enable_cost_optimization",
            ErrorCategory.NETWORK_ERROR: "use_cached_data",
            ErrorCategory.TIMEOUT_ERROR: "reduce_analysis_complexity",
            ErrorCategory.SYSTEM_OVERLOAD: "queue_for_later_processing",
        }

        return fallback_actions.get(error_category)

    def get_recovery_suggestions(self, error_category: ErrorCategory) -> dict[str, Any]:
        """
        获取错误恢复建议

        Args:
            error_category: 错误类别

        Returns:
            Dict[str, Any]: 恢复建议配置
        """
        recovery_config = {
            ErrorCategory.API_KEY_MISSING: {
                "immediate_action": "show_api_key_setup_guide",
                "auto_retry": False,
                "retry_delay": 0,
            },
            ErrorCategory.API_QUOTA_EXCEEDED: {
                "immediate_action": "enable_cost_optimization",
                "auto_retry": True,
                "retry_delay": 300,  # 5分钟
            },
            ErrorCategory.NETWORK_ERROR: {
                "immediate_action": "switch_to_offline_mode",
                "auto_retry": True,
                "retry_delay": 30,  # 30秒
            },
            ErrorCategory.MODEL_UNAVAILABLE: {
                "immediate_action": "select_alternative_model",
                "auto_retry": True,
                "retry_delay": 60,  # 1分钟
            },
            ErrorCategory.TIMEOUT_ERROR: {
                "immediate_action": "reduce_complexity",
                "auto_retry": True,
                "retry_delay": 10,  # 10秒
            },
        }

        return recovery_config.get(
            error_category,
            {
                "immediate_action": "show_error_message",
                "auto_retry": False,
                "retry_delay": 0,
            },
        )

    def format_error_for_display(self, user_error: UserFriendlyError) -> dict[str, Any]:
        """
        格式化错误信息用于界面显示

        Args:
            user_error: 用户友好错误对象

        Returns:
            Dict[str, Any]: 格式化的显示信息
        """
        return {
            "type": "error",
            "category": user_error.category.value,
            "title": user_error.title,
            "message": user_error.message,
            "suggestion": user_error.suggestion,
            "action_required": user_error.action_required,
            "retry_possible": user_error.retry_possible,
            "estimated_fix_time": user_error.estimated_fix_time,
            "help_url": user_error.help_url,
            "display_style": "friendly",
            "severity": "high" if user_error.action_required else "medium",
        }


# 创建全局错误处理器实例
error_handler = UserFriendlyErrorHandler()


def handle_user_friendly_error(
    error: Exception,
    context: dict[str, Any] | None = None,
    user_action: str | None = None,
) -> dict[str, Any]:
    """
    便捷函数：处理错误并返回格式化的显示信息

    Args:
        error: 异常对象
        context: 上下文信息
        user_action: 用户操作

    Returns:
        Dict[str, Any]: 格式化的错误显示信息
    """
    user_error = error_handler.handle_error(error, context, user_action)
    return error_handler.format_error_for_display(user_error)
