# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=321  
**爬取时间**: 2025-08-09 22:35:31

---

## 东方财富热板

---

接口：dc\_hot
描述：获取东方财富App热榜数据，包括A股市场、ETF基金、港股市场、美股市场等等，每日盘中提取4次，收盘后4次，最晚22点提取一次。
限量：单次最大2000条，可根据日期等参数循环获取全部数据
积分：用户积8000积分可调取使用，积分获取办法请参阅[积分获取办法](https://tushare.pro/document/1?doc_id=13)

注意：本接口只限个人学习和研究使用，如需商业用途，请自行联系东方财富解决数据采购问题。

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| trade\_date | str | N | 交易日期 |
| ts\_code | str | N | TS代码 |
| market | str | N | 类型(A股市场、ETF基金、港股市场、美股市场) |
| hot\_type | str | N | 热点类型(人气榜、飙升榜) |
| is\_new | str | N | 是否最新（默认Y，如果为N则为盘中和盘后阶段采集，具体时间可参考rank\_time字段，状态N每小时更新一次，状态Y更新时间为22：30） |

**输出参数**

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| trade\_date | str | Y | 交易日期 |
| data\_type | str | Y | 数据类型 |
| ts\_code | str | Y | 股票代码 |
| ts\_name | str | Y | 股票名称 |
| rank | int | Y | 排行或者热度 |
| pct\_change | float | Y | 涨跌幅% |
| current\_price | float | Y | 当前价 |
| rank\_time | str | Y | 排行榜获取时间 |

**接口示例**

```
#获取查询月份券商金股
df = pro.dc_hot(trade_date='20240415', market='A股市场',hot_type='人气榜',  fields='ts_code,ts_name,rank')
```

**数据示例**

```
ts_code   ts_name  rank
0   601099.SH     太平洋     1
1   601995.SH    中金公司     2
2   002235.SZ    安妮股份     3
3   601136.SH    首创证券     4
4   600127.SH    金健米业     5
..        ...     ...   ...
95  300675.SZ     建科院    96
96  601900.SH    南方传媒    97
97  600280.SH    中央商场    98
98  300898.SZ    熊猫乳品    99
99  600519.SH    贵州茅台   100
```

**数据来源**

![](https://tushare.pro/files/web/dc1.jpg)
![](https://tushare.pro/files/web/dc2.png)
