# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=388  
**爬取时间**: 2025-08-09 22:36:15

---

## 港股财务指标数据

---

接口：hk\_fina\_indicator，可以通过[**数据工具**](https://tushare.pro/webclient/)调试和查看数据。
描述：获取港股上市公司财务指标数据，为避免服务器压力，现阶段每次请求最多返回200条记录，可通过设置日期多次请求获取更多数据。
权限：需单独开权限或有15000积分，具体权限信息请参考[权限列表](https://tushare.pro/document/1?doc_id=290)
提示：当前接口按单只股票获取其历史数据，单次请求最大返回10000行数据，可循环提取

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | Y | 股票代码 |
| period | str | N | 报告期(格式：YYYYMMDD） |
| report\_type | str | N | 报告期类型（Q1一季报Q2半年报Q3三季报Q4年报） |
| start\_date | str | N | 报告期开始日期(格式：YYYYMMDD） |
| end\_date | str | N | 报告结束日期(格式：YYYYMMDD） |

**输出参数**

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | Y | 股票代码 |
| name | str | Y | 股票名称 |
| end\_date | str | Y | 报告期 |
| ind\_type | str | Y | 报告类型,Q-按报告期(季度),Y-按年度 |
| report\_type | str | Y | 报告期类型 |
| std\_report\_date | str | Y | 标准报告期 |
| per\_netcash\_operate | float | Y | 每股经营现金流(元) |
| per\_oi | float | Y | 每股营业收入(元) |
| bps | float | Y | 每股净资产(元) |
| basic\_eps | float | Y | 基本每股收益(元) |
| diluted\_eps | float | Y | 稀释每股收益(元) |
| operate\_income | float | Y | 营业总收入(元) |
| operate\_income\_yoy | float | Y | 营业总收入同比增长(%) |
| gross\_profit | float | Y | 毛利润(元) |
| gross\_profit\_yoy | float | Y | 毛利润同比增长(%) |
| holder\_profit | float | Y | 归母净利润(元) |
| holder\_profit\_yoy | float | Y | 归母净利润同比增长(%) |
| gross\_profit\_ratio | float | Y | 毛利率(%) |
| eps\_ttm | float | Y | ttm每股收益(元) |
| operate\_income\_qoq | float | Y | 营业总收入滚动环比增长(%) |
| net\_profit\_ratio | float | Y | 净利率(%) |
| roe\_avg | float | Y | 平均净资产收益率(%) |
| gross\_profit\_qoq | float | Y | 毛利润滚动环比增长(%) |
| roa | float | Y | 总资产净利率(%) |
| holder\_profit\_qoq | float | Y | 归母净利润滚动环比增长(%) |
| roe\_yearly | float | Y | 年化净资产收益率(%) |
| roic\_yearly | float | Y | 年化投资回报率(%) |
| total\_assets | float | Y | 资产总额 |
| total\_liabilities | float | Y | 负债总额 |
| tax\_ebt | float | Y | 所得税/利润总额(%) |
| ocf\_sales | float | Y | 经营现金流/营业收入(%) |
| total\_parent\_equity | float | Y | 本公司权益持有人应占权益 |
| debt\_asset\_ratio | float | Y | 资产负债率(%) |
| operate\_profit | float | Y | 经营盈利 |
| pretax\_profit | float | Y | 除税前盈利 |
| netcash\_operate | float | Y | 经营活动所得现金流量净额 |
| netcash\_invest | float | Y | 投资活动耗用现金流量净额 |
| netcash\_finance | float | Y | 融资活动耗用现金流量净额 |
| end\_cash | float | Y | 期末的现金及现金等价物 |
| divi\_ratio | float | Y | 分红比例 |
| dividend\_rate | float | Y | 股息率 |
| current\_ratio | float | Y | 流动比率(倍) |
| common\_acs | float | Y | 普通股应计股息 |
| currentdebt\_debt | float | Y | 流动负债/总负债(%) |
| issued\_common\_shares | float | Y | 已发行普通股 |
| hk\_common\_shares | float | Y | 港股本 |
| per\_shares | float | Y | 每手股数 |
| total\_market\_cap | float | Y | 总市值 |
| hksk\_market\_cap | float | Y | 港股市值 |
| pe\_ttm | float | Y | 滚动市盈率 |
| pb\_ttm | float | Y | 滚动市净率 |
| report\_date\_sq | str | Y | 季报日期 |
| report\_type\_sq | str | Y | 报告类型 |
| operate\_income\_sq | float | Y | 营业收入 |
| dps\_hkd | float | Y | 每股股息（港元） |
| operate\_income\_qoq\_sq | float | Y | 营业收入环比 |
| net\_profit\_ratio\_sq | float | Y | 净利润率 |
| holder\_profit\_sq | float | Y | 归属于股东净利润 |
| holder\_profit\_qoq\_sq | float | Y | 归母净利润环比 |
| roe\_avg\_sq | float | Y | 平均净资产收益率 |
| pe\_ttm\_sq | float | Y | 季报滚动市盈率 |
| pb\_ttm\_sq | float | Y | 季报滚动市净率 |
| roa\_sq | float | Y | 总资产收益率 |
| start\_date | float | Y | 会计年度起始日 |
| fiscal\_year | float | Y | 会计年度截止日 |
| currency | str | Y | 币种 港元（hkd） |
| is\_cny\_code | float | Y | 是否人民币代码 |
| dps\_hkd\_ly | float | Y | 上一年每股股息 |
| org\_type | str | Y | 企业类型 |
| premium\_income | float | Y | 保费收入 |
| premium\_income\_yoy | float | Y | 保费收入同比 |
| net\_interest\_income | float | Y | 净利息收入 |
| net\_interest\_income\_yoy | float | Y | 净利息收入同比 |
| fee\_commission\_income | float | Y | 手续费及佣金收入 |
| fee\_commission\_income\_yoy | float | Y | 手续费及佣金收入同比 |
| accounts\_rece\_tdays | float | Y | 应收账款周转率(次) |
| inventory\_tdays | float | Y | 存货周转率(次) |
| current\_assets\_tdays | float | Y | 流动资产周转率(次) |
| total\_assets\_tdays | float | Y | 总资产周转率(次) |
| premium\_expense | float | Y | 保险赔付支出 |
| loan\_deposit | float | Y | 贷款/存款 |
| loan\_equity | float | Y | 贷款/股东权益 |
| loan\_assets | float | Y | 贷款/总资产 |
| deposit\_equity | float | Y | 存款/股东权益 |
| deposit\_assets | float | Y | 存款/总资产 |
| equity\_multiplier | float | Y | 权益乘数 |
| equity\_ratio | float | Y | 产权比率 |

注：输出指标太多可在接口fields参数设定你需要的指标，例如：fields='ts\_coe,bps,basic\_eps'

**接口用法**

```yaml
pro = ts.pro_api()

#获取港股腾讯控股00700.HK股票2014年度的财务指标数据
df = pro.hk_fina_indicator(ts_code='00700.HK', period='20241231')

#获取港股腾讯控股00700.HK股票历年年报财务指标数据
df = pro.hk_fina_indicator(ts_code='00700.HK', report_type='Q4')
```

**数据样例**

```
ts_code  name  end_date  ... deposit_assets equity_multiplier equity_ratio
0   00700.HK  腾讯控股  20250331  ...           None            1.7083       0.7644
1   00700.HK  腾讯控股  20241231  ...           None            1.6899       0.7469
2   00700.HK  腾讯控股  20240930  ...           None            1.7576       0.8140
3   00700.HK  腾讯控股  20240630  ...           None            1.7841       0.8451
4   00700.HK  腾讯控股  20240331  ...           None            1.7962       0.8601
..       ...   ...       ...  ...            ...               ...          ...
86  00700.HK  腾讯控股  20030930  ...           None               NaN          NaN
87  00700.HK  腾讯控股  20030630  ...           None               NaN          NaN
88  00700.HK  腾讯控股  20030331  ...           None               NaN          NaN
89  00700.HK  腾讯控股  20021231  ...           None            1.0794       0.0794
90  00700.HK  腾讯控股  20011231  ...           None            1.3563       0.3563
```
