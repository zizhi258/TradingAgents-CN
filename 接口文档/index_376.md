# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=374  
**爬取时间**: 2025-08-09 22:36:06

---

## A股实时分钟

---

接口：rt\_min
描述：获取全A股票实时分钟数据，包括1~60min
限量：单次最大1000行数据，可以通过股票代码提取数据，支持逗号分隔的多个代码同时提取
权限：正式权限请参阅 [权限说明](https://tushare.pro/document/1?doc_id=290)

注：同时支持当日开盘以来的所有分钟数据，接口名：rt\_min\_daily（只支持一个个股票提取）

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| freq | str | Y | 1MIN,5MIN,15MIN,30MIN,60MIN （大写） |
| ts\_code | str | Y | 支持单个和多个：600000.SH 或者 600000.SH,000001.SZ |

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
| ts\_code | str | Y | 股票代码 |
| time | None | Y | 交易时间 |
| open | float | Y | 开票 |
| close | float | Y | 收盘 |
| high | float | Y | 最高 |
| low | float | Y | 最低 |
| vol | float | Y | 成交量(股） |
| amount | float | Y | 成交额（元） |

**接口用法**

```
pro = ts.pro_api()

#获取浦发银行60000.SH的实时分钟数据
df = pro.rt_min(ts_code='600000.SH', freq='1MIN')
```
