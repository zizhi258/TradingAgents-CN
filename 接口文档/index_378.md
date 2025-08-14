# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=376  
**爬取时间**: 2025-08-09 22:36:07

---

## 通达信板块信息

---

接口：tdx\_index
描述：获取通达信板块基础信息，包括概念板块、行业、风格、地域等
限量：单次最大1000条数据，可根据日期参数循环提取
权限：用户积累6000积分可调取，具体请参阅[积分获取办法](https://tushare.pro/document/1?doc_id=13)

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | N | 板块代码：xxxxxx.TDX |
| trade\_date | str | N | 交易日期(格式：YYYYMMDD） |
| idx\_type | str | N | 板块类型：概念板块、行业板块、风格板块、地区板块 |

**输出参数**

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | Y | 板块代码 |
| trade\_date | str | Y | 交易日期 |
| name | str | Y | 板块名称 |
| idx\_type | str | Y | 板块类型 |
| idx\_count | int | Y | 成分个数 |
| total\_share | float | Y | 总股本(亿) |
| float\_share | float | Y | 流通股(亿) |
| total\_mv | float | Y | 总市值(亿) |
| float\_mv | float | Y | 流通市值(亿) |

**接口示例**

```
#获取通达信2025年5月13日的概念板块列表
df = pro.tdx_index(trade_date='20250513', fields='ts_code,name,idx_type,idx_count')
```

**数据示例**

```
ts_code           name     idx_type  idx_count
0    880559.TDX   要约收购     风格板块          6
1    880728.TDX   航运概念     概念板块         64
2    880355.TDX   日用化工     行业板块         20
3    880423.TDX   酒店餐饮     行业板块          9
4    880875.TDX   中小银行     风格板块         28
..          ...    ...      ...        ...
477  880528.TDX  军工信息化     概念板块         99
478  880868.TDX   高贝塔值     风格板块        100
479  880430.TDX     航空     行业板块         52
480  880431.TDX     船舶     行业板块         12
481  880914.TDX   军贸概念     概念板块         25
```
