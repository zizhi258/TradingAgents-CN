# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=100  
**爬取时间**: 2025-08-09 22:33:14

---

## 股票曾用名

---

接口：namechange
描述：历史名称变更记录

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | N | TS代码 |
| start\_date | str | N | 公告开始日期 |
| end\_date | str | N | 公告结束日期 |

**输出参数**

| 名称 | 类型 | 默认输出 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | Y | TS代码 |
| name | str | Y | 证券名称 |
| start\_date | str | Y | 开始日期 |
| end\_date | str | Y | 结束日期 |
| ann\_date | str | Y | 公告日期 |
| change\_reason | str | Y | 变更原因 |

**接口示例**

```
pro = ts.pro_api()

df = pro.namechange(ts_code='600848.SH', fields='ts_code,name,start_date,end_date,change_reason')
```

**数据样例**

```
ts_code    name    start_date   end_date      change_reason
0  600848.SH   上海临港   20151118      None         改名
1  600848.SH   自仪股份   20070514  20151117         撤销ST
2  600848.SH   ST自仪     20061026  20070513         完成股改
3  600848.SH   SST自仪   20061009  20061025        未股改加S
4  600848.SH   ST自仪     20010508  20061008         ST
5  600848.SH   自仪股份  19940324  20010507         其他
```
