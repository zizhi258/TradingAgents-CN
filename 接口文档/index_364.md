# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=362  
**爬取时间**: 2025-08-09 22:35:58

---

## 东方财富概念板块

---

接口：dc\_index
描述：获取东方财富每个交易日的概念板块数据，支持按日期查询
限量：单次最大可获取5000条数据，历史数据可根据日期循环获取
权限：用户积累5000积分可调取，具体请参阅[积分获取办法](https://tushare.pro/document/1?doc_id=13)

注意：本接口只限个人学习和研究使用，如需商业用途，请自行联系东方财富解决数据采购问题。

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | N | 指数代码（支持多个代码同时输入，用逗号分隔） |
| name | str | N | 板块名称（例如：人形机器人） |
| trade\_date | str | N | 交易日期（YYYYMMDD格式，下同） |
| start\_date | str | N | 开始日期 |
| end\_date | str | N | 结束日期 |

**输出参数**

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | Y | 概念代码 |
| trade\_date | str | Y | 交易日期 |
| name | str | Y | 概念名称 |
| leading | str | Y | 领涨股票名称 |
| leading\_code | str | Y | 领涨股票代码 |
| pct\_change | float | Y | 涨跌幅 |
| leading\_pct | float | Y | 领涨股票涨跌幅 |
| total\_mv | float | Y | 总市值（万元） |
| turnover\_rate | float | Y | 换手率 |
| up\_num | int | Y | 上涨家数 |
| down\_num | int | Y | 下降家数 |

**接口示例**

```
#获取东方财富2025年1月3日的概念板块列表
df = pro.dc_index(trade_date='20250103', fields='ts_code,name,turnover_rate,up_num,down_num')
```

**数据示例**

```
ts_code   name       turnover_rate  up_num  down_num
0    BK1186.DC   首发经济        8.3700       4        31
1    BK1185.DC   冰雪经济        4.0800       2        32
2    BK1184.DC  人形机器人        4.0800       2        62
3    BK1183.DC   谷子经济        4.6300       2        55
4    BK1182.DC   智谱AI        5.4000       0        33
..         ...    ...           ...     ...       ...
453  BK0498.DC    AB股        1.7300       4        67
454  BK0494.DC   节能环保        2.1600      32       378
455  BK0493.DC    新能源        1.4800      19       184
456  BK0492.DC    煤化工        1.7000      16        56
457  BK0490.DC     军工        2.5200      32       465
```
