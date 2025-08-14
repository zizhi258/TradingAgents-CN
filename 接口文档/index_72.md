# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=70  
**爬取时间**: 2025-08-09 22:32:55

---

## 金色财经

---

接口：jinse
描述：获取金色采集即时和历史资讯数据（5分钟更新一次）

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| start\_date | datetime | Y | 开始时间 格式：YYYY-MM-DD HH:MM:SS |
| end\_date | datetime | Y | 结束时间 格式：YYYY-MM-DD HH:MM:SS |

**输出参数**

| 名称 | 类型 | 描述 |
| --- | --- | --- |
| title | str | 标题 |
| content | str | 内容 |
| type | str | 类型 |
| url | str | URL |
| datetime | str | 时间 |

**接口用法**

由于数据量可能比较大，我们限定了必须设定起止时间来获取数据，并且每次最多只能取200条数据。

```json
pro = ts.pro_api()

df = pro.jinse(start_date='2018-08-17 16:00:00', end_date='2018-08-17 18:00:00', \
                fields='title, type, datetime')
```

或者

```json
df = pro.query('jinse', start_date='2018-08-17 16:00:00', end_date='2018-08-17 18:00:00', \
                fields='title, type, datetime')
```

**数据样例**

```json
title                  type             datetime
0   OMO智能合约使以太坊交易费用大幅增加             动态    2018-08-17 17:49:21
1   币威美国 CSO：钱包是下一个区块链千万级社群      声音    2018-08-17 17:35:06
2   OKCoin大量币种上涨YOYO的24H涨幅达到13,611.22%   行情    2018-08-17 17:29:22
3   社交纸牌类游戏运营商KamaGames推出平台Token              2018-08-17 17:18:54
4   PST正式上线CoinMex将开放PST/ETH交易对           动态    2018-08-17 17:17:10
5   币倍交易所系统安全防护升级                      公告  2018-08-17 17:10:24
6   ARTCN将上线LBank                                动态  2018-08-17 16:59:58
7   金色盘面：数字货币若无实质性利好刺激 短期内牛市难言   分析  2018-08-17 16:49:55
8   金色盘面：LSK/BTC 短线走势强劲 注意疯狂         分析  2018-08-17 16:45:27
9   EOS 15分钟跌幅超过1.00%                         行情  2018-08-17 16:29:29
10  金色盘面：EOS/USD 突破压力位  趋势看多          分析  2018-08-17 16:13:35
11  BOTTOS铂链与金山云正式达成合作                  动态  2018-08-17 16:13:29
12  Crypto Facilities上线BCH期货交易                动态  2018-08-17 16:07:41
13  Alex Erasmus 将担任Block.one首席法律官          动态  2018-08-17 16:03:13
```
