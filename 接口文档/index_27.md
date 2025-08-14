# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=25  
**爬取时间**: 2025-08-09 22:32:27

---

## 基础信息

---

接口：stock\_basic，可以通过[**数据工具**](https://tushare.pro/webclient/)调试和查看数据
描述：获取基础信息数据，包括股票代码、名称、上市日期、退市日期等
权限：2000积分起。此接口是基础信息，调取一次就可以拉取完，建议保存倒本地存储后使用

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | N | TS股票代码 |
| name | str | N | 名称 |
| market | str | N | 市场类别 （主板/创业板/科创板/CDR/北交所） |
| list\_status | str | N | 上市状态 L上市 D退市 P暂停上市，默认是L |
| exchange | str | N | 交易所 SSE上交所 SZSE深交所 BSE北交所 |
| is\_hs | str | N | 是否沪深港通标的，N否 H沪股通 S深股通 |

**输出参数**

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | Y | TS代码 |
| symbol | str | Y | 股票代码 |
| name | str | Y | 股票名称 |
| area | str | Y | 地域 |
| industry | str | Y | 所属行业 |
| fullname | str | N | 股票全称 |
| enname | str | N | 英文全称 |
| cnspell | str | Y | 拼音缩写 |
| market | str | Y | 市场类型（主板/创业板/科创板/CDR） |
| exchange | str | N | 交易所代码 |
| curr\_type | str | N | 交易货币 |
| list\_status | str | N | 上市状态 L上市 D退市 P暂停上市 |
| list\_date | str | Y | 上市日期 |
| delist\_date | str | N | 退市日期 |
| is\_hs | str | N | 是否沪深港通标的，N否 H沪股通 S深股通 |
| act\_name | str | Y | 实控人名称 |
| act\_ent\_type | str | Y | 实控人企业性质 |

说明：旧版上的PE/PB/股本等字段，请在行情接口[“每日指标”](https://tushare.pro/document/2?doc_id=32)中获取。

**接口示例**

```
pro = ts.pro_api()

#查询当前所有正常上市交易的股票列表

data = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,list_date')
```

或者：

```
#查询当前所有正常上市交易的股票列表

data = pro.query('stock_basic', exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,list_date')
```

**数据样例**

```
ts_code     symbol     name     area industry    list_date
0     000001.SZ  000001  平安银行   深圳       银行  19910403
1     000002.SZ  000002   万科A   深圳     全国地产  19910129
2     000004.SZ  000004  国农科技   深圳     生物制药  19910114
3     000005.SZ  000005  世纪星源   深圳     房产服务  19901210
4     000006.SZ  000006  深振业A   深圳     区域地产  19920427
5     000007.SZ  000007   全新好   深圳     酒店餐饮  19920413
6     000008.SZ  000008  神州高铁   北京     运输设备  19920507
7     000009.SZ  000009  中国宝安   深圳      综合类  19910625
8     000010.SZ  000010  美丽生态   深圳     建筑施工  19951027
9     000011.SZ  000011  深物业A   深圳     区域地产  19920330
10    000012.SZ  000012   南玻A   深圳       玻璃  19920228
11    000014.SZ  000014  沙河股份   深圳     全国地产  19920602
12    000016.SZ  000016  深康佳A   深圳     家用电器  19920327
13    000017.SZ  000017  深中华A   深圳     文教休闲  19920331
14    000018.SZ  000018  神州长城   深圳     装修装饰  19920616
15    000019.SZ  000019  深深宝A   深圳      软饮料  19921012
16    000020.SZ  000020  深华发A   深圳      元器件  19920428
17    000021.SZ  000021   深科技   深圳     电脑设备  19940202
18    000022.SZ  000022  深赤湾A   深圳       港口  19930505
19    000023.SZ  000023  深天地A   深圳     其他建材  19930429
20    000025.SZ  000025   特力A   深圳     汽车服务  19930621
```
