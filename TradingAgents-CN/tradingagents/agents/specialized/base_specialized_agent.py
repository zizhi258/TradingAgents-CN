"""
Base Specialized Agent
专业智能体基类，为9个专业角色提供统一的接口和功能
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import json

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger


@dataclass
class AgentAnalysisResult:
    """智能体分析结果"""
    agent_role: str
    analysis_content: str
    confidence_score: float
    key_points: List[str]
    risk_factors: List[str]
    recommendations: List[str]
    supporting_data: Dict[str, Any]
    timestamp: datetime
    model_used: str
    execution_time: int  # milliseconds
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'agent_role': self.agent_role,
            'analysis_content': self.analysis_content,
            'confidence_score': self.confidence_score,
            'key_points': self.key_points,
            'risk_factors': self.risk_factors,
            'recommendations': self.recommendations,
            'supporting_data': self.supporting_data,
            'timestamp': self.timestamp.isoformat(),
            'model_used': self.model_used,
            'execution_time': self.execution_time
        }


class BaseSpecializedAgent(ABC):
    """专业智能体基类"""
    
    def __init__(self, 
                 agent_role: str,
                 description: str,
                 multi_model_manager,
                 config: Dict[str, Any] = None):
        """
        初始化专业智能体
        
        Args:
            agent_role: 智能体角色名称
            description: 智能体描述
            multi_model_manager: 多模型管理器实例
            config: 配置参数
        """
        self.agent_role = agent_role
        self.description = description
        self.multi_model_manager = multi_model_manager
        self.config = config or {}
        
        # 智能体专用的提示词模板
        self.system_prompt_template = self._build_system_prompt_template()
        self.analysis_prompt_template = self._build_analysis_prompt_template()
        
        # 性能统计
        self.total_analyses = 0
        self.successful_analyses = 0
        self.average_confidence = 0.0
        
        # 日志记录器
        self.logger = get_logger(f'agent_{agent_role}')
        self.logger.info(f"{agent_role} 智能体初始化完成")
    
    @abstractmethod
    def _build_system_prompt_template(self) -> str:
        """构建系统提示词模板，子类必须实现"""
        pass
    
    @abstractmethod
    def _build_analysis_prompt_template(self) -> str:
        """构建分析提示词模板，子类必须实现"""
        pass
    
    @abstractmethod
    def get_specialized_task_type(self) -> str:
        """获取专业化的任务类型，子类必须实现"""
        pass
    
    @abstractmethod
    def validate_input_data(self, data: Dict[str, Any]) -> bool:
        """验证输入数据，子类必须实现"""
        pass
    
    @abstractmethod
    def extract_key_metrics(self, analysis_result: str) -> Dict[str, Any]:
        """从分析结果中提取关键指标，子类必须实现"""
        pass
    
    def analyze(self, 
                input_data: Dict[str, Any],
                context: Dict[str, Any] = None,
                complexity_level: str = "medium") -> AgentAnalysisResult:
        """
        执行专业分析
        
        Args:
            input_data: 输入数据
            context: 上下文信息
            complexity_level: 复杂度级别
            
        Returns:
            AgentAnalysisResult: 分析结果
        """
        start_time = datetime.now()
        context = context or {}
        
        try:
            # 验证输入数据
            if not self.validate_input_data(input_data):
                raise ValueError(f"{self.agent_role} 输入数据验证失败")
            
            # 构建分析提示词
            analysis_prompt = self._build_full_analysis_prompt(input_data, context)
            
            # 执行分析任务
            task_result = self.multi_model_manager.execute_task(
                agent_role=self.agent_role,
                task_prompt=analysis_prompt,
                task_type=self.get_specialized_task_type(),
                complexity_level=complexity_level,
                context=context
            )
            
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            if not task_result.success:
                raise RuntimeError(f"分析执行失败: {task_result.error_message}")
            
            # 解析分析结果
            parsed_result = self._parse_analysis_result(task_result.result)
            
            # 提取关键指标
            key_metrics = self.extract_key_metrics(task_result.result)
            
            # 构建结果对象
            analysis_result = AgentAnalysisResult(
                agent_role=self.agent_role,
                analysis_content=task_result.result,
                confidence_score=self._calculate_confidence_score(parsed_result, key_metrics),
                key_points=parsed_result.get('key_points', []),
                risk_factors=parsed_result.get('risk_factors', []),
                recommendations=parsed_result.get('recommendations', []),
                supporting_data=key_metrics,
                timestamp=start_time,
                model_used=task_result.model_used.name if task_result.model_used else 'unknown',
                execution_time=execution_time
            )
            
            # 更新性能统计
            self._update_performance_stats(analysis_result.confidence_score, True)
            
            self.logger.info(f"分析完成: {self.agent_role}, 置信度: {analysis_result.confidence_score:.3f}")
            
            return analysis_result
            
        except Exception as e:
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            self.logger.error(f"{self.agent_role} 分析失败: {e}", exc_info=True)
            
            # 更新性能统计
            self._update_performance_stats(0.0, False)
            
            return AgentAnalysisResult(
                agent_role=self.agent_role,
                analysis_content=f"分析失败: {str(e)}",
                confidence_score=0.0,
                key_points=[],
                risk_factors=[f"分析执行异常: {str(e)}"],
                recommendations=[],
                supporting_data={},
                timestamp=start_time,
                model_used='unknown',
                execution_time=execution_time
            )
    
    def _build_full_analysis_prompt(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """构建完整的分析提示词"""
        # 系统角色设定
        full_prompt = f"{self.system_prompt_template}\n\n"
        
        # 分析任务指令
        full_prompt += f"{self.analysis_prompt_template}\n\n"
        
        # 输入数据
        full_prompt += "=== 分析数据 ===\n"
        for key, value in input_data.items():
            if isinstance(value, (dict, list)):
                full_prompt += f"{key}: {json.dumps(value, ensure_ascii=False, indent=2)}\n"
            else:
                full_prompt += f"{key}: {value}\n"
        
        # 上下文信息
        if context:
            full_prompt += "\n=== 上下文信息 ===\n"
            for key, value in context.items():
                if key not in ['session_id', 'model_params']:  # 过滤内部参数
                    full_prompt += f"{key}: {value}\n"
        
        # 输出格式要求
        full_prompt += self._get_output_format_instruction()
        
        return full_prompt
    
    def _get_output_format_instruction(self) -> str:
        """获取输出格式指令"""
        return """
