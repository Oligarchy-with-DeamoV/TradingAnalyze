#!/bin/bash

# =============================================================================
# TradingAnalyze 快速因子分析示例
# =============================================================================
# 这是一个简化的示例脚本，展示核心的数据下载和因子回测流程
# 适合快速入门和测试
#
# 使用方法:
#   chmod +x examples/quick_factor_example.sh
#   ./examples/quick_factor_example.sh
# =============================================================================

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_step() {
    echo -e "${CYAN}🔧 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# =============================================================================
# 配置参数 (简化版本用于快速测试)
# =============================================================================

WORKSPACE="./quick_example"
STOCKS="AAPL,MSFT,GOOGL"  # 只用3只股票快速测试
START_DATE="2023-01-01"
END_DATE="2023-06-30"    # 缩短时间范围

# 创建工作目录
mkdir -p "$WORKSPACE"

echo -e "${BLUE}🚀 TradingAnalyze 快速因子分析示例${NC}"
echo -e "${BLUE}====================================${NC}"
echo -e "📁 工作目录: ${YELLOW}$(realpath $WORKSPACE)${NC}"
echo -e "📈 分析股票: ${YELLOW}$STOCKS${NC}"
echo -e "📅 分析期间: ${YELLOW}$START_DATE${NC} 到 ${YELLOW}$END_DATE${NC}"
echo ""

# =============================================================================
# 步骤1: 下载数据
# =============================================================================

echo -e "${BLUE}📥 步骤1: 下载股票数据${NC}"
print_step "从 Yahoo Finance 下载数据"

poetry run trading_analyze data download \
    --source yahoo \
    --symbols "$STOCKS" \
    --start "$START_DATE" \
    --end "$END_DATE" \
    --output "$WORKSPACE/raw_data"

if [ $? -eq 0 ]; then
    print_success "数据下载完成"
else
    print_error "数据下载失败"
    echo ""
    echo -e "${YELLOW}💡 数据下载失败的可能原因：${NC}"
    echo "   • Yahoo Finance API限流（最常见）"
    echo "   • 网络连接问题"
    echo "   • 股票代码不正确"
    echo ""
    echo -e "${CYAN}🔧 建议解决方案：${NC}"
    echo "   • 等待10-15分钟后重试"
    echo "   • 减少股票数量（当前: $STOCKS）"
    echo "   • 缩短时间范围"
    echo "   • 检查网络连接"
    echo ""
    echo -e "${PURPLE}继续执行剩余步骤进行演示...${NC}"
    
    # 创建示例数据用于演示
    echo "创建示例数据用于演示后续步骤..."
    mkdir -p "$WORKSPACE/raw_data"
    
    # 创建一个简单的示例CSV文件
    cat > "$WORKSPACE/raw_data/AAPL_sample.csv" << 'EOF'
Date,Open,High,Low,Close,Volume
2023-01-03,130.28,130.90,124.17,125.07,112117800
2023-01-04,126.89,128.66,125.08,126.36,89113600
2023-01-05,127.13,127.77,124.76,125.02,80962700
2023-01-06,126.01,130.29,124.89,129.62,87754700
2023-01-09,130.47,133.41,129.89,130.15,70790800
EOF
    
    echo "已创建示例数据用于演示: $WORKSPACE/raw_data/AAPL_sample.csv"
fi

echo ""

# =============================================================================
# 步骤2: 转换数据
# =============================================================================

echo -e "${BLUE}🔄 步骤2: 转换数据格式${NC}"
print_step "转换为 qlib 格式"

poetry run trading_analyze data convert \
    --input "$WORKSPACE/raw_data" \
    --output "$WORKSPACE/qlib_data"

if [ $? -eq 0 ]; then
    print_success "数据转换完成"
else
    print_error "数据转换失败"
    exit 1
fi

echo ""

# =============================================================================
# 步骤3: 初始化 qlib
# =============================================================================

echo -e "${BLUE}⚙️ 步骤3: 初始化 qlib 环境${NC}"
print_step "配置 qlib 环境"

poetry run trading_analyze factor init \
    --data_dir "$WORKSPACE/qlib_data" \
    --region us

if [ $? -eq 0 ]; then
    print_success "qlib 初始化完成"
else
    print_error "qlib 初始化失败"
    exit 1
fi

echo ""

# =============================================================================
# 步骤4: 计算因子
# =============================================================================

echo -e "${BLUE}🧮 步骤4: 计算因子${NC}"
print_step "计算 Alpha 因子"

poetry run trading_analyze factor calc \
    --stocks "$STOCKS" \
    --start "$START_DATE" \
    --end "$END_DATE" \
    --factors alpha \
    --output "$WORKSPACE/factors.csv" \
    --data_dir "$WORKSPACE/qlib_data"

if [ $? -eq 0 ]; then
    print_success "因子计算完成"
    echo "📄 因子数据: $WORKSPACE/factors.csv"
else
    print_error "因子计算失败"
    exit 1
fi

echo ""

# =============================================================================
# 步骤5: 分析因子
# =============================================================================

echo -e "${BLUE}📊 步骤5: 分析因子表现${NC}"
print_step "分析因子预测能力"

poetry run trading_analyze factor analyze \
    --factor_file "$WORKSPACE/factors.csv" \
    --stocks "$STOCKS" \
    --start "$START_DATE" \
    --end "$END_DATE" \
    --output "$WORKSPACE/analysis.json" \
    --data_dir "$WORKSPACE/qlib_data"

if [ $? -eq 0 ]; then
    print_success "因子分析完成"
    echo "📄 分析结果: $WORKSPACE/analysis.json"
else
    print_error "因子分析失败，但继续执行回测"
fi

echo ""

# =============================================================================
# 步骤6: 回测因子
# =============================================================================

echo -e "${BLUE}🚀 步骤6: 因子回测${NC}"
print_step "执行简单回测策略"

poetry run trading_analyze factor backtest \
    --factor_file "$WORKSPACE/factors.csv" \
    --strategy simple \
    --output "$WORKSPACE/backtest.json" \
    --data_dir "$WORKSPACE/qlib_data"

if [ $? -eq 0 ]; then
    print_success "回测完成"
    echo "📄 回测结果: $WORKSPACE/backtest.json"
else
    print_error "回测失败"
fi

echo ""

# =============================================================================
# 总结
# =============================================================================

echo -e "${BLUE}🎉 快速示例完成!${NC}"
echo -e "${GREEN}📁 结果文件位于: ${YELLOW}$(realpath $WORKSPACE)/${NC}"
echo ""
echo "📋 生成的文件:"
echo "   • 原始数据: $WORKSPACE/raw_data/"
echo "   • qlib 数据: $WORKSPACE/qlib_data/"
echo "   • 因子数据: $WORKSPACE/factors.csv"
echo "   • 分析结果: $WORKSPACE/analysis.json"
echo "   • 回测结果: $WORKSPACE/backtest.json"
echo ""
echo -e "${CYAN}💡 下一步:${NC}"
echo "   • 查看 analysis.json 了解因子表现"
echo "   • 查看 backtest.json 了解回测结果"
echo "   • 运行完整示例: ./examples/complete_factor_analysis.sh"
echo ""
print_success "示例执行完成! 🚀"
