# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=375  
**爬取时间**: 2025-08-09 22:36:06

---

## 北交所新旧代码对照表

---

接口：bse\_mapping
描述：获取北交所股票代码变更后新旧代码映射表数据
限量：单次最大1000条（本接口总数据量300以内）
积分：120积分即可调取

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| o\_code | str | N | 旧代码 |
| n\_code | str | N | 新代码 |

**输出参数**

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| name | str | Y | 股票名称 |
| o\_code | str | Y | 原代码 |
| n\_code | str | Y | 新代码 |
| list\_date | str | Y | 上市日期 |

**接口示例**

```yaml
#获取方大新材新旧代码对照数据
df = pro.bse_mapping(o_code='838163.BJ')

#获取全部变更的股票代码对照表
df = pro.bse_mapping()
```

**数据示例**

```
name     o_code   n_code    list_date
0  方大新材  838163.BJ  920163.BJ  20200727
```
