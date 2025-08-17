# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=51  
**爬取时间**: 2025-08-09 22:32:43

---

## 交易所交易对

---

接口：coinpair
描述：获取Tushare所能提供的所有交易和交易对名称，用于获得行情等数据。

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| trade\_date | str | N | 日期 |
| exchange | str | Y | 交易所 |

**输出参数**

| 名称 | 类型 | 描述 |
| --- | --- | --- |
| trade\_date | str | 日期 |
| exchange | str | 交易所 |
| exchange\_pair | str | 交易所原始交易对名称 |
| ts\_pair | str | Tushare标准名称 |

**交易所列表**

| 序号 | 交易所名称 |
| --- | --- |
| 1 | allcoin |
| 2 | bcex |
| 3 | bibox |
| 4 | bigone |
| 5 | binance |
| 6 | bitbank |
| 7 | bitfinex |
| 8 | bitflyer |
| 9 | bitflyex |
| 10 | bithumb |
| 11 | bitmex |
| 12 | bitstamp |
| 13 | bitstar |
| 14 | bittrex |
| 15 | bitvc |
| 16 | bitz |
| 17 | bleutrade |
| 18 | btcbox |
| 19 | btcc |
| 20 | btccp |
| 21 | btcturk |
| 22 | btc\_usd\_index |
| 23 | bter |
| 24 | chbtc |
| 25 | cobinhood |
| 26 | coinbase |
| 27 | coinbene |
| 28 | coincheck |
| 29 | coinegg |
| 30 | coinex |
| 31 | coinone |
| 32 | coinsuper |
| 33 | combine |
| 34 | currency |
| 35 | dextop |
| 36 | digifinex |
| 37 | exmo |
| 38 | exx |
| 39 | fcoin |
| 40 | fisco |
| 41 | future\_bitmex |
| 42 | gate |
| 43 | gateio |
| 44 | gdax |
| 45 | gemini |
| 46 | hadax |
| 47 | hbus |
| 48 | hft |
| 49 | hitbtc |
| 50 | huobi |
| 51 | huobiotc |
| 52 | huobip |
| 53 | huobix |
| 54 | idax |
| 55 | idex |
| 56 | index |
| 57 | itbit |
| 58 | jubi |
| 59 | korbit |
| 60 | kraken |
| 61 | kucoin |
| 62 | lbank |
| 63 | lbc |
| 64 | liqui |
| 65 | okcn |
| 66 | okcom |
| 67 | okef |
| 68 | okex |
| 69 | okotc |
| 70 | okusd |
| 71 | poloniex |
| 72 | quoine |
| 73 | quoinex |
| 74 | rightbtc |
| 75 | shuzibi |
| 76 | simex |
| 77 | topbtc |
| 78 | upbit |
| 79 | viabtc |
| 80 | yobit |
| 81 | yuanbao |
| 82 | yunbi |
| 83 | zaif |
| 84 | zb |

**接口用法**

```
pro = ts.pro_api()

df = pro.coinpair(exchange='huobi', trade_date='20180802')
```

或者

```
df = pro.query('coinpair', exchange='huobi', trade_date='20180802')
```

**数据样例**

```
trade_date exchange exchange_pair   ts_pair
0   20180802    huobi       btcusdt   btcusdt
1   20180802    huobi       bchusdt   bchusdt
2   20180802    huobi       ethusdt   ethusdt
3   20180802    huobi       etcusdt   etcusdt
4   20180802    huobi       ltcusdt   ltcusdt
5   20180802    huobi       eosusdt   eosusdt
6   20180802    huobi       xrpusdt   xrpusdt
7   20180802    huobi       omgusdt   omgusdt
8   20180802    huobi      dashusdt  dashusdt
9   20180802    huobi       zecusdt   zecusdt
```
