# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=74  
**爬取时间**: 2025-08-09 22:32:58

---

## 交易所公告

---

接口：exchange\_ann
描述：获取各个交易所公告的即时和历史资讯数据（5分钟更新一次，未来根据服务器压力再做调整）

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| start\_date | datetime | Y | 开始时间 格式：YYYY-MM-DD HH:MM:SS |
| end\_date | datetime | Y | 结束时间 格式：YYYY-MM-DD HH:MM:SS |

**输出参数**

| 名称 | 类型 | 描述 |
| --- | --- | --- |
| title | str | 标题 |
| content | str | 内容 |
| type | str | 类型 |
| url | str | URL |
| datetime | str | 时间 |

**接口用法**

由于数据量可能比较大，我们限定了必须设定起止时间来获取数据，并且每次最多只能取200条数据。

```json
pro = ts.pro_api()

df = pro.exchange_ann(start_date='2018-08-17 16:00:00', end_date='2018-08-17 18:00:00', \
                fields='title, datetime')
```

或者

```json
df = pro.query('exchange_ann', start_date='2018-08-17 16:00:00', end_date='2018-08-17 18:00:00', \
                fields='title, datetime')
```

**数据样例**

```json
title                     datetime
0   关于暂停EDU交易以及充提币的通知              2018-08-17 17:34:18
1   关于BCX计划开放提现的公告                    2018-08-17 17:25:41
2   K网国际站关于上线借贷功能的公告              2018-08-17 16:55:03
3   8月17日OCX回购详情                           2018-08-17 16:36:26
4   BigONE 开启官方 Telegram 用户讨论群的公告    2018-08-17 16:18:41
5   关于LBank上线ARTCN/USDT的公告                2018-08-17 16:12:04
```
