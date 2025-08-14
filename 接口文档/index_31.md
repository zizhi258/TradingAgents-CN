# Tushare数据

**来源**: https://tushare.pro/document/2?doc_id=29  
**爬取时间**: 2025-08-09 22:32:29

---

## Windows下安装Anaconda

作者： Tushare社区用户 **fei**

---

1、打开Anaconda官网（网址：<https://www.anaconda.com/download/>）为用户提供了不同操作系统不同Python版本的安装包。以Windows下64位Python3.6版本的安装包为例：下载Anaconda3-5.2.0-Windows-x86\_64.exe。（注：Anaconda文件名是由Python版本号、Anaconda版本号、操作系统系统和系统位数决定的，如Anaconda3-5.2.0-Windows-x86\_64.exe支持的是Python3、版本为5.2.0。）

![](https://tushare.pro/files/pro/img/install_anaconda_001.jpg)

2、安装包下载下来后，双击下载下来的.exe文件就可以安装了。

![](https://tushare.pro/files/pro/img/install_anaconda_002.jpg)

3、安装时将两个选项都选上，将安装路径写入环境变量，然后等待安装完成就可以了。（注：由于笔者已经安装了Anaconda，因此安装程序提醒会覆盖以前的安装版本，对于已经安装了Anaconda的用户，可以考虑不要勾选这一项。）

![](https://tushare.pro/files/pro/img/install_anaconda_003.jpg)

4、等待安装完毕（期间会多次跳出命令行，稍等片刻会自行关闭）；
5、最后，安装程序询问是否要安装Visual Studio Code（Microsoft开发的一种针对于编写现代Web和云应用的跨平台源代码编辑器）

![](https://tushare.pro/files/pro/img/install_anaconda_004.jpg)

6、安装完成后打开命令行可以使用python –version来查看python的版本信息，可以使用anaconda来配置python环境。

![](https://tushare.pro/files/pro/img/install_anaconda_005.jpg)

---

## Linux下安装Anaconda

---

1、通过wget下载Anaconda安装包，相对于官网（网址为：[https://www.anaconda.com/download/），中国大陆用户可以使用清华镜像（地址为：https://repo.continuum.io/archive/index.html）。](https://www.anaconda.com/download/%EF%BC%89%EF%BC%8C%E4%B8%AD%E5%9B%BD%E5%A4%A7%E9%99%86%E7%94%A8%E6%88%B7%E5%8F%AF%E4%BB%A5%E4%BD%BF%E7%94%A8%E6%B8%85%E5%8D%8E%E9%95%9C%E5%83%8F%EF%BC%88%E5%9C%B0%E5%9D%80%E4%B8%BA%EF%BC%9Ahttps://repo.continuum.io/archive/index.html%EF%BC%89%E3%80%82)

![](https://tushare.pro/files/pro/img/install_anaconda_006.jpg)

2、使用sh Anaconda3-5.2.0-Linux-x86\_64.sh按照提示进行安装

![](https://tushare.pro/files/pro/img/install_anaconda_007.jpg)

3、阅读完权限许可并同意后，安装程序询问安装的目录，默认为“/root/anaconda3”，笔者已经装过，所以输入另一个目录进行安装。

![](https://tushare.pro/files/pro/img/install_anaconda_008.jpg)

4、期间安装程序会询问是否将Anaconda的安装目录添加到系统路径中。如果添加进去，则可以直接使用诸如python这样的不加路径的命令，否则就要使用如/root/tmp/anaconda3/bin/python这样的带有路径的命令或者到python所在的目录使用./python运行。

![](https://tushare.pro/files/pro/img/install_anaconda_009.jpg)

5、最后，安装程序询问是否要安装Visual Studio Code（Microsoft开发的一种针对于编写现代 Web 和云应用的跨平台源代码编辑器）

![](https://tushare.pro/files/pro/img/install_anaconda_010.jpg)

6、如果选择安装，则等Visual Studio Code安装结束后，Anaconda安装程序结束，否则安装程序就直接结束了。
7、安装完成后可以使用python –version来查看python的版本信息，可以使用anaconda来配置python环境。

![](https://tushare.pro/files/pro/img/install_anaconda_011.jpg)
