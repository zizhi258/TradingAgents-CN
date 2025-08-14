# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=344  
**爬取时间**: 2025-08-09 22:35:46

---

## 东财概念及行业板块资金流向（DC）

---

接口：moneyflow\_ind\_dc
描述：获取东方财富板块资金流向，每天盘后更新
限量：单次最大可调取5000条数据，可以根据日期和代码循环提取全部数据
积分：5000积分可以调取，具体请参阅[积分获取办法](https://tushare.pro/document/1?doc_id=13)

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | N | 代码 |
| trade\_date | str | N | 交易日期（YYYYMMDD格式，下同） |
| start\_date | str | N | 开始日期 |
| end\_date | str | N | 结束日期 |
| content\_type | str | N | 资金类型(行业、概念、地域) |

**输出参数**

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| trade\_date | str | Y | 交易日期 |
| content\_type | str | Y | 数据类型 |
| ts\_code | str | Y | DC板块代码（行业、概念、地域） |
| name | str | Y | 板块名称 |
| pct\_change | float | Y | 板块涨跌幅（%） |
| close | float | Y | 板块最新指数 |
| net\_amount | float | Y | 今日主力净流入 净额（元） |
| net\_amount\_rate | float | Y | 今日主力净流入净占比% |
| buy\_elg\_amount | float | Y | 今日超大单净流入 净额（元） |
| buy\_elg\_amount\_rate | float | Y | 今日超大单净流入 净占比% |
| buy\_lg\_amount | float | Y | 今日大单净流入 净额（元） |
| buy\_lg\_amount\_rate | float | Y | 今日大单净流入 净占比% |
| buy\_md\_amount | float | Y | 今日中单净流入 净额（元） |
| buy\_md\_amount\_rate | float | Y | 今日中单净流入 净占比% |
| buy\_sm\_amount | float | Y | 今日小单净流入 净额（元） |
| buy\_sm\_amount\_rate | float | Y | 今日小单净流入 净占比% |
| buy\_sm\_amount\_stock | str | Y | 今日主力净流入最大股 |
| rank | int | Y | 序号 |

**接口示例**

```
#获取当日所有板块资金流向
df = pro.moneyflow_ind_dc(trade_date='20240927', fields='trade_date,name,pct_change, close, net_amount,net_amount_rate,rank')
```

**数据示例**

```
trade_date   name    pct_change      close      net_amount net_amount_rate  rank
0    20240927  互联网服务       6.28   16883.55   3056382208.00            3.93     1
1    20240927     证券       8.23  135249.80   2875528704.00            4.64     2
2    20240927   软件开发       8.28     721.35   2733378816.00            3.18     3
3    20240927   酿酒行业       6.47   49330.63   2568183040.00            5.24     4
4    20240927     电池       8.37     731.85   1328346624.00            3.05     5
..        ...    ...        ...        ...             ...             ...   ...
81   20240927   石油行业       2.31    4654.40   -611530368.00           -9.39    82
82   20240927   汽车整车       4.05    1386.22   -629528064.00           -2.42    83
83   20240927   综合行业       3.06    7437.08   -667341600.00           -7.28    84
84   20240927   家电行业       3.95   15815.68   -670035968.00           -2.37    85
85   20240927     银行      -0.33    3401.83  -2340180224.00           -6.41    86
```
