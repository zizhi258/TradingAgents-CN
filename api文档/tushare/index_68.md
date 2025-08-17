# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=66  
**爬取时间**: 2025-08-09 22:32:53

---

## 全球数字货币交易所

---

接口：coinexchanges
描述：获取全球数字货币交易所基本信息。

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| exchange | str | N | 交易所 |
| area\_code | str | N | 地区 （见下面列表） |

**输出参数**

| 名称 | 类型 | 描述 |
| --- | --- | --- |
| exchange | str | 交易所代码 |
| name | str | 交易所名称 |
| pairs | int | 交易对数量 |
| area\_code | str | 所在地区代码 |
| area | str | 所在地区 |
| coin\_trade | str | 支持现货交易 |
| fut\_trade | str | 支持期货交易 |
| oct\_trade | str | 支持场外交易 |
| deep\_share | str | 支持共享交易深度 |
| mineable | str | 支持挖矿交易 |
| desc | str | 交易所简介 |
| website | str | 交易所官网 |
| twitter | str | 交易所twitter |
| facebook | str | 交易所facebook |
| weibo | str | 交易所weibo |

**交易所地区说明**

| 地区代码 | 地区名称 |
| --- | --- |
| ae | 阿联酋 |
| au | 澳大利亚 |
| br | 巴西 |
| by | 白俄罗斯 |
| bz | 伯利兹 |
| ca | 加拿大 |
| cbb | 加勒比 |
| ch | 瑞士 |
| cl | 智利 |
| cn | 中国 |
| cy | 塞浦路斯 |
| dk | 丹麦 |
| ee | 爱沙尼亚 |
| es | 西班牙 |
| hk | 中国香港 |
| id | 印度尼西亚 |
| il | 以色列 |
| in | 印度 |
| jp | 日本 |
| kh | 柬埔寨 |
| kr | 韩国 |
| ky | 开曼群岛 |
| la | 老挝 |
| mn | 蒙古国 |
| mt | 马耳他 |
| mx | 墨西哥 |
| my | 马来西亚 |
| nl | 荷兰 |
| nz | 新西兰 |
| ph | 菲律宾 |
| pl | 波兰 |
| ru | 俄罗斯 |
| sc | 塞舌尔 |
| sg | 新加坡 |
| th | 泰国 |
| tr | 土耳其 |
| tz | 坦桑尼亚 |
| ua | 乌克兰 |
| uk | 英国 |
| us | 美国 |
| vn | 越南 |
| ws | 萨摩亚 |
| za | 南非 |

**接口用法**

```
pro = ts.pro_api()

df = pro.coinexchanges(area_code='us')

#按交易对数量排序
df = df.sort('pairs', ascending=False)
```

或者

```
df = pro.query('coinexchanges', area_code='us')
```

**数据样例**

```
exchange                   name     pairs    area_code  \
128                 cryptopia                    C网   1357        nz
168                    hitbtc                 HitBTC    822        uk
217                      okex                   OKEX    585        us
99               coinexchange           CoinExchange    489      None
199                  livecoin               Livecoin    462      None
24                    binance                 币安网    376      None
271                     yobit                  YoBit    376        ru
191                    kucoin                 库币网    359        us
155                   gate-io           比特儿海外版    355      None
175                      idex                   IDEX    333      None
80                        cex                    CEX    295        sg
55                    bittrex                    B网    280        us
256                     upbit                  Upbit    275        kr
206                  mercatox               Mercatox    275      None
249             trade-satoshi          Trade Satoshi    273        uk
239           stocks-exchange        Stocks.Exchange    273      None
171                  huobipro             火币全球站    272        sc
```
