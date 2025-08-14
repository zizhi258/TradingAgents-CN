# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=317  
**爬取时间**: 2025-08-09 22:35:29

---

## 实时涨跌幅排名(爬虫版)

---

接口：realtime\_list，由于采集和拼接当日以来的成交全历史，因此接口提取数据时需要一定时间，请耐心等待，请将tushare升级到1.3.3版本以上。
描述：本接口是tushare org版实时接口的顺延，数据来自网络，且不进入tushare服务器，属于爬虫接口，数据包括该股票当日开盘以来的所有分笔成交数据。
权限：0积分完全开放，但需要有tushare账号，如果没有账号请先[注册](https://tushare.pro/register)。
说明：由于该接口是纯爬虫程序，跟tushare服务器无关，因此tushare不对数据内容和质量负责。数据主要用于研究和学习使用，如做商业目的，请自行解决合规问题。

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| src | str | N | 数据源 （sina-新浪 dc-东方财富，默认dc） |

**东财数据输出参数**

| 名称 | 类型 | 描述 |
| --- | --- | --- |
| ts\_code | str | 股票代码 |
| name | str | 股票名称 |
| price | float | 当前价格 |
| pct\_change | float | 涨跌幅 |
| change | float | 涨跌额 |
| volume | int | 成交量（单位：手） |
| amount | int | 成交金额（元） |
| swing | float | 振幅 |
| low | float | 今日最低价 |
| high | float | 今日最高价 |
| open | float | 今日开盘价 |
| close | float | 今日收盘价 |
| vol\_ratio | int | 量比 |
| turnover\_rate | float | 换手率 |
| pe | int | 市盈率PE |
| pb | float | 市净率PB |
| total\_mv | float | 总市值（元） |
| float\_mv | float | 流通市值（元） |
| rise | float | 涨速 |
| 5min | float | 5分钟涨幅 |
| 60day | float | 60天涨幅 |
| 1tyear | float | 1年涨幅 |

**新浪数据输出参数**

| 名称 | 类型 | 描述 |
| --- | --- | --- |
| ts\_code | str | 股票代码 |
| name | str | 股票名称 |
| price | float | 当前价格 |
| pct\_change | float | 涨跌幅 |
| change | float | 涨跌额 |
| buy | float | 买入价 |
| sale | float | 卖出价 |
| close | float | 今日收盘价 |
| open | float | 今日开盘价 |
| high | float | 今日最高价 |
| low | float | 今日最低价 |
| volume | int | 成交量（单位：股） |
| amount | int | 成交金额（元） |
| time | str | 当前时间 |

**接口用法**

```yaml
import tushare as ts

#东财数据
df = ts.realtime_list(src='dc')

#sina数据
df = ts.realtime_list(src='sina')
```
