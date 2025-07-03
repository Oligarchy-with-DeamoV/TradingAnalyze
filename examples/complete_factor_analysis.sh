#!/bin/bash

# =============================================================================
# TradingAnalyze 完整因子分析示例
# =============================================================================
# 这个脚本展示了如何使用 TradingAnalyze CLI 进行完整的因子分析流程:
# 1. 数据下载
# 2. 数据转换和验证
# 3. 因子计算
# 4. 因子分析
# 5. 因子回测
#
# 使用方法:
#   chmod +x examples/complete_factor_analysis.sh
#   ./examples/complete_factor_analysis.sh
# =============================================================================

set -e  # 遇到错误立即退出

# 颜色输出函数
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================================${NC}"
}

print_step() {
    echo -e "${CYAN}🔧 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

# =============================================================================
# 配置参数
# =============================================================================

# 工作目录
WORKSPACE="./example_workspace"
RAW_DATA_DIR="$WORKSPACE/raw_data"
QLIB_DATA_DIR="$WORKSPACE/qlib_data"
OUTPUT_DIR="$WORKSPACE/output"

# 分析参数
STOCKS="AAPL,MSFT,GOOGL,TSLA,NVDA"  # 美股示例
START_DATE="2022-01-01"
END_DATE="2023-12-31"
REGION="us"

# 创建工作目录
mkdir -p "$RAW_DATA_DIR" "$QLIB_DATA_DIR" "$OUTPUT_DIR"

print_header "TradingAnalyze 完整因子分析示例"
echo -e "📁 工作目录: ${YELLOW}$(realpath $WORKSPACE)${NC}"
echo -e "📈 分析股票: ${YELLOW}$STOCKS${NC}"
echo -e "📅 分析期间: ${YELLOW}$START_DATE${NC} 到 ${YELLOW}$END_DATE${NC}"
echo ""

# =============================================================================
# 步骤1: 下载股票数据
# =============================================================================

print_header "📥 步骤1: 下载股票数据"

print_step "从 Yahoo Finance 下载数据..."
poetry run trading_analyze data download \
    --source yahoo \
    --symbols "$STOCKS" \
    --start "$START_DATE" \
    --end "$END_DATE" \
    --output "$RAW_DATA_DIR"

if [ $? -eq 0 ]; then
    print_success "数据下载完成"
    echo "📂 数据保存位置: $RAW_DATA_DIR"
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
    echo "   • 缩短时间范围（当前: $START_DATE 到 $END_DATE）"
    echo "   • 检查网络连接"
    echo ""
    print_warning "继续执行剩余步骤进行演示..."
    
    # 创建示例数据用于演示
    echo "创建示例数据用于演示后续步骤..."
    mkdir -p "$RAW_DATA_DIR"
    
    # 为每个股票创建示例数据
    for stock in $(echo $STOCKS | tr ',' ' '); do
        cat > "$RAW_DATA_DIR/${stock}_sample.csv" << 'EOF'
Date,Open,High,Low,Close,Volume
2022-01-03,130.28,130.90,124.17,125.07,112117800
2022-01-04,126.89,128.66,125.08,126.36,89113600
2022-01-05,127.13,127.77,124.76,125.02,80962700
2022-01-06,126.01,130.29,124.89,129.62,87754700
2022-01-09,130.47,133.41,129.89,130.15,70790800
EOF
    done
    
    echo "已创建示例数据用于演示: $RAW_DATA_DIR"
fi

echo ""

# =============================================================================
# 步骤2: 转换数据格式
# =============================================================================

print_header "🔄 步骤2: 转换数据为 qlib 格式"

print_step "转换 Yahoo Finance 数据为 qlib 格式..."
poetry run trading_analyze data convert \
    --input "$RAW_DATA_DIR" \
    --output "$QLIB_DATA_DIR"

if [ $? -eq 0 ]; then
    print_success "数据转换完成"
    echo "📂 qlib 数据位置: $QLIB_DATA_DIR"
else
    print_error "数据转换失败"
    exit 1
fi

echo ""

# =============================================================================
# 步骤3: 验证数据质量
# =============================================================================

print_header "✅ 步骤3: 验证数据质量"

print_step "验证数据完整性和质量..."
poetry run trading_analyze data validate \
    --data_dir "$QLIB_DATA_DIR" \
    --output "$OUTPUT_DIR/validation_report.txt"

if [ $? -eq 0 ]; then
    print_success "数据验证完成"
    echo "📄 验证报告: $OUTPUT_DIR/validation_report.txt"
    
    # 显示验证报告摘要
    if [ -f "$OUTPUT_DIR/validation_report.txt" ]; then
        echo "📋 验证报告摘要:"
        head -10 "$OUTPUT_DIR/validation_report.txt"
    fi
else
    print_warning "数据验证失败，但继续执行"
fi

echo ""

# =============================================================================
# 步骤4: 初始化 qlib 环境
# =============================================================================

print_header "⚙️ 步骤4: 初始化 qlib 环境"

print_step "初始化 qlib 配置..."
poetry run trading_analyze factor init \
    --data_dir "$QLIB_DATA_DIR" \
    --region "$REGION"

if [ $? -eq 0 ]; then
    print_success "qlib 环境初始化完成"
else
    print_error "qlib 初始化失败"
    exit 1
fi

echo ""

# =============================================================================
# 步骤5: 计算 Alpha 因子
# =============================================================================

print_header "🧮 步骤5: 计算 Alpha 因子"

print_step "计算预定义的 Alpha 因子..."
poetry run trading_analyze factor calc \
    --stocks "$STOCKS" \
    --start "$START_DATE" \
    --end "$END_DATE" \
    --factors alpha \
    --output "$OUTPUT_DIR/alpha_factors.csv" \
    --data_dir "$QLIB_DATA_DIR"

if [ $? -eq 0 ]; then
    print_success "Alpha 因子计算完成"
    echo "📄 因子数据: $OUTPUT_DIR/alpha_factors.csv"
    
    # 显示因子数据概览
    if [ -f "$OUTPUT_DIR/alpha_factors.csv" ]; then
        echo "📊 因子数据概览:"
        head -5 "$OUTPUT_DIR/alpha_factors.csv"
    fi
else
    print_error "Alpha 因子计算失败"
    exit 1
fi

echo ""

# =============================================================================
# 步骤6: 计算自定义因子
# =============================================================================

print_header "🎯 步骤6: 计算自定义因子"

# 创建自定义因子配置文件
CUSTOM_CONFIG="$OUTPUT_DIR/custom_factors.json"
cat > "$CUSTOM_CONFIG" << EOF
{
    "momentum_5d": "(close / delay(close, 5) - 1)",
    "momentum_20d": "(close / delay(close, 20) - 1)",
    "price_volume": "close * volume",
    "rsi_14": "ta_rsi(close, 14)",
    "ma_ratio": "close / ma(close, 20)",
    "volatility_20d": "std(log(close / delay(close, 1)), 20)",
    "return_1d": "(close / delay(close, 1) - 1)",
    "high_low_ratio": "(high - low) / close"
}
EOF

print_step "创建自定义因子配置文件..."
echo "📄 自定义因子配置: $CUSTOM_CONFIG"

print_step "计算自定义因子..."
poetry run trading_analyze factor calc \
    --stocks "$STOCKS" \
    --start "$START_DATE" \
    --end "$END_DATE" \
    --factors custom \
    --custom_config "$CUSTOM_CONFIG" \
    --output "$OUTPUT_DIR/custom_factors.csv" \
    --data_dir "$QLIB_DATA_DIR"

if [ $? -eq 0 ]; then
    print_success "自定义因子计算完成"
    echo "📄 自定义因子数据: $OUTPUT_DIR/custom_factors.csv"
else
    print_warning "自定义因子计算失败，但继续执行"
fi

echo ""

# =============================================================================
# 步骤7: 分析 Alpha 因子表现
# =============================================================================

print_header "📊 步骤7: 分析 Alpha 因子表现"

print_step "分析 Alpha 因子的预测能力..."
poetry run trading_analyze factor analyze \
    --factor_file "$OUTPUT_DIR/alpha_factors.csv" \
    --stocks "$STOCKS" \
    --start "$START_DATE" \
    --end "$END_DATE" \
    --periods "1,5,20" \
    --output "$OUTPUT_DIR/alpha_analysis.json" \
    --data_dir "$QLIB_DATA_DIR"

if [ $? -eq 0 ]; then
    print_success "Alpha 因子分析完成"
    echo "📄 分析结果: $OUTPUT_DIR/alpha_analysis.json"
else
    print_warning "Alpha 因子分析失败"
fi

echo ""

# =============================================================================
# 步骤8: 分析自定义因子表现 (如果存在)
# =============================================================================

if [ -f "$OUTPUT_DIR/custom_factors.csv" ]; then
    print_header "🎯 步骤8: 分析自定义因子表现"
    
    print_step "分析自定义因子的预测能力..."
    poetry run trading_analyze factor analyze \
        --factor_file "$OUTPUT_DIR/custom_factors.csv" \
        --stocks "$STOCKS" \
        --start "$START_DATE" \
        --end "$END_DATE" \
        --periods "1,5,20" \
        --output "$OUTPUT_DIR/custom_analysis.json" \
        --data_dir "$QLIB_DATA_DIR"
    
    if [ $? -eq 0 ]; then
        print_success "自定义因子分析完成"
        echo "📄 分析结果: $OUTPUT_DIR/custom_analysis.json"
    else
        print_warning "自定义因子分析失败"
    fi
    
    echo ""
fi

# =============================================================================
# 步骤9: 简单回测
# =============================================================================

print_header "🚀 步骤9: 简单因子回测"

print_step "执行基于 Alpha 因子的简单回测..."
poetry run trading_analyze factor backtest \
    --factor_file "$OUTPUT_DIR/alpha_factors.csv" \
    --strategy simple \
    --output "$OUTPUT_DIR/simple_backtest.json" \
    --data_dir "$QLIB_DATA_DIR"

if [ $? -eq 0 ]; then
    print_success "简单回测完成"
    echo "📄 回测结果: $OUTPUT_DIR/simple_backtest.json"
else
    print_warning "简单回测失败"
fi

echo ""

# =============================================================================
# 步骤10: 组合策略回测 (如果有自定义因子)
# =============================================================================

if [ -f "$OUTPUT_DIR/custom_factors.csv" ]; then
    print_header "💼 步骤10: 组合策略回测"
    
    print_step "使用最佳自定义因子执行组合策略回测..."
    poetry run trading_analyze factor backtest \
        --factor_file "$OUTPUT_DIR/custom_factors.csv" \
        --factors "momentum_20d,rsi_14,ma_ratio" \
        --strategy portfolio \
        --n_top 3 \
        --transaction_cost 0.002 \
        --rebalance_freq "20D" \
        --output "$OUTPUT_DIR/portfolio_backtest.json" \
        --report \
        --data_dir "$QLIB_DATA_DIR"
    
    if [ $? -eq 0 ]; then
        print_success "组合策略回测完成"
        echo "📄 回测结果: $OUTPUT_DIR/portfolio_backtest.json"
    else
        print_warning "组合策略回测失败"
    fi
    
    echo ""
fi

# =============================================================================
# 步骤11: 生成实验汇总
# =============================================================================

print_header "📋 步骤11: 生成实验汇总"

SUMMARY_FILE="$OUTPUT_DIR/experiment_summary.md"

cat > "$SUMMARY_FILE" << EOF
# TradingAnalyze 因子分析实验汇总

## 实验配置

- **分析股票**: $STOCKS
- **时间范围**: $START_DATE 到 $END_DATE
- **市场区域**: $REGION
- **工作目录**: $(realpath $WORKSPACE)
- **执行时间**: $(date)

## 生成的文件

### 数据文件
- 原始数据: \`$RAW_DATA_DIR\`
- qlib 数据: \`$QLIB_DATA_DIR\`
- 数据验证报告: \`$OUTPUT_DIR/validation_report.txt\`

### 因子文件
- Alpha 因子: \`$OUTPUT_DIR/alpha_factors.csv\`
- 自定义因子: \`$OUTPUT_DIR/custom_factors.csv\`
- 自定义因子配置: \`$OUTPUT_DIR/custom_factors.json\`

### 分析结果
- Alpha 因子分析: \`$OUTPUT_DIR/alpha_analysis.json\`
- 自定义因子分析: \`$OUTPUT_DIR/custom_analysis.json\`

### 回测结果
- 简单回测: \`$OUTPUT_DIR/simple_backtest.json\`
- 组合策略回测: \`$OUTPUT_DIR/portfolio_backtest.json\`

## 下一步建议

1. **查看数据质量**: 检查 \`validation_report.txt\` 了解数据完整性
2. **分析因子表现**: 查看 \`*_analysis.json\` 文件中的 IC 和 IR 指标
3. **评估回测结果**: 比较不同策略的收益率和风险指标
4. **优化参数**: 调整因子组合、调仓频率、交易成本等参数
5. **扩展分析**: 尝试更多股票、更长时间段或其他因子

## 常用 CLI 命令

\`\`\`bash
# 查看帮助
poetry run trading_analyze --help
poetry run trading_analyze data --help
poetry run trading_analyze factor --help

# 下载更多数据
poetry run trading_analyze data download --source yahoo --symbols "AAPL,MSFT" --start 2023-01-01 --end 2023-12-31

# 计算不同因子
poetry run trading_analyze factor calc --stocks "AAPL,MSFT" --start 2023-01-01 --end 2023-12-31 --factors alpha

# 回测优化
poetry run trading_analyze factor backtest --factor_file factors.csv --strategy portfolio --n_top 5 --transaction_cost 0.001
\`\`\`
EOF

print_success "实验汇总已生成"
echo "📄 汇总报告: $SUMMARY_FILE"

echo ""

# =============================================================================
# 最终总结
# =============================================================================

print_header "🎉 完整因子分析流程已完成!"

echo -e "${GREEN}✅ 主要成果:${NC}"
echo "   📂 完整的数据管道: 下载 → 转换 → 验证"
echo "   🧮 因子计算: Alpha 因子 + 自定义因子"
echo "   📊 因子分析: IC/IR 分析和表现评估"
echo "   🚀 策略回测: 简单策略 + 组合策略"

echo ""
echo -e "${CYAN}📁 所有结果文件位于: ${YELLOW}$(realpath $OUTPUT_DIR)${NC}"
echo -e "${CYAN}📖 详细报告: ${YELLOW}$SUMMARY_FILE${NC}"

echo ""
echo -e "${PURPLE}💡 提示:${NC}"
echo "   • 查看各个 JSON 文件了解详细的数量化结果"
echo "   • 根据 IC/IR 指标选择最佳因子"
echo "   • 调整回测参数优化策略表现"
echo "   • 使用验证报告确保数据质量"

echo ""
print_success "示例执行完成! 🚀"
