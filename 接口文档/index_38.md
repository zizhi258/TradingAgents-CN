# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=36  
**爬取时间**: 2025-08-09 22:32:33

---

## 资产负债表

---

接口：balancesheet，可以通过[**数据工具**](https://tushare.pro/webclient/)调试和查看数据。
描述：获取上市公司资产负债表
积分：用户需要至少2000积分才可以调取，具体请参阅[积分获取办法](https://tushare.pro/document/1?doc_id=13)

提示：当前接口只能按单只股票获取其历史数据，如果需要获取某一季度全部上市公司数据，请使用balancesheet\_vip接口（参数一致），需积攒5000积分。

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | Y | 股票代码 |
| ann\_date | str | N | 公告日期(YYYYMMDD格式，下同) |
| start\_date | str | N | 公告开始日期 |
| end\_date | str | N | 公告结束日期 |
| period | str | N | 报告期(每个季度最后一天的日期，比如20171231表示年报，20170630半年报，20170930三季报) |
| report\_type | str | N | 报告类型：见下方详细说明 |
| comp\_type | str | N | 公司类型：1一般工商业 2银行 3保险 4证券 |

**输出参数**

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | Y | TS股票代码 |
| ann\_date | str | Y | 公告日期 |
| f\_ann\_date | str | Y | 实际公告日期 |
| end\_date | str | Y | 报告期 |
| report\_type | str | Y | 报表类型 |
| comp\_type | str | Y | 公司类型(1一般工商业2银行3保险4证券) |
| end\_type | str | Y | 报告期类型 |
| total\_share | float | Y | 期末总股本 |
| cap\_rese | float | Y | 资本公积金 |
| undistr\_porfit | float | Y | 未分配利润 |
| surplus\_rese | float | Y | 盈余公积金 |
| special\_rese | float | Y | 专项储备 |
| money\_cap | float | Y | 货币资金 |
| trad\_asset | float | Y | 交易性金融资产 |
| notes\_receiv | float | Y | 应收票据 |
| accounts\_receiv | float | Y | 应收账款 |
| oth\_receiv | float | Y | 其他应收款 |
| prepayment | float | Y | 预付款项 |
| div\_receiv | float | Y | 应收股利 |
| int\_receiv | float | Y | 应收利息 |
| inventories | float | Y | 存货 |
| amor\_exp | float | Y | 待摊费用 |
| nca\_within\_1y | float | Y | 一年内到期的非流动资产 |
| sett\_rsrv | float | Y | 结算备付金 |
| loanto\_oth\_bank\_fi | float | Y | 拆出资金 |
| premium\_receiv | float | Y | 应收保费 |
| reinsur\_receiv | float | Y | 应收分保账款 |
| reinsur\_res\_receiv | float | Y | 应收分保合同准备金 |
| pur\_resale\_fa | float | Y | 买入返售金融资产 |
| oth\_cur\_assets | float | Y | 其他流动资产 |
| total\_cur\_assets | float | Y | 流动资产合计 |
| fa\_avail\_for\_sale | float | Y | 可供出售金融资产 |
| htm\_invest | float | Y | 持有至到期投资 |
| lt\_eqt\_invest | float | Y | 长期股权投资 |
| invest\_real\_estate | float | Y | 投资性房地产 |
| time\_deposits | float | Y | 定期存款 |
| oth\_assets | float | Y | 其他资产 |
| lt\_rec | float | Y | 长期应收款 |
| fix\_assets | float | Y | 固定资产 |
| cip | float | Y | 在建工程 |
| const\_materials | float | Y | 工程物资 |
| fixed\_assets\_disp | float | Y | 固定资产清理 |
| produc\_bio\_assets | float | Y | 生产性生物资产 |
| oil\_and\_gas\_assets | float | Y | 油气资产 |
| intan\_assets | float | Y | 无形资产 |
| r\_and\_d | float | Y | 研发支出 |
| goodwill | float | Y | 商誉 |
| lt\_amor\_exp | float | Y | 长期待摊费用 |
| defer\_tax\_assets | float | Y | 递延所得税资产 |
| decr\_in\_disbur | float | Y | 发放贷款及垫款 |
| oth\_nca | float | Y | 其他非流动资产 |
| total\_nca | float | Y | 非流动资产合计 |
| cash\_reser\_cb | float | Y | 现金及存放中央银行款项 |
| depos\_in\_oth\_bfi | float | Y | 存放同业和其它金融机构款项 |
| prec\_metals | float | Y | 贵金属 |
| deriv\_assets | float | Y | 衍生金融资产 |
| rr\_reins\_une\_prem | float | Y | 应收分保未到期责任准备金 |
| rr\_reins\_outstd\_cla | float | Y | 应收分保未决赔款准备金 |
| rr\_reins\_lins\_liab | float | Y | 应收分保寿险责任准备金 |
| rr\_reins\_lthins\_liab | float | Y | 应收分保长期健康险责任准备金 |
| refund\_depos | float | Y | 存出保证金 |
| ph\_pledge\_loans | float | Y | 保户质押贷款 |
| refund\_cap\_depos | float | Y | 存出资本保证金 |
| indep\_acct\_assets | float | Y | 独立账户资产 |
| client\_depos | float | Y | 其中：客户资金存款 |
| client\_prov | float | Y | 其中：客户备付金 |
| transac\_seat\_fee | float | Y | 其中:交易席位费 |
| invest\_as\_receiv | float | Y | 应收款项类投资 |
| total\_assets | float | Y | 资产总计 |
| lt\_borr | float | Y | 长期借款 |
| st\_borr | float | Y | 短期借款 |
| cb\_borr | float | Y | 向中央银行借款 |
| depos\_ib\_deposits | float | Y | 吸收存款及同业存放 |
| loan\_oth\_bank | float | Y | 拆入资金 |
| trading\_fl | float | Y | 交易性金融负债 |
| notes\_payable | float | Y | 应付票据 |
| acct\_payable | float | Y | 应付账款 |
| adv\_receipts | float | Y | 预收款项 |
| sold\_for\_repur\_fa | float | Y | 卖出回购金融资产款 |
| comm\_payable | float | Y | 应付手续费及佣金 |
| payroll\_payable | float | Y | 应付职工薪酬 |
| taxes\_payable | float | Y | 应交税费 |
| int\_payable | float | Y | 应付利息 |
| div\_payable | float | Y | 应付股利 |
| oth\_payable | float | Y | 其他应付款 |
| acc\_exp | float | Y | 预提费用 |
| deferred\_inc | float | Y | 递延收益 |
| st\_bonds\_payable | float | Y | 应付短期债券 |
| payable\_to\_reinsurer | float | Y | 应付分保账款 |
| rsrv\_insur\_cont | float | Y | 保险合同准备金 |
| acting\_trading\_sec | float | Y | 代理买卖证券款 |
| acting\_uw\_sec | float | Y | 代理承销证券款 |
| non\_cur\_liab\_due\_1y | float | Y | 一年内到期的非流动负债 |
| oth\_cur\_liab | float | Y | 其他流动负债 |
| total\_cur\_liab | float | Y | 流动负债合计 |
| bond\_payable | float | Y | 应付债券 |
| lt\_payable | float | Y | 长期应付款 |
| specific\_payables | float | Y | 专项应付款 |
| estimated\_liab | float | Y | 预计负债 |
| defer\_tax\_liab | float | Y | 递延所得税负债 |
| defer\_inc\_non\_cur\_liab | float | Y | 递延收益-非流动负债 |
| oth\_ncl | float | Y | 其他非流动负债 |
| total\_ncl | float | Y | 非流动负债合计 |
| depos\_oth\_bfi | float | Y | 同业和其它金融机构存放款项 |
| deriv\_liab | float | Y | 衍生金融负债 |
| depos | float | Y | 吸收存款 |
| agency\_bus\_liab | float | Y | 代理业务负债 |
| oth\_liab | float | Y | 其他负债 |
| prem\_receiv\_adva | float | Y | 预收保费 |
| depos\_received | float | Y | 存入保证金 |
| ph\_invest | float | Y | 保户储金及投资款 |
| reser\_une\_prem | float | Y | 未到期责任准备金 |
| reser\_outstd\_claims | float | Y | 未决赔款准备金 |
| reser\_lins\_liab | float | Y | 寿险责任准备金 |
| reser\_lthins\_liab | float | Y | 长期健康险责任准备金 |
| indept\_acc\_liab | float | Y | 独立账户负债 |
| pledge\_borr | float | Y | 其中:质押借款 |
| indem\_payable | float | Y | 应付赔付款 |
| policy\_div\_payable | float | Y | 应付保单红利 |
| total\_liab | float | Y | 负债合计 |
| treasury\_share | float | Y | 减:库存股 |
| ordin\_risk\_reser | float | Y | 一般风险准备 |
| forex\_differ | float | Y | 外币报表折算差额 |
| invest\_loss\_unconf | float | Y | 未确认的投资损失 |
| minority\_int | float | Y | 少数股东权益 |
| total\_hldr\_eqy\_exc\_min\_int | float | Y | 股东权益合计(不含少数股东权益) |
| total\_hldr\_eqy\_inc\_min\_int | float | Y | 股东权益合计(含少数股东权益) |
| total\_liab\_hldr\_eqy | float | Y | 负债及股东权益总计 |
| lt\_payroll\_payable | float | Y | 长期应付职工薪酬 |
| oth\_comp\_income | float | Y | 其他综合收益 |
| oth\_eqt\_tools | float | Y | 其他权益工具 |
| oth\_eqt\_tools\_p\_shr | float | Y | 其他权益工具(优先股) |
| lending\_funds | float | Y | 融出资金 |
| acc\_receivable | float | Y | 应收款项 |
| st\_fin\_payable | float | Y | 应付短期融资款 |
| payables | float | Y | 应付款项 |
| hfs\_assets | float | Y | 持有待售的资产 |
| hfs\_sales | float | Y | 持有待售的负债 |
| cost\_fin\_assets | float | Y | 以摊余成本计量的金融资产 |
| fair\_value\_fin\_assets | float | Y | 以公允价值计量且其变动计入其他综合收益的金融资产 |
| cip\_total | float | Y | 在建工程(合计)(元) |
| oth\_pay\_total | float | Y | 其他应付款(合计)(元) |
| long\_pay\_total | float | Y | 长期应付款(合计)(元) |
| debt\_invest | float | Y | 债权投资(元) |
| oth\_debt\_invest | float | Y | 其他债权投资(元) |
| oth\_eq\_invest | float | N | 其他权益工具投资(元) |
| oth\_illiq\_fin\_assets | float | N | 其他非流动金融资产(元) |
| oth\_eq\_ppbond | float | N | 其他权益工具:永续债(元) |
| receiv\_financing | float | N | 应收款项融资 |
| use\_right\_assets | float | N | 使用权资产 |
| lease\_liab | float | N | 租赁负债 |
| contract\_assets | float | Y | 合同资产 |
| contract\_liab | float | Y | 合同负债 |
| accounts\_receiv\_bill | float | Y | 应收票据及应收账款 |
| accounts\_pay | float | Y | 应付票据及应付账款 |
| oth\_rcv\_total | float | Y | 其他应收款(合计)（元） |
| fix\_assets\_total | float | Y | 固定资产(合计)(元) |
| update\_flag | str | Y | 更新标识 |

**接口使用说明**

```
pro = ts.pro_api()

df = pro.balancesheet(ts_code='600000.SH', start_date='20180101', end_date='20180730', fields='ts_code,ann_date,f_ann_date,end_date,report_type,comp_type,cap_rese')
```

获取某一季度全部股票数据

```
df2 = pro.balancesheet_vip(period='20181231',fields='ts_code,ann_date,f_ann_date,end_date,report_type,comp_type,cap_rese')
```

**数据样例**

```
ts_code  ann_date f_ann_date  end_date report_type comp_type  \
0  600000.SH  20180830   20180830  20180630           1         2
1  600000.SH  20180428   20180428  20180331           1         2

             cap_rese
0  8.176000e+10
1  8.176000e+10
```

**主要报表类型说明**

| 代码 | 类型 | 说明 |
| --- | --- | --- |
| 1 | 合并报表 | 上市公司最新报表（默认） |
| 2 | 单季合并 | 单一季度的合并报表 |
| 3 | 调整单季合并表 | 调整后的单季合并报表（如果有） |
| 4 | 调整合并报表 | 本年度公布上年同期的财务报表数据，报告期为上年度 |
| 5 | 调整前合并报表 | 数据发生变更，将原数据进行保留，即调整前的原数据 |
| 6 | 母公司报表 | 该公司母公司的财务报表数据 |
| 7 | 母公司单季表 | 母公司的单季度表 |
| 8 | 母公司调整单季表 | 母公司调整后的单季表 |
| 9 | 母公司调整表 | 该公司母公司的本年度公布上年同期的财务报表数据 |
| 10 | 母公司调整前报表 | 母公司调整之前的原始财务报表数据 |
| 11 | 母公司调整前合并报表 | 母公司调整之前合并报表原数据 |
| 12 | 母公司调整前报表 | 母公司报表发生变更前保留的原数据 |
