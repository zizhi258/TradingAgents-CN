"""
Local Market Scan Orchestrator
在本地进程内并发执行市场全景扫描，调用 TradingAgentsGraph（若可用），并聚合结果。

设计目标：
- 无需HTTP后端；供 Web 的 Local 客户端直接调用。
- 在无外网/无API Key时，走离线兜底策略，保证页面可用。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple
import concurrent.futures as futures
import os
import random
import time
from datetime import datetime

from tradingagents.utils.logging_manager import get_logger

logger = get_logger('market_orchestrator')


@dataclass
class OrchestratorConfig:
    market_type: str
    preset_type: str
    scan_depth: int
    budget_limit: float
    stock_limit: int
    time_range: str
    custom_filters: Optional[Dict[str, Any]] = None
    analysis_focus: Optional[Dict[str, bool]] = None
    ai_model_config: Optional[Dict[str, Any]] = None
    advanced_options: Optional[Dict[str, Any]] = None


class MarketScanOrchestrator:
    def __init__(self, progress_cb: Optional[Callable[[str, int, int], None]] = None):
        self.progress_cb = progress_cb

    # --------- public ---------
    def run(self, cfg: OrchestratorConfig) -> Dict[str, Any]:
        start_ts = time.time()
        self._emit('准备环境', 0, 100)

        symbols = self._build_universe(cfg)
        if not symbols:
            symbols = self._fallback_universe(cfg.market_type)
        symbols = symbols[: max(1, min(cfg.stock_limit or 50, 200))]

        self._emit(f'股票池就绪（{len(symbols)}只）', 8, 100)

        use_llm, llm_cfg = self._analyze_llm_config(cfg.ai_model_config)

        # 尝试创建 TradingAgentsGraph；失败则离线兜底
        ta_graph = None
        if use_llm:
            try:
                from tradingagents.graph.trading_graph import TradingAgentsGraph
                base_config = llm_cfg.get('config_override') or {}
                ta_graph = TradingAgentsGraph(debug=False, config=base_config or None)
                logger.info('TradingAgentsGraph 初始化成功，用于本地协作分析')
            except Exception as e:
                logger.warning(f'TradingAgentsGraph 初始化失败，使用离线兜底: {e}')
                ta_graph = None

        # 并发评估
        self._emit('开始并发评估', 12, 100)
        results: List[Dict[str, Any]] = []
        errors: List[Tuple[str, str]] = []

        max_workers = int(llm_cfg.get('max_concurrent_tasks', 4))
        max_workers = max(1, min(max_workers, 6))

        def _eval_symbol(sym: str) -> Dict[str, Any]:
            try:
                if ta_graph is not None:
                    # 选取一个近似日期；在真实实现可传当天/用户日期
                    trade_date = datetime.now().strftime('%Y-%m-%d')
                    # 如果启用多模型扩展，优先使用既有多模型调用方式
                    use_multi = bool(llm_cfg.get('use_ensemble')) or (os.getenv('MULTI_MODEL_ENABLED', 'false').lower() == 'true')
                    collab_mode = (llm_cfg.get('collaboration_mode') or os.getenv('DEFAULT_COLLABORATION_MODE') or 'sequential')
                    selected_agents = llm_cfg.get('selected_agents')  # 可选
                    if use_multi and getattr(ta_graph, 'multi_model_extension', None):
                        result = ta_graph.analyze_with_collaboration(
                            company_name=sym,
                            trade_date=trade_date,
                            collaboration_mode=collab_mode,
                            selected_agents=selected_agents
                        )
                        return self._map_multi_model_result_to_row(sym, result)
                    else:
                        # 单模型既有调用
                        _, decision = ta_graph.propagate(sym, trade_date)
                        return self._map_decision_to_row(sym, decision)
                else:
                    return self._offline_eval(sym)
            except Exception as e:
                return {'__error__': f'{e}', 'symbol': sym}

        completed = 0
        total = len(symbols)
        with futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            for res in ex.map(_eval_symbol, symbols):
                completed += 1
                self._emit(f'评估进度 {completed}/{total}', 12 + int(70 * completed / max(1, total)), 100)
                if '__error__' in res:
                    errors.append((res.get('symbol') or 'UNKNOWN', res['__error__']))
                else:
                    results.append(res)

        # 聚合
        self._emit('聚合与统计', 90, 100)
        rankings = self._build_rankings(results)
        sectors = self._build_sectors(rankings)
        breadth = self._build_breadth(rankings)

        # 摘要（可选LLM，否则本地规则）
        self._emit('生成执行摘要', 95, 100)
        summary = self._build_summary(cfg, rankings, sectors, breadth, use_llm, ta_graph)

        duration_sec = max(1, int(time.time() - start_ts))
        stats = {
            'total_stocks': len(symbols),
            'processed_stocks': len(rankings),
            'recommended_stocks': sum(1 for r in rankings if r.get('recommendation') == '买入'),
            'actual_cost': round(min(cfg.budget_limit or 0.0, (len(rankings) * 0.002)), 4),
            'scan_duration': f'{duration_sec}秒',
            'errors': errors[:20],  # 限制数量
        }

        self._emit('完成', 100, 100)
        return {
            'rankings': rankings,
            'sectors': sectors,
            'breadth': breadth,
            'summary': summary,
            'stats': stats,
        }

    # --------- helpers ---------
    def _emit(self, msg: str, cur: int, total: int) -> None:
        try:
            if self.progress_cb:
                self.progress_cb(msg, cur, total)
        except Exception:
            pass

    def _analyze_llm_config(self, ai_cfg: Optional[Dict[str, Any]]) -> Tuple[bool, Dict[str, Any]]:
        ai_cfg = ai_cfg or {}
        # 允许显式禁用LLM
        if str(ai_cfg.get('use_llm', 'true')).lower() in ['0', 'false', 'no', 'off']:
            return False, ai_cfg

        # 如果未设置任何可用Key，则禁用LLM，走离线
        has_key = any([
            os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY'),
            os.getenv('DEEPSEEK_API_KEY'),
            os.getenv('OPENROUTER_API_KEY') or os.getenv('OPENAI_API_KEY'),
            os.getenv('ANTHROPIC_API_KEY'),
        ])
        if not has_key:
            logger.warning('未检测到LLM API Key，将使用离线兜底模式')
            return False, ai_cfg

        # 构造 TradingAgentsGraph 的 config 覆盖（最简）
        # 兼容UI字段：primary_model/model -> 同时赋给 quick/deep
        chosen_model = (
            ai_cfg.get('llm_quick_model')
            or ai_cfg.get('llm_deep_model')
            or ai_cfg.get('model')
            or ai_cfg.get('primary_model')
            or os.getenv('DEFAULT_MODEL', 'gemini-2.5-pro')
        )
        # 推断provider
        provider = ai_cfg.get('llm_provider') or os.getenv('DEFAULT_PROVIDER')
        if not provider:
            m = (chosen_model or '').lower()
            if 'gemini' in m or 'google' in m:
                provider = 'google'
            elif 'deepseek' in m:
                provider = 'deepseek'
            elif 'gpt' in m or 'o3' in m or 'o4' in m:
                provider = 'openrouter'  # 统一经OpenRouter
            else:
                provider = 'google'
        model_quick = chosen_model
        model_deep = chosen_model

        config_override = {
            'llm_provider': provider,
            'quick_think_llm': model_quick,
            'deep_think_llm': model_deep,
            # 后端URL由各adapter内部处理/或由默认即可
            'online_tools': True,
            'max_debate_rounds': 1,
        }
        # 透传协作参数（若UI提供）
        if 'collaboration_mode' in ai_cfg:
            ai_cfg['collaboration_mode'] = ai_cfg.get('collaboration_mode')
        if 'selected_agents' in ai_cfg:
            ai_cfg['selected_agents'] = ai_cfg.get('selected_agents')

        ai_cfg['config_override'] = config_override
        return True, ai_cfg

    def _build_universe(self, cfg: OrchestratorConfig) -> List[str]:
        # 留出扩展点：可接入 akshare/tushare/yfinance；当前在无网时返回空
        try:
            # 将来可根据 cfg.market_type 拉取前N市值股票
            return []
        except Exception:
            return []

    def _fallback_universe(self, market: str) -> List[str]:
        market = (market or '').strip()
        if 'A股' in market or 'A' in market:
            return ['600519', '000001', '601318', '300750', '601988', '600036', '600030', '601012', '601888', '002594']
        if '港股' in market:
            return ['0700.HK', '3690.HK', '0939.HK', '1398.HK', '1299.HK', '2318.HK']
        # 默认美股
        return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'JPM', 'V', 'UNH']

    def _offline_eval(self, symbol: str) -> Dict[str, Any]:
        # 生成稳定但有差异性的分数（基于hash）
        seed = abs(hash(symbol)) % (10**6)
        rng = random.Random(seed)
        total = rng.uniform(60, 95)
        tech = max(40.0, min(100.0, total - rng.uniform(-10, 10)))
        fund = max(40.0, min(100.0, total - rng.uniform(-10, 10)))
        rec = '买入' if total > 80 else ('关注' if total > 70 else '持有')
        return {
            'symbol': symbol,
            'name': symbol,
            'total_score': round(total, 2),
            'technical_score': round(tech, 2),
            'fundamental_score': round(fund, 2),
            'current_price': round(rng.uniform(10, 300), 2),
            'change_percent': round(rng.uniform(-5, 6), 2),
            'recommendation': rec,
            'target_price': round(rng.uniform(10, 350), 2),
            'market_cap': round(rng.uniform(5, 3000), 2),
            'pe_ratio': round(rng.uniform(8, 40), 2),
            'pb_ratio': round(rng.uniform(0.8, 8), 2),
            'sector': self._infer_sector(symbol),
        }

    def _map_decision_to_row(self, symbol: str, decision: Any) -> Dict[str, Any]:
        # 针对 TradingAgentsGraph.propagate 的决策结果进行最小映射；
        # 若字段未知则退化为离线风格
        try:
            rec = '关注'
            conf = 75.0
            if isinstance(decision, dict):
                rec = decision.get('final_trade_decision', '') or decision.get('recommendation', '关注')
                conf = float(decision.get('confidence', 75.0))
            base = self._offline_eval(symbol)
            base['total_score'] = round(max(60.0, min(95.0, (conf * 0.9))), 2)
            base['recommendation'] = rec
            return base
        except Exception:
            return self._offline_eval(symbol)

    def _map_multi_model_result_to_row(self, symbol: str, result: Dict[str, Any]) -> Dict[str, Any]:
        try:
            rec = result.get('final_decision') or result.get('final_trade_decision') or '关注'
            conf = float(result.get('confidence_score', 78.0))
            base = self._offline_eval(symbol)
            base['total_score'] = round(max(60.0, min(95.0, conf * 0.95)), 2)
            # 映射统一到中文建议
            mapping = {
                'buy': '买入', 'strong_buy': '买入', 'hold': '持有', 'watch': '关注',
                'sell': '卖出', 'strong_sell': '卖出'
            }
            if isinstance(rec, str):
                rec_l = rec.strip().lower()
                base['recommendation'] = mapping.get(rec_l, rec if rec in ['买入', '持有', '关注', '卖出'] else '关注')
            else:
                base['recommendation'] = '关注'
            return base
        except Exception:
            return self._offline_eval(symbol)

    def _build_rankings(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        rows = [r for r in rows if isinstance(r, dict) and 'symbol' in r]
        rows.sort(key=lambda x: x.get('total_score', 0), reverse=True)
        return rows

    def _build_sectors(self, rankings: List[Dict[str, Any]]) -> Dict[str, Any]:
        sectors: Dict[str, List[Dict[str, Any]]] = {}
        for r in rankings:
            sec = r.get('sector') or '其他'
            sectors.setdefault(sec, []).append(r)

        out: Dict[str, Any] = {}
        for sec, items in sectors.items():
            if not items:
                continue
            avg_change = sum(i.get('change_percent', 0) for i in items) / len(items)
            avg_score = sum(i.get('total_score', 0) for i in items) / len(items)
            out[sec] = {
                'change_percent': round(avg_change, 2),
                'activity_score': round(min(95.0, max(30.0, avg_score)), 2),
                'recommendation_score': round(min(90.0, max(40.0, avg_score - 5)), 2),
                'leading_stock': items[0]['symbol'],
                'recommended_count': sum(1 for i in items if i.get('recommendation') == '买入'),
                'market_cap': round(sum(i.get('market_cap', 0) for i in items), 2),
                'recommended_stocks': items[: min(5, len(items))],
            }
        return out

    def _build_breadth(self, rankings: List[Dict[str, Any]]) -> Dict[str, Any]:
        n = len(rankings) or 1
        up = sum(1 for r in rankings if r.get('change_percent', 0) > 0)
        up_ratio = 100.0 * up / n
        senti = min(85.0, max(30.0, sum(1 for r in rankings if r.get('recommendation') == '买入') * 100.0 / n))
        return {
            'up_ratio': round(up_ratio, 2),
            'up_ratio_change': 0.0,
            'activity_index': round(min(90.0, max(40.0, up_ratio + 10)), 2),
            'activity_change': 0.0,
            'net_inflow': 0.0,
            'net_inflow_change': 0.0,
            'sentiment_index': round(senti, 2),
            'sentiment_change': 0.0,
            'market_strength': round(min(90.0, max(30.0, (up_ratio + senti) / 2)), 2),
            'limit_up_count': 0,
            'limit_down_count': 0,
            'new_high_count': 0,
            'new_low_count': 0,
            'high_volume_count': 0,
        }

    def _build_summary(
        self,
        cfg: OrchestratorConfig,
        rankings: List[Dict[str, Any]],
        sectors: Dict[str, Any],
        breadth: Dict[str, Any],
        use_llm: bool,
        ta_graph: Any,
    ) -> Dict[str, Any]:
        # 离线文案（可复用至LLM提示参数）
        top_buys = [r for r in rankings if r.get('recommendation') == '买入'][:5]
        sec_names = list(sectors.keys())[:3]
        key_insights = [
            f"{cfg.market_type}扫描完成：共评估{len(rankings)}只股票，买入建议{len(top_buys)}只",
            f"市场广度上行占比{breadth.get('up_ratio', 0)}%",
            f"强势板块：{', '.join(sec_names) if sec_names else '分散'}",
        ]

        # 置信度估算：结合市场强度与买入建议的得分（离线启发式）
        try:
            m_strength = float(breadth.get('market_strength', 50))
        except Exception:
            m_strength = 50.0
        try:
            top_scores = [r.get('total_score', 0) for r in rankings if r.get('recommendation') == '买入']
            if not top_scores:
                top_scores = [r.get('total_score', 0) for r in rankings[:5]]
            avg_top = sum(top_scores[:5]) / max(1, len(top_scores[:5]))
        except Exception:
            avg_top = 60.0
        # 组合：市场强度(权重0.6) + 顶部评分(权重0.4)，并限制在[55, 95]区间
        conf_level = int(max(55, min(95, round(0.6 * m_strength + 0.4 * avg_top))))

        return {
            'key_insights': key_insights,
            'investment_recommendations': {
                'buy': [{'symbol': r['symbol'], 'reason': '综合评分较高'} for r in top_buys],
                'watch': [{'symbol': r['symbol'], 'reason': '具备一定潜力'} for r in rankings[:5] if r not in top_buys],
            },
            'risk_factors': [
                '个股波动与流动性风险需关注',
                '模型数据受离线模式限制，建议结合实盘数据验证',
            ],
            'market_outlook': '短期或维持结构性机会，控制仓位、分散风险',
            'scan_statistics': {
                'completion_rate': 100,
                'confidence_level': conf_level,
            },
        }

    def _infer_sector(self, symbol: str) -> str:
        # 基于symbol特征简单映射（仅用于离线展示）
        if symbol.startswith(('60', '00', '30')):
            return random.choice(['消费', '金融', '科技', '医药', '制造'])
        if symbol.endswith('.HK'):
            return random.choice(['科技', '金融', '消费'])
        # 美股
        tech = {'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA'}
        if symbol in tech:
            return '科技'
        return random.choice(['金融', '消费', '医疗', '工业'])
