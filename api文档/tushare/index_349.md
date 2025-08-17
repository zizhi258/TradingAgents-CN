# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=347  
**爬取时间**: 2025-08-09 22:35:48

---

## 开盘啦榜单数据

---

接口：kpl\_list
描述：获取开盘啦涨停、跌停、炸板等榜单数据
限量：单次最大8000条数据，可根据日期循环获取历史数据
积分：5000积分每分钟可以请求200次每天总量1万次，8000积分以上每分钟500次每天总量不限制，具体请参阅[积分获取办法](https://tushare.pro/document/1?doc_id=13)

注：开盘啦是一个优秀的专业打板app，有兴趣的用户可以自行下载安装。本接口仅限用于量化研究，如需商业用途，请自行联系开盘APP官方。

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | N | 股票代码 |
| trade\_date | str | N | 交易日期 |
| tag | str | N | 板单类型（涨停/炸板/跌停/自然涨停/竞价) |
| start\_date | str | N | 开始日期 |
| end\_date | str | N | 结束日期 |

**输出参数**

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | Y | 代码 |
| name | str | Y | 名称 |
| trade\_date | str | Y | 交易时间 |
| lu\_time | str | Y | 涨停时间 |
| ld\_time | str | Y | 跌停时间 |
| open\_time | str | Y | 开板时间 |
| last\_time | str | Y | 最后涨停时间 |
| lu\_desc | str | Y | 涨停原因 |
| tag | str | Y | 标签 |
| theme | str | Y | 板块 |
| net\_change | float | Y | 主力净额(元) |
| bid\_amount | float | Y | 竞价成交额(元) |
| status | str | Y | 状态（N连板） |
| bid\_change | float | Y | 竞价净额 |
| bid\_turnover | float | Y | 竞价换手% |
| lu\_bid\_vol | float | Y | 涨停委买额 |
| pct\_chg | float | Y | 涨跌幅% |
| bid\_pct\_chg | float | Y | 竞价涨幅% |
| rt\_pct\_chg | float | Y | 实时涨幅% |
| limit\_order | float | Y | 封单 |
| amount | float | Y | 成交额 |
| turnover\_rate | float | Y | 换手率% |
| free\_float | float | Y | 实际流通 |
| lu\_limit\_order | float | Y | 最大封单 |

**接口用法**

```
pro = ts.pro_api()

df = pro.kpl_list(trade_date='20240927', tag='涨停', fields='ts_code,name,trade_date,tag,theme,status')
```

**数据样例**

```
ts_code  name      trade_date tag         theme         status
0    000762.SZ  西藏矿业   20240927  涨停       锂矿、盐湖提锂     首板
1    300399.SZ  天利科技   20240927  涨停    互联网金融、金融概念     首板
2    002673.SZ  西部证券   20240927  涨停      证券、控参股基金     首板
3    002050.SZ  三花智控   20240927  涨停  汽车热管理、比亚迪产业链     首板
4    600801.SH  华新水泥   20240927  涨停        水泥、地产链     首板
..         ...   ...        ...  ..           ...    ...
126  600696.SH  岩石股份   20240927  涨停         白酒、酿酒    2连板
127  600606.SH  绿地控股   20240927  涨停       房地产、地产链    2连板
128  000882.SZ  华联股份   20240927  涨停      零售、互联网金融    2连板
129  000069.SZ  华侨城Ａ   20240927  涨停       房地产、地产链    2连板
130  002570.SZ   贝因美   20240927  涨停       多胎概念、乳业     首板
```