=== 输出要求 ===
请按以下结构化格式输出分析结果：

## 核心观点
[列出3-5个核心观点]

## 详细分析
[提供详细的专业分析]

## 风险因素
[识别并列出相关风险]

## 投资建议
[基于分析给出具体建议]

## 置信度评估
[说明分析的可信度和依据]

请确保分析客观、专业，基于数据和逻辑推理。
"""
    
    def _parse_analysis_result(self, result_text: str) -> Dict[str, Any]:
        """解析分析结果文本，提取结构化信息"""
        parsed = {
            'key_points': [],
            'risk_factors': [],
            'recommendations': [],
            'confidence_explanation': ''
        }
        
        try:
            lines = result_text.split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 识别章节标题
                if line.startswith('## 核心观点') or 'core' in line.lower() and 'point' in line.lower():
                    current_section = 'key_points'
                elif line.startswith('## 风险因素') or 'risk' in line.lower():
                    current_section = 'risk_factors'
                elif line.startswith('## 投资建议') or line.startswith('## 建议') or 'recommend' in line.lower():
                    current_section = 'recommendations'
                elif line.startswith('## 置信度') or 'confidence' in line.lower():
                    current_section = 'confidence_explanation'
                elif line.startswith('##'):
                    current_section = None
                
                # 提取内容
                elif current_section and line.startswith(('- ', '• ', '1. ', '2. ', '3. ')):
                    content = line.lstrip('- •123456789. ').strip()
                    if content:
                        parsed[current_section].append(content)
                elif current_section == 'confidence_explanation' and not line.startswith('#'):
                    parsed[current_section] += line + ' '
        
        except Exception as e:
            self.logger.warning(f"解析分析结果失败: {e}")
        
        return parsed
    
    def _calculate_confidence_score(self, parsed_result: Dict[str, Any], metrics: Dict[str, Any]) -> float:
        """计算置信度评分"""
        base_score = 0.7  # 基础分数
        
        # 根据关键点数量调整
        key_points_count = len(parsed_result.get('key_points', []))
        if key_points_count >= 3:
            base_score += 0.1
        elif key_points_count < 2:
            base_score -= 0.1
        
        # 根据风险识别调整
        risk_factors_count = len(parsed_result.get('risk_factors', []))
        if risk_factors_count > 0:
            base_score += 0.05  # 识别风险是好事
        
        # 根据建议数量调整
        recommendations_count = len(parsed_result.get('recommendations', []))
        if recommendations_count >= 2:
            base_score += 0.1
        elif recommendations_count == 0:
            base_score -= 0.15
        
        # 根据数据完整性调整
        if metrics:
            data_completeness = len(metrics) / 10.0  # 假设10个指标为满分
            base_score += min(data_completeness * 0.1, 0.1)
        
        # 确保分数在合理范围内
        return max(0.1, min(base_score, 0.95))
    
    def _update_performance_stats(self, confidence_score: float, success: bool) -> None:
        """更新性能统计"""
        self.total_analyses += 1
        
        if success:
            self.successful_analyses += 1
            # 更新平均置信度
            self.average_confidence = (
                (self.average_confidence * (self.successful_analyses - 1) + confidence_score)
                / self.successful_analyses
            )
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        success_rate = self.successful_analyses / self.total_analyses if self.total_analyses > 0 else 0
        
        return {
            'agent_role': self.agent_role,
            'total_analyses': self.total_analyses,
            'successful_analyses': self.successful_analyses,
            'success_rate': success_rate,
            'average_confidence': self.average_confidence,
            'performance_grade': self._calculate_performance_grade(success_rate, self.average_confidence)
        }
    
    def _calculate_performance_grade(self, success_rate: float, avg_confidence: float) -> str:
        """计算性能等级"""
        overall_score = (success_rate * 0.6 + avg_confidence * 0.4)
        
        if overall_score >= 0.9:
            return 'A+'
        elif overall_score >= 0.8:
            return 'A'
        elif overall_score >= 0.7:
            return 'B+'
        elif overall_score >= 0.6:
            return 'B'
        elif overall_score >= 0.5:
            return 'C'
        else:
            return 'D'
    
    def __str__(self) -> str:
        return f"{self.agent_role}: {self.description}"
    
    def __repr__(self) -> str:
        return f"BaseSpecializedAgent(role='{self.agent_role}', analyses={self.total_analyses})"