# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=246  
**爬取时间**: 2025-08-09 22:34:44

---

## 可转债转股价变动

---

接口：cb\_price\_chg
描述：获取可转债转股价变动
限量：单次最大2000，总量不限制
权限：本接口需单独开权限（跟积分没关系），具体请参阅[积分获取办法](https://tushare.pro/document/1?doc_id=290)

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | Y | 转债代码，支持多值输入 |

**输出参数**

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | Y | 转债代码 |
| bond\_short\_name | str | Y | 转债简称 |
| publish\_date | str | Y | 公告日期 |
| change\_date | str | Y | 变动日期 |
| convert\_price\_initial | float | Y | 初始转股价格 |
| convertprice\_bef | float | Y | 修正前转股价格 |
| convertprice\_aft | float | Y | 修正后转股价格 |

**接口示例**

```
pro = ts.pro_api(your token)
#获取可转债转股价变动
df = pro.cb_price_chg(ts_code="113556.SH,128114.SZ,128110.SZ",fields="ts_code,bond_short_name,change_date,convert_price_initial,convertprice_bef,convertprice_aft")
```

**数据示例**

```
ts_code bond_short_name change_date convert_price_initial convertprice_bef convertprice_aft
0  113556.SH    至纯转债    20191220           29.4700             None             None
1  113556.SH    至纯转债    20200629           29.4700          29.4700          29.3800
2  128110.SZ    永兴转债    20200609           17.1600             None             None
3  128114.SZ    正邦转债    20200617           16.0900             None             None
```
