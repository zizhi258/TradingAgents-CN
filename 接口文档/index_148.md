# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=146  
**爬取时间**: 2025-08-09 22:33:43

---

## A股复权行情

---

**接口名称** ：pro\_bar
**接口说明** ：复权行情通过[通用行情接口](https://tushare.pro/document/2?doc_id=109)实现，利用Tushare Pro提供的[复权因子](https://tushare.pro/document/2?doc_id=28)进行动态计算，因此http方式无法调取。若需要静态复权行情（支持http），请访问[股票技术因子接口](https://tushare.pro/document/2?doc_id=296)。
**Python SDK版本要求**： >= 1.2.26

**复权说明**

| 类型 | 算法 | 参数标识 |
| --- | --- | --- |
| 不复权 | 无 | 空或None |
| 前复权 | 当日收盘价 × 当日复权因子 / 最新复权因子 | qfq |
| 后复权 | 当日收盘价 × 当日复权因子 | hfq |

注：目前只支持A股的日线复权。在Tushare数据接口里，不管是旧版的一些接口还是Pro版的行情接口，都是以用户设定的end\_date开始往前复权，跟所有行情软件或者财经网站上看到的前复权可能存在差异，因为行情软件都是以最近一个交易日开始往前复权的。比如今天是2018年10月26日，您想查2018年1月5日～2018年9月28日的前复权数据，Tushare是先查找9月28日的复权因子，从28日开始复权，而行情软件是从10月26日这天开始复权的。同时，Tushare的复权采用“分红再投”模式计算。

**接口参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | Y | 证券代码 |
| start\_date | str | N | 开始日期 (格式：YYYYMMDD) |
| end\_date | str | N | 结束日期 (格式：YYYYMMDD) |
| asset | str | Y | 资产类别：E股票 I沪深指数 C数字货币 FT期货 FD基金 O期权，默认E |
| adj | str | N | 复权类型(只针对股票)：None未复权 qfq前复权 hfq后复权 , 默认None |
| freq | str | Y | 数据频度 ：1MIN表示1分钟（1/5/15/30/60分钟） D日线 ，默认D |
| ma | list | N | 均线，支持任意周期的均价和均量，输入任意合理int数值 |

**接口用例**

日线复权

```yaml
#取000001的前复权行情
df = ts.pro_bar(ts_code='000001.SZ', adj='qfq', start_date='20180101', end_date='20181011')

#取000001的后复权行情
df = ts.pro_bar(ts_code='000001.SZ', adj='hfq', start_date='20180101', end_date='20181011')
```

周线复权

```yaml
#取000001的周线前复权行情
df = ts.pro_bar( ts_code='000001.SZ', freq='W', adj='qfq', start_date='20180101', end_date='20181011')

#取000001的周线后复权行情
df = ts.pro_bar(ts_code='000001.SZ', freq='W', adj='hfq', start_date='20180101', end_date='20181011')
```

月线复权

```yaml
#取000001的月线前复权行情
df = ts.pro_bar(ts_code='000001.SZ', freq='M', adj='qfq', start_date='20180101', end_date='20181011')

#取000001的月线后复权行情
df = ts.pro_bar(ts_code='000001.SZ', freq='M', adj='hfq', start_date='20180101', end_date='20181011')
```
