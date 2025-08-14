# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=125  
**爬取时间**: 2025-08-09 22:33:30

---

## 概念股分类

---

接口：concept
描述：获取概念股分类，目前只有ts一个来源，未来将逐步增加来源
积分：用户需要至少300积分才可以调取，具体请参阅[积分获取办法](https://tushare.pro/document/1?doc_id=13)

注意：本接口数据已停止更新，请转移到[同花顺概念接口](https://tushare.pro/document/2?doc_id=259)

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| src | str | N | 来源，默认为ts |

**输出参数**

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| code | str | Y | 概念分类ID |
| name | str | Y | 概念分类名称 |
| src | str | Y | 来源 |

**接口使用**

```yaml
pro = ts.pro_api()

df = pro.concept()

#或者
# df = pro.concept(src='ts')
```

**数据示例**

```
code        name    src
2      TS2          5G  ts
3      TS3          机场  ts
4      TS4         高价股  ts
5      TS5          烧碱  ts
6      TS6       AH溢价股  ts
7      TS7          保险  ts
8      TS8         PVC  ts
9      TS9          啤酒  ts
10    TS10          火电  ts
11    TS11          银行  ts
12    TS12         碳纤维  ts
13    TS13         安邦系  ts
14    TS14         特高压  ts
15    TS15         高股息  ts
16    TS16         光通信  ts
17    TS17         草甘膦  ts
18    TS18        高速公路  ts
19    TS19        有色-铝  ts
20    TS20        有色-锆  ts
```
