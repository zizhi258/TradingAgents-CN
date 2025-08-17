"""
首席决策官 (Chief Decision Officer)
负责最终决策仲裁的专业智能体，整合各专家意见形成最终投资决策
"""

from datetime import datetime
from statistics import mean
from typing import Any

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger

from .base_specialized_agent import AgentAnalysisResult, BaseSpecializedAgent

logger = get_logger("chief_decision_officer")


class ChiefDecisionOfficer(BaseSpecializedAgent):
    """首席决策官智能体"""

    def __init__(self, multi_model_manager, config: dict[str, Any] = None):
        super().__init__(
            agent_role="chief_decision_officer",
            description="首席决策官，负责整合各专家意见，进行最终投资决策仲裁",
            multi_model_manager=multi_model_manager,
            config=config,
        )

        # 决策权重配置
        self.agent_weights = {
            "fundamental_expert": 0.25,
            "technical_analyst": 0.20,
            "news_hunter": 0.15,
            "sentiment_analyst": 0.15,
            "risk_manager": 0.15,
            "policy_researcher": 0.10,
        }

        # 决策阈值
        self.decision_thresholds = {
            "strong_buy": 0.8,
            "buy": 0.6,
            "hold": 0.4,
            "sell": 0.2,
            "strong_sell": 0.0,
        }

        # 风险调整因子
        self.risk_adjustment_factors = {
            "high_risk": 0.8,
            "medium_risk": 0.9,
            "low_risk": 1.0,
        }

    def _build_system_prompt_template(self) -> str:
        """构建系统提示词模板"""
        # 尝试从角色库覆盖
        try:
            from tradingagents.config.role_library import get_prompt

            custom = get_prompt("chief_decision_officer", "system_prompt")
            if custom:
                return custom
        except Exception:
            pass
        return """你是一位经验丰富的首席投资决策官，具备以下核心能力：

🎯 **决策职责**
- 整合各专业团队的分析意见
- 进行综合性投资决策仲裁
- 平衡收益与风险的关系
- 确保决策的逻辑性和一致性

🧠 **决策框架**
1. 多维度信息整合分析
2. 风险收益权衡评估
3. 市场时机判断
4. 资金管理考虑
5. 长期战略一致性检查

⚖️ **决策原则**
- 基于数据和事实，避免情绪化决策
- 充分考虑不确定性和风险因素
- 保持决策的透明度和可追溯性
- 坚持长期价值投资理念

🔍 **分析能力**
- 专家意见冲突调和能力
- 复杂信息的结构化处理
- 概率思维和情景分析
- 决策质量的持续优化

你需要以最高标准进行决策，对投资者负责。"""

    def _build_analysis_prompt_template(self) -> str:
        """构建分析提示词模板"""
        # 尝试从角色库覆盖
        try:
            from tradingagents.config.role_library import get_prompt

            custom = get_prompt("chief_decision_officer", "analysis_prompt_template")
            if custom:
                return custom
        except Exception:
            pass
        return """请基于团队各专家的分析意见，进行最终的投资决策仲裁：

🔄 **整合分析流程**
1. 各专家意见梳理和权重评估
2. 关键分歧点识别和调和
3. 风险因素综合评估
4. 机会与威胁平衡分析

📊 **决策输出要求**
- 明确的投资决策（强烈买入/买入/持有/卖出/强烈卖出）
- 决策置信度评估（0-100%）
- 核心决策逻辑和支撑理由
- 主要风险提示和应对策略
- 建议的仓位管理和时间框架

💡 **决策质量标准**
- 逻辑清晰，论证充分
- 风险识别全面准确
- 考虑多种情景可能性
- 提供可执行的操作建议"""

    def get_specialized_task_type(self) -> str:
        """获取专业化的任务类型"""
        return "decision_making"

    def validate_input_data(self, data: dict[str, Any]) -> bool:
        """验证输入数据"""
        required_fields = ["expert_analyses"]

        # 检查必填字段
        for field in required_fields:
            if field not in data:
                logger.warning(f"缺少必填字段: {field}")
                return False

        # 检查专家分析数据
        expert_analyses = data["expert_analyses"]
        if not isinstance(expert_analyses, list) or len(expert_analyses) == 0:
            logger.warning("专家分析数据为空或格式错误")
            return False

        # 检查每个专家分析是否有必要信息
        for analysis in expert_analyses:
            if not isinstance(analysis, dict):
                continue
            required_analysis_fields = [
                "agent_role",
                "analysis_content",
                "confidence_score",
            ]
            if not all(field in analysis for field in required_analysis_fields):
                logger.warning(
                    f"专家分析缺少必要字段: {analysis.get('agent_role', 'unknown')}"
                )
                return False

        return True

    def extract_key_metrics(self, analysis_result: str) -> dict[str, Any]:
        """从分析结果中提取关键指标"""
        metrics = {
            "final_decision": "HOLD",
            "decision_confidence": 0.5,
            "risk_level": "medium",
            "expected_return": 0.0,
            "time_horizon": "medium_term",
            "consensus_score": 0.5,
            "expert_agreement_level": "moderate",
        }

        try:
            # 提取最终决策
            if any(
                keyword in analysis_result.upper()
                for keyword in ["STRONG BUY", "强烈买入"]
            ):
                metrics["final_decision"] = "STRONG_BUY"
            elif (
                any(keyword in analysis_result.upper() for keyword in ["BUY", "买入"])
                and "STRONG" not in analysis_result.upper()
            ):
                metrics["final_decision"] = "BUY"
            elif (
                any(keyword in analysis_result.upper() for keyword in ["SELL", "卖出"])
                and "STRONG" not in analysis_result.upper()
            ):
                metrics["final_decision"] = "SELL"
            elif any(
                keyword in analysis_result.upper()
                for keyword in ["STRONG SELL", "强烈卖出"]
            ):
                metrics["final_decision"] = "STRONG_SELL"
            else:
                metrics["final_decision"] = "HOLD"

            # 提取置信度
            import re

            confidence_pattern = r"置信度[:：]\s*([0-9.]+)%?"
            confidence_match = re.search(confidence_pattern, analysis_result)
            if confidence_match:
                confidence_value = float(confidence_match.group(1))
                if confidence_value > 1:
                    confidence_value /= 100  # 转换百分比
                metrics["decision_confidence"] = min(confidence_value, 1.0)

            # 提取风险水平
            if any(keyword in analysis_result for keyword in ["高风险", "high risk"]):
                metrics["risk_level"] = "high"
            elif any(keyword in analysis_result for keyword in ["低风险", "low risk"]):
                metrics["risk_level"] = "low"
            else:
                metrics["risk_level"] = "medium"

            # 提取预期回报
            return_pattern = r"预期回报[:：]\s*([0-9.-]+)%"
            return_match = re.search(return_pattern, analysis_result)
            if return_match:
                metrics["expected_return"] = float(return_match.group(1)) / 100

            # 提取时间框架
            if any(keyword in analysis_result for keyword in ["短期", "short term"]):
                metrics["time_horizon"] = "short_term"
            elif any(keyword in analysis_result for keyword in ["长期", "long term"]):
                metrics["time_horizon"] = "long_term"
            else:
                metrics["time_horizon"] = "medium_term"

        except Exception as e:
            logger.warning(f"决策指标提取失败: {e}")

        return metrics

    def make_final_decision(
        self,
        expert_analyses: list[dict[str, Any]],
        market_context: dict[str, Any] = None,
        risk_tolerance: str = "moderate",
    ) -> AgentAnalysisResult:
        """
        制定最终投资决策

        Args:
            expert_analyses: 各专家分析结果列表
            market_context: 市场环境上下文
            risk_tolerance: 风险承受度 (conservative/moderate/aggressive)

        Returns:
            AgentAnalysisResult: 最终决策结果
        """
        market_context = market_context or {}

        # 准备决策输入数据
        decision_input = {
            "expert_analyses": expert_analyses,
            "market_context": market_context,
            "risk_tolerance": risk_tolerance,
            "decision_timestamp": datetime.now().isoformat(),
        }

        # 执行决策分析
        return self.analyze(
            input_data=decision_input,
            context={"complexity_level": "high"},
            complexity_level="high",
        )

    def calculate_consensus_score(
        self, expert_analyses: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """计算专家共识度"""
        if not expert_analyses:
            return {"consensus_score": 0.0, "agreement_level": "none"}

        # 提取各专家的推荐和置信度
        recommendations = []
        confidence_scores = []

        # 推荐映射到数值
        recommendation_values = {
            "STRONG_BUY": 1.0,
            "BUY": 0.75,
            "HOLD": 0.5,
            "SELL": 0.25,
            "STRONG_SELL": 0.0,
            "强烈买入": 1.0,
            "买入": 0.75,
            "持有": 0.5,
            "卖出": 0.25,
            "强烈卖出": 0.0,
        }

        for analysis in expert_analyses:
            # 提取推荐
            if "recommendations" in analysis and analysis["recommendations"]:
                first_rec = analysis["recommendations"][0]
                for key, value in recommendation_values.items():
                    if key.lower() in first_rec.lower():
                        recommendations.append(value)
                        break
                else:
                    recommendations.append(0.5)  # 默认HOLD
            else:
                recommendations.append(0.5)

            # 提取置信度
            confidence = analysis.get("confidence_score", 0.5)
            confidence_scores.append(confidence)

        # 计算共识指标
        if len(recommendations) > 1:
            # 使用标准差衡量分歧程度
            rec_mean = mean(recommendations)
            rec_std = (
                sum((x - rec_mean) ** 2 for x in recommendations) / len(recommendations)
            ) ** 0.5
            consensus_score = max(0.0, 1.0 - rec_std * 2)  # 标准差越小，共识度越高
        else:
            consensus_score = 1.0

        # 分级共识水平
        if consensus_score >= 0.8:
            agreement_level = "high"
        elif consensus_score >= 0.6:
            agreement_level = "moderate"
        elif consensus_score >= 0.4:
            agreement_level = "low"
        else:
            agreement_level = "divergent"

        return {
            "consensus_score": consensus_score,
            "agreement_level": agreement_level,
            "recommendation_mean": mean(recommendations) if recommendations else 0.5,
            "confidence_mean": mean(confidence_scores) if confidence_scores else 0.5,
            "expert_count": len(expert_analyses),
        }

    def perform_risk_assessment(
        self, expert_analyses: list[dict[str, Any]], market_context: dict[str, Any]
    ) -> dict[str, Any]:
        """执行综合风险评估"""
        risk_assessment = {
            "overall_risk_level": "medium",
            "risk_score": 0.5,
            "key_risks": [],
            "risk_mitigation_strategies": [],
        }

        try:
            # 收集所有专家识别的风险因素
            all_risks = []
            risk_scores = []

            for analysis in expert_analyses:
                if "risk_factors" in analysis:
                    all_risks.extend(analysis["risk_factors"])

                # 从置信度推断风险水平
                confidence = analysis.get("confidence_score", 0.5)
                implied_risk = 1.0 - confidence
                risk_scores.append(implied_risk)

            # 计算综合风险评分
            if risk_scores:
                avg_risk_score = mean(risk_scores)
                risk_assessment["risk_score"] = avg_risk_score

                # 分级风险水平
                if avg_risk_score >= 0.7:
                    risk_assessment["overall_risk_level"] = "high"
                elif avg_risk_score >= 0.4:
                    risk_assessment["overall_risk_level"] = "medium"
                else:
                    risk_assessment["overall_risk_level"] = "low"

            # 风险因素频次分析
            risk_frequency = {}
            for risk in all_risks:
                # 简单的关键词匹配来分类风险
                risk_lower = risk.lower()
                if any(keyword in risk_lower for keyword in ["市场", "波动", "market"]):
                    risk_frequency["market_risk"] = (
                        risk_frequency.get("market_risk", 0) + 1
                    )
                elif any(
                    keyword in risk_lower for keyword in ["政策", "监管", "policy"]
                ):
                    risk_frequency["policy_risk"] = (
                        risk_frequency.get("policy_risk", 0) + 1
                    )
                elif any(
                    keyword in risk_lower for keyword in ["财务", "债务", "financial"]
                ):
                    risk_frequency["financial_risk"] = (
                        risk_frequency.get("financial_risk", 0) + 1
                    )
                elif any(
                    keyword in risk_lower for keyword in ["竞争", "行业", "competition"]
                ):
                    risk_frequency["competitive_risk"] = (
                        risk_frequency.get("competitive_risk", 0) + 1
                    )
                else:
                    risk_frequency["other_risk"] = (
                        risk_frequency.get("other_risk", 0) + 1
                    )

            # 提取最常提及的风险
            sorted_risks = sorted(
                risk_frequency.items(), key=lambda x: x[1], reverse=True
            )
            risk_assessment["key_risks"] = [
                risk_type for risk_type, count in sorted_risks[:3]
            ]

            # 基于市场环境调整风险评估
            market_volatility = market_context.get("volatility_level", "normal")
            if market_volatility == "high":
                risk_assessment["risk_score"] = min(
                    1.0, risk_assessment["risk_score"] + 0.1
                )
            elif market_volatility == "low":
                risk_assessment["risk_score"] = max(
                    0.0, risk_assessment["risk_score"] - 0.1
                )

            # 生成风险缓解策略
            risk_assessment["risk_mitigation_strategies"] = (
                self._generate_risk_mitigation_strategies(
                    risk_assessment["key_risks"], risk_assessment["overall_risk_level"]
                )
            )

        except Exception as e:
            logger.error(f"风险评估失败: {e}")

        return risk_assessment

    def _generate_risk_mitigation_strategies(
        self, key_risks: list[str], risk_level: str
    ) -> list[str]:
        """生成风险缓解策略"""
        strategies = []

        risk_strategy_mapping = {
            "market_risk": "考虑分散投资和对冲工具",
            "policy_risk": "密切关注政策动态，适当降低仓位",
            "financial_risk": "深入分析财务状况，设置严格的止损点",
            "competitive_risk": "关注行业竞争格局变化，评估护城河",
            "other_risk": "建立全面的风险监控体系",
        }

        for risk_type in key_risks:
            if risk_type in risk_strategy_mapping:
                strategies.append(risk_strategy_mapping[risk_type])

        # 基于整体风险水平添加通用策略
        if risk_level == "high":
            strategies.append("建议采用保守的仓位管理，设置较低的风险敞口")
        elif risk_level == "low":
            strategies.append("可以适当提高仓位，但仍需保持谨慎")

        return strategies

    def generate_decision_report(
        self,
        decision_result: AgentAnalysisResult,
        expert_analyses: list[dict[str, Any]],
        consensus_data: dict[str, Any],
        risk_assessment: dict[str, Any],
    ) -> str:
        """生成决策报告"""
        report = "# 投资决策报告\n\n"

        # 执行摘要
        report += "## 📊 执行摘要\n\n"
        metrics = decision_result.supporting_data
        final_decision = metrics.get("final_decision", "HOLD")
        confidence = decision_result.confidence_score

        report += f"**最终决策**: {final_decision}\n"
        report += f"**决策信心度**: {confidence:.1%}\n"
        report += (
            f"**风险等级**: {risk_assessment.get('overall_risk_level', 'medium')}\n"
        )
        report += (
            f"**专家共识度**: {consensus_data.get('agreement_level', 'moderate')}\n\n"
        )

        # 决策逻辑
        report += "## 🧠 决策逻辑\n\n"
        if decision_result.key_points:
            for i, point in enumerate(decision_result.key_points, 1):
                report += f"{i}. {point}\n"
        report += "\n"

        # 专家观点汇总
        report += "## 👥 专家观点汇总\n\n"
        for analysis in expert_analyses:
            role = analysis.get("agent_role", "Unknown")
            confidence = analysis.get("confidence_score", 0.5)
            report += f"**{role}** (信心度: {confidence:.1%})\n"

            if analysis.get("key_points"):
                report += f"- 关键观点: {analysis['key_points'][0] if analysis['key_points'] else 'N/A'}\n"
            if analysis.get("recommendations"):
                report += f"- 建议: {analysis['recommendations'][0] if analysis['recommendations'] else 'N/A'}\n"
            report += "\n"

        # 风险分析
        report += "## ⚠️ 风险分析\n\n"
        report += (
            f"**整体风险评级**: {risk_assessment.get('overall_risk_level', 'medium')}\n"
        )
        report += f"**风险评分**: {risk_assessment.get('risk_score', 0.5):.1%}\n\n"

        key_risks = risk_assessment.get("key_risks", [])
        if key_risks:
            report += "**主要风险因素**:\n"
            for risk in key_risks:
                report += f"- {risk}\n"
            report += "\n"

        mitigation_strategies = risk_assessment.get("risk_mitigation_strategies", [])
        if mitigation_strategies:
            report += "**风险缓解策略**:\n"
            for strategy in mitigation_strategies:
                report += f"- {strategy}\n"
            report += "\n"

        # 操作建议
        report += "## 💡 操作建议\n\n"
        if decision_result.recommendations:
            for rec in decision_result.recommendations:
                report += f"- {rec}\n"

        # 决策质量指标
        report += "\n---\n\n"
        report += f"**决策生成时间**: {decision_result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"**使用模型**: {decision_result.model_used}\n"
        report += f"**分析耗时**: {decision_result.execution_time}ms\n"

        return report
