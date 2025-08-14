# Docker 容器控制指南

## 🛑 关闭 Docker 容器的方法

### 方法 1：停止所有容器（推荐）

```bash
# 进入项目目录
cd TradingAgents-CN

# 停止并移除所有容器
docker-compose down

# 如果需要同时删除数据卷（谨慎使用）
docker-compose down -v
```

### 方法 2：仅停止容器（保留容器）

```bash
# 停止所有服务但保留容器
docker-compose stop

# 重新启动已停止的容器
docker-compose start
```

### 方法 3：停止特定服务

```bash
# 只停止web服务
docker-compose stop web

# 只停止数据库服务
docker-compose stop db

# 只停止调度器服务
docker-compose stop scheduler
```

## 📋 查看容器状态

### 查看当前运行的容器

```bash
# 查看项目相关容器
docker-compose ps

# 查看所有Docker容器
docker ps

# 查看所有容器（包括已停止的）
docker ps -a
```

### 查看容器日志

```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志
docker-compose logs web
docker-compose logs db

# 实时查看日志
docker-compose logs -f web
```

## 🔄 重启容器

### 重启所有服务

```bash
# 重启所有容器
docker-compose restart

# 重新构建并启动
docker-compose up -d --build
```

### 重启特定服务

```bash
# 重启web服务
docker-compose restart web
```

## 🧹 清理 Docker 资源

### 清理未使用的资源

```bash
# 清理未使用的容器、网络、镜像
docker system prune

# 清理所有未使用的资源（包括数据卷）
docker system prune -a --volumes
```

### 删除特定镜像

```bash
# 查看所有镜像
docker images

# 删除特定镜像
docker rmi <镜像ID或名称>

# 删除项目相关镜像
docker rmi tradingagents-cn_web
```

## ⚡ 快速操作命令

### 常用组合命令

```bash
# 完全停止并清理
docker-compose down && docker system prune -f

# 重新构建并启动
docker-compose down && docker-compose up -d --build

# 查看状态和日志
docker-compose ps && docker-compose logs --tail=50
```

## 🚨 紧急停止

### 强制停止所有 Docker 容器

```bash
# 停止所有运行中的容器
docker stop $(docker ps -q)

# 强制杀死所有容器
docker kill $(docker ps -q)
```

## 💡 使用建议

### 日常开发

- 使用 `docker-compose down` 完全停止
- 使用 `docker-compose up -d` 后台启动
- 使用 `docker-compose logs -f web` 查看实时日志

### 测试 UI 修复

- 停止 Docker：`docker-compose down`
- 使用 Python 直接启动：`python start_web.py`
- 这样可以更快地测试 UI 变化

### 资源管理

- 定期运行 `docker system prune` 清理资源
- 监控磁盘空间使用情况
- 必要时清理旧的镜像和容器

## 🔍 故障排除

### 端口占用问题

```bash
# 查看端口占用
netstat -tulpn | grep :8501
lsof -i :8501

# 杀死占用端口的进程
kill -9 <进程ID>
```

### 权限问题

```bash
# 如果遇到权限问题，可能需要使用sudo
sudo docker-compose down
sudo docker system prune
```

### 网络问题

```bash
# 重置Docker网络
docker network prune

# 查看Docker网络
docker network ls
```
