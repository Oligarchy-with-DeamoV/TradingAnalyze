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
            # 如果有本地数据目录，使用本地文件系统提供者
            if self.provider_uri and Path(self.provider_uri).exists():
                # 使用本地数据提供者配置
                provider_config = {
                    "provider": "LocalFileProvider", 
                    "provider_uri": self.provider_uri,
                    "calendar": {"provider": "LocalFileProvider"},
                    "instrument": {"provider": "LocalFileProvider"},
                    "feature": {"provider": "LocalFileProvider"}
                }
                qlib.init(provider_config=provider_config, region=self.region)
            else:
                # 默认配置
                qlib.init(region=self.region)
            
            self.initialized = True
            logger.info("qlib 初始化成功", provider_uri=self.provider_uri, region=self.region)
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
            # First try to use qlib's data provider
            data = D.features(
                instruments=instruments,
                fields=fields,
                start_time=start_time,
                end_time=end_time,
                freq="day"
            )
            logger.info(f"成功获取数据，形状: {data.shape}")
            
            # If data is empty and we have a local provider_uri, try to load CSV data directly
            if data.empty and self.provider_uri and Path(self.provider_uri).exists():
                logger.warning("qlib 数据提供者返回空数据，尝试直接读取 CSV 文件")
                data = self._load_csv_data_directly(instruments, start_time, end_time, fields)
                
            return data
        except Exception as e:
            logger.error(f"获取股票数据失败: {e}")
            # Try fallback to CSV if qlib provider fails
            if self.provider_uri and Path(self.provider_uri).exists():
                logger.info("尝试直接从 CSV 文件加载数据")
                try:
                    return self._load_csv_data_directly(instruments, start_time, end_time, fields)
                except Exception as csv_e:
                    logger.error(f"CSV 数据加载也失败: {csv_e}")
            raise
    
    def _load_csv_data_directly(self, instruments: Union[str, List[str]], 
                               start_time: str, end_time: str,
                               fields: List[str]) -> pd.DataFrame:
        """直接从 CSV 文件加载数据作为备用方案。"""
        if isinstance(instruments, str):
            instruments = [instruments]
        
        features_dir = Path(self.provider_uri) / "features"
        all_data = []
        
        for instrument in instruments:
            csv_file = features_dir / instrument / "1d.csv"
            if not csv_file.exists():
                logger.warning(f"CSV 文件不存在: {csv_file}")
                continue
                
            # 读取CSV数据
            df = pd.read_csv(csv_file)
            df['datetime'] = pd.to_datetime(df['datetime'])
            df = df.set_index('datetime')
            
            # 过滤日期范围
            start_date = pd.to_datetime(start_time)
            end_date = pd.to_datetime(end_time)
            df = df[(df.index >= start_date) & (df.index <= end_date)]
            
            # 只保留需要的字段
            available_fields = [f for f in fields if f in df.columns]
            if available_fields:
                df = df[available_fields]
                
                # 为每一行添加 instrument 信息，创建正确的多重索引
                df_with_instrument = df.copy()
                df_with_instrument['instrument'] = instrument
                df_with_instrument = df_with_instrument.reset_index().set_index(['datetime', 'instrument'])
                all_data.append(df_with_instrument)
        
        if all_data:
            result = pd.concat(all_data)
            logger.info(f"从 CSV 直接加载数据成功，形状: {result.shape}")
            return result
        else:
            logger.error("没有找到有效的 CSV 数据文件")
            return pd.DataFrame()
    
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
            # 首先尝试使用 qlib 的表达式计算因子
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
            
            # 如果数据为空且有本地数据，尝试使用本地数据计算
            if factor_data.empty and self.provider_uri and Path(self.provider_uri).exists():
                logger.warning("qlib 因子计算返回空数据，尝试使用本地数据计算")
                factor_data = self._calculate_factors_from_csv(instruments, start_time, end_time, alpha_factors)
            
            return factor_data
            
        except Exception as e:
            logger.error(f"计算 Alpha 因子失败: {e}")
            # 尝试使用 CSV 数据作为备用方案
            if self.provider_uri and Path(self.provider_uri).exists():
                logger.info("尝试使用本地 CSV 数据计算因子")
                try:
                    return self._calculate_factors_from_csv(instruments, start_time, end_time, alpha_factors)
                except Exception as csv_e:
                    logger.error(f"使用 CSV 数据计算因子也失败: {csv_e}")
            raise
    
    def _calculate_factors_from_csv(self, instruments: Union[str, List[str]], 
                                   start_time: str, end_time: str,
                                   alpha_factors: Dict[str, str]) -> pd.DataFrame:
        """使用 CSV 数据计算因子作为备用方案。"""
        # 首先加载基础数据
        base_data = self._load_csv_data_directly(
            instruments, start_time, end_time, 
            ["$open", "$high", "$low", "$close", "$volume"]
        )
        
        if base_data.empty:
            logger.error("无法加载基础数据进行因子计算")
            return pd.DataFrame()
        
        # 使用简化的因子计算
        factor_results = []
        
        for instrument in (instruments if isinstance(instruments, list) else [instruments]):
            # 获取单个股票数据
            try:
                stock_data = base_data.xs(instrument, level='instrument')
                
                # 计算简化版因子
                factors = self._calculate_simple_factors(stock_data)
                
                # 添加 instrument 信息
                factors.index = pd.MultiIndex.from_product(
                    [factors.index, [instrument]], 
                    names=['datetime', 'instrument']
                )
                
                factor_results.append(factors)
                
            except Exception as e:
                logger.warning(f"计算股票 {instrument} 的因子失败: {e}")
                continue
        
        if factor_results:
            result = pd.concat(factor_results)
            logger.info(f"使用 CSV 数据成功计算因子，形状: {result.shape}")
            return result
        else:
            logger.error("没有成功计算任何股票的因子")
            return pd.DataFrame()
    
    def _calculate_simple_factors(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算简化版的因子，使用 pandas 而不是 qlib 表达式。"""
        factors = pd.DataFrame(index=data.index)
        
        try:
            # 价格相关因子
            factors['returns_1d'] = data['$close'].pct_change(1)
            factors['returns_5d'] = data['$close'].pct_change(5)
            factors['returns_20d'] = data['$close'].pct_change(20)
            
            # 移动平均因子
            factors['ma_5'] = data['$close'].rolling(5).mean()
            factors['ma_10'] = data['$close'].rolling(10).mean()
            factors['ma_20'] = data['$close'].rolling(20).mean()
            factors['ma_60'] = data['$close'].rolling(60).mean()
            
            # 相对价格位置
            factors['close_to_ma20'] = data['$close'] / factors['ma_20'] - 1
            factors['close_to_high20'] = data['$close'] / data['$high'].rolling(20).max() - 1
            factors['close_to_low20'] = data['$close'] / data['$low'].rolling(20).min() - 1
            
            # 波动率因子
            returns = data['$close'].pct_change()
            factors['volatility_20d'] = returns.rolling(20).std()
            factors['volatility_60d'] = returns.rolling(60).std()
            
            # 成交量因子
            factors['volume_ma_20'] = data['$volume'].rolling(20).mean()
            factors['volume_ratio'] = data['$volume'] / factors['volume_ma_20']
            factors['turnover_20d'] = (data['$volume'] / data['$close']).rolling(20).mean()
            
            # 价量结合因子
            factors['vwap_5'] = (data['$close'] * data['$volume']).rolling(5).sum() / data['$volume'].rolling(5).sum()
            factors['price_volume_corr'] = data['$close'].rolling(20).corr(data['$volume'])
            
            # 技术指标 (简化版 RSI)
            delta = data['$close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            factors['rsi_14'] = 100 - (100 / (1 + rs))
            
            factors['bias_20'] = (data['$close'] - factors['ma_20']) / factors['ma_20']
            
            # 高频因子
            factors['high_low_ratio'] = data['$high'] / data['$low']
            factors['open_close_ratio'] = data['$open'] / data['$close']
            factors['intraday_return'] = (data['$close'] - data['$open']) / data['$open']
            
            # 动量因子
            factors['momentum_5d'] = (data['$close'] - data['$close'].shift(5)) / data['$close'].shift(5)
            factors['momentum_20d'] = (data['$close'] - data['$close'].shift(20)) / data['$close'].shift(20)
            factors['momentum_60d'] = (data['$close'] - data['$close'].shift(60)) / data['$close'].shift(60)
            
            # 反转因子
            factors['reversal_1d'] = -returns.shift(1)
            factors['reversal_5d'] = -returns.rolling(5).mean()
            
            logger.debug(f"成功计算 {len(factors.columns)} 个因子")
            
        except Exception as e:
            logger.error(f"计算因子时出错: {e}")
            
        return factors
    
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
                                    factor_data: Optional[pd.DataFrame] = None,
                                    periods: List[int] = [1, 5, 20]) -> pd.DataFrame:
        """
        获取包含前瞻收益标签的因子数据。
        
        Args:
            instruments: 股票代码或代码列表
            start_time: 开始时间
            end_time: 结束时间
            factor_data: 现有的因子数据，如果为None则重新计算
            periods: 前瞻收益期数列表
            
        Returns:
            包含因子和前瞻收益标签的DataFrame
        """
        if not self.initialized:
            raise RuntimeError("qlib 未初始化")
        
        try:
            # 如果没有提供因子数据，先计算因子
            if factor_data is None:
                factor_data = self.calculate_alpha_factors(instruments, start_time, end_time)
            
            if factor_data.empty:
                logger.error("因子数据为空，无法添加收益标签")
                return pd.DataFrame()
            
            # 获取价格数据来计算前瞻收益
            price_data = self.get_stock_data(instruments, start_time, end_time, ["$close"])
            
            if price_data.empty:
                logger.warning("无法获取价格数据，尝试直接从CSV计算前瞻收益")
                return self._add_returns_from_csv(factor_data, instruments, periods)
            
            # 计算前瞻收益标签
            returns_data = self._calculate_forward_returns(price_data, periods)
            
            # 合并因子数据和收益数据 - 确保索引结构匹配
            try:
                # 验证索引结构
                if isinstance(factor_data.index, pd.MultiIndex) and isinstance(returns_data.index, pd.MultiIndex):
                    if factor_data.index.nlevels != returns_data.index.nlevels:
                        logger.warning(f"索引层级不匹配: factor_data={factor_data.index.nlevels}, returns_data={returns_data.index.nlevels}")
                        # 尝试重新对齐索引
                        returns_data = returns_data.reindex(factor_data.index)
                
                combined_data = factor_data.join(returns_data, how='left')
                logger.info(f"成功添加前瞻收益标签，最终数据形状: {combined_data.shape}")
                return combined_data
            except Exception as join_error:
                logger.error(f"数据合并失败: {join_error}")
                # 尝试使用更简单的合并方法
                combined_data = factor_data.copy()
                for col in returns_data.columns:
                    try:
                        combined_data[col] = returns_data[col]
                    except Exception:
                        logger.warning(f"无法添加列: {col}")
                return combined_data
            
        except Exception as e:
            logger.error(f"添加前瞻收益失败: {e}")
            # 作为备用方案，尝试从CSV数据计算
            if self.provider_uri and Path(self.provider_uri).exists():
                logger.info("尝试从CSV数据计算前瞻收益")
                return self._add_returns_from_csv(factor_data, instruments, periods)
            raise
    
    def _calculate_forward_returns(self, price_data: pd.DataFrame, periods: List[int]) -> pd.DataFrame:
        """计算前瞻收益标签。"""
        returns_data = pd.DataFrame(index=price_data.index)
        
        for period in periods:
            # 计算前瞻收益 - 修复多重索引问题
            forward_returns = price_data['$close'].groupby(level='instrument').apply(
                lambda x: x.shift(-period) / x - 1
            )
            
            # 确保索引结构正确 - 重置为与原数据相同的多重索引
            if isinstance(forward_returns.index, pd.MultiIndex) and forward_returns.index.nlevels > 2:
                # 如果groupby产生了3级索引，需要重新构造为2级索引
                forward_returns = forward_returns.droplevel(0)
            
            returns_data[f'label_{period}d'] = forward_returns
        
        return returns_data
    
    def _calculate_forward_returns_robust(self, price_data: pd.DataFrame, periods: List[int]) -> pd.DataFrame:
        """计算前瞻收益标签的稳健版本，避免多重索引问题。"""
        returns_data = pd.DataFrame(index=price_data.index)
        
        # 获取所有股票代码
        if isinstance(price_data.index, pd.MultiIndex):
            instruments = price_data.index.get_level_values('instrument').unique()
        else:
            instruments = [None]  # 单层索引情况
        
        for period in periods:
            returns_series = pd.Series(index=price_data.index, dtype=float)
            
            for instrument in instruments:
                try:
                    if isinstance(price_data.index, pd.MultiIndex):
                        # 多重索引情况
                        stock_prices = price_data.xs(instrument, level='instrument')['$close']
                        forward_returns = stock_prices.shift(-period) / stock_prices - 1
                        
                        # 将结果分配给正确的多重索引位置
                        for date, ret_value in forward_returns.items():
                            if not pd.isna(ret_value):
                                try:
                                    returns_series.loc[(date, instrument)] = ret_value
                                except (KeyError, IndexError):
                                    continue
                    else:
                        # 单层索引情况
                        stock_prices = price_data['$close']
                        forward_returns = stock_prices.shift(-period) / stock_prices - 1
                        returns_series = forward_returns
                        
                except Exception as e:
                    logger.warning(f"计算股票 {instrument} 的 {period} 日前瞻收益失败: {e}")
                    continue
            
            returns_data[f'label_{period}d'] = returns_series
        
        return returns_data

    def _add_returns_from_csv(self, factor_data: pd.DataFrame, 
                             instruments: Union[str, List[str]], 
                             periods: List[int]) -> pd.DataFrame:
        """从CSV数据直接计算并添加前瞻收益标签。"""
        if isinstance(instruments, str):
            instruments = [instruments]
        
        features_dir = Path(self.provider_uri) / "features"
        combined_data = factor_data.copy()
        
        for instrument in instruments:
            csv_file = features_dir / instrument / "1d.csv"
            if not csv_file.exists():
                logger.warning(f"CSV 文件不存在: {csv_file}")
                continue
            
            # 读取价格数据
            df = pd.read_csv(csv_file)
            df['datetime'] = pd.to_datetime(df['datetime'])
            df = df.set_index('datetime')
            
            # 计算前瞻收益
            for period in periods:
                forward_returns = df['$close'].shift(-period) / df['$close'] - 1
                
                # 将收益添加到对应的多重索引位置
                for date, ret_value in forward_returns.items():
                    try:
                        if (date, instrument) in combined_data.index:
                            combined_data.loc[(date, instrument), f'label_{period}d'] = ret_value
                    except (KeyError, IndexError):
                        continue
        
        logger.info(f"从CSV数据成功添加前瞻收益，数据形状: {combined_data.shape}")
        return combined_data

    def load_factor_data(self, file_path: str) -> pd.DataFrame:
        """加载因子数据文件。"""
        try:
            data = pd.read_csv(file_path)
            
            # 如果有datetime和instrument列，设置为多重索引
            if 'datetime' in data.columns and 'instrument' in data.columns:
                data['datetime'] = pd.to_datetime(data['datetime'])
                data = data.set_index(['datetime', 'instrument'])
            
            logger.info(f"成功加载因子数据，形状: {data.shape}")
            return data
            
        except Exception as e:
            logger.error(f"加载因子数据失败: {e}")
            return pd.DataFrame()
    
    def save_factor_data(self, factor_data: pd.DataFrame, file_path: str):
        """保存因子数据到文件。"""
        try:
            # 确保目录存在
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            # 保存为CSV
            factor_data.to_csv(file_path)
            
            logger.info(f"因子数据已保存到: {file_path}")
            
        except Exception as e:
            logger.error(f"保存因子数据失败: {e}")
            raise
