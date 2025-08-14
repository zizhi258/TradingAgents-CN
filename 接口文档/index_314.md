# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=312  
**爬取时间**: 2025-08-09 22:35:26

---

## 游资每日明细

---

接口：hm\_detail
描述：获取每日游资交易明细，数据开始于2022年8。游资分类名录，请点击[游资名录](https://tushare.pro/document/2?doc_id=311)
限量：单次最多提取2000条记录，可循环调取，总量不限制
积分：用户积10000积分可调取使用，积分获取办法请参阅[积分获取办法](https://tushare.pro/document/1?doc_id=13)

![](https://tushare.pro/files/wx/yzpt.png)

注：数据为当日部分数据，此处只未作为示例效果。

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| trade\_date | str | N | 交易日期(YYYYMMDD) |
| ts\_code | str | N | 股票代码 |
| hm\_name | str | N | 游资名称 |
| start\_date | str | N | 开始日期(YYYYMMDD) |
| end\_date | str | N | 结束日期(YYYYMMDD) |

**输出参数**

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| trade\_date | str | Y | 交易日期 |
| ts\_code | str | Y | 股票代码 |
| ts\_name | str | Y | 股票名称 |
| buy\_amount | float | Y | 买入金额（元） |
| sell\_amount | float | Y | 卖出金额（元） |
| net\_amount | float | Y | 净买卖（元） |
| hm\_name | str | Y | 游资名称 |
| hm\_orgs | str | Y | 关联机构（一般为营业部或机构专用） |
| tag | str | N | 标签 |

**接口示例**

```
pro = ts.pro_api()

#获取单日全部明细
df = pro.hm_detail(trade_date='20230815')
```
