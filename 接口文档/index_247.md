# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=245  
**爬取时间**: 2025-08-09 22:34:44

---

## 工业生产者出厂价格指数

---

接口：cn\_ppi
描述：获取PPI工业生产者出厂价格指数数据
限量：单次最大5000，一次可以提取全部数据
权限：用户600积分可以使用，具体请参阅[积分获取办法](https://tushare.pro/document/1?doc_id=13)

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| m | str | N | 月份（YYYYMM，下同），支持多个月份同时输入，逗号分隔 |
| start\_m | str | N | 开始月份 |
| end\_m | str | N | 结束月份 |

**输出参数**

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| month | str | Y | 月份YYYYMM |
| ppi\_yoy | float | Y | PPI：全部工业品：当月同比 |
| ppi\_mp\_yoy | float | Y | PPI：生产资料：当月同比 |
| ppi\_mp\_qm\_yoy | float | Y | PPI：生产资料：采掘业：当月同比 |
| ppi\_mp\_rm\_yoy | float | Y | PPI：生产资料：原料业：当月同比 |
| ppi\_mp\_p\_yoy | float | Y | PPI：生产资料：加工业：当月同比 |
| ppi\_cg\_yoy | float | Y | PPI：生活资料：当月同比 |
| ppi\_cg\_f\_yoy | float | Y | PPI：生活资料：食品类：当月同比 |
| ppi\_cg\_c\_yoy | float | Y | PPI：生活资料：衣着类：当月同比 |
| ppi\_cg\_adu\_yoy | float | Y | PPI：生活资料：一般日用品类：当月同比 |
| ppi\_cg\_dcg\_yoy | float | Y | PPI：生活资料：耐用消费品类：当月同比 |
| ppi\_mom | float | Y | PPI：全部工业品：环比 |
| ppi\_mp\_mom | float | Y | PPI：生产资料：环比 |
| ppi\_mp\_qm\_mom | float | Y | PPI：生产资料：采掘业：环比 |
| ppi\_mp\_rm\_mom | float | Y | PPI：生产资料：原料业：环比 |
| ppi\_mp\_p\_mom | float | Y | PPI：生产资料：加工业：环比 |
| ppi\_cg\_mom | float | Y | PPI：生活资料：环比 |
| ppi\_cg\_f\_mom | float | Y | PPI：生活资料：食品类：环比 |
| ppi\_cg\_c\_mom | float | Y | PPI：生活资料：衣着类：环比 |
| ppi\_cg\_adu\_mom | float | Y | PPI：生活资料：一般日用品类：环比 |
| ppi\_cg\_dcg\_mom | float | Y | PPI：生活资料：耐用消费品类：环比 |
| ppi\_accu | float | Y | PPI：全部工业品：累计同比 |
| ppi\_mp\_accu | float | Y | PPI：生产资料：累计同比 |
| ppi\_mp\_qm\_accu | float | Y | PPI：生产资料：采掘业：累计同比 |
| ppi\_mp\_rm\_accu | float | Y | PPI：生产资料：原料业：累计同比 |
| ppi\_mp\_p\_accu | float | Y | PPI：生产资料：加工业：累计同比 |
| ppi\_cg\_accu | float | Y | PPI：生活资料：累计同比 |
| ppi\_cg\_f\_accu | float | Y | PPI：生活资料：食品类：累计同比 |
| ppi\_cg\_c\_accu | float | Y | PPI：生活资料：衣着类：累计同比 |
| ppi\_cg\_adu\_accu | float | Y | PPI：生活资料：一般日用品类：累计同比 |
| ppi\_cg\_dcg\_accu | float | Y | PPI：生活资料：耐用消费品类：累计同比 |

**接口调用**

```
pro = ts.pro_api()

df = pro.cn_ppi(start_m='201905', end_m='202005')

#获取指定字段
df = pro.cn_ppi(start_m='201905', end_m='202005', fields='month,ppi_yoy,ppi_mom,ppi_accu')
```

**数据样例**

```
month ppi_yoy ppi_mom ppi_accu
0   202005   -3.70   -0.40    -1.70
1   202004   -3.10   -1.30    -1.20
2   202003   -1.50   -1.00    -0.60
3   202002   -0.40   -0.50    -0.20
4   202001    0.10    0.00     0.10
5   201912   -0.50    0.00    -0.30
6   201911   -1.40   -0.10    -0.30
7   201910   -1.60    0.10    -0.20
8   201909   -1.20    0.10     0.00
9   201908   -0.80   -0.10     0.10
10  201907   -0.30   -0.20     0.20
11  201906    0.00   -0.30     0.30
12  201905    0.60    0.20     0.40
```
