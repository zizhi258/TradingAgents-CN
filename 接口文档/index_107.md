# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=105  
**爬取时间**: 2025-08-09 22:33:17

---

## Twitter大V数据

接口：twitter\_kol

描述：获取Twitter上数字货币领域大V的消息（5分钟更新一次，未来根据服务器压力再做调整）

**输入参数**

| 名称 | 类型 | 必选 | 描述 |
| --- | --- | --- | --- |
| start\_date | datetime | Y | 开始时间 格式：YYYY-MM-DD HH:MM:SS |
| end\_date | datetime | Y | 结束时间 格式：YYYY-MM-DD HH:MM:SS |

**输出参数**

| 名称 | 类型 | 描述 |
| --- | --- | --- |
| id | int | 记录ID（采集站点中的） |
| account\_id | int | 账号ID（采集站点中的） |
| account | str | 账号 |
| nickname | str | 昵称 |
| avatar | str | 头像 |
| content\_id | int | 类容ID（采集站点中的） |
| content | str | 原始内容 |
| is\_retweet | int | 是否转发：0-否；1-是 |
| retweet\_content | json | 转发内容，json格式，包含了另一个Twitter结构 |
| media | json | 附件，json格式，包含了资源类型、资源链接等 |
| posted\_at | int | 发布时间戳 |
| content\_translation | str | 内容翻译 |
| str\_posted\_at | str | 发布时间，根据posted\_at转换而来 |
| create\_at | str | 采集时间 |

注：内容中包含HTML标签怎么办？

答：请见[PYTHON过滤HTML标签](https://tushare.pro/document/1?doc_id=91)

**接口用法**

由于数据量可能比较大，我们限定了必须设定起止时间来获取数据，并且每次最多只能取200条数据。

```json
pro = ts.pro_api()

pro.twitter_kol(start_date='2018-09-26 14:15:41', end_date='2018-09-26 16:20:11', fields="id,account,nickname,content,retweet_content,media,str_posted_at")
```

或者

```json
pro.query('twitter_kol', start_date='2018-09-26 14:15:41', end_date='2018-09-26 16:20:11', fields="id,account,nickname,content,retweet_content,media,str_posted_at")
```

**数据样例**

| id | account | nickname | content | retweet\_content | media | str\_posted\_at |
| --- | --- | --- | --- | --- | --- | --- |
| 1116360 | Excellion | Samson Mow | RT <span style="color... | {'account': 'woonomic', 'nickname': 'Willy Woo... | [] | 2018-09-26 16:20:11 |
| 1116361 | WhalePanda | WhalePanda | @EJachno1 Sur... | None | [] | 2018-09-26 14:39:41 |
| 1116362 | WhalePanda | WhalePanda | Pretty sure that applications that go through ... | None | [] | 2018-09-26 14:29:11 |
| 1116364 | WhalePanda | WhalePanda | Example of what 99% of all the applications fo... | None | [{'type': 'image', 'thumbnail': '<http://pbs.tw>... | 2018-09-26 14:15:41 |
