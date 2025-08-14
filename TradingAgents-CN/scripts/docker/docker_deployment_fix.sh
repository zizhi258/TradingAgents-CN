#!/bin/bash

# Docker Deployment Fix Script for TradingAgents-CN
# 修复Docker部署问题的完整解决方案

set -e

echo "🐳 TradingAgents-CN Docker部署修复脚本"
echo "========================================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查Docker和Docker Compose
check_prerequisites() {
    echo -e "${BLUE}📋 检查前置条件...${NC}"
    
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker未安装，请先安装Docker${NC}"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}❌ Docker Compose未安装，请先安装Docker Compose${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Docker和Docker Compose已安装${NC}"
}

# 检查必要文件
check_files() {
    echo -e "${BLUE}📁 检查必要文件...${NC}"
    
    required_files=(".env" "docker-compose.yml" "Dockerfile" "pyproject.toml")
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            echo -e "${RED}❌ 缺少必要文件: $file${NC}"
            exit 1
        fi
    done
    
    echo -e "${GREEN}✅ 所有必要文件存在${NC}"
}

# 验证环境变量配置
check_env_vars() {
    echo -e "${BLUE}🔑 检查环境变量配置...${NC}"
    
    if [[ ! -f ".env" ]]; then
        echo -e "${RED}❌ .env文件不存在${NC}"
        exit 1
    fi
    
    # 检查关键环境变量
    required_vars=(
        "SILICONFLOW_API_KEY"
        "GEMINI_API_KEY"
        "DEEPSEEK_API_KEY"
        "MULTI_MODEL_ENABLED"
    )
    
    missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if ! grep -q "^${var}=" .env; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        echo -e "${YELLOW}⚠️ 缺少以下环境变量:${NC}"
        for var in "${missing_vars[@]}"; do
            echo -e "${YELLOW}  - $var${NC}"
        done
        echo -e "${YELLOW}请检查.env文件配置${NC}"
    else
        echo -e "${GREEN}✅ 关键环境变量已配置${NC}"
    fi
}

# 停止现有容器
stop_existing_containers() {
    echo -e "${BLUE}🛑 停止现有容器...${NC}"
    
    if docker-compose ps --services --filter "status=running" | grep -q .; then
        docker-compose down
        echo -e "${GREEN}✅ 现有容器已停止${NC}"
    else
        echo -e "${YELLOW}ℹ️ 没有运行中的容器${NC}"
    fi
}

# 清理旧镜像（可选）
clean_old_images() {
    echo -e "${BLUE}🧹 清理旧Docker镜像...${NC}"
    
    read -p "是否清理旧的Docker镜像？(y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if docker images | grep -q "tradingagents-cn"; then
            docker rmi tradingagents-cn:latest || true
            echo -e "${GREEN}✅ 旧镜像已清理${NC}"
        else
            echo -e "${YELLOW}ℹ️ 没有找到旧镜像${NC}"
        fi
    else
        echo -e "${YELLOW}ℹ️ 跳过镜像清理${NC}"
    fi
}

# 构建Docker镜像
build_images() {
    echo -e "${BLUE}🔨 构建Docker镜像...${NC}"
    
    echo -e "${YELLOW}构建可能需要5-10分钟，请耐心等待...${NC}"
    
    if docker-compose build --no-cache; then
        echo -e "${GREEN}✅ Docker镜像构建成功${NC}"
    else
        echo -e "${RED}❌ Docker镜像构建失败${NC}"
        exit 1
    fi
}

# 启动服务
start_services() {
    echo -e "${BLUE}🚀 启动Docker服务...${NC}"
    
    # 先启动数据库服务
    echo -e "${YELLOW}启动数据库服务...${NC}"
    docker-compose up -d mongodb redis
    
    # 等待数据库启动
    echo -e "${YELLOW}等待数据库服务启动...${NC}"
    sleep 30
    
    # 启动主应用
    echo -e "${YELLOW}启动主应用...${NC}"
    docker-compose up -d web
    
    echo -e "${GREEN}✅ 所有服务已启动${NC}"
}

# 验证服务状态
verify_services() {
    echo -e "${BLUE}🔍 验证服务状态...${NC}"
    
    # 检查容器状态
    echo -e "${YELLOW}检查容器状态...${NC}"
    docker-compose ps
    
    # 等待服务完全启动
    echo -e "${YELLOW}等待服务完全启动（60秒）...${NC}"
    sleep 60
    
    # 检查健康状态
    echo -e "${YELLOW}检查服务健康状态...${NC}"
    
    services=("web" "mongodb" "redis")
    
    for service in "${services[@]}"; do
        if docker-compose ps | grep -q "$service.*Up"; then
            echo -e "${GREEN}✅ $service: 运行中${NC}"
        else
            echo -e "${RED}❌ $service: 未运行${NC}"
        fi
    done
}

