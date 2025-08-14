#!/bin/bash

# TradingAgents-CN 分析日志查看工具
# 使用方法: ./scripts/view_analysis_logs.sh [选项]

echo "🔍 TradingAgents-CN 分析日志查看工具"
echo "========================================"

case "$1" in
    "real-time"|"rt")
        echo "📺 实时查看分析日志..."
        docker-compose logs -f web | grep -E "(🤖|✅|❌|模型选择|API调用|分析完成|执行成功|执行失败|DeepSeek|备用模型)"
        ;;
    "models"|"m")
        echo "🤖 查看模型执行日志..."
        docker-compose logs --tail 200 web | grep -E "(模型选择|任务执行|API调用|DeepSeek|执行成功|执行失败|备用模型|置信度)" | tail -30
        ;;
    "agents"|"a")
        echo "🤖 查看智能体分析日志..."
        docker-compose logs --tail 200 web | grep -E "(运行智能体|分析完成|news_hunter|fundamental_expert|technical_analyst|sentiment_analyst|risk_manager)" | tail -20
        ;;
    "results"|"r")
        echo "📊 查看分析结果日志..."
        docker exec TradingAgents-web tail -50 /app/logs/tradingagents.log | grep -E "(分析结果|TaskResult|analysis.*success|final_result)"
        ;;
    "errors"|"e")
        echo "❌ 查看错误日志..."
        docker-compose logs --tail 100 web | grep -E "(ERROR|WARN|❌|失败|异常|timeout|超时)" | tail -20
        ;;
    "costs"|"c")
        echo "💰 查看成本统计..."
        docker-compose logs --tail 200 web | grep -E "(成本|cost|耗时|token|tokens)" | tail -15
        ;;
    "structured"|"s")
        echo "📋 查看结构化日志..."
        docker exec TradingAgents-web tail -100 /app/logs/tradingagents_structured.log | tail -20
        ;;
    "help"|"h"|*)
        echo "📖 使用方法:"
        echo "  ./scripts/view_analysis_logs.sh [选项]"
        echo ""
        echo "选项:"
        echo "  real-time, rt  - 实时查看分析日志"
        echo "  models, m      - 查看模型执行日志"
        echo "  agents, a      - 查看智能体分析日志"  
        echo "  results, r     - 查看分析结果日志"
        echo "  errors, e      - 查看错误日志"
        echo "  costs, c       - 查看成本统计"
        echo "  structured, s  - 查看结构化日志"
        echo "  help, h        - 显示帮助信息"
        echo ""
        echo "示例:"
        echo "  ./scripts/view_analysis_logs.sh rt     # 实时查看"
        echo "  ./scripts/view_analysis_logs.sh m      # 查看模型日志"
        echo "  ./scripts/view_analysis_logs.sh a      # 查看智能体日志"
        ;;
esac