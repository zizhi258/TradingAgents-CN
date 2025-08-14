# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=103  
**爬取时间**: 2025-08-09 22:33:16

---

## 分红送股

---

接口：dividend
描述：分红送股数据
权限：用户需要至少2000积分才可以调取，具体请参阅[积分获取办法](https://tushare.pro/document/1?doc_id=13)

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | N | TS代码 |
| ann\_date | str | N | 公告日 |
| record\_date | str | N | 股权登记日期 |
| ex\_date | str | N | 除权除息日 |
| imp\_ann\_date | str | N | 实施公告日 |

以上参数至少有一个不能为空

**输出参数**

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | Y | TS代码 |
| end\_date | str | Y | 分红年度 |
| ann\_date | str | Y | 预案公告日 |
| div\_proc | str | Y | 实施进度 |
| stk\_div | float | Y | 每股送转 |
| stk\_bo\_rate | float | Y | 每股送股比例 |
| stk\_co\_rate | float | Y | 每股转增比例 |
| cash\_div | float | Y | 每股分红（税后） |
| cash\_div\_tax | float | Y | 每股分红（税前） |
| record\_date | str | Y | 股权登记日 |
| ex\_date | str | Y | 除权除息日 |
| pay\_date | str | Y | 派息日 |
| div\_listdate | str | Y | 红股上市日 |
| imp\_ann\_date | str | Y | 实施公告日 |
| base\_date | str | N | 基准日 |
| base\_share | float | N | 基准股本（万） |

**接口示例**

```
pro = ts.pro_api()

df = pro.dividend(ts_code='600848.SH', fields='ts_code,div_proc,stk_div,record_date,ex_date')
```

**数据样例**

```
ts_code div_proc  stk_div record_date   ex_date
    0  600848.SH       实施     0.10    19950606  19950607
    1  600848.SH       实施     0.10    19970707  19970708
    2  600848.SH       实施     0.15    19960701  19960702
    3  600848.SH       实施     0.10    19980706  19980707
    4  600848.SH       预案     0.00        None      None
    5  600848.SH       实施     0.00    20180522  20180523
```
