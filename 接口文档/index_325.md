# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=323  
**爬取时间**: 2025-08-09 22:35:33

---

## 柜台流通式债券最优报价

---

接口：bc\_bestotcqt
描述：柜台流通式债券最优报价
限量：单次最大2000，可多次提取，总量不限制
积分：用户需要至少500积分可以试用调取，2000积分以上频次相对较高，积分越多权限越大，具体请参阅[积分获取办法](https://tushare.pro/document/1?doc_id=13)

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| trade\_date | str | N | 报价日期(YYYYMMDD格式，下同) |
| start\_date | str | N | 开始日期 |
| end\_date | str | N | 结束日期 |
| ts\_code | str | N | TS代码 |

**输出参数**

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| trade\_date | str | N | 报价日期 |
| ts\_code | str | N | 债券编码 |
| name | str | N | 债券简称 |
| remain\_maturity | str | N | 剩余期限 |
| bond\_type | str | N | 债券类型 |
| best\_buy\_bank | str | N | 最优报买价方 |
| best\_buy\_yield | float | N | 投资者最优买入价到期收益率（%） |
| best\_buy\_price | float | N | 投资者最优买入全价 |
| best\_sell\_bank | str | N | 最优卖报价方 |
| best\_sell\_yield | float | N | 投资者最优卖出价到期收益率（%） |
| best\_sell\_price | float | N | 投资者最优卖出全价 |

**接口示例**

```
pro = ts.pro_api(your token)
#获取柜台流通式债券最优报价
df = pro.bc_bestotcqt(ts_code='200013.BC',start_date='20240325',end_date='20240329',fields='trade_date,ts_code,name,remain_maturity,best_buy_bank,best_buy_yield,best_sell_bank,best_sell_yield')
```

**数据示例**

```
trade_date ts_code name remain_maturity best_buy_bank best_buy_yield best_sell_bank best_sell_yield
0   20240325  200013.BC  20附息国债13     1年211天       建设银行         1.9041        工商银行          1.9227
1   20240326  200013.BC  20附息国债13     1年210天       工商银行         1.8813        工商银行          1.9133
2   20240327  200013.BC  20附息国债13     1年209天       工商银行         1.8718        工商银行          1.9039
3   20240328  200013.BC  20附息国债13     1年208天       工商银行         1.8623        建设银行          1.8921
4   20240329  200013.BC  20附息国债13     1年207天       工商银行         1.8528        交通银行          1.8464
```
