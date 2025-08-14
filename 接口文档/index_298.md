# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=296  
**爬取时间**: 2025-08-09 22:35:16

---

## 股票技术因子（量化因子）

---

接口：stk\_factor
描述：获取股票每日技术面因子数据，用于跟踪股票当前走势情况，数据由Tushare社区自产，覆盖全历史
限量：单次最大10000条，可以循环或者分页提取
积分：5000积分每分钟可以请求100次，8000积分以上每分钟500次，具体请参阅[积分获取办法](https://tushare.pro/document/1?doc_id=13)

```
注：
1、本接口的前复权行情是从最新一个交易日开始往前复权，是历史当日的数据快照数据不更新
2、pro_bar接口的前复权是动态复权，即以end_date参数开始往前复权，与本接口会存在不一致的可能
3、本接口技术指标都是基于前复权价格计算
```

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | N | 股票代码 |
| trade\_date | str | N | 交易日期 （yyyymmdd，下同） |
| start\_date | str | N | 开始日期 |
| end\_date | str | N | 结束日期 |

**输出参数**

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | Y | 股票代码 |
| trade\_date | str | Y | 交易日期 |
| close | float | Y | 收盘价 |
| open | float | Y | 开盘价 |
| high | float | Y | 最高价 |
| low | float | Y | 最低价 |
| pre\_close | float | Y | 昨收价 |
| change | float | Y | 涨跌额 |
| pct\_change | float | Y | 涨跌幅 |
| vol | float | Y | 成交量 （手） |
| amount | float | Y | 成交额 （千元） |
| adj\_factor | float | Y | 复权因子 |
| open\_hfq | float | Y | 开盘价后复权 |
| open\_qfq | float | Y | 开盘价前复权 |
| close\_hfq | float | Y | 收盘价后复权 |
| close\_qfq | float | Y | 收盘价前复权 |
| high\_hfq | float | Y | 最高价后复权 |
| high\_qfq | float | Y | 最高价前复权 |
| low\_hfq | float | Y | 最低价后复权 |
| low\_qfq | float | Y | 最低价前复权 |
| pre\_close\_hfq | float | Y | 昨收价后复权 |
| pre\_close\_qfq | float | Y | 昨收价前复权 |
| macd\_dif | float | Y | MCAD\_DIF (基于前复权价格计算，下同) |
| macd\_dea | float | Y | MCAD\_DEA |
| macd | float | Y | MCAD |
| kdj\_k | float | Y | KDJ\_K |
| kdj\_d | float | Y | KDJ\_D |
| kdj\_j | float | Y | KDJ\_J |
| rsi\_6 | float | Y | RSI\_6 |
| rsi\_12 | float | Y | RSI\_12 |
| rsi\_24 | float | Y | RSI\_24 |
| boll\_upper | float | Y | BOLL\_UPPER |
| boll\_mid | float | Y | BOLL\_MID |
| boll\_lower | float | Y | BOLL\_LOWER |
| cci | float | Y | CCI |

**接口用法**

```
pro = ts.pro_api()

df = pro.stk_factor(ts_code='600000.SH', start_date='20220501', end_date='20220520', fields='ts_code,trade_date,macd,kdj_k,kdj_d,kdj_j')
```

**数据样例**

```
ts_code trade_date   macd   kdj_k   kdj_d   kdj_j
0   600000.SH   20220520   0.027  72.966  64.718   89.46
1   600000.SH   20220519   0.015  63.615  60.594  69.656
2   600000.SH   20220518   0.023  67.645  59.084  84.766
3   600000.SH   20220517   0.025  68.134  54.804  94.794
4   600000.SH   20220516   0.014  60.309  48.139  84.649
5   600000.SH   20220513   0.006  55.328  42.054  81.877
6   600000.SH   20220512  -0.022  37.046  35.417  40.306
7   600000.SH   20220511  -0.027  33.948  34.602   32.64
8   600000.SH   20220510   -0.03  30.652  34.929  22.098
9   600000.SH   20220509  -0.029  28.029  37.067   9.952
10  600000.SH   20220506  -0.018  37.498  41.587  29.321
11  600000.SH   20220505  -0.004  48.139  43.631  57.155
```
