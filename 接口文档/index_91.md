# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=89  
**爬取时间**: 2025-08-09 22:33:08

---

## DLL载入问题之查询依赖的DLL

作者：Tushare社区用户 **晓子**

---

### >> 问题描述 <<

如果“确信”所需要的DLL都已经放在了需要的位置，但还是会有诸如下方的“DLL load failed”。很可能是因为你所认为的运行环境并非是所运行程序真正的运行环境。在得到来自其他人的程序，而并未被告知是什么运行环境的时候很可能会这样。如笔者就被给了一个提供python接口的程序，仅被告知是64位针对python3的程序。于是就用python3.6在64位机器上调了很久，找了很多资料都不成。后来用[Dependency Walker 2.2](http://www.dependencywalker.com/)查询了下所依赖的dll，发现缺少python35.dll，才意识到使用的是python3.5而非python3.6。改换了环境就好了。故而，在这里做下记录，供自己和后来者参考。

```
Traceback (most recent call last):
  File "C:/xxx/python/tmp.py", line 1, in <module>
    import xxxxxxx
ImportError: DLL load failed: 找不到指定的模块。
```

### >> 软件使用 <<

使用也很简单，只要运行程序，然后点击“文件”打开所需要查询依赖dll的可执行文件即可，如下图（图片来自dependencywalker官网）：

![](http://www.dependencywalker.com/snapshot.png)
