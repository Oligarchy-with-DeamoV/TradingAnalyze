"""基于 qlib 的回测器 - 使用 qlib 进行因子回测和策略评估。"""

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
            raise ImportError("qlib 未安装，请运行: pip install qlib")
        
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
                    'ic_series': ic_series
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
            # 这里应该是完整的 qlib 回测流程
            # 由于 qlib 的复杂性，这里提供一个简化的示例框架
            logger.info("开始 qlib 标准回测")
            
            # 实际的 qlib 回测需要更复杂的配置
            # 包括模型训练、策略执行、风险分析等
            
            results = {
                "status": "completed",
                "config": config,
                "message": "这是一个简化的回测示例，完整实现需要根据具体需求配置"
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
                elif pd.isna(obj):
                    return None
                return obj
            
            # 递归转换结果
            def recursive_convert(obj):
                if isinstance(obj, dict):
                    return {k: recursive_convert(v) for k, v in obj.items()}
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
