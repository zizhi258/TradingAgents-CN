"""
Chief Writer (主笔人)
负责在多智能体完成分析后，汲取各方观点，产出结构化、完整、不可偷懒的长文报告
"""

from typing import Dict, Any, List
from datetime import datetime

from .base_specialized_agent import BaseSpecializedAgent, AgentAnalysisResult
from tradingagents.utils.logging_init import get_logger
from tradingagents.config.provider_models import model_provider_manager


logger = get_logger('chief_writer')


class ChiefWriter(BaseSpecializedAgent):
    """主笔人/总编辑：融合多方观点，写作规整长文"""

    def __init__(self, multi_model_manager, config: Dict[str, Any] = None):
        super().__init__(
            agent_role="chief_writer",
            description="主笔人，负责融合多方专家观点，输出结构化长文",
            multi_model_manager=multi_model_manager,
            config=config,
        )

    def _build_system_prompt_template(self) -> str:
        return (
            "你是一位资深财经主笔人/总编辑，擅长将多学科专家的分析凝练为高质量、结构化的长文。\n"
            "写作原则：\n"
            "- 全面、严谨、可读性强，确保逻辑链条完整、论据充分\n"
            "- 必须充分吸收各专家观点，不允许偷懒略写，不得以‘由于篇幅原因’等措辞回避细节\n"
            "- 主动比对分歧，形成共识与差异的清晰对照\n"
            "- 中文专业、简洁、条理清晰；避免口水化表达\n"
        )

    def _build_analysis_prompt_template(self) -> str:
        return (
            "请基于输入的多智能体分析结果，撰写一篇完整、结构化的长文报告。\n"
            "输出要求（Markdown）：\n"
            "# 标题（含公司名与主题）\n"
            "## 执行摘要（200-300字，给出核心结论与建议）\n"
            "## 公司与市场背景（关键业务、赛道、所处周期）\n"
            "## 多方观点融汇\n"
            "- 新闻猎手（News）与舆情要点\n"
            "- 基本面（Fundamental）核心因子与估值视角\n"
            "- 技术面（Technical）趋势、关键位与信号\n"
            "- 情绪面（Sentiment）与资金面线索\n"
            "- 风险与政策（Risk/Policy）约束与催化\n"
            "## 分歧与共识（列举冲突观点与形成的共识结论）\n"
            "## 投资逻辑链条（自上而下/自下而上的推理路径，因果清晰）\n"
            "## 情景与时间框架（短/中/长期；触发条件；监控指标）\n"
            "## 风险与对策（列出主要风险及缓释方案）\n"
            "## 结论与操作建议（仓位、入场/止损/目标区间）\n"
            "## 附录（如需：关键指标表、名词解释、引用来源）\n"
            "硬性规范：\n"
            "- 不得出现‘略’、‘省略’、‘篇幅有限’等偷懒措辞\n"
            "- 吸收每位专家的关键洞见，引用时标注角色名称\n"
            "- 文章最少1200字；结构齐全，标题层级清晰\n"
        )

    def _get_output_format_instruction(self) -> str:
        # 覆盖基类默认输出格式，按主笔人文章结构输出
        return ""

    def get_specialized_task_type(self) -> str:
        return "article_composition"

    def validate_input_data(self, data: Dict[str, Any]) -> bool:
        # 需要至少包含专家分析列表
        if not isinstance(data, dict):
            return False
        if 'expert_analyses' not in data:
            logger.warning("主笔人输入缺少 expert_analyses")
            return False
        experts = data.get('expert_analyses')
        return isinstance(experts, list) and len(experts) > 0

    def extract_key_metrics(self, analysis_result: str) -> Dict[str, Any]:
        # 简要提取文章长度与章节覆盖度
        try:
            word_count = len(analysis_result)
            section_keywords = [
                "执行摘要", "背景", "观点融汇", "分歧与共识",
                "投资逻辑", "情景", "风险", "结论与操作建议",
            ]
            sections_covered = sum(1 for k in section_keywords if k in analysis_result)
            return {
                'word_count': word_count,
                'sections_covered': sections_covered,
            }
        except Exception:
            return {'word_count': 0, 'sections_covered': 0}

    def analyze(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any] = None,
        complexity_level: str = "high",
    ) -> AgentAnalysisResult:
        start_time = datetime.now()
        context = context or {}

        try:
            if not self.validate_input_data(input_data):
                raise ValueError("chief_writer 输入数据验证失败")

            prompt = self._build_full_analysis_prompt(input_data, context)

            # 解析主笔人模型优先级：context(会话/临时) > 持久化/角色库推荐 > 合理默认
            selected_model = None
            try:
                ctx_overrides = (context or {}).get('model_overrides') or {}
                if isinstance(ctx_overrides, dict):
                    selected_model = ctx_overrides.get(self.agent_role)
                if not selected_model:
                    # 使用角色库/推荐策略选择最佳模型
                    selected_model = model_provider_manager.get_best_model_for_role('chief_writer') or 'gemini-2.5-pro'
            except Exception:
                selected_model = 'gemini-2.5-pro'

            task_result = self.multi_model_manager.execute_task(
                agent_role=self.agent_role,
                task_prompt=prompt,
                task_type=self.get_specialized_task_type(),
                complexity_level=complexity_level,
                context=context,
                model_override=selected_model,
            )

            exec_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            if not task_result.success:
                raise RuntimeError(f"主笔人写作失败: {task_result.error_message}")

            # 质量把关：长度/结构/禁用偷懒措辞
            metrics = self.extract_key_metrics(task_result.result)
            lazy_phrases = ["省略", "篇幅有限", "不再赘述"]
            need_retry = (
                metrics.get('word_count', 0) < 1200 or
                metrics.get('sections_covered', 0) < 6 or
                any(p in task_result.result for p in lazy_phrases)
            )

            if need_retry:
                reinforce_prompt = (
                    f"{prompt}\n\n"
                    "注意：上述初稿未满足长度/结构/严谨性要求。请按输出要求完整展开，"
                    "覆盖所有章节，至少1200字，严禁出现‘省略’、‘篇幅有限’、‘不再赘述’等措辞，"
                    "充分纳入各专家观点与分歧对照，并补充证据与逻辑链条。"
                )
                # 二次写作沿用上一次选择的模型
                task_result = self.multi_model_manager.execute_task(
                    agent_role=self.agent_role,
                    task_prompt=reinforce_prompt,
                    task_type=self.get_specialized_task_type(),
                    complexity_level=complexity_level,
                    context={**context, 'reinforced': True} if context else {'reinforced': True},
                    model_override=selected_model,
                )
                exec_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                if not task_result.success:
                    raise RuntimeError(f"主笔人二次写作失败: {task_result.error_message}")
                metrics = self.extract_key_metrics(task_result.result)

            return AgentAnalysisResult(
                agent_role=self.agent_role,
                analysis_content=task_result.result,
                confidence_score=0.9 if metrics.get('sections_covered', 0) >= 6 else 0.75,
                key_points=[],
                risk_factors=[],
                recommendations=[],
                supporting_data=metrics,
                timestamp=start_time,
                model_used=task_result.model_used.name if task_result.model_used else 'gemini-2.5-pro',
                execution_time=exec_ms,
            )

        except Exception as e:
            exec_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.error(f"chief_writer 分析失败: {e}")
            return AgentAnalysisResult(
                agent_role=self.agent_role,
                analysis_content=f"写作失败: {str(e)}",
                confidence_score=0.0,
                key_points=[],
                risk_factors=["主笔人写作执行异常"],
                recommendations=[],
                supporting_data={},
                timestamp=start_time,
                model_used='unknown',
                execution_time=exec_ms,
            )


