"""
基本面专家 (Fundamental Expert)
专门负责公司基本面分析的专业智能体，包括财务分析、估值分析等
"""

from typing import Dict, Any, List
import re
from datetime import datetime
import json

from .base_specialized_agent import BaseSpecializedAgent, AgentAnalysisResult

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger
logger = get_logger('fundamental_expert')


class FundamentalExpert(BaseSpecializedAgent):
    """基本面专家智能体"""
    
    def __init__(self, multi_model_manager, config: Dict[str, Any] = None):
        super().__init__(
            agent_role="fundamental_expert",
            description="公司基本面分析专家，专注于财务分析、估值模型和企业价值评估",
            multi_model_manager=multi_model_manager,
            config=config
        )
        
        # 关键财务指标
        self.key_financial_metrics = {
            'profitability': ['ROE', 'ROA', 'ROIC', '净利润率', '毛利率'],
            'growth': ['营收增长率', '净利润增长率', 'EPS增长率', '自由现金流增长'],
            'valuation': ['PE', 'PB', 'PS', 'PEG', 'EV/EBITDA'],
            'debt': ['资产负债率', '流动比率', '速动比率', '利息覆盖倍数'],
            'efficiency': ['存货周转率', '应收账款周转率', '总资产周转率']
        }
        
        # 行业基准数据（示例）
        self.industry_benchmarks = {
            '科技': {'PE': 25, 'PB': 3.5, 'ROE': 0.15, '净利润率': 0.12},
            '金融': {'PE': 8, 'PB': 0.9, 'ROE': 0.12, '净利润率': 0.20},
            '制造业': {'PE': 15, 'PB': 1.8, 'ROE': 0.10, '净利润率': 0.08},
            '消费': {'PE': 20, 'PB': 2.5, 'ROE': 0.18, '净利润率': 0.10},
            '医药': {'PE': 30, 'PB': 4.0, 'ROE': 0.12, '净利润率': 0.15}
        }
    
    def _build_system_prompt_template(self) -> str:
        """构建系统提示词模板"""
        return """你是一名资深的基本面分析专家，拥有深厚的财务分析和估值建模经验：

💼 **专业背景**
- 10年以上财务分析经验
- CFA持证人，具备国际先进的分析方法
- 擅长多种估值模型（DCF、DDM、PE/PB相对估值等）
- 熟悉各行业特点和估值标准

📊 **核心能力**
- 财务报表深度分析
- 盈利能力和成长性评估
- 估值模型构建和应用
- 行业比较和竞争分析
- 风险因子识别和量化

🔍 **分析框架**
1. 财务健康状况评估
2. 盈利能力和效率分析
3. 成长性和可持续性评估
4. 估值水平和投资价值判断
5. 风险因素识别和影响评估

你的分析应该基于扎实的财务数据，运用科学的分析方法，提供客观专业的投资建议。"""
    
    def _build_analysis_prompt_template(self) -> str:
        """构建分析提示词模板"""
        return """请对提供的公司进行全面的基本面分析，重点关注：

📈 **财务分析重点**
1. 盈利能力分析（ROE、ROA、净利润率等）
2. 成长性分析（营收、利润、现金流增长）
3. 财务稳健性（负债结构、现金流、偿债能力）
4. 运营效率（周转率、资产利用效率）

💰 **估值分析**
- 绝对估值法（DCF现金流折现）
- 相对估值法（PE、PB、PS等倍数比较）
- 行业估值水平比较
- 内在价值vs市场价格分析

⚖️ **投资价值评估**
- 投资亮点和竞争优势
- 主要风险和挑战
- 合理价值区间预测
- 投资建议和策略"""
    
    def get_specialized_task_type(self) -> str:
        """获取专业化的任务类型"""
        return "fundamental_analysis"
    
    def validate_input_data(self, data: Dict[str, Any]) -> bool:
        """验证输入数据"""
        required_fields = ['company_name']
        financial_data_fields = ['financial_data', 'balance_sheet', 'income_statement', 'cash_flow']
        
        # 检查必填字段
        for field in required_fields:
            if field not in data or not data[field]:
                logger.warning(f"缺少必填字段: {field}")
                return False
        
        # 检查是否有财务数据
        has_financial_data = any(field in data and data[field] for field in financial_data_fields)
        if not has_financial_data:
            logger.warning("缺少财务数据，无法进行基本面分析")
            return False
        
        return True
    
    def extract_key_metrics(self, analysis_result: str) -> Dict[str, Any]:
        """从分析结果中提取关键指标"""
        metrics = {
            'valuation_score': 0.5,
            'growth_score': 0.5,
            'profitability_score': 0.5,
            'debt_score': 0.5,
            'overall_score': 0.5,
            'fair_value_estimate': None,
            'investment_rating': 'HOLD',
            'key_risks': [],
            'key_strengths': []
        }
        
        try:
            # 提取估值评分
            valuation_match = re.search(r'估值评分[:：]\s*([0-9.]+)', analysis_result)
            if valuation_match:
                metrics['valuation_score'] = min(float(valuation_match.group(1)), 1.0)
            
            # 提取成长性评分
            growth_match = re.search(r'成长性评分[:：]\s*([0-9.]+)', analysis_result)
            if growth_match:
                metrics['growth_score'] = min(float(growth_match.group(1)), 1.0)
            
            # 提取盈利能力评分
            profit_match = re.search(r'盈利能力评分[:：]\s*([0-9.]+)', analysis_result)
            if profit_match:
                metrics['profitability_score'] = min(float(profit_match.group(1)), 1.0)
            
            # 提取公允价值估计
            fair_value_match = re.search(r'公允价值[:：]\s*([0-9.]+)', analysis_result)
            if fair_value_match:
                metrics['fair_value_estimate'] = float(fair_value_match.group(1))
            
            # 提取投资评级
            if any(keyword in analysis_result for keyword in ['强烈买入', 'STRONG BUY']):
                metrics['investment_rating'] = 'STRONG_BUY'
            elif any(keyword in analysis_result for keyword in ['买入', 'BUY']):
                metrics['investment_rating'] = 'BUY'
            elif any(keyword in analysis_result for keyword in ['持有', 'HOLD']):
                metrics['investment_rating'] = 'HOLD'
            elif any(keyword in analysis_result for keyword in ['卖出', 'SELL']):
                metrics['investment_rating'] = 'SELL'
            
            # 计算综合评分
            metrics['overall_score'] = (
                metrics['valuation_score'] * 0.3 +
                metrics['growth_score'] * 0.25 +
                metrics['profitability_score'] * 0.25 +
                metrics['debt_score'] * 0.2
            )
            
        except Exception as e:
            logger.warning(f"指标提取失败: {e}")
        
        return metrics
    
    def calculate_financial_ratios(self, financial_data: Dict[str, Any]) -> Dict[str, float]:
        """计算关键财务比率"""
        ratios = {}
        
        try:
            # 从财务数据中提取基础数据
            revenue = financial_data.get('revenue', 0)
            net_income = financial_data.get('net_income', 0)
            total_assets = financial_data.get('total_assets', 0)
            shareholders_equity = financial_data.get('shareholders_equity', 0)
            total_debt = financial_data.get('total_debt', 0)
            market_cap = financial_data.get('market_cap', 0)
            
            # 计算盈利能力比率
            if total_assets > 0:
                ratios['ROA'] = net_income / total_assets
            
            if shareholders_equity > 0:
                ratios['ROE'] = net_income / shareholders_equity
            
            if revenue > 0:
                ratios['net_margin'] = net_income / revenue
            
            # 计算估值比率
            if net_income > 0 and market_cap > 0:
                ratios['PE'] = market_cap / net_income
            
            if shareholders_equity > 0 and market_cap > 0:
                ratios['PB'] = market_cap / shareholders_equity
            
            # 计算负债比率
            if total_assets > 0:
                ratios['debt_to_assets'] = total_debt / total_assets
            
            if shareholders_equity > 0:
                ratios['debt_to_equity'] = total_debt / shareholders_equity
            
        except Exception as e:
            logger.error(f"财务比率计算失败: {e}")
        
        return ratios
    
    def compare_with_industry(self, 
                            company_ratios: Dict[str, float],
                            industry: str) -> Dict[str, Any]:
        """与行业基准比较"""
        comparison = {
            'industry': industry,
            'above_average': [],
            'below_average': [],
            'industry_percentile': {}
        }
        
        if industry not in self.industry_benchmarks:
            return comparison
        
        benchmarks = self.industry_benchmarks[industry]
        
        for metric, company_value in company_ratios.items():
            if metric in benchmarks:
                benchmark_value = benchmarks[metric]
                
                # 计算相对表现
                if metric in ['PE']:  # 对于PE，越低越好（在合理范围内）
                    if company_value < benchmark_value * 0.8:
                        comparison['above_average'].append(f"{metric}: {company_value:.2f} vs 行业{benchmark_value}")
                    elif company_value > benchmark_value * 1.2:
                        comparison['below_average'].append(f"{metric}: {company_value:.2f} vs 行业{benchmark_value}")
                else:  # 对于ROE、净利润率等，越高越好
                    if company_value > benchmark_value * 1.1:
                        comparison['above_average'].append(f"{metric}: {company_value:.2f} vs 行业{benchmark_value}")
                    elif company_value < benchmark_value * 0.9:
                        comparison['below_average'].append(f"{metric}: {company_value:.2f} vs 行业{benchmark_value}")
                
                # 计算百分位数（简化版）
                ratio = company_value / benchmark_value if benchmark_value != 0 else 1
                if metric in ['PE']:
                    percentile = max(0, min(100, 100 - (ratio - 1) * 50))
                else:
                    percentile = max(0, min(100, 50 + (ratio - 1) * 50))
                
                comparison['industry_percentile'][metric] = percentile
        
        return comparison
    
    def perform_dcf_analysis(self, 
                           financial_data: Dict[str, Any],
                           growth_assumptions: Dict[str, float] = None) -> Dict[str, Any]:
        """执行DCF现金流折现分析"""
        if not growth_assumptions:
            growth_assumptions = {
                'revenue_growth': 0.05,  # 5%收入增长
                'margin_improvement': 0.0,  # 利润率保持稳定
                'capex_ratio': 0.03,  # 资本支出占收入3%
                'discount_rate': 0.10,  # 10%折现率
                'terminal_growth': 0.02  # 2%永续增长率
            }
        
        dcf_result = {
            'fair_value_per_share': 0,
            'upside_downside': 0,
            'sensitivity_analysis': {},
            'key_assumptions': growth_assumptions
        }
        
        try:
            # 获取基础财务数据
            revenue = financial_data.get('revenue', 0)
            net_income = financial_data.get('net_income', 0)
            shares_outstanding = financial_data.get('shares_outstanding', 1)
            current_price = financial_data.get('current_price', 0)
            
            if revenue == 0 or shares_outstanding == 0:
                logger.warning("DCF分析所需的基础数据不足")
                return dcf_result
            
            # 简化的DCF计算（5年预测期）
            projection_years = 5
            projected_fcf = []
            
            for year in range(1, projection_years + 1):
                # 预测收入
                projected_revenue = revenue * ((1 + growth_assumptions['revenue_growth']) ** year)
                
                # 预测净利润率
                current_margin = net_income / revenue if revenue > 0 else 0
                projected_margin = current_margin + (growth_assumptions.get('margin_improvement', 0) * year)
                
                # 预测自由现金流（简化）
                projected_net_income = projected_revenue * projected_margin
                capex = projected_revenue * growth_assumptions['capex_ratio']
                projected_fcf_year = projected_net_income - capex
                
                # 折现到现值
                discount_factor = (1 + growth_assumptions['discount_rate']) ** year
                present_value = projected_fcf_year / discount_factor
                projected_fcf.append(present_value)
            
            # 计算终值
            terminal_fcf = projected_fcf[-1] * (1 + growth_assumptions['terminal_growth'])
            terminal_value = terminal_fcf / (growth_assumptions['discount_rate'] - growth_assumptions['terminal_growth'])
            terminal_pv = terminal_value / ((1 + growth_assumptions['discount_rate']) ** projection_years)
            
            # 计算企业价值和每股价值
            enterprise_value = sum(projected_fcf) + terminal_pv
            fair_value_per_share = enterprise_value / shares_outstanding
            
            dcf_result['fair_value_per_share'] = fair_value_per_share
            
            # 计算上涨/下跌空间
            if current_price > 0:
                dcf_result['upside_downside'] = (fair_value_per_share - current_price) / current_price
            
            # 敏感性分析
            dcf_result['sensitivity_analysis'] = self._perform_sensitivity_analysis(
                financial_data, growth_assumptions
            )
            
        except Exception as e:
            logger.error(f"DCF分析计算失败: {e}")
        
        return dcf_result
    
    def _perform_sensitivity_analysis(self,
                                    financial_data: Dict[str, Any],
                                    base_assumptions: Dict[str, float]) -> Dict[str, Any]:
        """执行敏感性分析"""
        sensitivity = {}
        
        # 关键假设的敏感性分析
        key_variables = ['revenue_growth', 'discount_rate']
        
        for variable in key_variables:
            sensitivity[variable] = {}
            base_value = base_assumptions[variable]
            
            # 测试+/- 1%, 2%的情况
            for change in [-0.02, -0.01, 0.01, 0.02]:
                modified_assumptions = base_assumptions.copy()
                modified_assumptions[variable] = base_value + change
                
                # 重新计算DCF（简化版）
                modified_result = self.perform_dcf_analysis(financial_data, modified_assumptions)
                fair_value = modified_result['fair_value_per_share']
                
                sensitivity[variable][f"{change:+.1%}"] = fair_value
        
        return sensitivity
    
    def generate_investment_thesis(self, analysis_result: AgentAnalysisResult) -> str:
        """生成投资论点摘要"""
        thesis = f"## {analysis_result.agent_role} - 投资论点\n\n"
        
        # 投资亮点
        if analysis_result.key_points:
            thesis += "### 💡 投资亮点\n"
            for point in analysis_result.key_points[:3]:
                thesis += f"- {point}\n"
            thesis += "\n"
        
        # 主要风险
        if analysis_result.risk_factors:
            thesis += "### ⚠️ 主要风险\n"
            for risk in analysis_result.risk_factors[:3]:
                thesis += f"- {risk}\n"
            thesis += "\n"
        
        # 投资建议
        if analysis_result.recommendations:
            thesis += "### 📊 投资建议\n"
            for rec in analysis_result.recommendations[:2]:
                thesis += f"- {rec}\n"
            thesis += "\n"
        
        # 置信度和评级
        confidence = analysis_result.confidence_score
        if confidence >= 0.8:
            rating = "高信心推荐"
        elif confidence >= 0.6:
            rating = "中等信心推荐"
        else:
            rating = "低信心，需谨慎"
        
        thesis += f"**分析师信心度**: {confidence:.1%} ({rating})\n"
        thesis += f"**使用模型**: {analysis_result.model_used}\n"
        
        return thesis