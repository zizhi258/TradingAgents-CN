#!/bin/bash
# Docker Compose启动脚本（包含调度服务）

echo "🚀 启动TradingAgents-CN（包含邮件调度服务）..."

# 检查.env文件是否存在
if [ ! -f .env ]; then
    echo "❌ 错误: .env文件不存在"
    echo "请复制.env.example为.env并配置必要的参数"
    exit 1
fi

# 检查是否配置了邮件服务
if ! grep -q "SMTP_USER=" .env || ! grep -q "SMTP_PASS=" .env; then
    echo "⚠️ 警告: 邮件服务未配置"
    echo "如需使用邮件功能，请在.env中配置SMTP参数"
fi

# 构建镜像
echo "🔨 构建Docker镜像..."
docker-compose build

# 启动服务
echo "🚀 启动所有服务..."
docker-compose --profile scheduler up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 5

# 显示服务状态
echo "📊 服务状态："
docker-compose ps

echo ""
echo "✅ 服务启动完成！"
echo ""
echo "🌐 访问地址："
echo "  - Web界面: http://localhost:8501"
echo "  - Redis管理: http://localhost:8081"
echo "  - MongoDB管理: http://localhost:8082 (用户名/密码: admin/tradingagents123)"
echo ""
echo "📧 邮件订阅功能："
echo "  1. 在Web界面选择'订阅管理'添加订阅"
echo "  2. 调度服务会在各交易所收市后自动发送研报"
echo ""
echo "📋 查看日志："
echo "  - Web日志: docker-compose logs -f web"
echo "  - 调度日志: docker-compose logs -f scheduler"
echo ""
echo "⏹️ 停止服务: docker-compose down"
