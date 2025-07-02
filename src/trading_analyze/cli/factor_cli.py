"""因子挖掘 CLI 命令。"""

import json
from pathlib import Path

import click
import structlog

from ..factor_mining import QlibBacktester, QlibFactorCalculator

logger = structlog.get_logger()


@click.group()
def factor_cli():
    """因子挖掘相关命令。"""
    pass


@factor_cli.command("init")
@click.option("--data_dir", default="./qlib_data", help="qlib 数据目录")
@click.option("--region", default="cn", help="市场区域 (cn/us)")
def init_qlib(data_dir, region):
    """初始化 qlib 环境。"""
    try:
        click.echo(f"初始化 qlib 环境...")
        click.echo(f"数据目录: {data_dir}")
        click.echo(f"市场区域: {region}")
        
        # 创建数据目录
        Path(data_dir).mkdir(parents=True, exist_ok=True)
        
        # 初始化 qlib
        calculator = QlibFactorCalculator(provider_uri=data_dir, region=region)
        status = calculator.check_qlib_status()
        
        if status["initialized"]:
            click.echo("✅ qlib 初始化成功")
            click.echo(f"状态: {json.dumps(status, indent=2, ensure_ascii=False)}")
        else:
            click.echo("❌ qlib 初始化失败", err=True)
        
    except Exception as e:
        logger.error("qlib 初始化失败", error=str(e))
        click.echo(f"错误: {str(e)}", err=True)


@factor_cli.command("calc")
@click.option("--stocks", help="股票代码列表，逗号分隔")
@click.option("--start", help="开始日期 (YYYY-MM-DD)")
@click.option("--end", help="结束日期 (YYYY-MM-DD)")
@click.option("--factors", help="因子类型 (alpha/custom)")
@click.option("--custom_config", help="自定义因子配置文件路径")
@click.option("--output", default="factors.csv", help="输出文件")
@click.option("--data_dir", default="./qlib_data", help="qlib 数据目录")
def calculate_factors(stocks, start, end, factors, custom_config, output, data_dir):
    """计算因子。"""
    try:
        click.echo(f"计算因子...")
        
        if not stocks or not start or not end:
            click.echo("错误: 需要提供 --stocks, --start, --end 参数", err=True)
            return
        
        stock_list = [s.strip() for s in stocks.split(",")]
        click.echo(f"股票: {stock_list}")
        click.echo(f"时间范围: {start} 到 {end}")
        
        # 初始化计算器
        calculator = QlibFactorCalculator(provider_uri=data_dir)
        
        # 计算因子
        if factors == "alpha" or not factors:
            click.echo("计算 Alpha 因子...")
            factor_data = calculator.calculate_alpha_factors(stock_list, start, end)
        elif factors == "custom" and custom_config:
            click.echo(f"使用自定义配置: {custom_config}")
            with open(custom_config, 'r') as f:
                factor_expressions = json.load(f)
            factor_data = calculator.calculate_custom_factors(stock_list, start, end, factor_expressions)
        else:
            click.echo("错误: 无效的因子类型或缺少自定义配置", err=True)
            return
        
        # 保存结果
        calculator.save_factor_data(factor_data, output)
        click.echo(f"✅ 因子计算完成，结果保存到: {output}")
        click.echo(f"数据形状: {factor_data.shape}")
        
    except Exception as e:
        logger.error("因子计算失败", error=str(e))
        click.echo(f"错误: {str(e)}", err=True)


