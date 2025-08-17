#!/usr/bin/env python3
"""
Tushare数据源工具类
提供A股市场数据获取功能，包括实时行情、历史数据、财务数据等
"""

import os
import time
import warnings
from datetime import datetime, timedelta

import pandas as pd

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger

logger = get_logger("agents")
warnings.filterwarnings("ignore")

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger  # noqa: E402

# 导入缓存管理器
try:
    from .cache_manager import get_cache  # noqa: F401

    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    logger.warning("⚠️ 缓存管理器不可用")

# 导入Tushare
try:
    import tushare as ts

    TUSHARE_AVAILABLE = True
except ImportError:
    TUSHARE_AVAILABLE = False
    logger.error("❌ Tushare库未安装，请运行: pip install tushare")


class TushareProvider:
    """Tushare数据提供器"""

    def __init__(self, token: str = None, enable_cache: bool = True):
        """
        初始化Tushare提供器

        Args:
            token: Tushare API token
            enable_cache: 是否启用缓存
        """
        self.connected = False
        self.enable_cache = enable_cache and CACHE_AVAILABLE
        self.api = None

        # 初始化缓存管理器
        self.cache_manager = None
        if self.enable_cache:
            try:
                from .cache_manager import get_cache

                self.cache_manager = get_cache()
            except Exception as e:
                logger.warning(f"⚠️ 缓存管理器初始化失败: {e}")
                self.enable_cache = False

        # 获取API token（使用强健的配置解析）
        if not token:
            try:
                from ..config.env_utils import parse_str_env

                token = parse_str_env("TUSHARE_TOKEN", "")
            except ImportError:
                # 回退到原始方法
                token = os.getenv("TUSHARE_TOKEN", "")

        if not token:
            logger.warning("⚠️ 未找到Tushare API token，请设置TUSHARE_TOKEN环境变量")
            return

        # 初始化Tushare API
        if TUSHARE_AVAILABLE:
            try:
                ts.set_token(token)
                self.api = ts.pro_api()
                self.connected = True
                logger.info("✅ Tushare API连接成功")
            except Exception as e:
                logger.error(f"❌ Tushare API连接失败: {e}")
        else:
            logger.error("❌ Tushare库不可用")

    def get_stock_list(self) -> pd.DataFrame:
        """
        获取A股股票列表

        Returns:
            DataFrame: 股票列表数据
        """
        if not self.connected:
            logger.error("❌ Tushare未连接")
            return pd.DataFrame()

        try:
            # 尝试从缓存获取
            if self.enable_cache:
                cache_key = self.cache_manager.find_cached_stock_data(
                    symbol="tushare_stock_list", max_age_hours=24  # 股票列表缓存24小时
                )

                if cache_key:
                    cached_data = self.cache_manager.load_stock_data(cache_key)
                    if cached_data is not None:
                        # 检查是否为DataFrame且不为空
                        if hasattr(cached_data, "empty") and not cached_data.empty:
                            logger.info(f"📦 从缓存获取股票列表: {len(cached_data)}条")
                            return cached_data
                        elif isinstance(cached_data, str) and cached_data.strip():
                            logger.info("📦 从缓存获取股票列表: 字符串格式")
                            return cached_data

            logger.info("🔄 从Tushare获取A股股票列表...")

            # 获取股票基本信息
            stock_list = self.api.stock_basic(
                exchange="",
                list_status="L",  # 上市状态
                fields="ts_code,symbol,name,area,industry,market,list_date",
            )

            if stock_list is not None and not stock_list.empty:
                logger.info(f"✅ 获取股票列表成功: {len(stock_list)}条")

                # 缓存数据
                if self.enable_cache and self.cache_manager:
                    try:
                        cache_key = self.cache_manager.save_stock_data(
                            symbol="tushare_stock_list",
                            data=stock_list,
                            data_source="tushare",
                        )
                        logger.info(
                            f"💾 A股股票列表已缓存: tushare_stock_list (tushare) -> {cache_key}"
                        )
                    except Exception as e:
                        logger.error(f"⚠️ 缓存保存失败: {e}")

                return stock_list
            else:
                logger.warning("⚠️ Tushare返回空数据")
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"❌ 获取股票列表失败: {e}")
            return pd.DataFrame()

    def get_stock_daily(
        self, symbol: str, start_date: str = None, end_date: str = None
    ) -> pd.DataFrame:
        """
        获取股票日线数据

        Args:
            symbol: 股票代码（如：000001.SZ）
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）

        Returns:
            DataFrame: 日线数据
        """
        # 记录详细的调用信息
        logger.info("🔍 [Tushare详细日志] get_stock_daily 开始执行")
        logger.info(
            f"🔍 [Tushare详细日志] 输入参数: symbol='{symbol}', start_date='{start_date}', end_date='{end_date}'"
        )
        logger.info(f"🔍 [Tushare详细日志] 连接状态: {self.connected}")
        logger.info(
            f"🔍 [Tushare详细日志] API对象: {type(self.api).__name__ if self.api else 'None'}"
        )

        if not self.connected:
            logger.error("❌ [Tushare详细日志] Tushare未连接，无法获取数据")
            return pd.DataFrame()

        # 使用 daily 端点（普通积分可用），并在本地基于 pct_chg 计算连续前复权价
        try:
            logger.info(
                f"🔍 [股票代码追踪] get_stock_daily 调用 _normalize_symbol，传入参数: '{symbol}'"
            )
            ts_code = self._normalize_symbol(symbol)
            logger.info(f"🔍 [股票代码追踪] _normalize_symbol 返回结果: '{ts_code}'")

            # 规范日期格式（YYYYMMDD）
            original_start = start_date
            original_end = end_date
            if end_date is None:
                end_date = datetime.now().strftime("%Y%m%d")
                logger.info(
                    f"🔍 [Tushare详细日志] 结束日期为空，设置为当前日期: {end_date}"
                )
            else:
                end_date = end_date.replace("-", "")
                logger.info(
                    f"🔍 [Tushare详细日志] 结束日期转换: '{original_end}' -> '{end_date}'"
                )

            if start_date is None:
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
                logger.info(
                    f"🔍 [Tushare详细日志] 开始日期为空，设置为一年前: {start_date}"
                )
            else:
                start_date = start_date.replace("-", "")
                logger.info(
                    f"🔍 [Tushare详细日志] 开始日期转换: '{original_start}' -> '{start_date}'"
                )

            logger.info(
                f"🔄 从Tushare获取{ts_code}数据 ({start_date} 到 {end_date})..."
            )
            api_start_time = time.time()
            try:
                data = self.api.daily(
                    ts_code=ts_code, start_date=start_date, end_date=end_date
                )
                api_duration = time.time() - api_start_time
                logger.info(
                    f"🔍 [Tushare详细日志] API调用完成，耗时: {api_duration:.3f}秒"
                )
            except Exception as api_error:
                api_duration = time.time() - api_start_time
                logger.error(
                    f"❌ [Tushare详细日志] API调用异常，耗时: {api_duration:.3f}秒"
                )
                logger.error(
                    f"❌ [Tushare详细日志] API异常类型: {type(api_error).__name__}"
                )
                logger.error(f"❌ [Tushare详细日志] API异常信息: {str(api_error)}")
                return pd.DataFrame()

            logger.info(
                f"🔍 [Tushare详细日志] 返回数据类型: {type(data)} 形状: {getattr(data,'shape', None)}"
            )
            if data is None or getattr(data, "empty", True):
                logger.warning(f"⚠️ [Tushare详细日志] daily 返回空数据: {ts_code}")
                return pd.DataFrame()

            # 数据预处理
            data = data.sort_values("trade_date")
            data["trade_date"] = pd.to_datetime(data["trade_date"])

            # 计算前复权价格（基于 pct_chg 连续价）
            data = self._calculate_forward_adjusted_prices(data)

            # 缓存
            if self.enable_cache and self.cache_manager:
                try:
                    cache_key = self.cache_manager.save_stock_data(
                        symbol=symbol, data=data, data_source="tushare"
                    )
                    logger.info(
                        f"💾 A股历史数据已缓存: {symbol} (tushare) -> {cache_key}"
                    )
                except Exception as cache_error:
                    logger.error(f"⚠️ 缓存保存失败: {cache_error}")

            logger.info(f"✅ 获取{ts_code}数据成功: {len(data)}条")
            return data

        except Exception as e:
            logger.error(f"❌ 获取{symbol}数据失败: {e}")
            return pd.DataFrame()

    def get_stock_daily_probar(
        self,
        symbol: str,
        start_date: str = None,
        end_date: str = None,
        adj: str = "qfq",
    ) -> pd.DataFrame:
        """使用官方 pro_bar 返回复权行情（默认前复权）。

        Args:
            symbol: 股票代码（如：000001.SZ 或 600519.SH）
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
            adj: 复权类型('qfq'前复权, 'hfq'后复权, ''未复权)

        Returns:
            DataFrame: 复权后的日线数据
        """
        if not self.connected:
            logger.error("❌ [Tushare详细日志] Tushare未连接，无法获取 pro_bar 数据")
            return pd.DataFrame()

        try:
            # 标准化 ts_code
            ts_code = self._normalize_symbol(symbol)

            # 日期格式：YYYYMMDD
            if end_date is None:
                end_date_fmt = datetime.now().strftime("%Y%m%d")
            else:
                end_date_fmt = end_date.replace("-", "")
            if start_date is None:
                start_date_fmt = (datetime.now() - timedelta(days=365)).strftime(
                    "%Y%m%d"
                )
            else:
                start_date_fmt = start_date.replace("-", "")

            logger.info(
                f"🔍 [Tushare详细日志] 调用 ts.pro_bar: ts_code='{ts_code}', start='{start_date_fmt}', end='{end_date_fmt}', adj='{adj}'"
            )

            # 官方 pro_bar（与daily_basic不同，为bar端点）
            import tushare as ts

            df = ts.pro_bar(
                ts_code=ts_code,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                adj=adj,
            )

            if df is None or df.empty:
                logger.warning(
                    f"⚠️ [Tushare详细日志] pro_bar 返回空数据: {ts_code}，将回退到 daily"
                )
            else:
                # 排序与日期型
                df = df.sort_values("trade_date")
                df["trade_date"] = pd.to_datetime(df["trade_date"])

                logger.info(
                    f"✅ [Tushare详细日志] pro_bar 获取成功: {ts_code}, {len(df)}条"
                )
                return df

        except Exception as e:
            logger.warning(f"⚠️ [Tushare详细日志] pro_bar 调用失败，将回退到 daily: {e}")

        # 回退到 daily
        return self.get_stock_daily(symbol, start_date, end_date)

    def _calculate_forward_adjusted_prices(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        基于pct_chg计算前复权价格

        Tushare的daily接口返回除权价格，在除权日会出现价格跳跃。
        使用pct_chg（涨跌幅）重新计算连续的前复权价格，确保价格序列的连续性。

        Args:
            data: 包含除权价格和pct_chg的DataFrame

        Returns:
            DataFrame: 包含前复权价格的数据
        """
        if data.empty or "pct_chg" not in data.columns:
            logger.warning("⚠️ 数据为空或缺少pct_chg列，无法计算前复权价格")
            return data

        try:
            # 复制数据避免修改原始数据
            adjusted_data = data.copy()

            # 确保数据按日期排序
            adjusted_data = adjusted_data.sort_values("trade_date").reset_index(
                drop=True
            )

            # 保存原始价格列（用于对比）
            adjusted_data["close_raw"] = adjusted_data["close"].copy()
            adjusted_data["open_raw"] = adjusted_data["open"].copy()
            adjusted_data["high_raw"] = adjusted_data["high"].copy()
            adjusted_data["low_raw"] = adjusted_data["low"].copy()

            # 从最新的收盘价开始，向前计算前复权价格
            # 使用最后一天的收盘价作为基准
            latest_close = float(adjusted_data.iloc[-1]["close"])

            # 计算前复权收盘价
            adjusted_closes = [latest_close]

            # 从倒数第二天开始向前计算
            for i in range(len(adjusted_data) - 2, -1, -1):
                pct_change = (
                    float(adjusted_data.iloc[i + 1]["pct_chg"]) / 100.0
                )  # 转换为小数

                # 前一天的前复权收盘价 = 今天的前复权收盘价 / (1 + 今天的涨跌幅)
                prev_close = adjusted_closes[0] / (1 + pct_change)
                adjusted_closes.insert(0, prev_close)

            # 更新收盘价
            adjusted_data["close"] = adjusted_closes

            # 计算其他价格的调整比例
            for i in range(len(adjusted_data)):
                if adjusted_data.iloc[i]["close_raw"] != 0:  # 避免除零
                    # 计算调整比例
                    adjustment_ratio = (
                        adjusted_data.iloc[i]["close"]
                        / adjusted_data.iloc[i]["close_raw"]
                    )

                    # 应用调整比例到其他价格
                    adjusted_data.iloc[i, adjusted_data.columns.get_loc("open")] = (
                        adjusted_data.iloc[i]["open_raw"] * adjustment_ratio
                    )
                    adjusted_data.iloc[i, adjusted_data.columns.get_loc("high")] = (
                        adjusted_data.iloc[i]["high_raw"] * adjustment_ratio
                    )
                    adjusted_data.iloc[i, adjusted_data.columns.get_loc("low")] = (
                        adjusted_data.iloc[i]["low_raw"] * adjustment_ratio
                    )

            # 添加标记表示这是前复权价格
            adjusted_data["price_type"] = "forward_adjusted"

            logger.info(f"✅ 前复权价格计算完成，数据条数: {len(adjusted_data)}")
            logger.info(
                f"📊 价格调整范围: 最早调整比例 {adjusted_data.iloc[0]['close'] / adjusted_data.iloc[0]['close_raw']:.4f}"
            )

            return adjusted_data

        except Exception as e:
            logger.error(f"❌ 前复权价格计算失败: {e}")
            logger.error("❌ 返回原始数据")
            return data

    def get_stock_info(self, symbol: str) -> dict:
        """
        获取股票基本信息

        Args:
            symbol: 股票代码

        Returns:
            Dict: 股票基本信息
        """
        if not self.connected:
            return {"symbol": symbol, "name": f"股票{symbol}", "source": "unknown"}

        try:
            logger.info(
                f"🔍 [股票代码追踪] get_stock_info 调用 _normalize_symbol，传入参数: '{symbol}'"
            )
            ts_code = self._normalize_symbol(symbol)
            logger.info(f"🔍 [股票代码追踪] _normalize_symbol 返回结果: '{ts_code}'")

            # 获取股票基本信息
            logger.info(
                f"🔍 [股票代码追踪] 调用 Tushare API stock_basic，传入参数: ts_code='{ts_code}'"
            )
            basic_info = self.api.stock_basic(
                ts_code=ts_code,
                fields="ts_code,symbol,name,area,industry,market,list_date",
            )

            logger.info(
                f"🔍 [股票代码追踪] Tushare API stock_basic 返回数据形状: {basic_info.shape if basic_info is not None and hasattr(basic_info, 'shape') else 'None'}"
            )
            if basic_info is not None and not basic_info.empty:
                logger.info(
                    f"🔍 [股票代码追踪] 返回数据内容: {basic_info.to_dict('records')}"
                )

            if basic_info is not None and not basic_info.empty:
                info = basic_info.iloc[0]
                return {
                    "symbol": symbol,
                    "ts_code": info["ts_code"],
                    "name": info["name"],
                    "area": info.get("area", ""),
                    "industry": info.get("industry", ""),
                    "market": info.get("market", ""),
                    "list_date": info.get("list_date", ""),
                    "source": "tushare",
                }
            else:
                return {"symbol": symbol, "name": f"股票{symbol}", "source": "unknown"}

        except Exception as e:
            logger.error(f"❌ 获取{symbol}股票信息失败: {e}")
            return {"symbol": symbol, "name": f"股票{symbol}", "source": "unknown"}

    def get_financial_data(self, symbol: str, period: str = "20231231") -> dict:
        """
        获取财务数据

        Args:
            symbol: 股票代码
            period: 报告期（YYYYMMDD）

        Returns:
            Dict: 财务数据
        """
        if not self.connected:
            return {}

        try:
            ts_code = self._normalize_symbol(symbol)

            financials = {}

            # 获取资产负债表
            try:
                balance_sheet = self.api.balancesheet(
                    ts_code=ts_code,
                    period=period,
                    fields="ts_code,ann_date,f_ann_date,end_date,report_type,comp_type,total_assets,total_liab,total_hldr_eqy_exc_min_int",
                )
                financials["balance_sheet"] = (
                    balance_sheet.to_dict("records")
                    if balance_sheet is not None and not balance_sheet.empty
                    else []
                )
            except Exception as e:
                logger.error(f"⚠️ 获取资产负债表失败: {e}")
                financials["balance_sheet"] = []

            # 获取利润表
            try:
                income_statement = self.api.income(
                    ts_code=ts_code,
                    period=period,
                    fields="ts_code,ann_date,f_ann_date,end_date,report_type,comp_type,total_revenue,total_cogs,operate_profit,total_profit,n_income",
                )
                financials["income_statement"] = (
                    income_statement.to_dict("records")
                    if income_statement is not None and not income_statement.empty
                    else []
                )
            except Exception as e:
                logger.error(f"⚠️ 获取利润表失败: {e}")
                financials["income_statement"] = []

            # 获取现金流量表
            try:
                cash_flow = self.api.cashflow(
                    ts_code=ts_code,
                    period=period,
                    fields="ts_code,ann_date,f_ann_date,end_date,report_type,comp_type,net_profit,finan_exp,c_fr_sale_sg,c_paid_goods_s",
                )
                financials["cash_flow"] = (
                    cash_flow.to_dict("records")
                    if cash_flow is not None and not cash_flow.empty
                    else []
                )
            except Exception as e:
                logger.error(f"⚠️ 获取现金流量表失败: {e}")
                financials["cash_flow"] = []

            return financials

        except Exception as e:
            logger.error(f"❌ 获取{symbol}财务数据失败: {e}")
            return {}

    def _normalize_symbol(self, symbol: str) -> str:
        """
        标准化股票代码为Tushare格式

        Args:
            symbol: 原始股票代码

        Returns:
            str: Tushare格式的股票代码
        """
        # 添加详细的股票代码追踪日志
        logger.info(
            f"🔍 [股票代码追踪] _normalize_symbol 接收到的原始股票代码: '{symbol}' (类型: {type(symbol)})"
        )
        logger.info(f"🔍 [股票代码追踪] 股票代码长度: {len(str(symbol))}")
        logger.info(f"🔍 [股票代码追踪] 股票代码字符: {list(str(symbol))}")

        original_symbol = symbol

        # 移除可能的前缀
        symbol = symbol.replace("sh.", "").replace("sz.", "")
        if symbol != original_symbol:
            logger.info(
                f"🔍 [股票代码追踪] 移除前缀后: '{original_symbol}' -> '{symbol}'"
            )

        # 如果已经是Tushare格式，直接返回
        if "." in symbol:
            logger.info(f"🔍 [股票代码追踪] 已经是Tushare格式，直接返回: '{symbol}'")
            return symbol

        # 根据代码判断交易所
        if symbol.startswith("6"):
            result = f"{symbol}.SH"  # 上海证券交易所
            logger.info(f"🔍 [股票代码追踪] 上海证券交易所: '{symbol}' -> '{result}'")
            return result
        elif symbol.startswith(("0", "3")):
            result = f"{symbol}.SZ"  # 深圳证券交易所
            logger.info(f"🔍 [股票代码追踪] 深圳证券交易所: '{symbol}' -> '{result}'")
            return result
        elif symbol.startswith("8"):
            result = f"{symbol}.BJ"  # 北京证券交易所
            logger.info(f"🔍 [股票代码追踪] 北京证券交易所: '{symbol}' -> '{result}'")
            return result
        else:
            # 默认深圳
            result = f"{symbol}.SZ"
            logger.info(
                f"🔍 [股票代码追踪] 默认深圳证券交易所: '{symbol}' -> '{result}'"
            )
            return result

    def search_stocks(self, keyword: str) -> pd.DataFrame:
        """
        搜索股票

        Args:
            keyword: 搜索关键词

        Returns:
            DataFrame: 搜索结果
        """
        try:
            stock_list = self.get_stock_list()

            if stock_list.empty:
                return pd.DataFrame()

            # 按名称和代码搜索
            mask = (
                stock_list["name"].str.contains(keyword, na=False)
                | stock_list["symbol"].str.contains(keyword, na=False)
                | stock_list["ts_code"].str.contains(keyword, na=False)
            )

            results = stock_list[mask]
            logger.debug(f"🔍 搜索'{keyword}'找到{len(results)}只股票")

            return results

        except Exception as e:
            logger.error(f"❌ 搜索股票失败: {e}")
            return pd.DataFrame()


# ==================== 本地回放 Provider（可选） ====================
class LocalTushareOutputProvider:
    """只读Provider：从本地文件回放Tushare样式输出。

    目录规范（base_dir）：
    - daily_{symbol}.csv
    - info_{symbol}.json
    - financials_{symbol}.json（可选）
    """

    def __init__(self, base_dir: str, enable_cache: bool = True):
        self.base_dir = str(base_dir)
        self.enable_cache = enable_cache
        self.connected = True  # 对适配器表示可用

    # helpers
    def _norm_symbol(self, symbol: str) -> str:
        import re

        s = str(symbol or "").strip()
        m = re.search(r"(\d{6})", s)
        return m.group(1) if m else s

    def _csv_path(self, symbol: str) -> str:
        import os

        sym = self._norm_symbol(symbol)
        candidate = os.path.join(self.base_dir, f"daily_{sym}.csv")
        if os.path.exists(candidate):
            return candidate
        return os.path.join(self.base_dir, f"daily_{symbol}.csv")

    def _json_path(self, kind: str, symbol: str) -> str:
        import os

        sym = self._norm_symbol(symbol)
        candidate = os.path.join(self.base_dir, f"{kind}_{sym}.json")
        if os.path.exists(candidate):
            return candidate
        return os.path.join(self.base_dir, f"{kind}_{symbol}.json")

    # API
    def get_stock_daily(
        self, symbol: str, start_date: str = None, end_date: str = None
    ) -> pd.DataFrame:
        import os

        p = self._csv_path(symbol)
        if not os.path.exists(p):
            logger.warning(f"⚠️ 本地样本不存在: {p}")
            return pd.DataFrame()

        # 兼容读取
        try:
            df = pd.read_csv(p)
        except UnicodeDecodeError:
            df = pd.read_csv(p, encoding="utf-8-sig")
        except Exception:
            df = pd.read_csv(p, encoding_errors="ignore")

        # 统一日期列
        if "trade_date" not in df.columns and "date" in df.columns:
            df = df.rename(columns={"date": "trade_date"})
        if "trade_date" in df.columns:
            df["trade_date"] = (
                df["trade_date"].astype(str).str.replace("-", "", regex=False)
            )
            try:
                df["trade_date"] = pd.to_datetime(
                    df["trade_date"], format="%Y%m%d", errors="coerce"
                )
            except Exception:
                df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce")
            df = df.sort_values("trade_date").reset_index(drop=True)

        return df

    def get_stock_info(self, symbol: str) -> dict:
        import json
        import os

        p = self._json_path("info", symbol)
        if os.path.exists(p):
            try:
                with open(p, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"⚠️ 读取本地info失败: {p}: {e}")
        sym = self._norm_symbol(symbol)
        return {"symbol": sym, "name": f"股票{sym}", "source": "local"}

    def get_financial_data(self, symbol: str, period: str = "20231231") -> dict:
        import json
        import os

        p = self._json_path("financials", symbol)
        if os.path.exists(p):
            try:
                with open(p, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"⚠️ 读取本地financials失败: {p}: {e}")
        return {}

    def search_stocks(self, keyword: str) -> pd.DataFrame:
        import glob
        import json
        import os

        rows = []
        for f in glob.glob(os.path.join(self.base_dir, "info_*.json")):
            try:
                with open(f, encoding="utf-8") as fp:
                    info = json.load(fp)
                name = str(info.get("name", ""))
                sym = str(info.get("symbol", ""))
                ts_code = str(info.get("ts_code", ""))
                if keyword in name or keyword in sym or keyword in ts_code:
                    rows.append(info)
            except Exception:
                continue
        return pd.DataFrame(rows)


# 全局提供器实例
_tushare_provider = None


def get_tushare_provider() -> TushareProvider:
    """获取全局Tushare提供器实例。

    若设置了 LOCAL_TUSHARE_OUTPUT_DIR 且目录存在，则优先使用本地回放Provider。
    """
    global _tushare_provider
    if _tushare_provider is None:
        local_dir = os.getenv("LOCAL_TUSHARE_OUTPUT_DIR")
        if local_dir and os.path.isdir(local_dir):
            logger.info(f"📂 使用本地Tushare回放目录: {local_dir}")
            _tushare_provider = LocalTushareOutputProvider(local_dir)
        else:
            _tushare_provider = TushareProvider()
    return _tushare_provider


def get_china_stock_data_tushare(
    symbol: str, start_date: str = None, end_date: str = None
) -> pd.DataFrame:
    """
    获取中国股票数据的便捷函数（Tushare数据源）

    Args:
        symbol: 股票代码
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        DataFrame: 股票数据
    """
    provider = get_tushare_provider()
    return provider.get_stock_daily(symbol, start_date, end_date)


def get_china_stock_info_tushare(symbol: str) -> dict:
    """
    获取中国股票信息的便捷函数（Tushare数据源）

    Args:
        symbol: 股票代码

    Returns:
        Dict: 股票信息
    """
    provider = get_tushare_provider()
    return provider.get_stock_info(symbol)
