# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=275  
**爬取时间**: 2025-08-09 22:35:03

---

## 机构调研表

---

接口：stk\_surv
描述：获取上市公司机构调研记录数据
限量：单次最大获取100条数据，可循环或分页提取
积分：用户积5000积分可使用

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | N | 股票代码 |
| trade\_date | str | N | 调研日期 |
| start\_date | str | N | 调研开始日期 |
| end\_date | str | N | 调研结束日期 |

**输出参数**

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | Y | 股票代码 |
| name | str | Y | 股票名称 |
| surv\_date | str | Y | 调研日期 |
| fund\_visitors | str | Y | 机构参与人员 |
| rece\_place | str | Y | 接待地点 |
| rece\_mode | str | Y | 接待方式 |
| rece\_org | str | Y | 接待的公司 |
| org\_type | str | Y | 接待公司类型 |
| comp\_rece | str | Y | 上市公司接待人员 |
| content | None | N | 调研内容 |

**接口用法**

```
pro = ts.pro_api()

df = pro.stk_surv(ts_code='002223.SZ', trade_date='20211024', fields='ts_code,name,surv_date,fund_visitors,rece_place,rece_mode,rece_org')
```

**数据样例**

```
ts_code  name  surv_date fund_visitors rece_place      rece_mode                          rece_org
1   002223.SZ  鱼跃医疗  20211024            郝淼       电话会议    特定对象调研                              宝盈基金
2   002223.SZ  鱼跃医疗  20211024           秦瑶函       电话会议    特定对象调研                           贝莱德资产管理
3   002223.SZ  鱼跃医疗  20211024            谭飞       电话会议    特定对象调研                              博远基金
4   002223.SZ  鱼跃医疗  20211024            李晗       电话会议    特定对象调研                            创金合信基金
..        ...   ...       ...           ...        ...       ...                               ...
77  002223.SZ  鱼跃医疗  20211024           李虹达       电话会议    特定对象调研                              中信建投
78  002223.SZ  鱼跃医疗  20211024           李明蔚       电话会议    特定对象调研                              中银国际
79  002223.SZ  鱼跃医疗  20211024            王俊       电话会议    特定对象调研                            重庆穿石投资
80  002223.SZ  鱼跃医疗  20211024            李扬       电话会议    特定对象调研                              朱雀基金
81  002223.SZ  鱼跃医疗  20211024           徐烨程       电话会议    特定对象调研                            逐流资产管理
```
