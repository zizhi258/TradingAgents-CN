# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=336  
**爬取时间**: 2025-08-09 22:35:41

---

## 股票周/月线行情(每日更新)

---

接口：stk\_weekly\_monthly
描述：股票周/月线行情(每日更新)
限量：单次最大6000

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | N | TS代码 |
| trade\_date | str | N | 交易日期(YYYYMMDD，下同) |
| start\_date | str | N | 开始交易日期 |
| end\_date | str | N | 结束交易日期 |
| freq | str | Y | 频率week周，month月 |

**输出参数**

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | Y | 股票代码 |
| trade\_date | str | Y | 交易日期（每周五或者月末日期） |
| end\_date | str | Y | 计算截至日期 |
| freq | str | Y | 频率(周week,月month) |
| open | float | Y | (周/月)开盘价 |
| high | float | Y | (周/月)最高价 |
| low | float | Y | (周/月)最低价 |
| close | float | Y | (周/月)收盘价 |
| pre\_close | float | Y | 上一(周/月)收盘价 |
| vol | float | Y | (周/月)成交量 |
| amount | float | Y | (周/月)成交额 |
| change | float | Y | (周/月)涨跌额 |
| pct\_chg | float | Y | (周/月)涨跌幅(未复权,如果是复权请用 通用行情接口) |
