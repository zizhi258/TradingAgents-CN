# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=358  
**爬取时间**: 2025-08-09 22:35:55

---

## 指数技术因子(专业版)

---

接口：idx\_factor\_pro
描述：获取指数每日技术面因子数据，用于跟踪指数当前走势情况，数据由Tushare社区自产，覆盖全历史；输出参数\_bfq表示不复权描述中说明了因子的默认传参，如需要特殊参数或者更多因子可以联系管理员评估，指数包括大盘指数 申万行业指数 中信指数
限量：单次最大8000
积分：5000积分每分钟可以请求30次，8000积分以上每分钟500次

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | N | 指数代码(大盘指数 申万指数 中信指数) |
| start\_date | str | N | 开始日期 |
| end\_date | str | N | 结束日期 |
| trade\_date | str | N | 交易日期 |

**输出参数**

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | Y | 指数代码 |
| trade\_date | str | Y | 交易日期 |
| open | float | Y | 开盘价 |
| high | float | Y | 最高价 |
| low | float | Y | 最低价 |
| close | float | Y | 收盘价 |
| pre\_close | float | Y | 昨收价 |
| change | float | Y | 涨跌额 |
| pct\_change | float | Y | 涨跌幅 （未复权，如果是复权请用 通用行情接口 ） |
| vol | float | Y | 成交量 （手） |
| amount | float | Y | 成交额 （千元） |
| asi\_bfq | float | Y | 振动升降指标-OPEN, CLOSE, HIGH, LOW, M1=26, M2=10 |
| asit\_bfq | float | Y | 振动升降指标-OPEN, CLOSE, HIGH, LOW, M1=26, M2=10 |
| atr\_bfq | float | Y | 真实波动N日平均值-CLOSE, HIGH, LOW, N=20 |
| bbi\_bfq | float | Y | BBI多空指标-CLOSE, M1=3, M2=6, M3=12, M4=20 |
| bias1\_bfq | float | Y | BIAS乖离率-CLOSE, L1=6, L2=12, L3=24 |
| bias2\_bfq | float | Y | BIAS乖离率-CLOSE, L1=6, L2=12, L3=24 |
| bias3\_bfq | float | Y | BIAS乖离率-CLOSE, L1=6, L2=12, L3=24 |
| boll\_lower\_bfq | float | Y | BOLL指标，布林带-CLOSE, N=20, P=2 |
| boll\_mid\_bfq | float | Y | BOLL指标，布林带-CLOSE, N=20, P=2 |
| boll\_upper\_bfq | float | Y | BOLL指标，布林带-CLOSE, N=20, P=2 |
| brar\_ar\_bfq | float | Y | BRAR情绪指标-OPEN, CLOSE, HIGH, LOW, M1=26 |
| brar\_br\_bfq | float | Y | BRAR情绪指标-OPEN, CLOSE, HIGH, LOW, M1=26 |
| cci\_bfq | float | Y | 顺势指标又叫CCI指标-CLOSE, HIGH, LOW, N=14 |
| cr\_bfq | float | Y | CR价格动量指标-CLOSE, HIGH, LOW, N=20 |
| dfma\_dif\_bfq | float | Y | 平行线差指标-CLOSE, N1=10, N2=50, M=10 |
| dfma\_difma\_bfq | float | Y | 平行线差指标-CLOSE, N1=10, N2=50, M=10 |
| dmi\_adx\_bfq | float | Y | 动向指标-CLOSE, HIGH, LOW, M1=14, M2=6 |
| dmi\_adxr\_bfq | float | Y | 动向指标-CLOSE, HIGH, LOW, M1=14, M2=6 |
| dmi\_mdi\_bfq | float | Y | 动向指标-CLOSE, HIGH, LOW, M1=14, M2=6 |
| dmi\_pdi\_bfq | float | Y | 动向指标-CLOSE, HIGH, LOW, M1=14, M2=6 |
| downdays | float | Y | 连跌天数 |
| updays | float | Y | 连涨天数 |
| dpo\_bfq | float | Y | 区间震荡线-CLOSE, M1=20, M2=10, M3=6 |
| madpo\_bfq | float | Y | 区间震荡线-CLOSE, M1=20, M2=10, M3=6 |
| ema\_bfq\_10 | float | Y | 指数移动平均-N=10 |
| ema\_bfq\_20 | float | Y | 指数移动平均-N=20 |
| ema\_bfq\_250 | float | Y | 指数移动平均-N=250 |
| ema\_bfq\_30 | float | Y | 指数移动平均-N=30 |
| ema\_bfq\_5 | float | Y | 指数移动平均-N=5 |
| ema\_bfq\_60 | float | Y | 指数移动平均-N=60 |
| ema\_bfq\_90 | float | Y | 指数移动平均-N=90 |
| emv\_bfq | float | Y | 简易波动指标-HIGH, LOW, VOL, N=14, M=9 |
| maemv\_bfq | float | Y | 简易波动指标-HIGH, LOW, VOL, N=14, M=9 |
| expma\_12\_bfq | float | Y | EMA指数平均数指标-CLOSE, N1=12, N2=50 |
| expma\_50\_bfq | float | Y | EMA指数平均数指标-CLOSE, N1=12, N2=50 |
| kdj\_bfq | float | Y | KDJ指标-CLOSE, HIGH, LOW, N=9, M1=3, M2=3 |
| kdj\_d\_bfq | float | Y | KDJ指标-CLOSE, HIGH, LOW, N=9, M1=3, M2=3 |
| kdj\_k\_bfq | float | Y | KDJ指标-CLOSE, HIGH, LOW, N=9, M1=3, M2=3 |
| ktn\_down\_bfq | float | Y | 肯特纳交易通道, N选20日，ATR选10日-CLOSE, HIGH, LOW, N=20, M=10 |
| ktn\_mid\_bfq | float | Y | 肯特纳交易通道, N选20日，ATR选10日-CLOSE, HIGH, LOW, N=20, M=10 |
| ktn\_upper\_bfq | float | Y | 肯特纳交易通道, N选20日，ATR选10日-CLOSE, HIGH, LOW, N=20, M=10 |
| lowdays | float | Y | LOWRANGE(LOW)表示当前最低价是近多少周期内最低价的最小值 |
| topdays | float | Y | TOPRANGE(HIGH)表示当前最高价是近多少周期内最高价的最大值 |
| ma\_bfq\_10 | float | Y | 简单移动平均-N=10 |
| ma\_bfq\_20 | float | Y | 简单移动平均-N=20 |
| ma\_bfq\_250 | float | Y | 简单移动平均-N=250 |
| ma\_bfq\_30 | float | Y | 简单移动平均-N=30 |
| ma\_bfq\_5 | float | Y | 简单移动平均-N=5 |
| ma\_bfq\_60 | float | Y | 简单移动平均-N=60 |
| ma\_bfq\_90 | float | Y | 简单移动平均-N=90 |
| macd\_bfq | float | Y | MACD指标-CLOSE, SHORT=12, LONG=26, M=9 |
| macd\_dea\_bfq | float | Y | MACD指标-CLOSE, SHORT=12, LONG=26, M=9 |
| macd\_dif\_bfq | float | Y | MACD指标-CLOSE, SHORT=12, LONG=26, M=9 |
| mass\_bfq | float | Y | 梅斯线-HIGH, LOW, N1=9, N2=25, M=6 |
| ma\_mass\_bfq | float | Y | 梅斯线-HIGH, LOW, N1=9, N2=25, M=6 |
| mfi\_bfq | float | Y | MFI指标是成交量的RSI指标-CLOSE, HIGH, LOW, VOL, N=14 |
| mtm\_bfq | float | Y | 动量指标-CLOSE, N=12, M=6 |
| mtmma\_bfq | float | Y | 动量指标-CLOSE, N=12, M=6 |
| obv\_bfq | float | Y | 能量潮指标-CLOSE, VOL |
| psy\_bfq | float | Y | 投资者对股市涨跌产生心理波动的情绪指标-CLOSE, N=12, M=6 |
| psyma\_bfq | float | Y | 投资者对股市涨跌产生心理波动的情绪指标-CLOSE, N=12, M=6 |
| roc\_bfq | float | Y | 变动率指标-CLOSE, N=12, M=6 |
| maroc\_bfq | float | Y | 变动率指标-CLOSE, N=12, M=6 |
| rsi\_bfq\_12 | float | Y | RSI指标-CLOSE, N=12 |
| rsi\_bfq\_24 | float | Y | RSI指标-CLOSE, N=24 |
| rsi\_bfq\_6 | float | Y | RSI指标-CLOSE, N=6 |
| taq\_down\_bfq | float | Y | 唐安奇通道(海龟)交易指标-HIGH, LOW, 20 |
| taq\_mid\_bfq | float | Y | 唐安奇通道(海龟)交易指标-HIGH, LOW, 20 |
| taq\_up\_bfq | float | Y | 唐安奇通道(海龟)交易指标-HIGH, LOW, 20 |
| trix\_bfq | float | Y | 三重指数平滑平均线-CLOSE, M1=12, M2=20 |
| trma\_bfq | float | Y | 三重指数平滑平均线-CLOSE, M1=12, M2=20 |
| vr\_bfq | float | Y | VR容量比率-CLOSE, VOL, M1=26 |
| wr\_bfq | float | Y | W&R 威廉指标-CLOSE, HIGH, LOW, N=10, N1=6 |
| wr1\_bfq | float | Y | W&R 威廉指标-CLOSE, HIGH, LOW, N=10, N1=6 |
| xsii\_td1\_bfq | float | Y | 薛斯通道II-CLOSE, HIGH, LOW, N=102, M=7 |
| xsii\_td2\_bfq | float | Y | 薛斯通道II-CLOSE, HIGH, LOW, N=102, M=7 |
| xsii\_td3\_bfq | float | Y | 薛斯通道II-CLOSE, HIGH, LOW, N=102, M=7 |
| xsii\_td4\_bfq | float | Y | 薛斯通道II-CLOSE, HIGH, LOW, N=102, M=7 |
