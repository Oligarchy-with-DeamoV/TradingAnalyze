"""基于 qlib 的回测器 - 使用 qlib 进行因子回测和策略评估。"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd
import structlog

try:
    import qlib
    from qlib.backtest import backtest, executor
    from qlib.contrib.evaluate import risk_analysis
    from qlib.contrib.model.gbdt import LGBModel
    from qlib.contrib.strategy.signal_strategy import TopkDropoutStrategy
    from qlib.data import D
    from qlib.model.trainer import task_train
    from qlib.utils import init_instance_by_config
    from qlib.workflow import R
    QLIB_AVAILABLE = True
except ImportError:
    QLIB_AVAILABLE = False

logger = structlog.get_logger()


class QlibBacktester:
    """基于 qlib 的回测器，提供因子回测和策略评估功能。"""
    
    def __init__(self, provider_uri: Optional[str] = None, region: str = "cn"):
        """
        初始化 qlib 回测器。
        
        Args:
            provider_uri: qlib 数据提供者 URI
            region: 市场区域
        """
        if not QLIB_AVAILABLE:
            raise ImportError("qlib 未安装，请运行: pip install pyqlib")
        
        self.provider_uri = provider_uri
        self.region = region
        self.initialized = False
        self._init_qlib()
    
    def _init_qlib(self):
        """初始化 qlib 环境。"""
        try:
            if self.provider_uri:
                qlib.init(provider_uri=self.provider_uri, region=self.region)
            else:
                qlib.init(region=self.region)
            
            self.initialized = True
            logger.info("qlib 回测器初始化成功")
        except Exception as e:
            logger.error(f"qlib 初始化失败: {e}")
            self.initialized = False
            raise
    
    def calculate_ic_analysis(self, factor_data: pd.DataFrame,
                             factor_cols: List[str],
                             label_col: str = "label_1d") -> Dict[str, Any]:
        """
        计算因子 IC 分析。
        
        Args:
            factor_data: 包含因子和标签的数据
            factor_cols: 因子列名列表
            label_col: 标签列名
            
        Returns:
            IC 分析结果
        """
        if not self.initialized:
            raise RuntimeError("qlib 未初始化")
        
        if label_col not in factor_data.columns:
            raise ValueError(f"标签列 {label_col} 不存在")
        
        ic_results = {}
        
        for factor_col in factor_cols:
            if factor_col not in factor_data.columns:
                logger.warning(f"因子列 {factor_col} 不存在，跳过")
                continue
            
            # 计算 IC
            valid_data = factor_data[[factor_col, label_col]].dropna()
            if len(valid_data) == 0:
                logger.warning(f"因子 {factor_col} 没有有效数据")
                continue
            
            # 按日期分组计算 IC
            if isinstance(factor_data.index, pd.MultiIndex):
                # 假设是 (date, instrument) 的多重索引
                ic_series = valid_data.groupby(level=0).apply(
                    lambda x: x[factor_col].corr(x[label_col], method='spearman')
                )
            else:
                # 单一索引，计算总体 IC
                ic_series = pd.Series([valid_data[factor_col].corr(valid_data[label_col], method='spearman')])
            
            ic_series = ic_series.dropna()
            
            if len(ic_series) > 0:
                ic_results[factor_col] = {
                    'ic_mean': ic_series.mean(),
                    'ic_std': ic_series.std(),
                    'ic_ir': ic_series.mean() / ic_series.std() if ic_series.std() > 0 else 0,
                    'ic_positive_ratio': (ic_series > 0).mean(),
                    'ic_max': ic_series.max(),
                    'ic_min': ic_series.min(),
                    # 转换 ic_series 为可序列化的格式
                    'ic_series': {
                        str(k): float(v) for k, v in ic_series.items() if pd.notna(v)
                    }
                }
        
        logger.info(f"完成 {len(ic_results)} 个因子的 IC 分析")
        return ic_results
    
    def create_dataset_config(self, instruments: Union[str, List[str]],
                             start_time: str, end_time: str,
                             factor_expressions: Dict[str, str],
                             label_expression: str = "Ref($close, -1) / $close - 1") -> Dict:
        """
        创建 qlib 数据集配置。
        
        Args:
            instruments: 股票代码或代码列表
            start_time: 开始时间
            end_time: 结束时间
            factor_expressions: 因子表达式字典
            label_expression: 标签表达式
            
        Returns:
            数据集配置字典
        """
        # 合并因子和标签表达式
        all_fields = list(factor_expressions.values()) + [label_expression]
        all_names = list(factor_expressions.keys()) + ["label"]
        
        dataset_config = {
            "class": "DatasetH",
            "module_path": "qlib.data.dataset",
            "kwargs": {
                "handler": {
                    "class": "Alpha158",
                    "module_path": "qlib.contrib.data.handler",
                    "kwargs": {
                        "start_time": start_time,
                        "end_time": end_time,
                        "fit_start_time": start_time,
                        "fit_end_time": end_time,
                        "instruments": instruments,
                        "infer_processors": [
                            {
                                "class": "RobustZScoreNorm",
                                "kwargs": {"fields_group": "feature", "clip_outlier": True}
                            },
                            {"class": "Fillna", "kwargs": {"fields_group": "feature"}}
                        ],
                        "learn_processors": [
                            {"class": "DropnaLabel"},
                            {"class": "CSRankNorm", "kwargs": {"fields_group": "label"}}
                        ]
                    }
                },
                "segments": {
                    "train": (start_time, end_time),
                    "valid": (start_time, end_time),
                    "test": (start_time, end_time)
                }
            }
        }
        
        return dataset_config
    
    def create_simple_ml_backtest(self, factor_data: pd.DataFrame,
                                 factor_cols: List[str],
                                 label_col: str = "label_1d",
                                 train_ratio: float = 0.7,
                                 valid_ratio: float = 0.15) -> Dict[str, Any]:
        """
        创建简单的机器学习回测。
        
        Args:
            factor_data: 因子数据
            factor_cols: 因子列名列表
            label_col: 标签列名
            train_ratio: 训练集比例
            valid_ratio: 验证集比例
            
        Returns:
            回测结果
        """
        if not self.initialized:
            raise RuntimeError("qlib 未初始化")
        
        # 数据准备
        valid_data = factor_data[factor_cols + [label_col]].dropna()
        if len(valid_data) == 0:
            raise ValueError("没有有效的训练数据")
        
        # 数据分割
        n_total = len(valid_data)
        n_train = int(n_total * train_ratio)
        n_valid = int(n_total * valid_ratio)
        
        train_data = valid_data.iloc[:n_train]
        valid_data_split = valid_data.iloc[n_train:n_train + n_valid]
        test_data = valid_data.iloc[n_train + n_valid:]
        
        # 简单的线性回测分析
        results = {
            "data_summary": {
                "total_samples": n_total,
                "train_samples": len(train_data),
                "valid_samples": len(valid_data_split),
                "test_samples": len(test_data)
            },
            "factor_analysis": {},
            "performance_metrics": {}
        }
        
        # 分析每个因子的表现
        for factor_col in factor_cols:
            if factor_col not in valid_data.columns:
                continue
            
            # 计算因子与收益的相关性
            train_corr = train_data[factor_col].corr(train_data[label_col], method='spearman')
            test_corr = test_data[factor_col].corr(test_data[label_col], method='spearman') if len(test_data) > 0 else np.nan
            
            # 分位数分析
            try:
                test_quantiles = pd.qcut(test_data[factor_col], q=5, labels=False, duplicates='drop')
                quantile_returns = test_data.groupby(test_quantiles)[label_col].mean()
                
                results["factor_analysis"][factor_col] = {
                    "train_ic": train_corr,
                    "test_ic": test_corr,
                    "quantile_returns": quantile_returns.to_dict() if len(quantile_returns) > 0 else {}
                }
            except Exception as e:
                logger.warning(f"分位数分析失败: {e}")
                results["factor_analysis"][factor_col] = {
                    "train_ic": train_corr,
                    "test_ic": test_corr,
                    "quantile_returns": {}
                }
        
        # 计算组合表现指标
        if len(test_data) > 0:
            # 简单等权重组合
            factor_score = test_data[factor_cols].mean(axis=1)
            portfolio_returns = []
            
            # 按因子评分排序，选择前20%
            top_quantile = factor_score.quantile(0.8)
            selected_returns = test_data[factor_score >= top_quantile][label_col]
            
            if len(selected_returns) > 0:
                results["performance_metrics"] = {
                    "portfolio_return_mean": selected_returns.mean(),
                    "portfolio_return_std": selected_returns.std(),
                    "portfolio_sharpe": selected_returns.mean() / selected_returns.std() if selected_returns.std() > 0 else 0,
                    "benchmark_return_mean": test_data[label_col].mean(),
                    "excess_return": selected_returns.mean() - test_data[label_col].mean()
                }
        
        logger.info("简单机器学习回测完成")
        return results
    
    def run_qlib_backtest(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        运行 qlib 标准回测流程。
        
        Args:
            config: qlib 回测配置
            
        Returns:
            回测结果
        """
        if not self.initialized:
            raise RuntimeError("qlib 未初始化")
        
        try:
            logger.info("开始 qlib 标准回测")
            
            # 提取配置参数
            instruments = config.get("instruments", "csi300")
            start_time = config.get("start_time", "2020-01-01")
            end_time = config.get("end_time", "2021-12-31")
            model_type = config.get("model_type", "lgb")
            
            # 创建基础配置
            dataset_config = {
                "class": "DatasetH",
                "module_path": "qlib.data.dataset",
                "kwargs": {
                    "handler": {
                        "class": "Alpha158",
                        "module_path": "qlib.contrib.data.handler",
                        "kwargs": {
                            "start_time": start_time,
                            "end_time": end_time,
                            "fit_start_time": start_time,
                            "fit_end_time": end_time,
                            "instruments": instruments,
                        }
                    },
                    "segments": {
                        "train": (start_time, "2021-06-30"),
                        "valid": ("2021-07-01", "2021-09-30"),
                        "test": ("2021-10-01", end_time),
                    }
                }
            }
            
            # 模型配置
            if model_type == "lgb":
                model_config = {
                    "class": "LGBModel",
                    "module_path": "qlib.contrib.model.gbdt",
                    "kwargs": {
                        "loss": "mse",
                        "colsample_bytree": 0.8879,
                        "learning_rate": 0.0421,
                        "subsample": 0.8789,
                        "lambda_l1": 205.6999,
                        "lambda_l2": 580.9768,
                        "max_depth": 8,
                        "num_leaves": 210,
                        "num_threads": 20,
                    }
                }
            else:
                model_config = {
                    "class": "LinearModel", 
                    "module_path": "qlib.contrib.model.linear",
                }
            
            # 策略配置
            strategy_config = {
                "class": "TopkDropoutStrategy",
                "module_path": "qlib.contrib.strategy.signal_strategy",
                "kwargs": {
                    "signal": {
                        "class": "SignalStrategy",
                        "module_path": "qlib.contrib.strategy.signal_strategy",
                        "kwargs": {
                            "model": model_config,
                            "dataset": dataset_config,
                        }
                    },
                    "topk": 50,
                    "n_drop": 5,
                }
            }
            
            # 执行器配置
            executor_config = {
                "class": "SimulatorExecutor",
                "module_path": "qlib.backtest.executor",
                "kwargs": {
                    "time_per_step": "day",
                    "generate_portfolio_metrics": True,
                }
            }
            
            # 回测配置
            backtest_config = {
                "start_time": start_time,
                "end_time": end_time,
                "account": 100000000,
                "benchmark": "SH000300",
                "exchange_kwargs": {
                    "freq": "day",
                    "limit_threshold": 0.095,
                    "deal_price": "close",
                    "open_cost": 0.0005,
                    "close_cost": 0.0015,
                    "min_cost": 5,
                },
            }
            
            # 尝试运行回测（如果 qlib 完全可用）
            try:
                from qlib.backtest import backtest
                from qlib.workflow import R

                # 初始化组件
                strategy = init_instance_by_config(strategy_config)
                executor = init_instance_by_config(executor_config)
                
                # 运行回测
                portfolio_metric_dict, indicator_dict = backtest(
                    strategy=strategy,
                    executor=executor,
                    **backtest_config
                )
                
                # 风险分析
                analysis_freq = "day"
                report_normal, positions_normal = portfolio_metric_dict.get(analysis_freq)
                
                # 计算风险指标
                risk_analysis_config = {
                    "report_normal": report_normal,
                    "label_col": "label",
                    "indicator_analysis": True,
                    "indicator_dict": indicator_dict,
                }
                
                analysis_result = risk_analysis(**risk_analysis_config)
                
                results = {
                    "status": "completed",
                    "config": config,
                    "portfolio_metrics": portfolio_metric_dict,
                    "indicators": indicator_dict,
                    "risk_analysis": analysis_result,
                }
                
            except Exception as inner_e:
                logger.warning(f"完整 qlib 回测失败，返回配置信息: {inner_e}")
                # 如果完整回测失败，返回配置验证结果
                results = {
                    "status": "config_validated",
                    "config": config,
                    "dataset_config": dataset_config,
                    "model_config": model_config,
                    "strategy_config": strategy_config,
                    "executor_config": executor_config,
                    "backtest_config": backtest_config,
                    "message": f"配置已验证，但回测执行失败: {str(inner_e)}"
                }
            
            logger.info("qlib 回测完成")
            return results
            
        except Exception as e:
            logger.error(f"qlib 回测失败: {e}")
            raise
    
    def analyze_factor_performance(self, factor_data: pd.DataFrame,
                                  factor_cols: List[str],
                                  label_cols: List[str] = ["label_1d", "label_5d", "label_20d"]) -> Dict[str, Any]:
        """
        分析因子在不同时间周期的表现。
        
        Args:
            factor_data: 因子数据
            factor_cols: 因子列名列表
            label_cols: 不同周期的标签列名列表
            
        Returns:
            因子表现分析结果
        """
        if not self.initialized:
            raise RuntimeError("qlib 未初始化")
        
        results = {
            "factor_performance": {},
            "summary": {}
        }
        
        for label_col in label_cols:
            if label_col not in factor_data.columns:
                logger.warning(f"标签列 {label_col} 不存在，跳过")
                continue
            
            # 计算该周期下所有因子的 IC
            ic_analysis = self.calculate_ic_analysis(factor_data, factor_cols, label_col)
            results["factor_performance"][label_col] = ic_analysis
        
        # 生成总结
        if results["factor_performance"]:
            # 找出表现最好的因子
            best_factors = {}
            for period, factors in results["factor_performance"].items():
                if factors:
                    best_factor = max(factors.keys(), key=lambda f: abs(factors[f]["ic_mean"]))
                    best_factors[period] = {
                        "factor": best_factor,
                        "ic_mean": factors[best_factor]["ic_mean"],
                        "ic_ir": factors[best_factor]["ic_ir"]
                    }
            
            results["summary"]["best_factors_by_period"] = best_factors
        
        logger.info("因子表现分析完成")
        return results
    
    def save_backtest_results(self, results: Dict[str, Any], filepath: str):
        """
        保存回测结果。
        
        Args:
            results: 回测结果
            filepath: 保存路径
        """
        try:
            import json
            
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            
            # 处理不能序列化的对象
            def convert_for_json(obj):
                if isinstance(obj, pd.Series):
                    return obj.to_dict()
                elif isinstance(obj, pd.DataFrame):
                    return obj.to_dict()
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                elif isinstance(obj, (np.int64, np.int32)):
                    return int(obj)
                elif isinstance(obj, (np.float64, np.float32)):
                    return float(obj)
                elif isinstance(obj, pd.Timestamp):
                    return obj.strftime('%Y-%m-%d %H:%M:%S')
                elif hasattr(obj, 'isoformat'):  # datetime objects
                    return obj.isoformat()
                elif pd.isna(obj):
                    return None
                return obj
            
            # 递归转换结果
            def recursive_convert(obj):
                if isinstance(obj, dict):
                    converted_dict = {}
                    for k, v in obj.items():
                        # 确保键也被转换为字符串
                        if isinstance(k, pd.Timestamp):
                            key = k.strftime('%Y-%m-%d')
                        elif hasattr(k, 'isoformat'):
                            key = k.isoformat()
                        else:
                            key = str(k)
                        converted_dict[key] = recursive_convert(v)
                    return converted_dict
                elif isinstance(obj, list):
                    return [recursive_convert(item) for item in obj]
                else:
                    return convert_for_json(obj)
            
            converted_results = recursive_convert(results)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(converted_results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"回测结果已保存到: {filepath}")
            
        except Exception as e:
            logger.error(f"保存回测结果失败: {e}")
            raise
    
    def create_portfolio_backtest(self, factor_data: pd.DataFrame,
                                 factor_cols: List[str],
                                 label_col: str = "label_1d",
                                 n_top: int = 50,
                                 rebalance_freq: str = "20D",
                                 transaction_cost: float = 0.002) -> Dict[str, Any]:
        """
        创建组合回测，模拟真实的投资组合表现。
        
        Args:
            factor_data: 因子数据
            factor_cols: 因子列名列表
            label_col: 标签列名
            n_top: 选股数量
            rebalance_freq: 调仓频率
            transaction_cost: 交易成本
            
        Returns:
            组合回测结果
        """
        if not self.initialized:
            raise RuntimeError("qlib 未初始化")
        
        # 数据预处理
        valid_data = factor_data[factor_cols + [label_col]].dropna()
        if len(valid_data) == 0:
            raise ValueError("没有有效的回测数据")
        
        # 如果是多重索引 (date, instrument)，进行组合回测
        if isinstance(valid_data.index, pd.MultiIndex):
            return self._multi_index_portfolio_backtest(
                valid_data, factor_cols, label_col, n_top, rebalance_freq, transaction_cost
            )
        else:
            # 单一索引的简化回测
            return self._simple_portfolio_backtest(
                valid_data, factor_cols, label_col, n_top, transaction_cost
            )
    
    def _multi_index_portfolio_backtest(self, data: pd.DataFrame,
                                       factor_cols: List[str],
                                       label_col: str,
                                       n_top: int,
                                       rebalance_freq: str,
                                       transaction_cost: float) -> Dict[str, Any]:
        """多重索引数据的组合回测。"""
        # 假设索引是 (date, instrument)
        dates = data.index.get_level_values(0).unique().sort_values()
        
        # 计算因子综合得分
        factor_score = data[factor_cols].mean(axis=1)
        data_with_score = data.copy()
        data_with_score['factor_score'] = factor_score
        
        portfolio_returns = []
        portfolio_weights = []
        selected_stocks = []
        
        for date in dates:
            try:
                date_data = data_with_score.loc[date]
                if len(date_data) < n_top:
                    continue
                
                # 选择得分最高的股票
                top_stocks = date_data.nlargest(n_top, 'factor_score')
                
                # 计算组合收益
                if label_col in top_stocks.columns and len(top_stocks) > 0:
                    # 确保维度匹配
                    stock_returns = top_stocks[label_col].values
                    if len(stock_returns) > 0:
                        # 等权重
                        weights = np.ones(len(stock_returns)) / len(stock_returns)
                        
                        # 确保两个数组都是一维的
                        if stock_returns.ndim > 1:
                            stock_returns = stock_returns.flatten()
                        if weights.ndim > 1:
                            weights = weights.flatten()
                        
                        # 确保长度匹配
                        min_len = min(len(stock_returns), len(weights))
                        stock_returns = stock_returns[:min_len]
                        weights = weights[:min_len]
                        
                        portfolio_return = np.sum(stock_returns * weights)
                        portfolio_returns.append(portfolio_return)
                        portfolio_weights.append(weights)
                        selected_stocks.append(top_stocks.index.tolist())
                
            except Exception as e:
                logger.warning(f"日期 {date} 回测失败: {e}")
                continue
        
        # 计算绩效指标
        if portfolio_returns:
            returns_series = pd.Series(portfolio_returns, index=dates[:len(portfolio_returns)])
            benchmark_returns = data.groupby(level=0)[label_col].mean()
            
            # 对齐时间序列
            common_dates = returns_series.index.intersection(benchmark_returns.index)
            returns_series = returns_series.loc[common_dates]
            benchmark_returns = benchmark_returns.loc[common_dates]
            
            # 计算超额收益
            excess_returns = returns_series - benchmark_returns
            
            # 考虑交易成本
            if transaction_cost > 0:
                # 简化的交易成本计算
                turnover_cost = transaction_cost * 0.5  # 假设平均50%换手率
                returns_series_net = returns_series - turnover_cost
            else:
                returns_series_net = returns_series
            
            # 计算累计收益
            cumulative_returns = (1 + returns_series_net).cumprod()
            cumulative_benchmark = (1 + benchmark_returns).cumprod()
            
            results = {
                "portfolio_returns": returns_series.to_dict(),
                "benchmark_returns": benchmark_returns.to_dict(),
                "excess_returns": excess_returns.to_dict(),
                "cumulative_returns": cumulative_returns.to_dict(),
                "cumulative_benchmark": cumulative_benchmark.to_dict(),
                "performance_metrics": {
                    "total_return": cumulative_returns.iloc[-1] - 1 if len(cumulative_returns) > 0 else 0,
                    "benchmark_return": cumulative_benchmark.iloc[-1] - 1 if len(cumulative_benchmark) > 0 else 0,
                    "excess_return": (cumulative_returns.iloc[-1] - cumulative_benchmark.iloc[-1]) if len(cumulative_returns) > 0 else 0,
                    "annual_return": returns_series_net.mean() * 252,
                    "annual_volatility": returns_series_net.std() * np.sqrt(252),
                    "sharpe_ratio": (returns_series_net.mean() / returns_series_net.std() * np.sqrt(252)) if returns_series_net.std() > 0 else 0,
                    "max_drawdown": self._calculate_max_drawdown(cumulative_returns),
                    "win_rate": (returns_series_net > 0).mean(),
                    "avg_holding_period": len(returns_series) / len(set().union(*selected_stocks)) if selected_stocks else 0,
                },
                "selected_stocks": selected_stocks,
                "backtest_config": {
                    "n_top": n_top,
                    "rebalance_freq": rebalance_freq,
                    "transaction_cost": transaction_cost,
                    "factor_cols": factor_cols
                }
            }
        else:
            results = {
                "error": "没有有效的回测结果",
                "backtest_config": {
                    "n_top": n_top,
                    "rebalance_freq": rebalance_freq,
                    "transaction_cost": transaction_cost,
                    "factor_cols": factor_cols
                }
            }
        
        logger.info("多重索引组合回测完成")
        return results
    
    def _simple_portfolio_backtest(self, data: pd.DataFrame,
                                  factor_cols: List[str],
                                  label_col: str,
                                  n_top: int,
                                  transaction_cost: float) -> Dict[str, Any]:
        """简化的组合回测。"""
        # 计算因子综合得分
        factor_score = data[factor_cols].mean(axis=1)
        
        # 选择得分最高的样本
        n_select = min(n_top, len(data))
        top_indices = factor_score.nlargest(n_select).index
        
        # 计算组合表现
        portfolio_returns = data.loc[top_indices, label_col]
        benchmark_returns = data[label_col]
        
        # 绩效指标
        portfolio_mean = portfolio_returns.mean()
        benchmark_mean = benchmark_returns.mean()
        portfolio_std = portfolio_returns.std()
        
        results = {
            "performance_metrics": {
                "portfolio_return": portfolio_mean,
                "benchmark_return": benchmark_mean,
                "excess_return": portfolio_mean - benchmark_mean,
                "portfolio_volatility": portfolio_std,
                "sharpe_ratio": portfolio_mean / portfolio_std if portfolio_std > 0 else 0,
                "win_rate": (portfolio_returns > 0).mean(),
                "selection_ratio": n_select / len(data),
            },
            "selected_samples": top_indices.tolist(),
            "backtest_config": {
                "n_top": n_top,
                "transaction_cost": transaction_cost,
                "factor_cols": factor_cols
            }
        }
        
        logger.info("简化组合回测完成")
        return results
    
    def _calculate_max_drawdown(self, cumulative_returns: pd.Series) -> float:
        """计算最大回撤。"""
        if len(cumulative_returns) == 0:
            return 0.0
        
        peak = cumulative_returns.expanding(min_periods=1).max()
        drawdown = (cumulative_returns - peak) / peak
        return drawdown.min()
    
    def create_factor_report(self, analysis_results: Dict[str, Any],
                           output_dir: str = "factor_reports") -> str:
        """
        生成因子分析报告。
        
        Args:
            analysis_results: 因子分析结果
            output_dir: 输出目录
            
        Returns:
            报告文件路径
        """
        import os
        from datetime import datetime

        # 创建输出目录
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # 生成报告文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(output_dir, f"factor_report_{timestamp}.md")
        
        # 生成Markdown报告
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# 因子分析报告\n\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # 总结部分
            if "summary" in analysis_results:
                f.write("## 执行摘要\n\n")
                summary = analysis_results["summary"]
                
                if "best_factors_by_period" in summary:
                    f.write("### 各周期最佳因子\n\n")
                    f.write("| 周期 | 因子 | IC均值 | IR比率 |\n")
                    f.write("|------|------|--------|--------|\n")
                    
                    for period, info in summary["best_factors_by_period"].items():
                        f.write(f"| {period} | {info['factor']} | {info['ic_mean']:.4f} | {info['ic_ir']:.4f} |\n")
                    f.write("\n")
            
            # 因子表现详情
            if "factor_performance" in analysis_results:
                f.write("## 因子表现详情\n\n")
                
                for period, factors in analysis_results["factor_performance"].items():
                    f.write(f"### {period}\n\n")
                    f.write("| 因子 | IC均值 | IC标准差 | IR比率 | 胜率 | 最大IC | 最小IC |\n")
                    f.write("|------|--------|----------|--------|------|--------|--------|\n")
                    
                    for factor_name, metrics in factors.items():
                        f.write(f"| {factor_name} | "
                               f"{metrics['ic_mean']:.4f} | "
                               f"{metrics['ic_std']:.4f} | "
                               f"{metrics['ic_ir']:.4f} | "
                               f"{metrics['ic_positive_ratio']:.4f} | "
                               f"{metrics['ic_max']:.4f} | "
                               f"{metrics['ic_min']:.4f} |\n")
                    f.write("\n")
            
            # 回测结果
            if "performance_metrics" in analysis_results:
                f.write("## 回测绩效\n\n")
                metrics = analysis_results["performance_metrics"]
                
                f.write("| 指标 | 数值 |\n")
                f.write("|------|------|\n")
                for key, value in metrics.items():
                    if isinstance(value, (int, float)):
                        f.write(f"| {key} | {value:.4f} |\n")
                    else:
                        f.write(f"| {key} | {value} |\n")
                f.write("\n")
            
            # 配置信息
            if "backtest_config" in analysis_results:
                f.write("## 回测配置\n\n")
                config = analysis_results["backtest_config"]
                f.write("```json\n")
                f.write(json.dumps(config, indent=2, ensure_ascii=False))
                f.write("\n```\n\n")
        
        logger.info(f"因子报告已生成: {report_file}")
        return report_file
