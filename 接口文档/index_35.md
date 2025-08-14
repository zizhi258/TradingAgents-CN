# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=33  
**爬取时间**: 2025-08-09 22:32:32

---

## 利润表

---

接口：income，可以通过[**数据工具**](https://tushare.pro/webclient/)调试和查看数据。
描述：获取上市公司财务利润表数据
积分：用户需要至少2000积分才可以调取，具体请参阅[积分获取办法](https://tushare.pro/document/1?doc_id=13)

提示：当前接口只能按单只股票获取其历史数据，如果需要获取某一季度全部上市公司数据，请使用income\_vip接口（参数一致），需积攒5000积分。

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | Y | 股票代码 |
| ann\_date | str | N | 公告日期（YYYYMMDD格式，下同） |
| f\_ann\_date | str | N | 实际公告日期 |
| start\_date | str | N | 公告开始日期 |
| end\_date | str | N | 公告结束日期 |
| period | str | N | 报告期(每个季度最后一天的日期，比如20171231表示年报，20170630半年报，20170930三季报) |
| report\_type | str | N | 报告类型，参考文档最下方说明 |
| comp\_type | str | N | 公司类型（1一般工商业2银行3保险4证券） |

**输出参数**

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | Y | TS代码 |
| ann\_date | str | Y | 公告日期 |
| f\_ann\_date | str | Y | 实际公告日期 |
| end\_date | str | Y | 报告期 |
| report\_type | str | Y | 报告类型 见底部表 |
| comp\_type | str | Y | 公司类型(1一般工商业2银行3保险4证券) |
| end\_type | str | Y | 报告期类型 |
| basic\_eps | float | Y | 基本每股收益 |
| diluted\_eps | float | Y | 稀释每股收益 |
| total\_revenue | float | Y | 营业总收入 |
| revenue | float | Y | 营业收入 |
| int\_income | float | Y | 利息收入 |
| prem\_earned | float | Y | 已赚保费 |
| comm\_income | float | Y | 手续费及佣金收入 |
| n\_commis\_income | float | Y | 手续费及佣金净收入 |
| n\_oth\_income | float | Y | 其他经营净收益 |
| n\_oth\_b\_income | float | Y | 加:其他业务净收益 |
| prem\_income | float | Y | 保险业务收入 |
| out\_prem | float | Y | 减:分出保费 |
| une\_prem\_reser | float | Y | 提取未到期责任准备金 |
| reins\_income | float | Y | 其中:分保费收入 |
| n\_sec\_tb\_income | float | Y | 代理买卖证券业务净收入 |
| n\_sec\_uw\_income | float | Y | 证券承销业务净收入 |
| n\_asset\_mg\_income | float | Y | 受托客户资产管理业务净收入 |
| oth\_b\_income | float | Y | 其他业务收入 |
| fv\_value\_chg\_gain | float | Y | 加:公允价值变动净收益 |
| invest\_income | float | Y | 加:投资净收益 |
| ass\_invest\_income | float | Y | 其中:对联营企业和合营企业的投资收益 |
| forex\_gain | float | Y | 加:汇兑净收益 |
| total\_cogs | float | Y | 营业总成本 |
| oper\_cost | float | Y | 减:营业成本 |
| int\_exp | float | Y | 减:利息支出 |
| comm\_exp | float | Y | 减:手续费及佣金支出 |
| biz\_tax\_surchg | float | Y | 减:营业税金及附加 |
| sell\_exp | float | Y | 减:销售费用 |
| admin\_exp | float | Y | 减:管理费用 |
| fin\_exp | float | Y | 减:财务费用 |
| assets\_impair\_loss | float | Y | 减:资产减值损失 |
| prem\_refund | float | Y | 退保金 |
| compens\_payout | float | Y | 赔付总支出 |
| reser\_insur\_liab | float | Y | 提取保险责任准备金 |
| div\_payt | float | Y | 保户红利支出 |
| reins\_exp | float | Y | 分保费用 |
| oper\_exp | float | Y | 营业支出 |
| compens\_payout\_refu | float | Y | 减:摊回赔付支出 |
| insur\_reser\_refu | float | Y | 减:摊回保险责任准备金 |
| reins\_cost\_refund | float | Y | 减:摊回分保费用 |
| other\_bus\_cost | float | Y | 其他业务成本 |
| operate\_profit | float | Y | 营业利润 |
| non\_oper\_income | float | Y | 加:营业外收入 |
| non\_oper\_exp | float | Y | 减:营业外支出 |
| nca\_disploss | float | Y | 其中:减:非流动资产处置净损失 |
| total\_profit | float | Y | 利润总额 |
| income\_tax | float | Y | 所得税费用 |
| n\_income | float | Y | 净利润(含少数股东损益) |
| n\_income\_attr\_p | float | Y | 净利润(不含少数股东损益) |
| minority\_gain | float | Y | 少数股东损益 |
| oth\_compr\_income | float | Y | 其他综合收益 |
| t\_compr\_income | float | Y | 综合收益总额 |
| compr\_inc\_attr\_p | float | Y | 归属于母公司(或股东)的综合收益总额 |
| compr\_inc\_attr\_m\_s | float | Y | 归属于少数股东的综合收益总额 |
| ebit | float | Y | 息税前利润 |
| ebitda | float | Y | 息税折旧摊销前利润 |
| insurance\_exp | float | Y | 保险业务支出 |
| undist\_profit | float | Y | 年初未分配利润 |
| distable\_profit | float | Y | 可分配利润 |
| rd\_exp | float | Y | 研发费用 |
| fin\_exp\_int\_exp | float | Y | 财务费用:利息费用 |
| fin\_exp\_int\_inc | float | Y | 财务费用:利息收入 |
| transfer\_surplus\_rese | float | Y | 盈余公积转入 |
| transfer\_housing\_imprest | float | Y | 住房周转金转入 |
| transfer\_oth | float | Y | 其他转入 |
| adj\_lossgain | float | Y | 调整以前年度损益 |
| withdra\_legal\_surplus | float | Y | 提取法定盈余公积 |
| withdra\_legal\_pubfund | float | Y | 提取法定公益金 |
| withdra\_biz\_devfund | float | Y | 提取企业发展基金 |
| withdra\_rese\_fund | float | Y | 提取储备基金 |
| withdra\_oth\_ersu | float | Y | 提取任意盈余公积金 |
| workers\_welfare | float | Y | 职工奖金福利 |
| distr\_profit\_shrhder | float | Y | 可供股东分配的利润 |
| prfshare\_payable\_dvd | float | Y | 应付优先股股利 |
| comshare\_payable\_dvd | float | Y | 应付普通股股利 |
| capit\_comstock\_div | float | Y | 转作股本的普通股股利 |
| net\_after\_nr\_lp\_correct | float | N | 扣除非经常性损益后的净利润（更正前） |
| credit\_impa\_loss | float | N | 信用减值损失 |
| net\_expo\_hedging\_benefits | float | N | 净敞口套期收益 |
| oth\_impair\_loss\_assets | float | N | 其他资产减值损失 |
| total\_opcost | float | N | 营业总成本（二） |
| amodcost\_fin\_assets | float | N | 以摊余成本计量的金融资产终止确认收益 |
| oth\_income | float | N | 其他收益 |
| asset\_disp\_income | float | N | 资产处置收益 |
| continued\_net\_profit | float | N | 持续经营净利润 |
| end\_net\_profit | float | N | 终止经营净利润 |
| update\_flag | str | Y | 更新标识 |

**接口使用说明**

```
pro = ts.pro_api()

df = pro.income(ts_code='600000.SH', start_date='20180101', end_date='20180730', fields='ts_code,ann_date,f_ann_date,end_date,report_type,comp_type,basic_eps,diluted_eps')
```

获取某一季度全部股票数据

```
df = pro.income_vip(period='20181231',fields='ts_code,ann_date,f_ann_date,end_date,report_type,comp_type,basic_eps,diluted_eps')
```

**数据样例**

```
ts_code  ann_date f_ann_date  end_date report_type comp_type  basic_eps  diluted_eps  \
0  600000.SH  20180428   20180428  20180331           1         2       0.46         0.46
1  600000.SH  20180428   20180428  20180331           1         2       0.46         0.46
2  600000.SH  20180428   20180428  20171231           1         2       1.84         1.84
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
