# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=258  
**爬取时间**: 2025-08-09 22:34:52

---

## 交易所交易对（新）

---

接口：coin\_pair
描述：获取交易所和交易对信息
限量：单次最大5000，2000积分可调取

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| exchange | str | Y | 交易所 |
| ts\_code | str | N | 交易对代码 |

**输出参数**

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| exchange | str | Y | 交易所 |
| symbol | str | Y | 交易对 |
| is\_contract | str | Y | 是否合约 |
| status | str | Y | 状态Y可用N不可用 |
