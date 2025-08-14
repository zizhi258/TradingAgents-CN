# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=99  
**爬取时间**: 2025-08-09 22:33:14

---

## 优币指数成分

---

接口：**ubindex\_constituents**

描述：获取优币指数成分所对应的流通市值、权重以及指数调仓日价格等数据。

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| index\_name | str | Y | 指数名称（支持的指数请见下表） |
| start\_date | str | Y | 开始日期（包含），格式：yyyymmdd |
| end\_date | str | Y | 结束日期（包含），格式：yyyymmdd |

**输出参数**

| 名称 | 类型 | 描述 |
| --- | --- | --- |
| trade\_date | str | 指数日期 |
| index\_name | str | 指数名称 |
| symbol | str | 成分货币简称 |
| circulated\_cap | float | 计算周期内日流动市值均值 |
| weight | float | 计算周期内权重 |
| price | float | 指数日价格 |
| create\_time | datetime | 入库时间 |

**支持的指数**

| 指数名称 | 说明 |
| --- | --- |
| UBI7 | 平台类TOP7项目指数 |
| UBI0 | 平台类TOP10项目指数 |
| UBI20 | 平台类TOP20项目指数 |
| UBC7 | 币类TOP7项目指数 |
| UB7 | 市场整体类TOP7项目指数 |
| UB20 | 市场整体类TOP20项目指数 |

**接口用法 1**

```
pro = ts.pro_api()

pro.ubindex_constituents(index_name='UBI7', start_date='20180801', end_date='20180901')
```

或者

```
pro = ts.pro_api()

pro.query('ubindex_constituents', index_name='UBI7', start_date='20180801', end_date='20180901')
```

**数据样例 1**

| trade\_date | index\_name | symbol | weight |
| --- | --- | --- | --- |
| 20180901 | UBI7 | ETH | 30 |
| 20180901 | UBI7 | EOS | 16.838142 |
| 20180901 | UBI7 | XLM | 15.397589 |
| 20180901 | UBI7 | ADA | 12.515037 |
| 20180901 | UBI7 | ETC | 8.984187 |
| 20180901 | UBI7 | NEO | 8.635051 |
| 20180901 | UBI7 | XEM | 7.629994 |

**接口用法 2**

```
pro = ts.pro_api()

pro.ubindex_constituents(index_name='UBC7', start_date='20180801', end_date='20180901',
                         fields='trade_date, index_name, symbol, circulated_cap, weight, price, create_time')
```

或者

```
pro = ts.pro_api()

pro.query('ubindex_constituents', index_name='UBC7', start_date='20180801', end_date='20180901',
          fields='trade_date, index_name, symbol, circulated_cap, weight, price, create_time')
```

**数据样例 2**

| trade\_date | index\_name | symbol | circulated\_cap | weight | price | create\_time |
| --- | --- | --- | --- | --- | --- | --- |
| 20180901 | UBC7 | BTC | 1.151072e+11 | 30 | 7065.42 | 2018-09-08 23:11:02 |
| 20180901 | UBC7 | XRP | 1.356686e+10 | 21.400755 | 0.338932 | 2018-09-08 23:11:02 |
| 20180901 | UBC7 | BCH | 1.006408e+10 | 18.432174 | 552.78 | 2018-09-08 23:11:02 |
| 20180901 | UBC7 | LTC | 3.572799e+09 | 10.982311 | 63.35 | 2018-09-08 23:11:02 |
| 20180901 | UBC7 | XMR | 1.633730e+09 | 7.426422 | 119.53 | 2018-09-08 23:11:02 |
| 20180901 | UBC7 | DASH | 1.401305e+09 | 6.877898 | 199.89 | 2018-09-08 23:11:02 |
| 20180901 | UBC7 | ZEC | 7.055681e+08 | 4.88044 | 152.51 | 2018-09-08 23:11:02 |
