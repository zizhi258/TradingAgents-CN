# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=348  
**爬取时间**: 2025-08-09 22:35:49

---

## 个股资金流向（THS）

---

接口：moneyflow\_ths
描述：获取同花顺个股资金流向数据，每日盘后更新
限量：单次最大6000，可根据日期或股票代码循环提取数据
积分：用户需要至少5000积分才可以调取，具体请参阅[积分获取办法](https://tushare.pro/document/1?doc_id=13)

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | N | 股票代码 |
| trade\_date | str | N | 交易日期（YYYYMMDD格式，下同） |
| start\_date | str | N | 开始日期 |
| end\_date | str | N | 结束日期 |

**输出参数**

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| trade\_date | str | Y | 交易日期 |
| ts\_code | str | Y | 股票代码 |
| name | str | Y | 股票名称 |
| pct\_change | float | Y | 涨跌幅 |
| latest | float | Y | 最新价 |
| net\_amount | float | Y | 资金净流入(万元) |
| net\_d5\_amount | float | Y | 5日主力净额(万元) |
| buy\_lg\_amount | float | Y | 今日大单净流入额(万元) |
| buy\_lg\_amount\_rate | float | Y | 今日大单净流入占比(%) |
| buy\_md\_amount | float | Y | 今日中单净流入额(万元) |
| buy\_md\_amount\_rate | float | Y | 今日中单净流入占比(%) |
| buy\_sm\_amount | float | Y | 今日小单净流入额(万元) |
| buy\_sm\_amount\_rate | float | Y | 今日小单净流入占比(%) |

**接口示例**

```yaml
pro = ts.pro_api()

#获取单日全部股票数据
df = pro.moneyflow_ths(trade_date='20241011')

#获取单个股票数据
df = pro.moneyflow_ths(ts_code='002149.SZ', start_date='20241001', end_date='20241011')
```

```
trade_date ts_code  name  pct_change  ...  buy_md_amount  buy_md_amount_rate  buy_sm_amount  buy_sm_amount_rate
0   20241011  002149.SZ  西部材料        2.47  ...         -589.0                5.43         -191.0                1.76
1   20241010  002149.SZ  西部材料        1.22  ...        -2732.0               15.38        -1031.0                5.81
2   20241009  002149.SZ  西部材料        7.00  ...        -1941.0                9.25        -2079.0                9.90
3   20241008  002149.SZ  西部材料        5.17  ...        -2985.0                7.93        -2507.0                6.66
```
