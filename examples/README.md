# TradingAnalyze 示例

这个目录包含了使用 TradingAnalyze CLI 进行因子分析的完整示例。

## 快速开始

### 1. 快速示例 (推荐新手)

```bash
# 赋予执行权限
chmod +x examples/quick_factor_example.sh

# 运行快速示例 (约5-10分钟)
./examples/quick_factor_example.sh
```

**快速示例特点:**
- 使用3只美股 (AAPL, MSFT, GOOGL)
- 分析6个月数据 (2023年上半年)
- 包含完整流程: 数据下载 → 因子计算 → 因子分析 → 回测
- 适合快速验证环境和了解基本流程

### 2. 完整示例 (深度分析)

```bash
# 赋予执行权限
chmod +x examples/complete_factor_analysis.sh

# 运行完整示例 (约15-30分钟)
./examples/complete_factor_analysis.sh
```

**完整示例特点:**
- 使用5只美股 (AAPL, MSFT, GOOGL, TSLA, NVDA)
- 分析2年数据 (2022-2023)
- 包含Alpha因子和自定义因子
- 多种回测策略 (简单策略 + 组合策略)
- 完整的数据验证和分析报告

## 示例流程说明

### 数据管道
1. **数据下载**: 从Yahoo Finance下载股票数据
2. **数据转换**: 转换为qlib标准格式
3. **数据验证**: 检查数据质量和完整性

### 因子挖掘
4. **初始化qlib**: 配置qlib环境
5. **计算Alpha因子**: 使用预定义的Alpha因子
6. **计算自定义因子**: 技术指标和量价因子
7. **因子分析**: IC/IR分析评估因子表现

### 策略回测
8. **简单回测**: 基于单因子的简单策略
9. **组合回测**: 多因子组合策略
10. **结果分析**: 收益率、夏普比率、最大回撤等指标

## 输出文件说明

### 数据文件
- `raw_data/`: Yahoo Finance原始数据
- `qlib_data/`: qlib标准格式数据
- `validation_report.txt`: 数据质量验证报告

### 因子文件
- `alpha_factors.csv`: Alpha因子数据
- `custom_factors.csv`: 自定义因子数据
- `custom_factors.json`: 自定义因子配置

### 分析结果
- `alpha_analysis.json`: Alpha因子分析结果
- `custom_analysis.json`: 自定义因子分析结果
- `simple_backtest.json`: 简单回测结果
- `portfolio_backtest.json`: 组合策略回测结果

### 汇总报告
- `experiment_summary.md`: 实验汇总报告

## 自定义配置

### 修改股票池
编辑脚本中的 `STOCKS` 变量:
```bash
STOCKS="AAPL,MSFT,GOOGL,TSLA,NVDA,AMZN,META"
```

### 修改时间范围
编辑脚本中的日期变量:
```bash
START_DATE="2020-01-01"
END_DATE="2023-12-31"
```

### 自定义因子
修改 `custom_factors.json` 文件添加新的因子表达式:
```json
{
    "my_factor": "(close / ma(close, 10) - 1)",
    "volume_ratio": "volume / ma(volume, 20)"
}
```

## 常用CLI命令

### 数据相关
```bash
# 下载数据
poetry run trading_analyze data download --source yahoo --symbols "AAPL,MSFT" --start 2023-01-01 --end 2023-12-31

# 转换数据
poetry run trading_analyze data convert --input ./raw_data --output ./qlib_data

# 验证数据
poetry run trading_analyze data validate --input ./qlib_data --output validation.txt
```

### 因子相关
```bash
# 初始化qlib
poetry run trading_analyze factor init --data_dir ./qlib_data --region us

# 计算因子
poetry run trading_analyze factor calc --stocks "AAPL,MSFT" --start 2023-01-01 --end 2023-12-31 --factors alpha

# 分析因子
poetry run trading_analyze factor analyze --factor_file factors.csv --stocks "AAPL,MSFT" --start 2023-01-01 --end 2023-12-31

# 回测因子
poetry run trading_analyze factor backtest --factor_file factors.csv --strategy simple
```

## 注意事项

1. **网络连接**: 数据下载需要稳定的网络连接
2. **Yahoo Finance限流**: Yahoo Finance有严格的请求频率限制，可能需要：
   - 减少股票数量（建议一次最多3-5只）
   - 缩短时间范围
   - 增加请求间隔
   - 如果持续限流，可稍等几分钟后重试
3. **计算资源**: 大量股票和长时间范围需要更多计算时间
4. **依赖环境**: 确保已安装所有必要的Python包

## 故障排除

### 常见问题

**Q: Yahoo Finance限流/请求过多错误**
A: 这是正常现象，建议：
- 减少股票数量（示例中的3-5只通常没问题）
- 缩短时间范围（6个月以内）
- 等待10-15分钟后重试
- 考虑使用CSV数据源

**Q: 数据下载失败**
A: 检查网络连接，减少股票数量或缩短时间范围

**Q: qlib初始化失败**
A: 确保数据格式正确，检查qlib安装是否完整

**Q: 因子计算错误**
A: 验证股票代码格式，确保时间范围内有数据

**Q: 回测失败**
A: 检查因子数据是否包含有效的数值

### 获取帮助
```bash
# 查看总体帮助
poetry run trading_analyze --help

# 查看子命令帮助
poetry run trading_analyze data --help
poetry run trading_analyze factor --help
```

## ✅ 修复说明

最新版本已修复以下问题：
- ✅ Yahoo Finance API的threads参数兼容性
- ✅ 时区信息处理（UTC转换）
- ✅ CLI命令参数优化
- ✅ 重试机制和错误处理
- ✅ 数据转换格式标准化

示例脚本现在可以完整运行，即使遇到Yahoo Finance限流也会提供详细的解决建议。

基于这些示例，你可以:
1. 添加更多股票进行分析
2. 实现自己的因子表达式
3. 调整回测参数优化策略
4. 集成到自动化交易系统
5. 添加更多技术指标

## 反馈和贡献

如果你有任何问题或建议，欢迎提交Issue或Pull Request。