@factor_cli.command("analyze")
@click.option("--factor_file", required=True, help="因子数据文件路径")
@click.option("--stocks", help="股票代码列表，逗号分隔")
@click.option("--start", help="开始日期 (YYYY-MM-DD)")
@click.option("--end", help="结束日期 (YYYY-MM-DD)")
@click.option("--periods", default="1,5,20", help="前瞻收益周期，逗号分隔")
@click.option("--output", default="analysis_results.json", help="分析结果输出文件")
@click.option("--data_dir", default="./qlib_data", help="qlib 数据目录")
def analyze_factors(factor_file, stocks, start, end, periods, output, data_dir):
    """分析因子表现。"""
    try:
        click.echo(f"分析因子表现...")
        click.echo(f"因子文件: {factor_file}")
        
        # 初始化计算器和回测器
        calculator = QlibFactorCalculator(provider_uri=data_dir)
        backtester = QlibBacktester(provider_uri=data_dir)
        
        # 加载因子数据
        factor_data = calculator.load_factor_data(factor_file)
        click.echo(f"因子数据形状: {factor_data.shape}")
        
        # 如果需要添加收益数据
        if stocks and start and end:
            stock_list = [s.strip() for s in stocks.split(",")]
            period_list = [int(p.strip()) for p in periods.split(",")]
            
            click.echo("添加前瞻收益数据...")
            factor_data_with_returns = calculator.get_factor_data_with_returns(
                stock_list, start, end, None, period_list
            )
            
            # 使用有收益数据的版本进行分析
            factor_cols = [col for col in factor_data.columns if not col.startswith('label_')]
            label_cols = [f"label_{p}d" for p in period_list]
            
            analysis_results = backtester.analyze_factor_performance(
                factor_data_with_returns, factor_cols, label_cols
            )
        else:
            # 只分析现有数据
            factor_cols = [col for col in factor_data.columns if not col.startswith('label_')]
            label_cols = [col for col in factor_data.columns if col.startswith('label_')]
            
            if not label_cols:
                click.echo("警告: 没有找到标签数据，无法进行完整分析", err=True)
                return
            
            analysis_results = backtester.analyze_factor_performance(
                factor_data, factor_cols, label_cols
            )
        
        # 保存分析结果
        backtester.save_backtest_results(analysis_results, output)
        click.echo(f"✅ 因子分析完成，结果保存到: {output}")
        
        # 显示简要结果
        if "summary" in analysis_results and "best_factors_by_period" in analysis_results["summary"]:
            click.echo("\n📊 最佳因子汇总:")
            for period, info in analysis_results["summary"]["best_factors_by_period"].items():
                click.echo(f"  {period}: {info['factor']} (IC={info['ic_mean']:.4f}, IR={info['ic_ir']:.4f})")
        
    except Exception as e:
        logger.error("因子分析失败", error=str(e))
        click.echo(f"错误: {str(e)}", err=True)


@factor_cli.command("backtest")
@click.option("--factor_file", required=True, help="因子数据文件路径")
@click.option("--factors", help="要回测的因子列表，逗号分隔")
@click.option("--strategy", default="simple", help="回测策略类型 (simple/portfolio/qlib)")
@click.option("--n_top", default=50, type=int, help="选股数量")
@click.option("--transaction_cost", default=0.002, type=float, help="交易成本")
@click.option("--rebalance_freq", default="20D", help="调仓频率")
@click.option("--output", default="backtest_results.json", help="回测结果输出文件")
@click.option("--report", is_flag=True, help="生成详细报告")
@click.option("--data_dir", default="./qlib_data", help="qlib 数据目录")
def backtest_factors(factor_file, factors, strategy, n_top, transaction_cost, 
                    rebalance_freq, output, report, data_dir):
    """回测因子策略。"""
    try:
        click.echo(f"回测因子策略...")
        click.echo(f"因子文件: {factor_file}")
        click.echo(f"策略类型: {strategy}")
        
        # 初始化回测器
        backtester = QlibBacktester(provider_uri=data_dir)
        calculator = QlibFactorCalculator(provider_uri=data_dir)
        
        # 加载因子数据
        factor_data = calculator.load_factor_data(factor_file)
        click.echo(f"数据形状: {factor_data.shape}")
        
        # 确定要回测的因子
        if factors:
            factor_list = [f.strip() for f in factors.split(",")]
        else:
            factor_list = [col for col in factor_data.columns if not col.startswith('label_')]
        
        click.echo(f"回测因子: {factor_list}")
        
        # 确定标签列
        label_col = "label_1d" if "label_1d" in factor_data.columns else \
                   [col for col in factor_data.columns if col.startswith('label_')][0] if \
                   any(col.startswith('label_') for col in factor_data.columns) else \
                   factor_data.columns[-1]
        
        click.echo(f"使用标签: {label_col}")
        
        # 执行回测
        if strategy == "simple":
            results = backtester.create_simple_ml_backtest(
                factor_data, factor_list, label_col
            )
        elif strategy == "portfolio":
            results = backtester.create_portfolio_backtest(
                factor_data, factor_list, label_col, n_top, rebalance_freq, transaction_cost
            )
        elif strategy == "qlib":
            # qlib 标准回测配置
            qlib_config = {
                "start_time": "2020-01-01",
                "end_time": "2021-12-31",
                "instruments": "csi300",
                "model_type": "lgb"
            }
            results = backtester.run_qlib_backtest(qlib_config)
        else:
            click.echo("错误: 不支持的策略类型", err=True)
            click.echo("支持的策略: simple, portfolio, qlib")
            return
        
        # 保存结果
        backtester.save_backtest_results(results, output)
        click.echo(f"✅ 回测完成，结果保存到: {output}")
        
        # 显示关键指标
        if "performance_metrics" in results:
            metrics = results["performance_metrics"]
            click.echo("\n📈 回测结果:")
            
            # 根据策略类型显示不同的指标
            if strategy == "simple":
                click.echo(f"  组合收益率: {metrics.get('portfolio_return_mean', 'N/A'):.4f}")
                click.echo(f"  基准收益率: {metrics.get('benchmark_return_mean', 'N/A'):.4f}")
                click.echo(f"  超额收益: {metrics.get('excess_return', 'N/A'):.4f}")
                click.echo(f"  夏普比率: {metrics.get('portfolio_sharpe', 'N/A'):.4f}")
            elif strategy == "portfolio":
                click.echo(f"  年化收益率: {metrics.get('annual_return', 'N/A'):.4f}")
                click.echo(f"  年化波动率: {metrics.get('annual_volatility', 'N/A'):.4f}")
                click.echo(f"  夏普比率: {metrics.get('sharpe_ratio', 'N/A'):.4f}")
                click.echo(f"  最大回撤: {metrics.get('max_drawdown', 'N/A'):.4f}")
                click.echo(f"  胜率: {metrics.get('win_rate', 'N/A'):.4f}")
        
        # 生成详细报告
        if report:
            report_file = backtester.create_factor_report(results)
            click.echo(f"📄 详细报告已生成: {report_file}")
        
    except Exception as e:
        logger.error("因子回测失败", error=str(e))
        click.echo(f"错误: {str(e)}", err=True)


