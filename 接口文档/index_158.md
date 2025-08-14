# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=156  
**爬取时间**: 2025-08-09 22:33:49

---

## 全国电影剧本备案数据

---

接口：film\_record
描述：获取全国电影剧本备案的公示数据
限量：单次最大500，总量不限制
数据权限：用户需要至少120积分才可以调取，积分越多调取频次越高，具体请参阅[积分获取办法](https://tushare.pro/document/1?doc_id=13)

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| ann\_date | str | N | 公布日期 （至少输入一个参数，格式：YYYYMMDD，日期不连续，定期公布） |
| start\_date | str | N | 开始日期 |
| end\_date | str | N | 结束日期 |

**输出参数**

| 名称 | 类型 | 默认显示 | 描述 |
| --- | --- | --- | --- |
| rec\_no | str | Y | 备案号 |
| film\_name | str | Y | 影片名称 |
| rec\_org | str | Y | 备案单位 |
| script\_writer | str | Y | 编剧 |
| rec\_result | str | Y | 备案结果 |
| rec\_area | str | Y | 备案地（备案时间） |
| classified | str | Y | 影片分类 |
| date\_range | str | Y | 备案日期区间 |
| ann\_date | str | Y | 备案结果发布时间 |

**接口使用**

```yaml
pro = ts.pro_api()
#或者
#pro = ts.pro_api('your token')

df = pro.film_record(start_date='20181014', end_date='20181214')
```

**数据示例**

![](http://tushare.org/img/film_record.png)
