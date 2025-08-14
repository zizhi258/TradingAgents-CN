# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=44  
**爬取时间**: 2025-08-09 22:32:38

---

## 现金流量表

---

接口：cashflow，可以通过[**数据工具**](https://tushare.pro/webclient/)调试和查看数据。
描述：获取上市公司现金流量表
积分：用户需要至少2000积分才可以调取，具体请参阅[积分获取办法](https://tushare.pro/document/1?doc_id=13)

提示：当前接口只能按单只股票获取其历史数据，如果需要获取某一季度全部上市公司数据，请使用cashflow\_vip接口（参数一致），需积攒5000积分。

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | Y | 股票代码 |
| ann\_date | str | N | 公告日期（YYYYMMDD格式，下同） |
| f\_ann\_date | str | N | 实际公告日期 |
| start\_date | str | N | 公告开始日期 |
| end\_date | str | N | 公告结束日期 |
| period | str | N | 报告期(每个季度最后一天的日期，比如20171231表示年报，20170630半年报，20170930三季报) |
| report\_type | str | N | 报告类型：见下方详细说明 |
| comp\_type | str | N | 公司类型：1一般工商业 2银行 3保险 4证券 |
| is\_calc | int | N | 是否计算报表 |

**输出参数**

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | Y | TS股票代码 |
| ann\_date | str | Y | 公告日期 |
| f\_ann\_date | str | Y | 实际公告日期 |
| end\_date | str | Y | 报告期 |
| comp\_type | str | Y | 公司类型(1一般工商业2银行3保险4证券) |
| report\_type | str | Y | 报表类型 |
| end\_type | str | Y | 报告期类型 |
| net\_profit | float | Y | 净利润 |
| finan\_exp | float | Y | 财务费用 |
| c\_fr\_sale\_sg | float | Y | 销售商品、提供劳务收到的现金 |
| recp\_tax\_rends | float | Y | 收到的税费返还 |
| n\_depos\_incr\_fi | float | Y | 客户存款和同业存放款项净增加额 |
| n\_incr\_loans\_cb | float | Y | 向中央银行借款净增加额 |
| n\_inc\_borr\_oth\_fi | float | Y | 向其他金融机构拆入资金净增加额 |
| prem\_fr\_orig\_contr | float | Y | 收到原保险合同保费取得的现金 |
| n\_incr\_insured\_dep | float | Y | 保户储金净增加额 |
| n\_reinsur\_prem | float | Y | 收到再保业务现金净额 |
| n\_incr\_disp\_tfa | float | Y | 处置交易性金融资产净增加额 |
| ifc\_cash\_incr | float | Y | 收取利息和手续费净增加额 |
| n\_incr\_disp\_faas | float | Y | 处置可供出售金融资产净增加额 |
| n\_incr\_loans\_oth\_bank | float | Y | 拆入资金净增加额 |
| n\_cap\_incr\_repur | float | Y | 回购业务资金净增加额 |
| c\_fr\_oth\_operate\_a | float | Y | 收到其他与经营活动有关的现金 |
| c\_inf\_fr\_operate\_a | float | Y | 经营活动现金流入小计 |
| c\_paid\_goods\_s | float | Y | 购买商品、接受劳务支付的现金 |
| c\_paid\_to\_for\_empl | float | Y | 支付给职工以及为职工支付的现金 |
| c\_paid\_for\_taxes | float | Y | 支付的各项税费 |
| n\_incr\_clt\_loan\_adv | float | Y | 客户贷款及垫款净增加额 |
| n\_incr\_dep\_cbob | float | Y | 存放央行和同业款项净增加额 |
| c\_pay\_claims\_orig\_inco | float | Y | 支付原保险合同赔付款项的现金 |
| pay\_handling\_chrg | float | Y | 支付手续费的现金 |
| pay\_comm\_insur\_plcy | float | Y | 支付保单红利的现金 |
| oth\_cash\_pay\_oper\_act | float | Y | 支付其他与经营活动有关的现金 |
| st\_cash\_out\_act | float | Y | 经营活动现金流出小计 |
| n\_cashflow\_act | float | Y | 经营活动产生的现金流量净额 |
| oth\_recp\_ral\_inv\_act | float | Y | 收到其他与投资活动有关的现金 |
| c\_disp\_withdrwl\_invest | float | Y | 收回投资收到的现金 |
| c\_recp\_return\_invest | float | Y | 取得投资收益收到的现金 |
| n\_recp\_disp\_fiolta | float | Y | 处置固定资产、无形资产和其他长期资产收回的现金净额 |
| n\_recp\_disp\_sobu | float | Y | 处置子公司及其他营业单位收到的现金净额 |
| stot\_inflows\_inv\_act | float | Y | 投资活动现金流入小计 |
| c\_pay\_acq\_const\_fiolta | float | Y | 购建固定资产、无形资产和其他长期资产支付的现金 |
| c\_paid\_invest | float | Y | 投资支付的现金 |
| n\_disp\_subs\_oth\_biz | float | Y | 取得子公司及其他营业单位支付的现金净额 |
| oth\_pay\_ral\_inv\_act | float | Y | 支付其他与投资活动有关的现金 |
| n\_incr\_pledge\_loan | float | Y | 质押贷款净增加额 |
| stot\_out\_inv\_act | float | Y | 投资活动现金流出小计 |
| n\_cashflow\_inv\_act | float | Y | 投资活动产生的现金流量净额 |
| c\_recp\_borrow | float | Y | 取得借款收到的现金 |
| proc\_issue\_bonds | float | Y | 发行债券收到的现金 |
| oth\_cash\_recp\_ral\_fnc\_act | float | Y | 收到其他与筹资活动有关的现金 |
| stot\_cash\_in\_fnc\_act | float | Y | 筹资活动现金流入小计 |
| free\_cashflow | float | Y | 企业自由现金流量 |
| c\_prepay\_amt\_borr | float | Y | 偿还债务支付的现金 |
| c\_pay\_dist\_dpcp\_int\_exp | float | Y | 分配股利、利润或偿付利息支付的现金 |
| incl\_dvd\_profit\_paid\_sc\_ms | float | Y | 其中:子公司支付给少数股东的股利、利润 |
| oth\_cashpay\_ral\_fnc\_act | float | Y | 支付其他与筹资活动有关的现金 |
| stot\_cashout\_fnc\_act | float | Y | 筹资活动现金流出小计 |
| n\_cash\_flows\_fnc\_act | float | Y | 筹资活动产生的现金流量净额 |
| eff\_fx\_flu\_cash | float | Y | 汇率变动对现金的影响 |
| n\_incr\_cash\_cash\_equ | float | Y | 现金及现金等价物净增加额 |
| c\_cash\_equ\_beg\_period | float | Y | 期初现金及现金等价物余额 |
| c\_cash\_equ\_end\_period | float | Y | 期末现金及现金等价物余额 |
| c\_recp\_cap\_contrib | float | Y | 吸收投资收到的现金 |
| incl\_cash\_rec\_saims | float | Y | 其中:子公司吸收少数股东投资收到的现金 |
| uncon\_invest\_loss | float | Y | 未确认投资损失 |
| prov\_depr\_assets | float | Y | 加:资产减值准备 |
| depr\_fa\_coga\_dpba | float | Y | 固定资产折旧、油气资产折耗、生产性生物资产折旧 |
| amort\_intang\_assets | float | Y | 无形资产摊销 |
| lt\_amort\_deferred\_exp | float | Y | 长期待摊费用摊销 |
| decr\_deferred\_exp | float | Y | 待摊费用减少 |
| incr\_acc\_exp | float | Y | 预提费用增加 |
| loss\_disp\_fiolta | float | Y | 处置固定、无形资产和其他长期资产的损失 |
| loss\_scr\_fa | float | Y | 固定资产报废损失 |
| loss\_fv\_chg | float | Y | 公允价值变动损失 |
| invest\_loss | float | Y | 投资损失 |
| decr\_def\_inc\_tax\_assets | float | Y | 递延所得税资产减少 |
| incr\_def\_inc\_tax\_liab | float | Y | 递延所得税负债增加 |
| decr\_inventories | float | Y | 存货的减少 |
| decr\_oper\_payable | float | Y | 经营性应收项目的减少 |
| incr\_oper\_payable | float | Y | 经营性应付项目的增加 |
| others | float | Y | 其他 |
| im\_net\_cashflow\_oper\_act | float | Y | 经营活动产生的现金流量净额(间接法) |
| conv\_debt\_into\_cap | float | Y | 债务转为资本 |
| conv\_copbonds\_due\_within\_1y | float | Y | 一年内到期的可转换公司债券 |
| fa\_fnc\_leases | float | Y | 融资租入固定资产 |
| im\_n\_incr\_cash\_equ | float | Y | 现金及现金等价物净增加额(间接法) |
| net\_dism\_capital\_add | float | Y | 拆出资金净增加额 |
| net\_cash\_rece\_sec | float | Y | 代理买卖证券收到的现金净额(元) |
| credit\_impa\_loss | float | Y | 信用减值损失 |
| use\_right\_asset\_dep | float | Y | 使用权资产折旧 |
| oth\_loss\_asset | float | Y | 其他资产减值损失 |
| end\_bal\_cash | float | Y | 现金的期末余额 |
| beg\_bal\_cash | float | Y | 减:现金的期初余额 |
| end\_bal\_cash\_equ | float | Y | 加:现金等价物的期末余额 |
| beg\_bal\_cash\_equ | float | Y | 减:现金等价物的期初余额 |
| update\_flag | str | Y | 更新标志(1最新） |

**输出参数**

**接口使用说明**

```
pro = ts.pro_api()

df = pro.cashflow(ts_code='600000.SH', start_date='20180101', end_date='20180730')
```

获取某一季度全部股票数据

```
df2 = pro.cashflow_vip(period='20181231',fields='')
```

**数据样例**

```
ts_code  ann_date f_ann_date  end_date comp_type report_type    net_profit finan_exp  \
0  600000.SH  20180428   20180428  20180331         2           1           NaN      None
1  600000.SH  20180428   20180428  20171231         2           1  5.500200e+10      None
2  600000.SH  20180428   20180428  20171231         2           1  5.500200e+10      None
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
| 11 | 目公司调整前合并报表 | 母公司调整之前合并报表原数据 |
| 12 | 母公司调整前报表 | 母公司报表发生变更前保留的原数据 |
