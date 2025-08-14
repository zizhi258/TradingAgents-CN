# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=185  
**爬取时间**: 2025-08-09 22:34:08

---

## 可转债基本信息

---

接口：cb\_basic
描述：获取可转债基本信息
限量：单次最大2000，总量不限制
权限：用户需要至少2000积分才可以调取，但有流量控制，5000积分以上频次相对较高，积分越多权限越大，具体请参阅[积分获取办法](https://tushare.pro/document/1?doc_id=13)

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | N | 转债代码 |
| list\_date | str | N | 上市日期 |
| exchange | str | N | 上市地点 |

**输出参数**

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | Y | 转债代码 |
| bond\_full\_name | str | Y | 转债名称 |
| bond\_short\_name | str | Y | 转债简称 |
| cb\_code | str | Y | 转股申报代码 |
| stk\_code | str | Y | 正股代码 |
| stk\_short\_name | str | Y | 正股简称 |
| maturity | float | Y | 发行期限（年） |
| par | float | Y | 面值 |
| issue\_price | float | Y | 发行价格 |
| issue\_size | float | Y | 发行总额（元） |
| remain\_size | float | Y | 债券余额（元） |
| value\_date | str | Y | 起息日期 |
| maturity\_date | str | Y | 到期日期 |
| rate\_type | str | Y | 利率类型 |
| coupon\_rate | float | Y | 票面利率（%） |
| add\_rate | float | Y | 补偿利率（%） |
| pay\_per\_year | int | Y | 年付息次数 |
| list\_date | str | Y | 上市日期 |
| delist\_date | str | Y | 摘牌日 |
| exchange | str | Y | 上市地点 |
| conv\_start\_date | str | Y | 转股起始日 |
| conv\_end\_date | str | Y | 转股截止日 |
| conv\_stop\_date | str | Y | 停止转股日(提前到期) |
| first\_conv\_price | float | Y | 初始转股价 |
| conv\_price | float | Y | 最新转股价 |
| rate\_clause | str | Y | 利率说明 |
| put\_clause | str | N | 赎回条款 |
| maturity\_put\_price | str | N | 到期赎回价格(含税) |
| call\_clause | str | N | 回售条款 |
| reset\_clause | str | N | 特别向下修正条款 |
| conv\_clause | str | N | 转股条款 |
| guarantor | str | N | 担保人 |
| guarantee\_type | str | N | 担保方式 |
| issue\_rating | str | N | 发行信用等级 |
| newest\_rating | str | N | 最新信用等级 |
| rating\_comp | str | N | 最新评级机构 |

**接口示例**

```
pro = ts.pro_api(your token)
#获取可转债基础信息列表
df = pro.cb_basic(fields="ts_code,bond_short_name,stk_code,stk_short_name,list_date,delist_date")
```

**数据示例**

```
ts_code bond_short_name   stk_code stk_short_name   list_date delist_date
0    125002.SZ            万科转债  000002.SZ            万科Ａ  2002-06-28  2004-04-30
1    125009.SZ            宝安转券  000009.SZ           中国宝安  1993-02-10  1996-01-01
2    125069.SZ            侨城转债  000069.SZ           华侨城Ａ  2004-01-16  2005-04-29
3    125301.SZ            丝绸转债  000301.SZ           东方盛虹  1998-09-15  2003-08-28
4    126301.SZ            丝绸转2  000301.SZ           东方盛虹  2002-09-24  2006-09-18
```
