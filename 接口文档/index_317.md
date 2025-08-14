# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=315  
**爬取时间**: 2025-08-09 22:35:28

---

## 实时盘口TICK快照(爬虫版)

---

接口：realtime\_quote，A股实时行情
描述：本接口是tushare org版实时接口的顺延，数据来自网络，且不进入tushare服务器，属于爬虫接口，请将tushare升级到1.3.3版本以上。
权限：0积分完全开放，但需要有tushare账号，如果没有账号请先[注册](https://tushare.pro/register)。
说明：由于该接口是纯爬虫程序，跟tushare服务器无关，因此tushare不对数据内容和质量负责。数据主要用于研究和学习使用，如做商业目的，请自行解决合规问题。

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | N | 股票代码，需按tushare[股票和指数标准](https://tushare.pro/document/2?doc_id=14)代码输入，比如：000001.SZ表示平安银行，000001.SH表示上证指数 |
| src | str | N | 数据源 （sina-新浪 dc-东方财富，默认sina） |

src数据源说明：

| src源 | 说明 | 描述 |
| --- | --- | --- |
| sina | 新浪财经 | 支持多个多个股票同时输入，举例：ts\_code='600000.SH,000001.SZ'），一次最多不能超过50个股票 |
| dc | 东方财富 | 只支持单个股票提取 |

**输出参数**

| 名称 | 类型 | 描述 |
| --- | --- | --- |
| name | str | 股票名称 |
| ts\_code | str | 股票代码 |
| date | str | 交易日期 |
| time | str | 交易时间 |
| open | float | 开盘价 |
| pre\_close | float | 昨收价 |
| price | float | 现价 |
| high | float | 今日最高价 |
| low | float | 今日最低价 |
| bid | float | 竞买价，即“买一”报价（元） |
| ask | float | 竞卖价，即“卖一”报价（元） |
| volume | int | 成交量（src=sina时是股，src=dc时是手） |
| amount | float | 成交金额（元 CNY） |
| b1\_v | float | 委买一（量，单位：手，下同） |
| b1\_p | float | 委买一（价，单位：元，下同） |
| b2\_v | float | 委买二（量） |
| b2\_p | float | 委买二（价） |
| b3\_v | float | 委买三（量） |
| b3\_p | float | 委买三（价） |
| b4\_v | float | 委买四（量） |
| b4\_p | float | 委买四（价） |
| b5\_v | float | 委买五（量） |
| b5\_p | float | 委买五（价） |
| a1\_v | float | 委卖一（量，单位：手，下同） |
| a1\_p | float | 委卖一（价，单位：元，下同） |
| a2\_v | float | 委卖二（量） |
| a2\_p | float | 委卖二（价） |
| a3\_v | float | 委卖三（量） |
| a3\_p | float | 委卖三（价） |
| a4\_v | float | 委卖四（量） |
| a4\_p | float | 委卖四（价） |
| a5\_v | float | 委卖五（量） |
| a5\_p | float | 委卖五（价） |

**接口用法**

```yaml
import tushare as ts

#设置你的token，登录tushare在个人用户中心里拷贝
ts.set_token('你的token')

#sina数据
df = ts.realtime_quote(ts_code='600000.SH,000001.SZ,000001.SH')

#东财数据
df = ts.realtime_quote(ts_code='600000.SH', src='dc')
```

**数据样例**

```json
NAME    TS_CODE      DATE      TIME       OPEN  PRE_CLOSE      PRICE  ...   A2_P  A3_V   A3_P  A4_V   A4_P  A5_V   A5_P
0  浦发银行  600000.SH  20231222  15:00:00      6.570      6.570      6.580  ...  6.590  1834  6.600  4107  6.610  2684  6.620
1  平安银行  000001.SH  20231222  15:00:00      9.190      9.170      9.200  ...  9.210  2177  9.220  2568  9.230  2319  9.240
2  上证指数  000001.SH  20231222  15:30:39  2919.2879  2918.7149  2914.7752  ...      0            0            0            0
```
