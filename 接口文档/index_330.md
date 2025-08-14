# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=328  
**爬取时间**: 2025-08-09 22:35:36

---

## 股票技术面因子(专业版)

---

接口：stk\_factor\_pro
描述：获取股票每日技术面因子数据，用于跟踪股票当前走势情况，数据由Tushare社区自产，覆盖全历史；输出参数\_bfq表示不复权，\_qfq表示前复权 \_hfq表示后复权，描述中说明了因子的默认传参，如需要特殊参数或者更多因子可以联系管理员评估
限量：单次调取最多返回10000条数据，可以通过日期参数循环
积分：5000积分每分钟可以请求30次，8000积分以上每分钟500次，具体请参阅[积分获取办法](https://tushare.pro/document/1?doc_id=13)

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | N | 股票代码 |
| trade\_date | str | N | 交易日期(格式：yyyymmdd，下同) |
| start\_date | str | N | 开始日期 |
| end\_date | str | N | 结束日期 |

**输出参数**

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| ts\_code | str | Y | 股票代码 |
| trade\_date | str | Y | 交易日期 |
| open | float | Y | 开盘价 |
| open\_hfq | float | Y | 开盘价（后复权） |
| open\_qfq | float | Y | 开盘价（前复权） |
| high | float | Y | 最高价 |
| high\_hfq | float | Y | 最高价（后复权） |
| high\_qfq | float | Y | 最高价（前复权） |
| low | float | Y | 最低价 |
| low\_hfq | float | Y | 最低价（后复权） |
| low\_qfq | float | Y | 最低价（前复权） |
| close | float | Y | 收盘价 |
| close\_hfq | float | Y | 收盘价（后复权） |
| close\_qfq | float | Y | 收盘价（前复权） |
| pre\_close | float | Y | 昨收价(前复权)--为daily接口的pre\_close,以当时复权因子计算值跟前一日close\_qfq对不上，可不用 |
| change | float | Y | 涨跌额 |
| pct\_chg | float | Y | 涨跌幅 （未复权，如果是复权请用 通用行情接口 ） |
| vol | float | Y | 成交量 （手） |
| amount | float | Y | 成交额 （千元） |
| turnover\_rate | float | Y | 换手率（%） |
| turnover\_rate\_f | float | Y | 换手率（自由流通股） |
| volume\_ratio | float | Y | 量比 |
| pe | float | Y | 市盈率（总市值/净利润， 亏损的PE为空） |
| pe\_ttm | float | Y | 市盈率（TTM，亏损的PE为空） |
| pb | float | Y | 市净率（总市值/净资产） |
| ps | float | Y | 市销率 |
| ps\_ttm | float | Y | 市销率（TTM） |
| dv\_ratio | float | Y | 股息率 （%） |
| dv\_ttm | float | Y | 股息率（TTM）（%） |
| total\_share | float | Y | 总股本 （万股） |
| float\_share | float | Y | 流通股本 （万股） |
| free\_share | float | Y | 自由流通股本 （万） |
| total\_mv | float | Y | 总市值 （万元） |
| circ\_mv | float | Y | 流通市值（万元） |
| adj\_factor | float | Y | 复权因子 |
| asi\_bfq | float | Y | 振动升降指标-OPEN, CLOSE, HIGH, LOW, M1=26, M2=10 |
| asi\_hfq | float | Y | 振动升降指标-OPEN, CLOSE, HIGH, LOW, M1=26, M2=10 |
| asi\_qfq | float | Y | 振动升降指标-OPEN, CLOSE, HIGH, LOW, M1=26, M2=10 |
| asit\_bfq | float | Y | 振动升降指标-OPEN, CLOSE, HIGH, LOW, M1=26, M2=10 |
| asit\_hfq | float | Y | 振动升降指标-OPEN, CLOSE, HIGH, LOW, M1=26, M2=10 |
| asit\_qfq | float | Y | 振动升降指标-OPEN, CLOSE, HIGH, LOW, M1=26, M2=10 |
| atr\_bfq | float | Y | 真实波动N日平均值-CLOSE, HIGH, LOW, N=20 |
| atr\_hfq | float | Y | 真实波动N日平均值-CLOSE, HIGH, LOW, N=20 |
| atr\_qfq | float | Y | 真实波动N日平均值-CLOSE, HIGH, LOW, N=20 |
| bbi\_bfq | float | Y | BBI多空指标-CLOSE, M1=3, M2=6, M3=12, M4=20 |
| bbi\_hfq | float | Y | BBI多空指标-CLOSE, M1=3, M2=6, M3=12, M4=21 |
| bbi\_qfq | float | Y | BBI多空指标-CLOSE, M1=3, M2=6, M3=12, M4=22 |
| bias1\_bfq | float | Y | BIAS乖离率-CLOSE, L1=6, L2=12, L3=24 |
| bias1\_hfq | float | Y | BIAS乖离率-CLOSE, L1=6, L2=12, L3=24 |
| bias1\_qfq | float | Y | BIAS乖离率-CLOSE, L1=6, L2=12, L3=24 |
| bias2\_bfq | float | Y | BIAS乖离率-CLOSE, L1=6, L2=12, L3=24 |
| bias2\_hfq | float | Y | BIAS乖离率-CLOSE, L1=6, L2=12, L3=24 |
| bias2\_qfq | float | Y | BIAS乖离率-CLOSE, L1=6, L2=12, L3=24 |
| bias3\_bfq | float | Y | BIAS乖离率-CLOSE, L1=6, L2=12, L3=24 |
| bias3\_hfq | float | Y | BIAS乖离率-CLOSE, L1=6, L2=12, L3=24 |
| bias3\_qfq | float | Y | BIAS乖离率-CLOSE, L1=6, L2=12, L3=24 |
| boll\_lower\_bfq | float | Y | BOLL指标，布林带-CLOSE, N=20, P=2 |
| boll\_lower\_hfq | float | Y | BOLL指标，布林带-CLOSE, N=20, P=2 |
| boll\_lower\_qfq | float | Y | BOLL指标，布林带-CLOSE, N=20, P=2 |
| boll\_mid\_bfq | float | Y | BOLL指标，布林带-CLOSE, N=20, P=2 |
| boll\_mid\_hfq | float | Y | BOLL指标，布林带-CLOSE, N=20, P=2 |
| boll\_mid\_qfq | float | Y | BOLL指标，布林带-CLOSE, N=20, P=2 |
| boll\_upper\_bfq | float | Y | BOLL指标，布林带-CLOSE, N=20, P=2 |
| boll\_upper\_hfq | float | Y | BOLL指标，布林带-CLOSE, N=20, P=2 |
| boll\_upper\_qfq | float | Y | BOLL指标，布林带-CLOSE, N=20, P=2 |
| brar\_ar\_bfq | float | Y | BRAR情绪指标-OPEN, CLOSE, HIGH, LOW, M1=26 |
| brar\_ar\_hfq | float | Y | BRAR情绪指标-OPEN, CLOSE, HIGH, LOW, M1=26 |
| brar\_ar\_qfq | float | Y | BRAR情绪指标-OPEN, CLOSE, HIGH, LOW, M1=26 |
| brar\_br\_bfq | float | Y | BRAR情绪指标-OPEN, CLOSE, HIGH, LOW, M1=26 |
| brar\_br\_hfq | float | Y | BRAR情绪指标-OPEN, CLOSE, HIGH, LOW, M1=26 |
| brar\_br\_qfq | float | Y | BRAR情绪指标-OPEN, CLOSE, HIGH, LOW, M1=26 |
| cci\_bfq | float | Y | 顺势指标又叫CCI指标-CLOSE, HIGH, LOW, N=14 |
| cci\_hfq | float | Y | 顺势指标又叫CCI指标-CLOSE, HIGH, LOW, N=14 |
| cci\_qfq | float | Y | 顺势指标又叫CCI指标-CLOSE, HIGH, LOW, N=14 |
| cr\_bfq | float | Y | CR价格动量指标-CLOSE, HIGH, LOW, N=20 |
| cr\_hfq | float | Y | CR价格动量指标-CLOSE, HIGH, LOW, N=20 |
| cr\_qfq | float | Y | CR价格动量指标-CLOSE, HIGH, LOW, N=20 |
| dfma\_dif\_bfq | float | Y | 平行线差指标-CLOSE, N1=10, N2=50, M=10 |
| dfma\_dif\_hfq | float | Y | 平行线差指标-CLOSE, N1=10, N2=50, M=10 |
| dfma\_dif\_qfq | float | Y | 平行线差指标-CLOSE, N1=10, N2=50, M=10 |
| dfma\_difma\_bfq | float | Y | 平行线差指标-CLOSE, N1=10, N2=50, M=10 |
| dfma\_difma\_hfq | float | Y | 平行线差指标-CLOSE, N1=10, N2=50, M=10 |
| dfma\_difma\_qfq | float | Y | 平行线差指标-CLOSE, N1=10, N2=50, M=10 |
| dmi\_adx\_bfq | float | Y | 动向指标-CLOSE, HIGH, LOW, M1=14, M2=6 |
| dmi\_adx\_hfq | float | Y | 动向指标-CLOSE, HIGH, LOW, M1=14, M2=6 |
| dmi\_adx\_qfq | float | Y | 动向指标-CLOSE, HIGH, LOW, M1=14, M2=6 |
| dmi\_adxr\_bfq | float | Y | 动向指标-CLOSE, HIGH, LOW, M1=14, M2=6 |
| dmi\_adxr\_hfq | float | Y | 动向指标-CLOSE, HIGH, LOW, M1=14, M2=6 |
| dmi\_adxr\_qfq | float | Y | 动向指标-CLOSE, HIGH, LOW, M1=14, M2=6 |
| dmi\_mdi\_bfq | float | Y | 动向指标-CLOSE, HIGH, LOW, M1=14, M2=6 |
| dmi\_mdi\_hfq | float | Y | 动向指标-CLOSE, HIGH, LOW, M1=14, M2=6 |
| dmi\_mdi\_qfq | float | Y | 动向指标-CLOSE, HIGH, LOW, M1=14, M2=6 |
| dmi\_pdi\_bfq | float | Y | 动向指标-CLOSE, HIGH, LOW, M1=14, M2=6 |
| dmi\_pdi\_hfq | float | Y | 动向指标-CLOSE, HIGH, LOW, M1=14, M2=6 |
| dmi\_pdi\_qfq | float | Y | 动向指标-CLOSE, HIGH, LOW, M1=14, M2=6 |
| downdays | float | Y | 连跌天数 |
| updays | float | Y | 连涨天数 |
| dpo\_bfq | float | Y | 区间震荡线-CLOSE, M1=20, M2=10, M3=6 |
| dpo\_hfq | float | Y | 区间震荡线-CLOSE, M1=20, M2=10, M3=6 |
| dpo\_qfq | float | Y | 区间震荡线-CLOSE, M1=20, M2=10, M3=6 |
| madpo\_bfq | float | Y | 区间震荡线-CLOSE, M1=20, M2=10, M3=6 |
| madpo\_hfq | float | Y | 区间震荡线-CLOSE, M1=20, M2=10, M3=6 |
| madpo\_qfq | float | Y | 区间震荡线-CLOSE, M1=20, M2=10, M3=6 |
| ema\_bfq\_10 | float | Y | 指数移动平均-N=10 |
| ema\_bfq\_20 | float | Y | 指数移动平均-N=20 |
| ema\_bfq\_250 | float | Y | 指数移动平均-N=250 |
| ema\_bfq\_30 | float | Y | 指数移动平均-N=30 |
| ema\_bfq\_5 | float | Y | 指数移动平均-N=5 |
| ema\_bfq\_60 | float | Y | 指数移动平均-N=60 |
| ema\_bfq\_90 | float | Y | 指数移动平均-N=90 |
| ema\_hfq\_10 | float | Y | 指数移动平均-N=10 |
| ema\_hfq\_20 | float | Y | 指数移动平均-N=20 |
| ema\_hfq\_250 | float | Y | 指数移动平均-N=250 |
| ema\_hfq\_30 | float | Y | 指数移动平均-N=30 |
| ema\_hfq\_5 | float | Y | 指数移动平均-N=5 |
| ema\_hfq\_60 | float | Y | 指数移动平均-N=60 |
| ema\_hfq\_90 | float | Y | 指数移动平均-N=90 |
| ema\_qfq\_10 | float | Y | 指数移动平均-N=10 |
| ema\_qfq\_20 | float | Y | 指数移动平均-N=20 |
| ema\_qfq\_250 | float | Y | 指数移动平均-N=250 |
| ema\_qfq\_30 | float | Y | 指数移动平均-N=30 |
| ema\_qfq\_5 | float | Y | 指数移动平均-N=5 |
| ema\_qfq\_60 | float | Y | 指数移动平均-N=60 |
| ema\_qfq\_90 | float | Y | 指数移动平均-N=90 |
| emv\_bfq | float | Y | 简易波动指标-HIGH, LOW, VOL, N=14, M=9 |
| emv\_hfq | float | Y | 简易波动指标-HIGH, LOW, VOL, N=14, M=9 |
| emv\_qfq | float | Y | 简易波动指标-HIGH, LOW, VOL, N=14, M=9 |
| maemv\_bfq | float | Y | 简易波动指标-HIGH, LOW, VOL, N=14, M=9 |
| maemv\_hfq | float | Y | 简易波动指标-HIGH, LOW, VOL, N=14, M=9 |
| maemv\_qfq | float | Y | 简易波动指标-HIGH, LOW, VOL, N=14, M=9 |
| expma\_12\_bfq | float | Y | EMA指数平均数指标-CLOSE, N1=12, N2=50 |
| expma\_12\_hfq | float | Y | EMA指数平均数指标-CLOSE, N1=12, N2=50 |
| expma\_12\_qfq | float | Y | EMA指数平均数指标-CLOSE, N1=12, N2=50 |
| expma\_50\_bfq | float | Y | EMA指数平均数指标-CLOSE, N1=12, N2=50 |
| expma\_50\_hfq | float | Y | EMA指数平均数指标-CLOSE, N1=12, N2=50 |
| expma\_50\_qfq | float | Y | EMA指数平均数指标-CLOSE, N1=12, N2=50 |
| kdj\_bfq | float | Y | KDJ指标-CLOSE, HIGH, LOW, N=9, M1=3, M2=3 |
| kdj\_hfq | float | Y | KDJ指标-CLOSE, HIGH, LOW, N=9, M1=3, M2=3 |
| kdj\_qfq | float | Y | KDJ指标-CLOSE, HIGH, LOW, N=9, M1=3, M2=3 |
| kdj\_d\_bfq | float | Y | KDJ指标-CLOSE, HIGH, LOW, N=9, M1=3, M2=3 |
| kdj\_d\_hfq | float | Y | KDJ指标-CLOSE, HIGH, LOW, N=9, M1=3, M2=3 |
| kdj\_d\_qfq | float | Y | KDJ指标-CLOSE, HIGH, LOW, N=9, M1=3, M2=3 |
| kdj\_k\_bfq | float | Y | KDJ指标-CLOSE, HIGH, LOW, N=9, M1=3, M2=3 |
| kdj\_k\_hfq | float | Y | KDJ指标-CLOSE, HIGH, LOW, N=9, M1=3, M2=3 |
| kdj\_k\_qfq | float | Y | KDJ指标-CLOSE, HIGH, LOW, N=9, M1=3, M2=3 |
| ktn\_down\_bfq | float | Y | 肯特纳交易通道, N选20日，ATR选10日-CLOSE, HIGH, LOW, N=20, M=10 |
| ktn\_down\_hfq | float | Y | 肯特纳交易通道, N选20日，ATR选10日-CLOSE, HIGH, LOW, N=20, M=10 |
| ktn\_down\_qfq | float | Y | 肯特纳交易通道, N选20日，ATR选10日-CLOSE, HIGH, LOW, N=20, M=10 |
| ktn\_mid\_bfq | float | Y | 肯特纳交易通道, N选20日，ATR选10日-CLOSE, HIGH, LOW, N=20, M=10 |
| ktn\_mid\_hfq | float | Y | 肯特纳交易通道, N选20日，ATR选10日-CLOSE, HIGH, LOW, N=20, M=10 |
| ktn\_mid\_qfq | float | Y | 肯特纳交易通道, N选20日，ATR选10日-CLOSE, HIGH, LOW, N=20, M=10 |
| ktn\_upper\_bfq | float | Y | 肯特纳交易通道, N选20日，ATR选10日-CLOSE, HIGH, LOW, N=20, M=10 |
| ktn\_upper\_hfq | float | Y | 肯特纳交易通道, N选20日，ATR选10日-CLOSE, HIGH, LOW, N=20, M=10 |
| ktn\_upper\_qfq | float | Y | 肯特纳交易通道, N选20日，ATR选10日-CLOSE, HIGH, LOW, N=20, M=10 |
| lowdays | float | Y | LOWRANGE(LOW)表示当前最低价是近多少周期内最低价的最小值 |
| topdays | float | Y | TOPRANGE(HIGH)表示当前最高价是近多少周期内最高价的最大值 |
| ma\_bfq\_10 | float | Y | 简单移动平均-N=10 |
| ma\_bfq\_20 | float | Y | 简单移动平均-N=20 |
| ma\_bfq\_250 | float | Y | 简单移动平均-N=250 |
| ma\_bfq\_30 | float | Y | 简单移动平均-N=30 |
| ma\_bfq\_5 | float | Y | 简单移动平均-N=5 |
| ma\_bfq\_60 | float | Y | 简单移动平均-N=60 |
| ma\_bfq\_90 | float | Y | 简单移动平均-N=90 |
| ma\_hfq\_10 | float | Y | 简单移动平均-N=10 |
| ma\_hfq\_20 | float | Y | 简单移动平均-N=20 |
| ma\_hfq\_250 | float | Y | 简单移动平均-N=250 |
| ma\_hfq\_30 | float | Y | 简单移动平均-N=30 |
| ma\_hfq\_5 | float | Y | 简单移动平均-N=5 |
| ma\_hfq\_60 | float | Y | 简单移动平均-N=60 |
| ma\_hfq\_90 | float | Y | 简单移动平均-N=90 |
| ma\_qfq\_10 | float | Y | 简单移动平均-N=10 |
| ma\_qfq\_20 | float | Y | 简单移动平均-N=20 |
| ma\_qfq\_250 | float | Y | 简单移动平均-N=250 |
| ma\_qfq\_30 | float | Y | 简单移动平均-N=30 |
| ma\_qfq\_5 | float | Y | 简单移动平均-N=5 |
| ma\_qfq\_60 | float | Y | 简单移动平均-N=60 |
| ma\_qfq\_90 | float | Y | 简单移动平均-N=90 |
| macd\_bfq | float | Y | MACD指标-CLOSE, SHORT=12, LONG=26, M=9 |
| macd\_hfq | float | Y | MACD指标-CLOSE, SHORT=12, LONG=26, M=9 |
| macd\_qfq | float | Y | MACD指标-CLOSE, SHORT=12, LONG=26, M=9 |
| macd\_dea\_bfq | float | Y | MACD指标-CLOSE, SHORT=12, LONG=26, M=9 |
| macd\_dea\_hfq | float | Y | MACD指标-CLOSE, SHORT=12, LONG=26, M=9 |
| macd\_dea\_qfq | float | Y | MACD指标-CLOSE, SHORT=12, LONG=26, M=9 |
| macd\_dif\_bfq | float | Y | MACD指标-CLOSE, SHORT=12, LONG=26, M=9 |
| macd\_dif\_hfq | float | Y | MACD指标-CLOSE, SHORT=12, LONG=26, M=9 |
| macd\_dif\_qfq | float | Y | MACD指标-CLOSE, SHORT=12, LONG=26, M=9 |
| mass\_bfq | float | Y | 梅斯线-HIGH, LOW, N1=9, N2=25, M=6 |
| mass\_hfq | float | Y | 梅斯线-HIGH, LOW, N1=9, N2=25, M=6 |
| mass\_qfq | float | Y | 梅斯线-HIGH, LOW, N1=9, N2=25, M=6 |
| ma\_mass\_bfq | float | Y | 梅斯线-HIGH, LOW, N1=9, N2=25, M=6 |
| ma\_mass\_hfq | float | Y | 梅斯线-HIGH, LOW, N1=9, N2=25, M=6 |
| ma\_mass\_qfq | float | Y | 梅斯线-HIGH, LOW, N1=9, N2=25, M=6 |
| mfi\_bfq | float | Y | MFI指标是成交量的RSI指标-CLOSE, HIGH, LOW, VOL, N=14 |
| mfi\_hfq | float | Y | MFI指标是成交量的RSI指标-CLOSE, HIGH, LOW, VOL, N=14 |
| mfi\_qfq | float | Y | MFI指标是成交量的RSI指标-CLOSE, HIGH, LOW, VOL, N=14 |
| mtm\_bfq | float | Y | 动量指标-CLOSE, N=12, M=6 |
| mtm\_hfq | float | Y | 动量指标-CLOSE, N=12, M=6 |
| mtm\_qfq | float | Y | 动量指标-CLOSE, N=12, M=6 |
| mtmma\_bfq | float | Y | 动量指标-CLOSE, N=12, M=6 |
| mtmma\_hfq | float | Y | 动量指标-CLOSE, N=12, M=6 |
| mtmma\_qfq | float | Y | 动量指标-CLOSE, N=12, M=6 |
| obv\_bfq | float | Y | 能量潮指标-CLOSE, VOL |
| obv\_hfq | float | Y | 能量潮指标-CLOSE, VOL |
| obv\_qfq | float | Y | 能量潮指标-CLOSE, VOL |
| psy\_bfq | float | Y | 投资者对股市涨跌产生心理波动的情绪指标-CLOSE, N=12, M=6 |
| psy\_hfq | float | Y | 投资者对股市涨跌产生心理波动的情绪指标-CLOSE, N=12, M=6 |
| psy\_qfq | float | Y | 投资者对股市涨跌产生心理波动的情绪指标-CLOSE, N=12, M=6 |
| psyma\_bfq | float | Y | 投资者对股市涨跌产生心理波动的情绪指标-CLOSE, N=12, M=6 |
| psyma\_hfq | float | Y | 投资者对股市涨跌产生心理波动的情绪指标-CLOSE, N=12, M=6 |
| psyma\_qfq | float | Y | 投资者对股市涨跌产生心理波动的情绪指标-CLOSE, N=12, M=6 |
| roc\_bfq | float | Y | 变动率指标-CLOSE, N=12, M=6 |
| roc\_hfq | float | Y | 变动率指标-CLOSE, N=12, M=6 |
| roc\_qfq | float | Y | 变动率指标-CLOSE, N=12, M=6 |
| maroc\_bfq | float | Y | 变动率指标-CLOSE, N=12, M=6 |
| maroc\_hfq | float | Y | 变动率指标-CLOSE, N=12, M=6 |
| maroc\_qfq | float | Y | 变动率指标-CLOSE, N=12, M=6 |
| rsi\_bfq\_12 | float | Y | RSI指标-CLOSE, N=12 |
| rsi\_bfq\_24 | float | Y | RSI指标-CLOSE, N=24 |
| rsi\_bfq\_6 | float | Y | RSI指标-CLOSE, N=6 |
| rsi\_hfq\_12 | float | Y | RSI指标-CLOSE, N=12 |
| rsi\_hfq\_24 | float | Y | RSI指标-CLOSE, N=24 |
| rsi\_hfq\_6 | float | Y | RSI指标-CLOSE, N=6 |
| rsi\_qfq\_12 | float | Y | RSI指标-CLOSE, N=12 |
| rsi\_qfq\_24 | float | Y | RSI指标-CLOSE, N=24 |
| rsi\_qfq\_6 | float | Y | RSI指标-CLOSE, N=6 |
| taq\_down\_bfq | float | Y | 唐安奇通道(海龟)交易指标-HIGH, LOW, 20 |
| taq\_down\_hfq | float | Y | 唐安奇通道(海龟)交易指标-HIGH, LOW, 20 |
| taq\_down\_qfq | float | Y | 唐安奇通道(海龟)交易指标-HIGH, LOW, 20 |
| taq\_mid\_bfq | float | Y | 唐安奇通道(海龟)交易指标-HIGH, LOW, 20 |
| taq\_mid\_hfq | float | Y | 唐安奇通道(海龟)交易指标-HIGH, LOW, 20 |
| taq\_mid\_qfq | float | Y | 唐安奇通道(海龟)交易指标-HIGH, LOW, 20 |
| taq\_up\_bfq | float | Y | 唐安奇通道(海龟)交易指标-HIGH, LOW, 20 |
| taq\_up\_hfq | float | Y | 唐安奇通道(海龟)交易指标-HIGH, LOW, 20 |
| taq\_up\_qfq | float | Y | 唐安奇通道(海龟)交易指标-HIGH, LOW, 20 |
| trix\_bfq | float | Y | 三重指数平滑平均线-CLOSE, M1=12, M2=20 |
| trix\_hfq | float | Y | 三重指数平滑平均线-CLOSE, M1=12, M2=20 |
| trix\_qfq | float | Y | 三重指数平滑平均线-CLOSE, M1=12, M2=20 |
| trma\_bfq | float | Y | 三重指数平滑平均线-CLOSE, M1=12, M2=20 |
| trma\_hfq | float | Y | 三重指数平滑平均线-CLOSE, M1=12, M2=20 |
| trma\_qfq | float | Y | 三重指数平滑平均线-CLOSE, M1=12, M2=20 |
| vr\_bfq | float | Y | VR容量比率-CLOSE, VOL, M1=26 |
| vr\_hfq | float | Y | VR容量比率-CLOSE, VOL, M1=26 |
| vr\_qfq | float | Y | VR容量比率-CLOSE, VOL, M1=26 |
| wr\_bfq | float | Y | W&R 威廉指标-CLOSE, HIGH, LOW, N=10, N1=6 |
| wr\_hfq | float | Y | W&R 威廉指标-CLOSE, HIGH, LOW, N=10, N1=6 |
| wr\_qfq | float | Y | W&R 威廉指标-CLOSE, HIGH, LOW, N=10, N1=6 |
| wr1\_bfq | float | Y | W&R 威廉指标-CLOSE, HIGH, LOW, N=10, N1=6 |
| wr1\_hfq | float | Y | W&R 威廉指标-CLOSE, HIGH, LOW, N=10, N1=6 |
| wr1\_qfq | float | Y | W&R 威廉指标-CLOSE, HIGH, LOW, N=10, N1=6 |
| xsii\_td1\_bfq | float | Y | 薛斯通道II-CLOSE, HIGH, LOW, N=102, M=7 |
| xsii\_td1\_hfq | float | Y | 薛斯通道II-CLOSE, HIGH, LOW, N=102, M=7 |
| xsii\_td1\_qfq | float | Y | 薛斯通道II-CLOSE, HIGH, LOW, N=102, M=7 |
| xsii\_td2\_bfq | float | Y | 薛斯通道II-CLOSE, HIGH, LOW, N=102, M=7 |
| xsii\_td2\_hfq | float | Y | 薛斯通道II-CLOSE, HIGH, LOW, N=102, M=7 |
| xsii\_td2\_qfq | float | Y | 薛斯通道II-CLOSE, HIGH, LOW, N=102, M=7 |
| xsii\_td3\_bfq | float | Y | 薛斯通道II-CLOSE, HIGH, LOW, N=102, M=7 |
| xsii\_td3\_hfq | float | Y | 薛斯通道II-CLOSE, HIGH, LOW, N=102, M=7 |
| xsii\_td3\_qfq | float | Y | 薛斯通道II-CLOSE, HIGH, LOW, N=102, M=7 |
| xsii\_td4\_bfq | float | Y | 薛斯通道II-CLOSE, HIGH, LOW, N=102, M=7 |
| xsii\_td4\_hfq | float | Y | 薛斯通道II-CLOSE, HIGH, LOW, N=102, M=7 |
| xsii\_td4\_qfq | float | Y | 薛斯通道II-CLOSE, HIGH, LOW, N=102, M=7 |
