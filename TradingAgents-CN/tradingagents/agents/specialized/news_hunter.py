"""
快讯猎手 (News Hunter)
专门负责实时新闻收集、筛选和快速分析的专业智能体
"""

from typing import Dict, Any, List
import re
from datetime import datetime, timedelta

from .base_specialized_agent import BaseSpecializedAgent, AgentAnalysisResult

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger
logger = get_logger('news_hunter')


class NewsHunter(BaseSpecializedAgent):
    """快讯猎手智能体"""
    
    def __init__(self, multi_model_manager, config: Dict[str, Any] = None):
        super().__init__(
            agent_role="news_hunter",
            description="实时新闻和快讯收集分析专家，专注于快速识别市场相关的重要信息",
            multi_model_manager=multi_model_manager,
            config=config
        )
        
        # 新闻重要性关键词权重
        self.importance_keywords = {
            'critical': ['突发', '紧急', '重大', '暴跌', '暴涨', 'breaking', 'urgent', 'major'],
            'high': ['公告', '利好', '利空', '监管', '政策', 'announcement', 'policy', 'regulation'],
            'medium': ['业绩', '财报', '合作', '投资', 'earnings', 'partnership', 'investment'],
            'low': ['传言', '市场', '分析师', 'rumor', 'analyst', 'opinion']
        }
        
        # 情绪识别关键词
        self.sentiment_keywords = {
            'positive': ['利好', '上涨', '增长', '突破', '看好', 'positive', 'bullish', 'growth'],
            'negative': ['利空', '下跌', '下降', '风险', '担忧', 'negative', 'bearish', 'decline'],
            'neutral': ['持平', '稳定', '维持', 'stable', 'neutral', 'unchanged']
        }
    
    def _build_system_prompt_template(self) -> str:
        """构建系统提示词模板"""
        return """你是一名专业的快讯猎手和新闻分析师，具备以下核心能力：

🔍 **核心职责**
- 快速筛选和识别重要的市场新闻
- 评估新闻对股票市场的潜在影响
- 提供及时的市场动态分析
- 识别新闻中的关键信息和情绪倾向

📊 **专业技能**
- 新闻时效性和重要性评估
- 市场情绪和投资者反应分析
- 事件驱动的股价影响预判
- 多信源信息交叉验证

⚡ **工作特点**
- 快速响应，高效处理
- 注重时效性和准确性
- 提供清晰的影响评估
- 识别潜在的投资机会和风险

你的分析应该客观、及时、准确，帮助投资者快速理解市场动态。"""
    
    def _build_analysis_prompt_template(self) -> str:
        """构建分析提示词模板"""
        return """请对提供的新闻信息进行专业的快讯分析，重点关注：

🎯 **分析重点**
1. 新闻的重要性和紧急程度
2. 对相关股票/行业的潜在影响
3. 市场情绪和投资者可能的反应
4. 时间敏感性和持续影响评估

📈 **影响评估**
- 短期影响（1-3天）
- 中期影响（1-4周）
- 长期影响（1-3月）

🚨 **风险提示**
- 信息真实性评估
- 潜在的市场风险
- 需要关注的后续发展"""
    
    def get_specialized_task_type(self) -> str:
        """获取专业化的任务类型"""
        return "news_analysis"
    
    def validate_input_data(self, data: Dict[str, Any]) -> bool:
        """验证输入数据"""
        required_fields = ['news_content']
        optional_fields = ['news_title', 'source', 'timestamp', 'related_symbols']
        
        # 检查必填字段
        for field in required_fields:
            if field not in data or not data[field]:
                logger.warning(f"缺少必填字段: {field}")
                return False
        
        # 检查新闻内容长度
        news_content = data['news_content']
        if len(news_content.strip()) < 10:
            logger.warning("新闻内容过短，可能不足以进行有效分析")
            return False
        
        return True
    
    def extract_key_metrics(self, analysis_result: str) -> Dict[str, Any]:
        """从分析结果中提取关键指标"""
        metrics = {
            'importance_score': 0.5,
            'sentiment_score': 0.0,
            'urgency_level': 'medium',
            'market_impact': 'unknown',
            'affected_sectors': [],
            'time_sensitivity': 'normal'
        }
        
        try:
            # 提取重要性评分
            importance_match = re.search(r'重要性[:：]\s*([0-9.]+)', analysis_result)
            if importance_match:
                metrics['importance_score'] = min(float(importance_match.group(1)), 1.0)
            
            # 提取情绪倾向
            if any(keyword in analysis_result for keyword in ['利好', '正面', '积极', 'positive']):
                metrics['sentiment_score'] = 0.6
            elif any(keyword in analysis_result for keyword in ['利空', '负面', '消极', 'negative']):
                metrics['sentiment_score'] = -0.6
            
            # 提取紧急程度
            if any(keyword in analysis_result for keyword in ['紧急', '突发', 'urgent', 'breaking']):
                metrics['urgency_level'] = 'high'
            elif any(keyword in analysis_result for keyword in ['一般', 'normal']):
                metrics['urgency_level'] = 'medium'
            elif any(keyword in analysis_result for keyword in ['低', 'low']):
                metrics['urgency_level'] = 'low'
            
            # 提取市场影响程度
            if any(keyword in analysis_result for keyword in ['重大影响', 'major impact']):
                metrics['market_impact'] = 'high'
            elif any(keyword in analysis_result for keyword in ['中等影响', 'moderate impact']):
                metrics['market_impact'] = 'medium'
            elif any(keyword in analysis_result for keyword in ['轻微影响', 'minor impact']):
                metrics['market_impact'] = 'low'
            
        except Exception as e:
            logger.warning(f"指标提取失败: {e}")
        
        return metrics
    
    def analyze_news_batch(self, 
                          news_list: List[Dict[str, Any]],
                          context: Dict[str, Any] = None) -> List[AgentAnalysisResult]:
        """批量分析新闻"""
        results = []
        
        for news_item in news_list:
            try:
                result = self.analyze(news_item, context)
                results.append(result)
            except Exception as e:
                logger.error(f"批量新闻分析失败: {e}")
                # 创建失败结果
                failed_result = AgentAnalysisResult(
                    agent_role=self.agent_role,
                    analysis_content=f"分析失败: {str(e)}",
                    confidence_score=0.0,
                    key_points=[],
                    risk_factors=[f"分析异常: {str(e)}"],
                    recommendations=[],
                    supporting_data={},
                    timestamp=datetime.now(),
                    model_used='unknown',
                    execution_time=0
                )
                results.append(failed_result)
        
        return results
    
    def filter_important_news(self, 
                            news_list: List[Dict[str, Any]],
                            importance_threshold: float = 0.6) -> List[Dict[str, Any]]:
        """筛选重要新闻"""
        important_news = []
        
        for news_item in news_list:
            importance_score = self._calculate_news_importance(news_item)
            if importance_score >= importance_threshold:
                news_item['calculated_importance'] = importance_score
                important_news.append(news_item)
        
        # 按重要性排序
        important_news.sort(key=lambda x: x['calculated_importance'], reverse=True)
        
        return important_news
    
    def _calculate_news_importance(self, news_item: Dict[str, Any]) -> float:
        """计算新闻重要性分数"""
        content = news_item.get('news_content', '') + ' ' + news_item.get('news_title', '')
        content_lower = content.lower()
        
        importance_score = 0.3  # 基础分数
        
        # 关键词权重计算
        for level, keywords in self.importance_keywords.items():
            keyword_count = sum(1 for keyword in keywords if keyword in content_lower)
            
            if level == 'critical':
                importance_score += keyword_count * 0.3
            elif level == 'high':
                importance_score += keyword_count * 0.2
            elif level == 'medium':
                importance_score += keyword_count * 0.1
            elif level == 'low':
                importance_score += keyword_count * 0.05
        
        # 时效性加权
        if 'timestamp' in news_item:
            try:
                news_time = datetime.fromisoformat(news_item['timestamp'].replace('Z', '+00:00'))
                time_diff = datetime.now() - news_time.replace(tzinfo=None)
                
                if time_diff < timedelta(minutes=30):
                    importance_score += 0.2  # 30分钟内的新闻加权
                elif time_diff < timedelta(hours=2):
                    importance_score += 0.1  # 2小时内的新闻加权
            except Exception:
                pass
        
        # 来源可信度加权
        source = news_item.get('source', '').lower()
        trusted_sources = ['reuters', 'bloomberg', '新华社', '央视', 'cnbc']
        if any(trusted_source in source for trusted_source in trusted_sources):
            importance_score += 0.1
        
        return min(importance_score, 1.0)
    
    def get_sentiment_distribution(self, news_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """获取新闻情绪分布"""
        sentiment_counts = {'positive': 0, 'negative': 0, 'neutral': 0}
        total_news = len(news_list)
        
        if total_news == 0:
            return sentiment_counts
        
        for news_item in news_list:
            sentiment = self._detect_news_sentiment(news_item)
            sentiment_counts[sentiment] += 1
        
        # 计算百分比
        sentiment_distribution = {
            sentiment: (count / total_news) * 100
            for sentiment, count in sentiment_counts.items()
        }
        
        sentiment_distribution['total_analyzed'] = total_news
        sentiment_distribution['overall_sentiment'] = self._calculate_overall_sentiment(sentiment_distribution)
        
        return sentiment_distribution
    
    def _detect_news_sentiment(self, news_item: Dict[str, Any]) -> str:
        """检测新闻情绪"""
        content = news_item.get('news_content', '') + ' ' + news_item.get('news_title', '')
        content_lower = content.lower()
        
        positive_score = sum(1 for keyword in self.sentiment_keywords['positive'] if keyword in content_lower)
        negative_score = sum(1 for keyword in self.sentiment_keywords['negative'] if keyword in content_lower)
        neutral_score = sum(1 for keyword in self.sentiment_keywords['neutral'] if keyword in content_lower)
        
        if positive_score > negative_score and positive_score > neutral_score:
            return 'positive'
        elif negative_score > positive_score and negative_score > neutral_score:
            return 'negative'
        else:
            return 'neutral'
    
    def _calculate_overall_sentiment(self, sentiment_distribution: Dict[str, float]) -> str:
        """计算整体情绪倾向"""
        positive_pct = sentiment_distribution.get('positive', 0)
        negative_pct = sentiment_distribution.get('negative', 0)
        
        if positive_pct > negative_pct + 10:
            return 'bullish'
        elif negative_pct > positive_pct + 10:
            return 'bearish'
        else:
            return 'neutral'
    
    def generate_news_summary(self, 
                            news_analyses: List[AgentAnalysisResult],
                            max_items: int = 5) -> str:
        """生成新闻摘要"""
        if not news_analyses:
            return "暂无重要新闻分析结果"
        
        # 按置信度排序并取前N条
        sorted_analyses = sorted(news_analyses, 
                               key=lambda x: x.confidence_score, 
                               reverse=True)[:max_items]
        
        summary = "📰 **重要新闻摘要**\n\n"
        
        for i, analysis in enumerate(sorted_analyses, 1):
            summary += f"**{i}. {analysis.agent_role}分析**\n"
            summary += f"置信度: {analysis.confidence_score:.2f}\n"
            
            if analysis.key_points:
                summary += f"关键点: {'; '.join(analysis.key_points[:2])}\n"
            
            if analysis.recommendations:
                summary += f"建议: {analysis.recommendations[0]}\n"
            
            summary += "---\n"
        
        return summary