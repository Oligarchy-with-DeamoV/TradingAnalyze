"""基于 qlib 的因子计算器 - 使用 qlib 进行因子挖掘和计算。"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd
import structlog

try:
    import qlib
    from qlib.contrib.data.loader import QlibDataLoader
    from qlib.data import D
    from qlib.data.dataset import Dataset
    from qlib.utils import init_instance_by_config
    QLIB_AVAILABLE = True
except ImportError:
    QLIB_AVAILABLE = False

logger = structlog.get_logger()


class QlibFactorCalculator:
    """基于 qlib 的因子计算器，提供量化因子的计算和管理。"""
    
    def __init__(self, provider_uri: Optional[str] = None, region: str = "cn"):
        """
        初始化 qlib 因子计算器。
        
        Args:
            provider_uri: qlib 数据提供者 URI，如果为 None 则使用默认配置
            region: 市场区域，默认为中国市场 "cn"
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
                # 使用默认配置，通常是本地文件系统
                qlib.init(region=self.region)
            
            self.initialized = True
            logger.info("qlib 初始化成功")
        except Exception as e:
            logger.error(f"qlib 初始化失败: {e}")
            self.initialized = False
            raise
    
    def check_qlib_status(self) -> Dict[str, Any]:
        """检查 qlib 状态。"""
        return {
            "initialized": self.initialized,
            "provider_uri": self.provider_uri,
            "region": self.region,
            "qlib_available": QLIB_AVAILABLE
        }
    
    def get_stock_data(self, instruments: Union[str, List[str]], 
                      start_time: str, end_time: str,
                      fields: Optional[List[str]] = None) -> pd.DataFrame:
        """
        获取股票数据。
        
        Args:
            instruments: 股票代码或代码列表
            start_time: 开始时间，格式 "YYYY-MM-DD"
            end_time: 结束时间，格式 "YYYY-MM-DD"
            fields: 字段列表，如果为空则获取基础 OHLCV 数据
            
        Returns:
            股票数据 DataFrame
        """
        if not self.initialized:
            raise RuntimeError("qlib 未初始化")
        
        if fields is None:
            fields = ["$open", "$high", "$low", "$close", "$volume"]
        
        try:
            data = D.features(
                instruments=instruments,
                fields=fields,
                start_time=start_time,
                end_time=end_time,
                freq="day"
            )
            logger.info(f"成功获取数据，形状: {data.shape}")
            return data
        except Exception as e:
            logger.error(f"获取股票数据失败: {e}")
            raise
    
    def calculate_alpha_factors(self, instruments: Union[str, List[str]],
                               start_time: str, end_time: str) -> pd.DataFrame:
        """
        计算常用的 Alpha 因子。
        
        Args:
            instruments: 股票代码或代码列表
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            包含各种 Alpha 因子的 DataFrame
        """
        if not self.initialized:
            raise RuntimeError("qlib 未初始化")
        
        # 定义常用的 Alpha 因子表达式
        alpha_factors = {
            # 价格相关因子
            "returns_1d": "Ref($close, -1) / $close - 1",
            "returns_5d": "Ref($close, -5) / $close - 1", 
            "returns_20d": "Ref($close, -20) / $close - 1",
            
            # 移动平均因子
            "ma_5": "Mean($close, 5)",
            "ma_10": "Mean($close, 10)",
            "ma_20": "Mean($close, 20)",
            "ma_60": "Mean($close, 60)",
            
            # 相对价格位置
            "close_to_ma20": "$close / Mean($close, 20) - 1",
            "close_to_high20": "$close / Ref(Max($high, 20), -1) - 1",
            "close_to_low20": "$close / Ref(Min($low, 20), -1) - 1",
            
            # 波动率因子
            "volatility_20d": "Std(Ref($close, -1) / Ref($close, -2) - 1, 20)",
            "volatility_60d": "Std(Ref($close, -1) / Ref($close, -2) - 1, 60)",
            
            # 成交量因子
            "volume_ma_20": "Mean($volume, 20)",
            "volume_ratio": "$volume / Mean($volume, 20)",
            "turnover_20d": "Mean($volume / $close, 20)",
            
            # 价量结合因子
            "vwap_5": "Mean($close * $volume, 5) / Mean($volume, 5)",
            "price_volume_corr": "Corr($close, $volume, 20)",
            
            # 技术指标
            "rsi_14": "RSI($close, 14)",
            "bias_20": "($close - Mean($close, 20)) / Mean($close, 20)",
            
            # 高频因子
            "high_low_ratio": "$high / $low",
            "open_close_ratio": "$open / $close",
            "intraday_return": "($close - $open) / $open",
            
            # 动量因子
            "momentum_5d": "($close - Ref($close, -5)) / Ref($close, -5)",
            "momentum_20d": "($close - Ref($close, -20)) / Ref($close, -20)",
            "momentum_60d": "($close - Ref($close, -60)) / Ref($close, -60)",
            
            # 反转因子
            "reversal_1d": "-Ref($close, -1) / Ref($close, -2) + 1",
            "reversal_5d": "-Mean(Ref($close, -1) / Ref($close, -2) - 1, 5)",
        }
        
        logger.info(f"开始计算 {len(alpha_factors)} 个 Alpha 因子")
        
        try:
            # 使用 qlib 的表达式计算因子
            factor_data = D.features(
                instruments=instruments,
                fields=list(alpha_factors.values()),
                start_time=start_time,
                end_time=end_time,
                freq="day"
            )
            
            # 重命名列
            factor_data.columns = list(alpha_factors.keys())
            
            logger.info(f"成功计算因子，数据形状: {factor_data.shape}")
            return factor_data
            
        except Exception as e:
            logger.error(f"计算 Alpha 因子失败: {e}")
            raise
    
    def calculate_custom_factors(self, instruments: Union[str, List[str]],
                                start_time: str, end_time: str,
                                factor_expressions: Dict[str, str]) -> pd.DataFrame:
        """
        计算自定义因子表达式。
        
        Args:
            instruments: 股票代码或代码列表
            start_time: 开始时间
            end_time: 结束时间
            factor_expressions: 自定义因子表达式字典 {因子名: 表达式}
            
        Returns:
            包含自定义因子的 DataFrame
        """
        if not self.initialized:
            raise RuntimeError("qlib 未初始化")
        
        if not factor_expressions:
            logger.warning("没有提供自定义因子表达式")
            return pd.DataFrame()
        
        logger.info(f"开始计算 {len(factor_expressions)} 个自定义因子")
        
        try:
            factor_data = D.features(
                instruments=instruments,
                fields=list(factor_expressions.values()),
                start_time=start_time,
                end_time=end_time,
                freq="day"
            )
            
            # 重命名列
            factor_data.columns = list(factor_expressions.keys())
            
            logger.info(f"成功计算自定义因子，数据形状: {factor_data.shape}")
            return factor_data
            
        except Exception as e:
            logger.error(f"计算自定义因子失败: {e}")
            raise
    
    def get_factor_data_with_returns(self, instruments: Union[str, List[str]],
                                   start_time: str, end_time: str,
                                   factor_expressions: Optional[Dict[str, str]] = None,
                                   forward_periods: List[int] = [1, 5, 10, 20]) -> pd.DataFrame:
        """
        获取因子数据和前瞻收益。
        
        Args:
            instruments: 股票代码或代码列表
            start_time: 开始时间
            end_time: 结束时间
            factor_expressions: 自定义因子表达式，如果为空则使用默认因子
            forward_periods: 前瞻收益期数列表
            
        Returns:
            包含因子和前瞻收益的 DataFrame
        """
        # 获取因子数据
        if factor_expressions:
            factor_data = self.calculate_custom_factors(instruments, start_time, end_time, factor_expressions)
        else:
            factor_data = self.calculate_alpha_factors(instruments, start_time, end_time)
        
        # 添加前瞻收益
        return_expressions = {}
        for period in forward_periods:
            return_expressions[f"label_{period}d"] = f"Ref($close, -{period}) / $close - 1"
        
        if return_expressions:
            try:
                return_data = D.features(
                    instruments=instruments,
                    fields=list(return_expressions.values()),
                    start_time=start_time,
                    end_time=end_time,
                    freq="day"
                )
                return_data.columns = list(return_expressions.keys())
                
                # 合并因子数据和收益数据
                combined_data = pd.concat([factor_data, return_data], axis=1)
                
                logger.info(f"成功获取因子和收益数据，最终形状: {combined_data.shape}")
                return combined_data
                
            except Exception as e:
                logger.error(f"计算前瞻收益失败: {e}")
                return factor_data
        
        return factor_data
    
    def save_factor_data(self, factor_data: pd.DataFrame, filepath: str):
        """
        保存因子数据到文件。
        
        Args:
            factor_data: 因子数据
            filepath: 保存路径
        """
        try:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            
            if filepath.endswith('.csv'):
                factor_data.to_csv(filepath)
            elif filepath.endswith('.pickle') or filepath.endswith('.pkl'):
                factor_data.to_pickle(filepath)
            elif filepath.endswith('.parquet'):
                factor_data.to_parquet(filepath)
            else:
                # 默认保存为 pickle
                factor_data.to_pickle(filepath + '.pkl')
            
            logger.info(f"因子数据已保存到: {filepath}")
            
        except Exception as e:
            logger.error(f"保存因子数据失败: {e}")
            raise
    
    def load_factor_data(self, filepath: str) -> pd.DataFrame:
        """
        从文件加载因子数据。
        
        Args:
            filepath: 文件路径
            
        Returns:
            因子数据 DataFrame
        """
        try:
            if filepath.endswith('.csv'):
                data = pd.read_csv(filepath, index_col=[0, 1])
            elif filepath.endswith('.pickle') or filepath.endswith('.pkl'):
                data = pd.read_pickle(filepath)
            elif filepath.endswith('.parquet'):
                data = pd.read_parquet(filepath)
            else:
                raise ValueError(f"不支持的文件格式: {filepath}")
            
            logger.info(f"成功加载因子数据，形状: {data.shape}")
            return data
            
        except Exception as e:
            logger.error(f"加载因子数据失败: {e}")
            raise
