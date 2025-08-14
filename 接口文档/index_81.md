# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=79  
**爬取时间**: 2025-08-09 22:33:01

---

## 财务指标数据

---

接口：fina\_indicator，可以通过[**数据工具**](https://tushare.pro/webclient/)调试和查看数据。
描述：获取上市公司财务指标数据，为避免服务器压力，现阶段每次请求最多返回100条记录，可通过设置日期多次请求获取更多数据。
权限：用户需要至少2000积分才可以调取，具体请参阅[积分获取办法](https://tushare.pro/document/1?doc_id=13)

提示：当前接口只能按单只股票获取其历史数据，如果需要获取某一季度全部上市公司数据，请使用fina\_indicator\_vip接口（参数一致），需积攒5000积分。

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | Y | TS股票代码,e.g. 600001.SH/000001.SZ |
| ann\_date | str | N | 公告日期 |
| start\_date | str | N | 报告期开始日期 |
| end\_date | str | N | 报告期结束日期 |
| period | str | N | 报告期(每个季度最后一天的日期,比如20171231表示年报) |

**输出参数**

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | Y | TS代码 |
| ann\_date | str | Y | 公告日期 |
| end\_date | str | Y | 报告期 |
| eps | float | Y | 基本每股收益 |
| dt\_eps | float | Y | 稀释每股收益 |
| total\_revenue\_ps | float | Y | 每股营业总收入 |
| revenue\_ps | float | Y | 每股营业收入 |
| capital\_rese\_ps | float | Y | 每股资本公积 |
| surplus\_rese\_ps | float | Y | 每股盈余公积 |
| undist\_profit\_ps | float | Y | 每股未分配利润 |
| extra\_item | float | Y | 非经常性损益 |
| profit\_dedt | float | Y | 扣除非经常性损益后的净利润（扣非净利润） |
| gross\_margin | float | Y | 毛利 |
| current\_ratio | float | Y | 流动比率 |
| quick\_ratio | float | Y | 速动比率 |
| cash\_ratio | float | Y | 保守速动比率 |
| invturn\_days | float | N | 存货周转天数 |
| arturn\_days | float | N | 应收账款周转天数 |
| inv\_turn | float | N | 存货周转率 |
| ar\_turn | float | Y | 应收账款周转率 |
| ca\_turn | float | Y | 流动资产周转率 |
| fa\_turn | float | Y | 固定资产周转率 |
| assets\_turn | float | Y | 总资产周转率 |
| op\_income | float | Y | 经营活动净收益 |
| valuechange\_income | float | N | 价值变动净收益 |
| interst\_income | float | N | 利息费用 |
| daa | float | N | 折旧与摊销 |
| ebit | float | Y | 息税前利润 |
| ebitda | float | Y | 息税折旧摊销前利润 |
| fcff | float | Y | 企业自由现金流量 |
| fcfe | float | Y | 股权自由现金流量 |
| current\_exint | float | Y | 无息流动负债 |
| noncurrent\_exint | float | Y | 无息非流动负债 |
| interestdebt | float | Y | 带息债务 |
| netdebt | float | Y | 净债务 |
| tangible\_asset | float | Y | 有形资产 |
| working\_capital | float | Y | 营运资金 |
| networking\_capital | float | Y | 营运流动资本 |
| invest\_capital | float | Y | 全部投入资本 |
| retained\_earnings | float | Y | 留存收益 |
| diluted2\_eps | float | Y | 期末摊薄每股收益 |
| bps | float | Y | 每股净资产 |
| ocfps | float | Y | 每股经营活动产生的现金流量净额 |
| retainedps | float | Y | 每股留存收益 |
| cfps | float | Y | 每股现金流量净额 |
| ebit\_ps | float | Y | 每股息税前利润 |
| fcff\_ps | float | Y | 每股企业自由现金流量 |
| fcfe\_ps | float | Y | 每股股东自由现金流量 |
| netprofit\_margin | float | Y | 销售净利率 |
| grossprofit\_margin | float | Y | 销售毛利率 |
| cogs\_of\_sales | float | Y | 销售成本率 |
| expense\_of\_sales | float | Y | 销售期间费用率 |
| profit\_to\_gr | float | Y | 净利润/营业总收入 |
| saleexp\_to\_gr | float | Y | 销售费用/营业总收入 |
| adminexp\_of\_gr | float | Y | 管理费用/营业总收入 |
| finaexp\_of\_gr | float | Y | 财务费用/营业总收入 |
| impai\_ttm | float | Y | 资产减值损失/营业总收入 |
| gc\_of\_gr | float | Y | 营业总成本/营业总收入 |
| op\_of\_gr | float | Y | 营业利润/营业总收入 |
| ebit\_of\_gr | float | Y | 息税前利润/营业总收入 |
| roe | float | Y | 净资产收益率 |
| roe\_waa | float | Y | 加权平均净资产收益率 |
| roe\_dt | float | Y | 净资产收益率(扣除非经常损益) |
| roa | float | Y | 总资产报酬率 |
| npta | float | Y | 总资产净利润 |
| roic | float | Y | 投入资本回报率 |
| roe\_yearly | float | Y | 年化净资产收益率 |
| roa2\_yearly | float | Y | 年化总资产报酬率 |
| roe\_avg | float | N | 平均净资产收益率(增发条件) |
| opincome\_of\_ebt | float | N | 经营活动净收益/利润总额 |
| investincome\_of\_ebt | float | N | 价值变动净收益/利润总额 |
| n\_op\_profit\_of\_ebt | float | N | 营业外收支净额/利润总额 |
| tax\_to\_ebt | float | N | 所得税/利润总额 |
| dtprofit\_to\_profit | float | N | 扣除非经常损益后的净利润/净利润 |
| salescash\_to\_or | float | N | 销售商品提供劳务收到的现金/营业收入 |
| ocf\_to\_or | float | N | 经营活动产生的现金流量净额/营业收入 |
| ocf\_to\_opincome | float | N | 经营活动产生的现金流量净额/经营活动净收益 |
| capitalized\_to\_da | float | N | 资本支出/折旧和摊销 |
| debt\_to\_assets | float | Y | 资产负债率 |
| assets\_to\_eqt | float | Y | 权益乘数 |
| dp\_assets\_to\_eqt | float | Y | 权益乘数(杜邦分析) |
| ca\_to\_assets | float | Y | 流动资产/总资产 |
| nca\_to\_assets | float | Y | 非流动资产/总资产 |
| tbassets\_to\_totalassets | float | Y | 有形资产/总资产 |
| int\_to\_talcap | float | Y | 带息债务/全部投入资本 |
| eqt\_to\_talcapital | float | Y | 归属于母公司的股东权益/全部投入资本 |
| currentdebt\_to\_debt | float | Y | 流动负债/负债合计 |
| longdeb\_to\_debt | float | Y | 非流动负债/负债合计 |
| ocf\_to\_shortdebt | float | Y | 经营活动产生的现金流量净额/流动负债 |
| debt\_to\_eqt | float | Y | 产权比率 |
| eqt\_to\_debt | float | Y | 归属于母公司的股东权益/负债合计 |
| eqt\_to\_interestdebt | float | Y | 归属于母公司的股东权益/带息债务 |
| tangibleasset\_to\_debt | float | Y | 有形资产/负债合计 |
| tangasset\_to\_intdebt | float | Y | 有形资产/带息债务 |
| tangibleasset\_to\_netdebt | float | Y | 有形资产/净债务 |
| ocf\_to\_debt | float | Y | 经营活动产生的现金流量净额/负债合计 |
| ocf\_to\_interestdebt | float | N | 经营活动产生的现金流量净额/带息债务 |
| ocf\_to\_netdebt | float | N | 经营活动产生的现金流量净额/净债务 |
| ebit\_to\_interest | float | N | 已获利息倍数(EBIT/利息费用) |
| longdebt\_to\_workingcapital | float | N | 长期债务与营运资金比率 |
| ebitda\_to\_debt | float | N | 息税折旧摊销前利润/负债合计 |
| turn\_days | float | Y | 营业周期 |
| roa\_yearly | float | Y | 年化总资产净利率 |
| roa\_dp | float | Y | 总资产净利率(杜邦分析) |
| fixed\_assets | float | Y | 固定资产合计 |
| profit\_prefin\_exp | float | N | 扣除财务费用前营业利润 |
| non\_op\_profit | float | N | 非营业利润 |
| op\_to\_ebt | float | N | 营业利润／利润总额 |
| nop\_to\_ebt | float | N | 非营业利润／利润总额 |
| ocf\_to\_profit | float | N | 经营活动产生的现金流量净额／营业利润 |
| cash\_to\_liqdebt | float | N | 货币资金／流动负债 |
| cash\_to\_liqdebt\_withinterest | float | N | 货币资金／带息流动负债 |
| op\_to\_liqdebt | float | N | 营业利润／流动负债 |
| op\_to\_debt | float | N | 营业利润／负债合计 |
| roic\_yearly | float | N | 年化投入资本回报率 |
| total\_fa\_trun | float | N | 固定资产合计周转率 |
| profit\_to\_op | float | Y | 利润总额／营业收入 |
| q\_opincome | float | N | 经营活动单季度净收益 |
| q\_investincome | float | N | 价值变动单季度净收益 |
| q\_dtprofit | float | N | 扣除非经常损益后的单季度净利润 |
| q\_eps | float | N | 每股收益(单季度) |
| q\_netprofit\_margin | float | N | 销售净利率(单季度) |
| q\_gsprofit\_margin | float | N | 销售毛利率(单季度) |
| q\_exp\_to\_sales | float | N | 销售期间费用率(单季度) |
| q\_profit\_to\_gr | float | N | 净利润／营业总收入(单季度) |
| q\_saleexp\_to\_gr | float | Y | 销售费用／营业总收入 (单季度) |
| q\_adminexp\_to\_gr | float | N | 管理费用／营业总收入 (单季度) |
| q\_finaexp\_to\_gr | float | N | 财务费用／营业总收入 (单季度) |
| q\_impair\_to\_gr\_ttm | float | N | 资产减值损失／营业总收入(单季度) |
| q\_gc\_to\_gr | float | Y | 营业总成本／营业总收入 (单季度) |
| q\_op\_to\_gr | float | N | 营业利润／营业总收入(单季度) |
| q\_roe | float | Y | 净资产收益率(单季度) |
| q\_dt\_roe | float | Y | 净资产单季度收益率(扣除非经常损益) |
| q\_npta | float | Y | 总资产净利润(单季度) |
| q\_opincome\_to\_ebt | float | N | 经营活动净收益／利润总额(单季度) |
| q\_investincome\_to\_ebt | float | N | 价值变动净收益／利润总额(单季度) |
| q\_dtprofit\_to\_profit | float | N | 扣除非经常损益后的净利润／净利润(单季度) |
| q\_salescash\_to\_or | float | N | 销售商品提供劳务收到的现金／营业收入(单季度) |
| q\_ocf\_to\_sales | float | Y | 经营活动产生的现金流量净额／营业收入(单季度) |
| q\_ocf\_to\_or | float | N | 经营活动产生的现金流量净额／经营活动净收益(单季度) |
| basic\_eps\_yoy | float | Y | 基本每股收益同比增长率(%) |
| dt\_eps\_yoy | float | Y | 稀释每股收益同比增长率(%) |
| cfps\_yoy | float | Y | 每股经营活动产生的现金流量净额同比增长率(%) |
| op\_yoy | float | Y | 营业利润同比增长率(%) |
| ebt\_yoy | float | Y | 利润总额同比增长率(%) |
| netprofit\_yoy | float | Y | 归属母公司股东的净利润同比增长率(%) |
| dt\_netprofit\_yoy | float | Y | 归属母公司股东的净利润-扣除非经常损益同比增长率(%) |
| ocf\_yoy | float | Y | 经营活动产生的现金流量净额同比增长率(%) |
| roe\_yoy | float | Y | 净资产收益率(摊薄)同比增长率(%) |
| bps\_yoy | float | Y | 每股净资产相对年初增长率(%) |
| assets\_yoy | float | Y | 资产总计相对年初增长率(%) |
| eqt\_yoy | float | Y | 归属母公司的股东权益相对年初增长率(%) |
| tr\_yoy | float | Y | 营业总收入同比增长率(%) |
| or\_yoy | float | Y | 营业收入同比增长率(%) |
| q\_gr\_yoy | float | N | 营业总收入同比增长率(%)(单季度) |
| q\_gr\_qoq | float | N | 营业总收入环比增长率(%)(单季度) |
| q\_sales\_yoy | float | Y | 营业收入同比增长率(%)(单季度) |
| q\_sales\_qoq | float | N | 营业收入环比增长率(%)(单季度) |
| q\_op\_yoy | float | N | 营业利润同比增长率(%)(单季度) |
| q\_op\_qoq | float | Y | 营业利润环比增长率(%)(单季度) |
| q\_profit\_yoy | float | N | 净利润同比增长率(%)(单季度) |
| q\_profit\_qoq | float | N | 净利润环比增长率(%)(单季度) |
| q\_netprofit\_yoy | float | N | 归属母公司股东的净利润同比增长率(%)(单季度) |
| q\_netprofit\_qoq | float | N | 归属母公司股东的净利润环比增长率(%)(单季度) |
| equity\_yoy | float | Y | 净资产同比增长率 |
| rd\_exp | float | N | 研发费用 |
| update\_flag | str | N | 更新标识 |

**接口用法**

```
pro = ts.pro_api()

df = pro.fina_indicator(ts_code='600000.SH')
```

或者

```
df = pro.query('fina_indicator', ts_code='600000.SH', start_date='20170101', end_date='20180801')
```

**数据样例**

```
ts_code  ann_date  end_date   eps  dt_eps  total_revenue_ps  revenue_ps  \
0  600000.SH  20180830  20180630  0.95    0.95            2.8024      2.8024
1  600000.SH  20180428  20180331  0.46    0.46            1.3501      1.3501
2  600000.SH  20180428  20171231  1.84    1.84            5.7447      5.7447
3  600000.SH  20180428  20171231  1.84    1.84            5.7447      5.7447
4  600000.SH  20171028  20170930  1.45    1.45            4.2507      4.2507
5  600000.SH  20171028  20170930  1.45    1.45            4.2507      4.2507
6  600000.SH  20170830  20170630  0.97    0.97            2.9659      2.9659
7  600000.SH  20170427  20170331  0.63    0.63            1.9595      1.9595
8  600000.SH  20170427  20170331  0.63    0.63            1.9595      1.9595
```
