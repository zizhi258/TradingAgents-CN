# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=71  
**爬取时间**: 2025-08-09 22:32:56

---

## 巴比特

---

接口：btc8
描述：获取巴比特即时和历史资讯数据（5分钟更新一次，未来根据服务器压力再做调整）

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

df = pro.btc8(start_date='2018-08-17 16:00:00', end_date='2018-08-17 18:00:00', \
                fields='title, url, datetime')
```

或者

```json
df = pro.query('btc8', start_date='2018-08-17 16:00:00', end_date='2018-08-17 18:00:00', \
                fields='title, url, datetime')
```

**数据样例**

```
title                                  url  \
0  中国太保携手京东上线区块链专用发票电子化项目   https://www.8btc.com/article/255078
1  OKCoin韩国交易所多币种放量上涨，YOYO涨幅最高达22122.22%  https://www.8btc.com/article/255072
2  京东推出区块链开放平台  https://www.8btc.com/article/255067
3  金研院：区块链技术将逐步应用于黄金珠宝行业  https://www.8btc.com/article/255058
4  比特派钱包首期BTM理财于10分钟售罄  https://www.8btc.com/article/255051
5  比特币ETF“软性替代品”在美上市交易  https://www.8btc.com/article/255036
6  ETH未确认交易数量为84996笔  https://www.8btc.com/article/255031
7  首个区块链健康数据授权查看证上线  https://www.8btc.com/article/255021
8  Crypto Facilities推出比特现金期货合约交易  https://www.8btc.com/article/255011
9  巴比特加速器：GeekHub创变者计划正式启动  https://www.8btc.com/article/254982
```
