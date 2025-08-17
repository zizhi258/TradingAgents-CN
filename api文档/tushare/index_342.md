# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=340  
**爬取时间**: 2025-08-09 22:35:44

---

## 期货实时分钟行情

---

接口：rt\_fut\_min
描述：获取全市场期货合约实时分钟数据，支持1min/5min/15min/30min/60min行情，提供Python SDK、 http Restful API和websocket三种方式，如果需要主力合约分钟，请先通过主力[mapping](https://tushare.pro/document/2?doc_id=189)接口获取对应的合约代码后提取分钟。
限量：每分钟可以请求500次，支持多个合约同时提取
权限：需单独开权限，正式权限请参阅 [权限说明](https://tushare.pro/document/1?doc_id=290)  。

同时提供当日开市以来所有历史分钟，接口名：rt\_fut\_min\_daily，参数跟rt\_fut\_min一致，但只支持一个个合约提取。

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | Y | 股票代码，e.g.CU2310.SHF，支持多个合约（逗号分隔） |
| freq | str | Y | 分钟频度（1MIN/5MIN/15MIN/30MIN/60MIN） |

**freq参数说明**

| freq | 说明 |
| --- | --- |
| 1MIN | 1分钟 |
| 5MIN | 5分钟 |
| 15MIN | 15分钟 |
| 30MIN | 30分钟 |
| 60MIN | 60分钟 |

**输出参数**

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| code | str | Y | 股票代码 |
| freq | str | Y | 频度 |
| time | str | Y | 交易时间 |
| open | float | Y | 开盘价 |
| close | float | Y | 收盘价 |
| high | float | Y | 最高价 |
| low | float | Y | 最低价 |
| vol | int | Y | 成交量 |
| amount | float | Y | 成交金额 |
| oi | float | Y | 持仓量 |

**接口用法**

```yaml
pro = ts.pro_api()

#单个合约
df = pro.df = pro.rt_fut_min(ts_code='CU2501.SHF', freq='1MIN')

#多个合约
df = pro.df = pro.rt_fut_min(ts_code='CU2501.SHF,CU2502.SHF', freq='1MIN')
```
