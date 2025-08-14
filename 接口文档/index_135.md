# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=133  
**爬取时间**: 2025-08-09 22:33:35

---

# 通过R语言调取数据

---

![](https://tushare.pro/files/img/31.png)
> Tushare R package终于在R官方CRAN喜提“过会”获得通过！终于不用吹了牛逼却迟迟欠大家一个R包而有压抑感！终于可以激动发出我们的官宣：欢迎大家用R语言免费撸金融数据！
>
>
> 依然要感谢社区的小伙伴，楚霄，晓子，Binger在代码编写，文档整理付出了努力，在此深表谢意。Tushare正是在社区用户的共同建设和维护下一步步变得越来越好，也欢迎更多小伙伴一起参与。

【Tushare R包由楚霄贡献，晓子整理发布。】

```
推荐使用RStudio来完成数据操作，支持单步运行、包管理、环境（变量）查看、帮助文件查看（跳转）等诸多功能。下文，就是以RStudio作为编译环境来演示。
```

# 安装Tushare

打开RStudio，在控制台输入命令：

```
> install.packages('Tushare')
```

Tushare的R包需要依赖httr、tidyverse、forecast和data.table这四个包。

由于Tushare包中申明了依赖关系，因此这四个依赖包也会自动下载下来。如果下载过程卡住了，导致下载失败，可以重试几次，毕竟CRAN的服务器不在大陆，后面将介绍如何使用CRAN的国内镜像。

# 载入Tushare

如同安装过程，在载入Tushare的同时，R也会自动载入其依赖的包。

```
> library('Tushare')
```

也可以通过help查看Tushare的相关信息

```
> help('Tushare')
```

![](https://tushare.pro/files/img/33.png)

在R官网也可以看到Tushare的索引信息：

![](https://tushare.pro/files/img/34.png)
# 使用Tushare

获得api接口对象

```
> api <- Tushare::pro_api(token = 'YOUR TOKEN HERE')
```

如同在Python包中使用Tushare Pro的pro.query，向api（只要调用Tushare::pro\_api获得了接口，你可以使用任意的名字命名）传递想要调用的接口名以及相应的参数就可以调用相应的数据。

在api中，必须传递的是Tushare Pro提供的接口名（详细请见官方网站[https://tushare.pro/），其他参数视相应的接口传入相应的参数。](https://tushare.pro/%EF%BC%89%EF%BC%8C%E5%85%B6%E4%BB%96%E5%8F%82%E6%95%B0%E8%A7%86%E7%9B%B8%E5%BA%94%E7%9A%84%E6%8E%A5%E5%8F%A3%E4%BC%A0%E5%85%A5%E7%9B%B8%E5%BA%94%E7%9A%84%E5%8F%82%E6%95%B0%E3%80%82)

Tips：Tushare的0.1.1版本的R包暂时不支持fields字段。

示例1：只传入接口名而不传入其他参数调用api接口

```
> api(api_name = 'stock_basic')
```

![](https://tushare.pro/files/img/35.png)
接下来使用pro\_bar文档中的一个示例来演示传入接口名和其他参数调用api接口。

示例2：传入接口名和其他参数调用api接口

```
> api(api_name = 'daily', ts_code = "000001.SZ", start_date = "20181001", end_date = "20181010")
```

![](https://tushare.pro/files/img/36.png)

# pro\_bar接口的使用

获得pro\_bar接口，并命名为bar。和Tushare Pro的python包一样，为了统一使用行情接口，Tushare的R包也提供了pro\_bar。

```
> bar <- Tushare::pro_bar(token = 'YOUR TOKEN HERE')

> bar(ts_code = "000001.SZ", start_date = "20181001", end_date = "20181010")
```

![](http://tushare.org/img/37.png)
bar接口可以传递adj来同时调取行情以及复权因子，并将计算后的结果返回出来。其他接口参数请参考Tushare Pro网站的详细说明。

```
> bar(ts_code = "000001.SZ", start_date = "20181001", adj = "hfq", ma = c(5,10))
```

![](https://tushare.pro/files/img/38.png)

# 一个样例

最后，我们来执行一段程序，获取平安银行的后复权数据并完成可视化展示。

```shell
df = bar(ts_code="000001.SZ", start_date="20180101", adj="hfq", ma=c(5,10,20)) %>%

        mutate(trade_date = as.Date(gsub('^(\\d{4})(\\d{2})(\\d{2})$', '\\1-\\2-\\3', trade_date))) %>%

        mutate_at(vars(3:dim(.)[2]), as.numeric)

df$id = dim(df)[1]:1

df$candleLower = pmin(df$open, df$close)

df$candleUpper = pmax(df$open, df$close)

df$candleMiddle = (df$candleLower+df$candleUpper)/2

theme_set(theme_bw())

p = ggplot(df, aes(x=id))+

    geom_boxplot(aes(lower= candleLower,

                                     middle = candleLower,

                                     upper = candleUpper,

                                     ymin = low,

                                     ymax = high,

                                     color= ifelse(open>close,"green","red"),

                                     width= 0.5),

                             stat = 'identity',

                             size = .5)+

    scale_color_manual(values = c("green","red"))+

    theme(

        panel.grid.major = element_blank(),

        panel.grid.minor = element_blank(),

        panel.background = element_blank(),

        axis.title = element_blank(),

        axis.text.x = element_text(angle = 65, hjust = 1),

        legend.position="none"

    )

p + geom_line(aes(x=id, y=ma5), color="orange", size=.5)+

        geom_line(aes(x=id, y=ma10), color="purple", size=.5)+

geom_line(aes(x=id, y=ma20), color="blue", size=.5)
```

![](https://tushare.pro/files/img/39.png)
# Tushare账号和token获取

Tushare Pro数据虽然免费，但需要[注册](https://tushare.pro/register?reg=doc)一个账号，通过登录Pro网站可以获取免费token，之后就可以像以上介绍的方式获取数据了。

更多资料请关注“挖地兔”公众号：

![](https://tushare.pro/files/img/wechat_ts.png)
