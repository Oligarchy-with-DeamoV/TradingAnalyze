# TradingAnalyze

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![Poetry](https://img.shields.io/badge/dependency%20manager-poetry-blue.svg)](https://python-poetry.org/)

**TradingAnalyze** 是一个专业的量化交易分析工具，专注于因子挖掘、策略回测和交易分析。该项目基于 qlib 量化平台，提供完整的数据处理、因子计算、策略回测和交易分析功能。

## 🎯 项目理念

一个成功的量化交易者应该做到基于基本面选股，随后在中期进行交易投机来获得收益。本项目主要为量化交易模型提供支持，回答如何在基本面良好的标的中进行有效交易的问题。

结合券商导出的交易明细来分析账户操作者的交易习惯，帮助回溯反思和优化交易模型。

## ✨ 核心功能

### 📊 数据管道
- **多源数据下载**: 支持 Yahoo Finance、CSV 文件等多种数据源
- **数据格式转换**: 自动转换为 qlib 标准格式
- **数据质量验证**: 完整的数据质量检查和验证报告
- **交易日历生成**: 自动生成标准交易日历

### 🔍 因子挖掘
- **Alpha 因子计算**: 内置 27 个经典 Alpha 因子
- **自定义因子支持**: 支持自定义因子表达式
- **因子分析**: IC/IR 分析、因子表现评估
- **多维度分析**: 价格、成交量、波动率、技术指标等多维度因子

### 🎯 策略回测
- **简单策略回测**: 基于单因子的简单交易策略
- **组合策略回测**: 多因子组合策略回测
- **风险指标计算**: 夏普比率、最大回撤、年化收益等
- **回测报告生成**: 详细的回测结果分析报告

### 📈 交易分析
- **交易明细分析**: 支持券商交易明细导入分析
- **交易习惯分析**: 分析交易者的操作模式和习惯
- **策略表现评估**: 历史交易策略的表现评估

## 🚀 快速开始

### 环境要求
- Python 3.8+
- Poetry (推荐) 或 pip

### 安装依赖
```bash
# 使用 Poetry (推荐)
poetry install

# 或使用 pip
pip install -e .
```

### 快速体验
```bash
# 赋予执行权限
chmod +x examples/quick_factor_example.sh

# 运行快速示例 (约5-10分钟)
./examples/quick_factor_example.sh
```

这个快速示例包含：
- 下载 3 只美股数据 (AAPL, MSFT, GOOGL)
- 转换为 qlib 格式
- 计算 27 个 Alpha 因子
- 进行因子分析和回测

## 📖 详细使用指南

### 命令行工具
TradingAnalyze 提供了完整的命令行接口：

```bash
# 查看帮助
poetry run trading_analyze --help

# 数据相关命令
poetry run trading_analyze data --help

# 因子相关命令  
poetry run trading_analyze factor --help

# 交易分析命令
poetry run trading_analyze trading --help
```

### 数据处理流程
```bash
# 1. 下载数据
poetry run trading_analyze data download \
  --source yahoo \
  --symbols "AAPL,MSFT,GOOGL" \
  --start "2023-01-01" \
  --end "2023-12-31" \
  --output "./raw_data"

# 2. 转换数据格式
poetry run trading_analyze data convert \
  --input "./raw_data" \
  --output "./qlib_data"

# 3. 验证数据质量
poetry run trading_analyze data validate \
  --data_dir "./qlib_data" \
  --output "validation_report.txt"
```

### 因子计算与分析
```bash
# 1. 初始化 qlib 环境
poetry run trading_analyze factor init \
  --data_dir "./qlib_data" \
  --region "us"

# 2. 计算 Alpha 因子
poetry run trading_analyze factor calc \
  --stocks "AAPL,MSFT,GOOGL" \
  --start "2023-01-01" \
  --end "2023-12-31" \
  --factors "alpha" \
  --output "./alpha_factors.csv"

# 3. 因子分析
poetry run trading_analyze factor analyze \
  --factor_file "./alpha_factors.csv" \
  --stocks "AAPL,MSFT,GOOGL" \
  --start "2023-01-01" \
  --end "2023-12-31" \
  --output "./analysis_results.json"

# 4. 因子回测
poetry run trading_analyze factor backtest \
  --factor_file "./alpha_factors.csv" \
  --strategy "simple" \
  --output "./backtest_results.json"
```

### 交易分析
```bash
# 分析交易明细
poetry run trading_analyze trading analyze \
  --csv_file_path "./trading_records.csv"
```

## 💡 内置因子列表

### 价格因子
- `returns_1d`, `returns_5d`, `returns_20d`: 不同周期收益率
- `ma_5`, `ma_10`, `ma_20`, `ma_60`: 移动平均线

### 相对位置因子
- `close_to_ma20`: 收盘价相对20日均线位置
- `close_to_high20`: 收盘价相对20日最高价位置
- `close_to_low20`: 收盘价相对20日最低价位置

### 波动率因子
- `volatility_20d`, `volatility_60d`: 不同周期波动率

### 成交量因子
- `volume_ma_20`: 成交量移动平均
- `volume_ratio`: 成交量比率
- `turnover_20d`: 换手率
- `vwap_5`: 成交量加权平均价

### 技术指标因子
- `rsi_14`: 相对强弱指标
- `bias_20`: 乖离率
- `price_volume_corr`: 价量相关性

### 市场微观结构因子
- `high_low_ratio`: 最高最低价比率
- `open_close_ratio`: 开盘收盘价比率
- `intraday_return`: 日内收益率

### 动量和反转因子
- `momentum_5d`, `momentum_20d`, `momentum_60d`: 不同周期动量
- `reversal_1d`, `reversal_5d`: 短期反转因子

## 📁 项目结构

```
TradingAnalyze/
├── README.md                  # 项目说明
├── pyproject.toml             # 项目配置
├── poetry.lock                # 依赖锁定
├── examples/                  # 使用示例
│   ├── quick_factor_example.sh        # 快速示例
│   ├── complete_factor_analysis.sh    # 完整分析示例
│   └── README.md                      # 示例说明
├── src/trading_analyze/       # 核心代码
│   ├── __init__.py
│   ├── run.py                 # 程序入口
│   ├── cli/                   # 命令行接口
│   │   ├── data_cli.py        # 数据处理命令
│   │   ├── factor_cli.py      # 因子分析命令
│   │   └── trading_cli.py     # 交易分析命令
│   ├── data_pipeline/         # 数据处理管道
│   │   ├── downloader.py      # 数据下载器
│   │   ├── converter.py       # 数据格式转换
│   │   └── validator.py       # 数据验证
│   └── factor_mining/         # 因子挖掘
│       ├── qlib_factor_calculator.py  # 因子计算器
│       └── qlib_backtester.py         # 回测引擎
└── tests/                     # 测试代码
```

## 🔧 技术栈

- **核心框架**: [qlib](https://github.com/microsoft/qlib) - 微软开源量化平台
- **数据处理**: pandas, numpy
- **机器学习**: scikit-learn
- **数据源**: Yahoo Finance, CSV 文件
- **命令行**: Click
- **日志系统**: structlog
- **测试框架**: pytest
- **依赖管理**: Poetry

## 📊 Milestones

- [x] 支持 Yahoo Finance 数据下载
- [x] 完整的 qlib 数据处理管道
- [x] 27 个 Alpha 因子计算
- [x] 因子分析和回测功能
- [x] 命令行工具集成
- [x] 完整的示例和文档
- [ ] 支持更多券商数据格式
- [ ] 实时数据流处理
- [ ] 机器学习模型集成
- [ ] 交易信号生成
- [ ] 风险管理模块

## 🎯 使用场景

### 1. 量化研究
- 快速验证因子有效性
- 多因子组合策略研究
- 回测验证策略表现

### 2. 交易分析
- 分析历史交易记录
- 识别交易模式和习惯
- 优化交易策略

### 3. 风险管理
- 计算风险指标
- 监控策略表现
- 优化资产配置

## 🤝 贡献指南

欢迎贡献代码、报告问题或提出改进建议！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 Apache 2.0 许可证 - 详见 [LICENSE](LICENSE) 文件。

## 📞 联系方式

- 作者: Vincent Duan
- 邮箱: vincent.duan95@outlook.com
- 项目地址: https://github.com/Duan-JM/TradingAnalyze

## 🙏 致谢

感谢以下开源项目的支持：
- [qlib](https://github.com/microsoft/qlib) - 微软开源量化平台
- [Yahoo Finance API](https://github.com/ranaroussi/yfinance) - 免费的金融数据API
- [Poetry](https://python-poetry.org/) - 现代Python依赖管理工具

---

**免责声明**: 本项目仅用于学习和研究目的，不构成投资建议。使用本项目进行实际交易的风险由用户自行承担。
