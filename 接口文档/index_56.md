# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=54  
**爬取时间**: 2025-08-09 22:32:45

---

## 全球数字货币列表

---

接口：coinlist
描述：获取全球数字货币基本信息，包括发行日期、规模、所基于的公链和算法等。

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| issue\_date | str | Y | 发行日期 |
| start\_date | str | N | 开始日期 |
| end\_date | str | N | 结束日期 |

**输出参数**

| 名称 | 类型 | 描述 |
| --- | --- | --- |
| coin | str | 货币代码 |
| en\_name | str | 英文名称 |
| cn\_name | str | 中文名称 |
| issue\_date | str | 发行日期 |
| issue\_price | float | 发行价格（美元） |
| amount | float | 发行总量 |
| supply | float | 流通总量 |
| algo | str | 算法原理 |
| area | str | 发行地区 |
| desc | str | 描述 |
| labels | str | 标签分类 |

**接口用法**

```
pro = ts.pro_api()

df = pro.coinlist(start_date='20170101', end_date='20171231')
```

或者

```
df = pro.query('coinlist', start_date='20170101', end_date='20171231')
```

**数据样例**

```
coin                         en_name  cn_name issue_date        amount \
0    PYLNT                           Pylon     None   20171231  6.338580e+05
1      hlc                      HalalChain    绿色食品链   20171230  1.000000e+09
2      qlc                           Qlink     None   20171230  6.000000e+08
3       XP               Experience Points     None   20171230  2.683600e+11
4      CHT                   CoinHot Token       热币   20171230  3.692800e+08
5      DBC                 DeepBrain Chain      深脑链   20171229  1.000000e+10
6     HTML                        HTMLCoin     None   20171229  9.404459e+10
7      mot                    Olympus Labs     奥林巴斯   20171229  1.000000e+08
8     CPAY                       Cryptopay     None   20171229  9.041474e+07
9      dcr                          Decred     None   20171228  2.100000e+07
10     XPS                          Xpense     None   20171228  2.000000e+10
11     DIM                         DIMCOIN     None   20171228  9.000000e+09
12   ZIBER                           ZIBER     None   20171228  8.000000e+07
13    bnty                        Bounty0x     None   20171227  5.000000e+08
14      gt                         G Token     None   20171227  1.000000e+08
15    bifi                    Bitcoin File     None   20171227  2.100000e+10
16     ent                        ENT Cash     None   20171226  1.600000e+09
17     big                    BigONE Token     None   20171225  2.000000e+08
18     DAI                             Dai     None   20171225  5.561372e+07
19     UGC               United Game Chain     None   20171225  1.000000e+09
20     HCT               Hash Credit Token     None   20171225  1.500000e+09
```
