# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=215  
**爬取时间**: 2025-08-09 22:34:26

---

## 市场交易统计

---

接口：daily\_info
描述：获取交易所股票交易统计，包括各板块明细
限量：单次最大4000，可循环获取，总量不限制
权限：用户积600积分可调取， 频次有限制，积分越高每分钟调取频次越高，5000积分以上频次相对较高，积分获取方法请参阅[积分获取办法](https://tushare.pro/document/1?doc_id=13)

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| trade\_date | str | N | 交易日期（YYYYMMDD格式，下同） |
| ts\_code | str | N | 板块代码（请参阅下方列表） |
| exchange | str | N | 股票市场（SH上交所 SZ深交所） |
| start\_date | str | N | 开始日期 |
| end\_date | str | N | 结束日期 |
| fields | str | N | 指定提取字段 |

| 板块代码（TS\_CODE） | 板块名称（TS\_NAME） | 数据开始日期 |
| --- | --- | --- |
| SZ\_MARKET | 深圳市场 | 20041231 |
| SZ\_MAIN | 深圳主板 | 20081231 |
| SZ\_A | 深圳A股 | 20080103 |
| SZ\_B | 深圳B股 | 20080103 |
| SZ\_GEM | 创业板 | 20091030 |
| SZ\_SME | 中小企业板 | 20040602 |
| SZ\_FUND | 深圳基金市场 | 20080103 |
| SZ\_FUND\_ETF | 深圳基金ETF | 20080103 |
| SZ\_FUND\_LOF | 深圳基金LOF | 20080103 |
| SZ\_FUND\_CEF | 深圳封闭基金 | 20080103 |
| SZ\_FUND\_SF | 深圳分级基金 | 20080103 |
| SZ\_BOND | 深圳债券 | 20080103 |
| SZ\_BOND\_CN | 深圳债券现券 | 20080103 |
| SZ\_BOND\_REP | 深圳债券回购 | 20080103 |
| SZ\_BOND\_ABS | 深圳债券ABS | 20080103 |
| SZ\_BOND\_GOV | 深圳国债 | 20080103 |
| SZ\_BOND\_ENT | 深圳企业债 | 20080103 |
| SZ\_BOND\_COR | 深圳公司债 | 20080103 |
| SZ\_BOND\_CB | 深圳可转债 | 20080103 |
| SZ\_WR | 深圳权证 | 20080103 |
| ---- | ---- | --- |
| SH\_MARKET | 上海市场 | 20190102 |
| SH\_A | 上海A股 | 19910102 |
| SH\_B | 上海B股 | 19920221 |
| SH\_STAR | 科创板 | 20190722 |
| SH\_REP | 股票回购 | 20190102 |
| SH\_FUND | 上海基金市场 | 19901219 |
| SH\_FUND\_ETF | 上海基金ETF | 19901219 |
| SH\_FUND\_LOF | 上海基金LOF | 19901219 |
| SH\_FUND\_REP | 上海基金回购 | 19901219 |
| SH\_FUND\_CEF | 上海封闭式基金 | 19901219 |
| SH\_FUND\_METF | 上海交易型货币基金 | 19901219 |

**输出参数**

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| trade\_date | str | Y | 交易日期 |
| ts\_code | str | Y | 市场代码 |
| ts\_name | str | Y | 市场名称 |
| com\_count | int | Y | 挂牌数 |
| total\_share | float | Y | 总股本（亿股） |
| float\_share | float | Y | 流通股本（亿股） |
| total\_mv | float | Y | 总市值（亿元） |
| float\_mv | float | Y | 流通市值（亿元） |
| amount | float | Y | 交易金额（亿元） |
| vol | float | Y | 成交量（亿股） |
| trans\_count | int | Y | 成交笔数（万笔） |
| pe | float | Y | 平均市盈率 |
| tr | float | Y | 换手率（％），注：深交所暂无此列 |
| exchange | str | Y | 交易所（SH上交所 SZ深交所） |

**接口示例**

```yaml
#获取深圳市场20200320各板块交易数据
df = pro.daily_info(trade_date='20200320', exchange='SZ')

#获取深圳和上海市场20200320各板块交易指定字段的数据
df = pro.daily_info(trade_date='20200320', exchange='SZ,SH', fields='trade_date,ts_name,pe')
```

**数据示例**

```
trade_date    ts_code ts_name  com_count  total_share  float_share  \
0   20200320     SZ_GME     创业板        802      4124.04      3159.24
1   20200320    SZ_MAIN    深市主板        470      8177.40      7176.03
2   20200320  SZ_MARKET    深圳市场       2220     21657.12     17674.90
3   20200320     SZ_SME   中小企业板        948      9355.67      7339.62

    total_mv   float_mv   amount     vol  trans_count     pe    tr exchange
0   66494.71   44955.24  1475.76   99.65        830.0  50.37   NaN       SZ
1   70732.59   62551.44   961.92  102.30        554.0  16.12   NaN       SZ
2  236813.99  184009.16  4363.01     NaN          NaN  25.46  2.18       SZ
3   99586.67   76502.47  1925.32  179.21       1208.0  27.74   NaN       SZ
```