@factor_cli.command("workflow")
@click.option("--stocks", required=True, help="股票代码列表，逗号分隔")
@click.option("--start", required=True, help="开始日期 (YYYY-MM-DD)")
@click.option("--end", required=True, help="结束日期 (YYYY-MM-DD)")
@click.option("--factor_types", default="alpha", help="因子类型 (alpha/custom)")
@click.option("--custom_config", help="自定义因子配置文件路径")
@click.option("--strategy", default="portfolio", help="回测策略 (simple/portfolio/qlib)")
@click.option("--n_top", default=30, type=int, help="选股数量")
@click.option("--output_dir", default="./factor_workflow", help="输出目录")
@click.option("--data_dir", default="./qlib_data", help="qlib 数据目录")
def factor_workflow(stocks, start, end, factor_types, custom_config, strategy, 
                   n_top, output_dir, data_dir):
    """执行完整的因子挖掘工作流程：计算因子 -> 分析表现 -> 回测验证。"""
    try:
        import os
        from pathlib import Path
        
        click.echo("🚀 开始因子挖掘工作流程...")
        
        # 创建输出目录
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        stock_list = [s.strip() for s in stocks.split(",")]
        click.echo(f"📊 股票池: {stock_list}")
        click.echo(f"⏰ 时间范围: {start} 到 {end}")
        
        # 步骤1: 初始化环境
        click.echo("\n📋 步骤1: 初始化 qlib 环境...")
        calculator = QlibFactorCalculator(provider_uri=data_dir)
        backtester = QlibBacktester(provider_uri=data_dir)
        
        # 步骤2: 计算因子
        click.echo("\n🧮 步骤2: 计算因子...")
        factor_file = os.path.join(output_dir, "factors.csv")
        
        if factor_types == "alpha":
            factor_data = calculator.calculate_alpha_factors(stock_list, start, end)
        elif factor_types == "custom" and custom_config:
            with open(custom_config, 'r') as f:
                import json
                factor_expressions = json.load(f)
            factor_data = calculator.calculate_custom_factors(stock_list, start, end, factor_expressions)
        else:
            click.echo("❌ 错误: 无效的因子类型或缺少自定义配置", err=True)
            return
        
        calculator.save_factor_data(factor_data, factor_file)
        click.echo(f"   ✅ 因子计算完成，数据形状: {factor_data.shape}")
        
        # 步骤3: 添加前瞻收益数据
        click.echo("\n📈 步骤3: 添加前瞻收益数据...")
        periods = [1, 5, 20]  # 1日、5日、20日收益
        factor_data_with_returns = calculator.get_factor_data_with_returns(
            stock_list, start, end, None, periods
        )
        
        # 步骤4: 因子表现分析
        click.echo("\n🔍 步骤4: 分析因子表现...")
        factor_cols = [col for col in factor_data.columns if not col.startswith('label_')]
        label_cols = [f"label_{p}d" for p in periods]
        
        analysis_results = backtester.analyze_factor_performance(
            factor_data_with_returns, factor_cols, label_cols
        )
        
        analysis_file = os.path.join(output_dir, "factor_analysis.json")
        backtester.save_backtest_results(analysis_results, analysis_file)
        click.echo(f"   ✅ 因子分析完成")
        
        # 显示最佳因子
        if "summary" in analysis_results and "best_factors_by_period" in analysis_results["summary"]:
            click.echo("\n   🏆 最佳因子汇总:")
            for period, info in analysis_results["summary"]["best_factors_by_period"].items():
                click.echo(f"     {period}: {info['factor']} (IC={info['ic_mean']:.4f})")
        
        # 步骤5: 回测验证
        click.echo(f"\n🔬 步骤5: 回测验证 (策略: {strategy})...")
        
        # 选择表现最好的因子进行回测
        best_factors = []
        if "summary" in analysis_results and "best_factors_by_period" in analysis_results["summary"]:
            for period_info in analysis_results["summary"]["best_factors_by_period"].values():
                if period_info["factor"] not in best_factors:
                    best_factors.append(period_info["factor"])
        else:
            best_factors = factor_cols[:3]  # 默认选择前3个因子
        
        click.echo(f"   回测因子: {best_factors}")
        
        # 执行回测
        label_col = "label_1d"  # 使用1日收益作为标签
        if strategy == "simple":
            backtest_results = backtester.create_simple_ml_backtest(
                factor_data_with_returns, best_factors, label_col
            )
        elif strategy == "portfolio":
            backtest_results = backtester.create_portfolio_backtest(
                factor_data_with_returns, best_factors, label_col, n_top, "20D", 0.002
            )
        elif strategy == "qlib":
            qlib_config = {
                "start_time": start,
                "end_time": end,
                "instruments": stock_list,
                "model_type": "lgb"
            }
            backtest_results = backtester.run_qlib_backtest(qlib_config)
        else:
            click.echo("❌ 错误: 不支持的回测策略", err=True)
            return
        
        backtest_file = os.path.join(output_dir, "backtest_results.json")
        backtester.save_backtest_results(backtest_results, backtest_file)
        click.echo(f"   ✅ 回测完成")
        
        # 显示回测结果
        if "performance_metrics" in backtest_results:
            metrics = backtest_results["performance_metrics"]
            click.echo("\n   📊 回测绩效:")
            if strategy == "portfolio":
                click.echo(f"     年化收益率: {metrics.get('annual_return', 0):.4f}")
                click.echo(f"     夏普比率: {metrics.get('sharpe_ratio', 0):.4f}")
                click.echo(f"     最大回撤: {metrics.get('max_drawdown', 0):.4f}")
            else:
                click.echo(f"     超额收益: {metrics.get('excess_return', 0):.4f}")
                click.echo(f"     组合收益: {metrics.get('portfolio_return_mean', 0):.4f}")
        
        # 步骤6: 生成报告
        click.echo("\n📄 步骤6: 生成综合报告...")
        
        # 合并所有结果
        comprehensive_results = {
            "workflow_config": {
                "stocks": stock_list,
                "start_date": start,
                "end_date": end,
                "factor_types": factor_types,
                "strategy": strategy,
                "n_top": n_top
            },
            "factor_data_info": {
                "shape": factor_data.shape,
                "factors": factor_cols,
                "periods": periods
            },
            "factor_analysis": analysis_results,
            "backtest_results": backtest_results
        }
        
        report_file = backtester.create_factor_report(comprehensive_results, output_dir)
        
        click.echo(f"\n🎉 因子挖掘工作流程完成!")
        click.echo(f"📁 输出目录: {output_dir}")
        click.echo(f"📄 详细报告: {report_file}")
        click.echo("\n📋 生成的文件:")
        click.echo(f"  - 因子数据: {factor_file}")
        click.echo(f"  - 因子分析: {analysis_file}")
        click.echo(f"  - 回测结果: {backtest_file}")
        click.echo(f"  - 综合报告: {report_file}")
        
    except Exception as e:
        logger.error("因子挖掘工作流程失败", error=str(e))
        click.echo(f"❌ 错误: {str(e)}", err=True)



