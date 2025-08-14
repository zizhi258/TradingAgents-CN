# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=134  
**爬取时间**: 2025-08-09 22:33:36

---

## Tushare期货数据

---

1、Tushare期货交易所代码表

| 交易所名称 | 交易所代码 | 合约后缀 |
| --- | --- | --- |
| 郑州商品交易所 | CZCE | .ZCE |
| 上海期货交易所 | SHFE | .SHF |
| 大连商品交易所 | DCE | .DCE |
| 中国金融期货交易所 | CFFEX | .CFX |
| 上海国际能源交易所 | INE | .INE |
| 广州期货交易所 | GFEX | .GFE |

2、合约代码规则

| 主力合约 | 连续合约 | 普通合约 |
| --- | --- | --- |
| XX | XXL | XXMMDD |
| 例如：CU.SHF | 例如：CUL.SHF   例外：TL0表示30年期国债主力合约，TL表示T合约的主连合约，TLL表示TL合约的主连合约 | 例如：CU1811.SHF |
|  |  |  |
|  |  |  |

中金所

| 主力合约 | 连续合约 |
| --- | --- |
| IF.CFX ：沪深300期货主力合约 | IFL.CFX ：沪深300期货当月 |
|  | IFL1.CFX ：沪深300期货次月 |
|  | IFL2.CFX：沪深300期货当季 |
|  | IFL3.CFX：沪深300期货下季 |

中金所其他合约规则同上

3、一些数据规则
 在Tushare期货数据里，如果提取跟行情相关的数据，例如日线行情、每日结算参数等，都是带交易所后缀的，比如CU1811.SHF ；如果是提取跟品种相关数据，例如持仓排名，仓单数据等，只需要输入品种代码，比如CU:沪深300期货

4、目前提供的数据列表

| 数据名称 | API | 描述 | 需要最低积分 | 每分钟次数 |
| --- | --- | --- | --- | --- |
| [期货合约列表](https://tushare.pro/document/2?doc_id=135) | fut\_basic | 全部历史 | 2000 | 80 |
| [期货交易日历](https://tushare.pro/document/2?doc_id=137) | trade\_cal | 数据开始月1996年1月，定期更新 | 2000 | 200 |
| [期货日线行情](https://tushare.pro/document/2?doc_id=138) | fut\_daily | 数据开始月1996年1月，每日盘后更新 | 2000 | 120 |
| [每日成交持仓排名](https://tushare.pro/document/2?doc_id=139) | fut\_holding | 数据开始月2002年1月，每日盘后更新 | 2000 | 200 |
| [仓单日报](https://tushare.pro/document/2?doc_id=140) | fut\_wsr | 数据开始月2006年1月，每日盘后更新 | 2000 | 200 |
| [结算参数](https://tushare.pro/document/2?doc_id=141) | fut\_settle | 数据开始月2012年1月，每日盘后更新 | 2000 | 200 |
|  |  |  |  |  |

注：Tushare积分5000以上，正常调取无限制。(积分越高频次越高)