# 测试API连接
test_api_connections() {
    echo -e "${BLUE}🧪 测试API连接...${NC}"
    
    # 测试Web界面
    echo -e "${YELLOW}测试Web界面...${NC}"
    if curl -f http://localhost:8501/_stcore/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Web界面: 可访问${NC}"
        echo -e "${GREEN}   URL: http://localhost:8501${NC}"
    else
        echo -e "${RED}❌ Web界面: 不可访问${NC}"
    fi
    
    # 测试Google GenAI SDK
    echo -e "${YELLOW}测试Google GenAI SDK...${NC}"
    if docker exec TradingAgents-web python -c "from google import genai; print('Google GenAI SDK OK')" 2>/dev/null; then
        echo -e "${GREEN}✅ Google GenAI SDK: 已安装${NC}"
    else
        echo -e "${RED}❌ Google GenAI SDK: 未安装或有问题${NC}"
        echo -e "${YELLOW}尝试修复...${NC}"
        docker exec TradingAgents-web pip install google-genai
    fi
    
    # 测试数据库连接
    echo -e "${YELLOW}测试数据库连接...${NC}"
    if docker exec TradingAgents-web python -c "import pymongo; client = pymongo.MongoClient('mongodb://admin:tradingagents123@mongodb:27017/'); client.admin.command('ping'); print('MongoDB OK')" 2>/dev/null; then
        echo -e "${GREEN}✅ MongoDB: 连接正常${NC}"
    else
        echo -e "${RED}❌ MongoDB: 连接失败${NC}"
    fi
    
    if docker exec TradingAgents-web python -c "import redis; r = redis.Redis(host='redis', port=6379, password='tradingagents123'); r.ping(); print('Redis OK')" 2>/dev/null; then
        echo -e "${GREEN}✅ Redis: 连接正常${NC}"
    else
        echo -e "${RED}❌ Redis: 连接失败${NC}"
    fi
}

# 显示访问信息
show_access_info() {
    echo -e "${BLUE}📖 访问信息${NC}"
    echo "========================================"
    echo -e "${GREEN}🌐 Web界面: http://localhost:8501${NC}"
    echo -e "${GREEN}📊 MongoDB管理: http://localhost:8082${NC}"
    echo -e "${GREEN}   用户名: admin${NC}"
    echo -e "${GREEN}   密码: tradingagents123${NC}"
    echo ""
    echo -e "${YELLOW}📝 常用命令:${NC}"
    echo -e "${YELLOW}  查看日志: docker-compose logs -f web${NC}"
    echo -e "${YELLOW}  查看状态: docker-compose ps${NC}"
    echo -e "${YELLOW}  停止服务: docker-compose down${NC}"
    echo -e "${YELLOW}  重启服务: docker-compose restart${NC}"
}

# 显示故障排除信息
show_troubleshooting() {
    echo -e "${BLUE}🔧 故障排除${NC}"
    echo "========================================"
    echo -e "${YELLOW}如果遇到问题，请检查:${NC}"
    echo -e "${YELLOW}1. 确保API密钥正确配置在.env文件中${NC}"
    echo -e "${YELLOW}2. 检查防火墙是否阻止了端口8501${NC}"
    echo -e "${YELLOW}3. 确保Docker有足够的内存和磁盘空间${NC}"
    echo -e "${YELLOW}4. 查看容器日志: docker-compose logs -f web${NC}"
    echo ""
    echo -e "${YELLOW}📞 获取帮助:${NC}"
    echo -e "${YELLOW}  查看完整日志: docker-compose logs${NC}"
    echo -e "${YELLOW}  进入容器调试: docker exec -it TradingAgents-web bash${NC}"
    echo -e "${YELLOW}  重置环境: docker-compose down -v && docker system prune${NC}"
}

# 主函数
main() {
    echo -e "${GREEN}开始Docker部署修复流程...${NC}\n"
    
    check_prerequisites
    check_files  
    check_env_vars
    stop_existing_containers
    clean_old_images
    build_images
    start_services
    verify_services
    test_api_connections
    
    echo ""
    echo -e "${GREEN}🎉 Docker部署修复完成！${NC}"
    echo ""
    
    show_access_info
    echo ""
    show_troubleshooting
}

# 执行主函数
main "$@"