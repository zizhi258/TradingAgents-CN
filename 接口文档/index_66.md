# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=64  
**爬取时间**: 2025-08-09 22:32:51

---

## 交易所交易费率

---

接口：coinfees
描述：获取交易所当前和历史交易费率，目前支持的有huobi、okex、binance和bitfinex。

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| exchange | str | Y | 交易所 |
| asset\_type | str | N | 交易类别 coin币交易（默认） future期货交易 |

**输出参数**

| 名称 | 类型 | 描述 |
| --- | --- | --- |
| exchange | str | 交易所 |
| level | str | 交易级别和类型 |
| maker\_fee | float | 挂单费率 |
| taker\_fee | float | 吃单费率 |
| asset\_type | str | 资产类别 coin币交易 future期货交易 |
| start\_date | str | 费率开始执行日期 |
| end\_date | str | 本次费率失效日期 |

**exchange说明**

| exchange | 名称 | 优惠情况 |
| --- | --- | --- |
| huobi | 火币 | 按VIP级别不同有优惠，VIP需购买 |
| okex | okex | 按成交额度有优惠 |
| binance | 币安 | 按年优惠 |
| bitfinex | bitfinex | 按成交额度大小优惠 |
| fcoin | fcoin | 交易即挖矿，先收后返 |
| coinex | coin | 交易即挖矿，先收后返 |

**接口用法**

```
pro = ts.pro_api()

df = pro.coinfees(exchange='huobi')
```

或者

```
df = pro.query('coinfees', exchange='okex', asset_type='future')
```

**数据样例**

```
exchange level maker_fee taker_fee asset_type
0    huobi  VIP0     0.002     0.002       coin
1    huobi  VIP1    0.0018    0.0018       coin
2    huobi  VIP2    0.0016    0.0016       coin
3    huobi  VIP3    0.0014    0.0014       coin
4    huobi  VIP4    0.0012    0.0012       coin
5    huobi  VIP5     0.001     0.001       coin
```
