# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=126  
**爬取时间**: 2025-08-09 22:33:31

---

## 概念股列表

---

接口：concept\_detail
描述：获取概念股分类明细数据
积分：用户需要至少300积分才可以调取，具体请参阅[积分获取办法](https://tushare.pro/document/1?doc_id=13)

注意：本接口数据已停止更新，请转移到[同花顺概念接口](https://tushare.pro/document/2?doc_id=261)

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| id | str | N | 概念分类ID （id来自概念股分类接口） |
| ts\_code | str | N | 股票代码 （以上参数二选一） |

**输出参数**

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| id | str | Y | 概念代码 |
| concept\_name | str | Y | 概念名称 |
| ts\_code | str | Y | 股票代码 |
| name | str | Y | 股票名称 |
| in\_date | str | N | 纳入日期 |
| out\_date | str | N | 剔除日期 |

**接口使用**

```yaml
pro = ts.pro_api()

#取5G概念明细
df = pro.concept_detail(id='TS2', fields='ts_code,name')

#或者查询某个股票的概念

df = pro.concept_detail(ts_code = '600848.SH')
```

**数据示例**

```
ts_code   name
0   000008.SZ   神州高铁
1   000063.SZ   中兴通讯
2   000070.SZ   特发信息
3   000586.SZ   汇源通信
4   000636.SZ   风华高科
5   000810.SZ   创维数字
6   000836.SZ   富通鑫茂
7   000938.SZ   紫光股份
8   000988.SZ   华工科技
9   002023.SZ   海特高新
10  002089.SZ    新海宜
11  002115.SZ   三维通信
12  002138.SZ   顺络电子
13  002179.SZ   中航光电
14  002194.SZ  *ST凡谷
15  002217.SZ    合力泰
16  002229.SZ   鸿博股份
17  002231.SZ   奥维通信
18  002281.SZ   光迅科技
19  002309.SZ   中利集团
20  002313.SZ   日海智能
21  002384.SZ   东山精密
22  002396.SZ   星网锐捷
23  002402.SZ    和而泰
24  002446.SZ   盛路通信
25  002475.SZ   立讯精密
26  002491.SZ   通鼎互联
27  002544.SZ   杰赛科技
28  002547.SZ   春兴精工
29  002725.SZ   跃岭股份
```

**数据调取场景**

1、先通过概念股分类接口获取具体分类

```
df = pro.concept(src='ts')

print(df)
```

```
code        name src
0      TS0        密集调研  ts
1      TS1       南北船合并  ts
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
```

上面的code即概念股明细接口里的id参数

2、用上面接口示例的方法调取数据
