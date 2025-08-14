# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=238  
**爬取时间**: 2025-08-09 22:34:40

---

## 数字货币分钟

---

接口：coin\_bar
描述：获取数字货币数据，包括1分钟、5分、15、30、60分钟、日线等K线数据
限量：单次最大8000条数据
权限：120具备每分钟2次试用，开通正式权限请参考以下方式。

注：因访问量激增，造成服务器压力增大，我们需要采购更多的机器来存储和提供数据服务，需要[赞助](https://tushare.pro/document/2?doc_id=244)1000元或同等币值获得数据权限。支持微信、支付宝赞助，也支持数字货币赞助

**输入参数**

| 名称 | 类型 | 必选 | 描述 | 示例 |
| --- | --- | --- | --- | --- |
| ts\_code | str | N | 代码 | BTC\_USDT |
| exchange | str | N | 交易所 | huobi |
| freq | str | N | 频度 | 1min |
| is\_contract | str | N | 是否合约 | Y |
| start\_date | datetime | N | 开始日期 | 2020-04-01 00:00:01 |
| end\_date | datetime | N | 结束日期 | 2020-04-04 19:00:00 |

**freq说明**

| freq | 说明 |
| --- | --- |
| 1min | 1分钟 |
| 5min | 5分钟 |
| 15min | 15分钟 |
| 30min | 30分钟 |
| 60min | 60分钟 |
| 1day | 日线 |
| 1week | 周线 |

**输出参数**

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| exchange | str | Y | 交易所 |
| symbol | str | Y | 交易所原始代码 |
| freq | str | Y | 频度 |
| trade\_time | str | Y | 交易时间 |
| open | float | Y | 开盘价 |
| close | float | Y | 收盘价 |
| high | float | Y | 最高价 |
| low | float | Y | 最低价 |
| vol | float | Y | 成交量 |
| is\_contract | str | Y | 是否合约Y是N否 |

**接口用法**

```json
pro = ts.pro_api()

df = pro.coin_bar(exchange='okex', ts_code='BTC_USDT', freq='1min', start_date='2020-04-01 00:00:01', end_date='2020-04-22 19:00:00')
```

**数据样例**

```json
exchange    symbol  freq           trade_time    open   close    high     low         vol is_contract
0        okex  BTC_USDT  1min  2020-04-21 07:00:00  6861.7  6863.5  6867.9  6861.1  301.000000           Y
1        okex  BTC_USDT  1min  2020-04-21 07:00:00  6848.5  6852.7  6852.7  6848.5  137.000000           Y
2        okex  BTC_USDT  1min  2020-04-21 07:00:00  6872.5  6874.2  6875.1  6872.2  303.000000           Y
3        okex  BTC_USDT  1min  2020-04-21 07:00:00  6848.3  6848.5  6850.3  6848.1  220.000000           Y
4        okex  BTC_USDT  1min  2020-04-21 07:00:00  6875.2  6876.2  6878.9  6874.4   25.164881           N
...       ...       ...   ...                  ...     ...     ...     ...     ...         ...         ...
7995     okex  BTC_USDT  1min  2020-04-19 11:13:00  7158.3  7149.5  7158.3  7148.4  305.000000           Y
7996     okex  BTC_USDT  1min  2020-04-19 11:13:00  7160.1  7151.8  7160.1  7148.0  341.000000           Y
7997     okex  BTC_USDT  1min  2020-04-19 11:12:00  7158.0  7158.6  7160.3  7155.4  136.000000           Y
7998     okex  BTC_USDT  1min  2020-04-19 11:12:00  7157.8  7157.8  7157.8  7157.8   10.000000           Y
7999     okex  BTC_USDT  1min  2020-04-19 11:12:00  7157.3  7157.6  7158.5  7157.3   87.000000           Y
```
