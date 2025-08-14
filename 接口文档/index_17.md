# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=14  
**爬取时间**: 2025-08-09 22:32:21

---

## 沪深股票

沪深股票数据是Tushare最传统最有历史的数据服务项目，从一开始就为广大的投资者，尤其是量化投资者提供了稳定、便捷的接口。Tushare Pro版在继承了旧版API的便捷易用性的同时又加强了数据的广度和深度。最为关键的是，数据来源和采集方式也发生了根本的变化，除了公开渠道的数据源，最关键性的变化是Tushare构建起来了自有的数据存储和数据治理体系，同时依托平台化的维护和管理方式，让数据更稳定可靠，而且服务能力也能得到了质的变化。

Pro版首先提供的是基础数据，主要包括：

* [股票基础列表](https://tushare.pro/document/2?doc_id=25)
* [上市公司信息](https://tushare.pro/document/2?doc_id=112)
* [各交易所交易日历](https://tushare.pro/document/2?doc_id=26)
* [沪深股通成份股](https://tushare.pro/document/2?doc_id=104)
* [股票曾用名](https://tushare.pro/document/2?doc_id=100)
* [IPO新股列表](https://tushare.pro/document/2?doc_id=123)

```
在Tushare数据接口里，股票代码参数都叫ts_code，每种股票代码都有规范的后缀
```

| 交易所名称 | 交易所代码 | 股票代码后缀 | 备注 |
| --- | --- | --- | --- |
| 上海证券交易所 | SSE | .SH | 600000.SH(股票) 000001.SH(0开头指数) |
| 深圳证券交易所 | SZSE | .SZ | 000001.SZ(股票) 399005.SZ(3开头指数) |
| 北京证券交易所 | BSE | .BJ | 9、8和4开头的股票 |
| 香港证券交易所 | HKEX | .HK | 00001.HK |

当然，数据不仅上述所列，包括以下要介绍的部分，数据在一点点上线，社区朋友可以经常上来网站，或许会发现数据的更迭变化。

其次，就是最为重要的行情和财务数据部分，在行情数据方面，我们提供了：

* [日线行情](https://tushare.pro/document/2?doc_id=27)
* [中高频的分钟行情](https://tushare.pro/document/2?doc_id=109)
* Tick级行情
* [大单成交数据](https://tushare.pro/document/2?doc_id=170)
* [复权因子](https://tushare.pro/document/2?doc_id=28)
* [停复牌信息](https://tushare.pro/document/2?doc_id=31)
* [每日行情指标](https://tushare.pro/document/2?doc_id=32)

在财务等反应上市公司基本面情况的数据方面，目前提供的有：

* [利润表](https://tushare.pro/document/2?doc_id=33)
* [资产负债表](https://tushare.pro/document/2?doc_id=36)
* [现金流量表](https://tushare.pro/document/2?doc_id=44)
* [业绩预告](https://tushare.pro/document/2?doc_id=45)
* [业绩快报](https://tushare.pro/document/2?doc_id=46)
* [分红送股](https://tushare.pro/document/2?doc_id=103)
* [财务指标数据](https://tushare.pro/document/2?doc_id=79)
* [财务审计意见](https://tushare.pro/document/2?doc_id=80)
* [主营业务构成](https://tushare.pro/document/2?doc_id=81)

而在其他数据方面，其实也是对Tushare来说有很大发挥空间的市场行为和公司治理方面的参考数据，这一部分数据相信在未来很一段时间，我们都会作为一个重点来突破，为广大的社区用户和更多的投资者发掘、采集、整理和呈现好，一定会走心的为大家把数据的脏活累活消灭在各位写策略之前，让大家愉快的去实现自己的投资思想。总结一句话就是，大家只管安心的去挖矿赚钱就行了。

这部分数据，我们在这里暂时不一一罗列，已经在左侧菜单呈现，一目了然。
