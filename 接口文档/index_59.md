# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=57  
**爬取时间**: 2025-08-09 22:32:47

---

## 数字货币每日市值

---

接口：coincap
描述：获取数字货币每日市值数据，该接口每隔6小时采集一次数据，所以当日每个品种可能有多条数据，用户可根据实际情况过滤截取使用。

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| trade\_date | str | Y | 日期 |
| coin | str | N | coin代码, e.g. BTC/ETH/QTUM |

**输出参数**

| 名称 | 类型 | 描述 |
| --- | --- | --- |
| trade\_date | str | 交易日期 |
| coin | str | 货币代码 |
| name | str | 货币名称 |
| marketcap | str | 市值（美元） |
| price | float | 当前时间价格（美元） |
| vol24 | float | 24小时成交额（美元） |
| supply | float | 流通总量 |
| create\_time | str | 数据采集时间 |

**接口使用**

```
pro = ts.pro_api()

df = pro.coincap(trade_date='20180806')
```

或者

```
df = pro.query('coincap', trade_date='20180806', coin='BTC')
```

**数据样例**

```json
trade_date   coin              name     marketcap         vol24          create_time
    0   20180806    BTC       BTC Bitcoin  1.232036e+11  1.719294e+07  2018-08-06 11:10:28
    1   20180806    ETH      ETH Ethereum  4.184291e+10  1.011476e+08  2018-08-06 11:10:28
    2   20180806    XRP           XRP XRP  1.710519e+10  3.929987e+10  2018-08-06 11:10:28
    3   20180806    BCH  BCH Bitcoin Cash  1.239949e+10  1.727725e+07  2018-08-06 11:10:28
    4   20180806    EOS           EOS EOS  6.480991e+09  9.062451e+08  2018-08-06 11:10:28
    5   20180806    XLM       XLM Stellar  4.654252e+09  1.877026e+10  2018-08-06 11:10:28
    6   20180806    LTC      LTC Litecoin  4.391543e+09  5.772298e+07  2018-08-06 11:10:28
    7   20180806    ADA       ADA Cardano  3.512526e+09  2.592707e+10  2018-08-06 11:10:28
    8   20180806  MIOTA        MIOTA IOTA  2.546902e+09  2.779530e+09  2018-08-06 11:10:28
    9   20180806   USDT       USDT Tether  2.440917e+09  2.437140e+09  2018-08-06 11:10:28
```
