"""数据转换器 - 将原始数据转换为 qlib 格式。"""

import os
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd
import structlog

try:
    import qlib
    from qlib.data import dump_bin
    QLIB_AVAILABLE = True
except ImportError:
    QLIB_AVAILABLE = False

logger = structlog.get_logger()


class DataConverter:
    """数据转换器，将原始数据转换为 qlib 格式。"""
    
    def __init__(self, input_dir: str = "./raw_data", output_dir: str = "./qlib_data"):
        """初始化转换器。
        
        Args:
            input_dir: 原始数据目录
            output_dir: qlib 数据输出目录
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建 qlib 标准目录结构
        (self.output_dir / "instruments").mkdir(exist_ok=True)
        (self.output_dir / "features").mkdir(exist_ok=True)
        
    def convert_to_qlib_format(
        self,
        data_dict: Optional[Dict[str, pd.DataFrame]] = None,
        file_pattern: str = "*.csv"
    ) -> bool:
        """转换数据为 qlib 格式。
        
        Args:
            data_dict: 数据字典，如果为 None 则从文件读取
            file_pattern: 文件匹配模式
            
        Returns:
            转换是否成功
        """
        try:
            if data_dict is None:
                data_dict = self._load_data_from_files(file_pattern)
                
            if not data_dict:
                logger.error("没有找到要转换的数据")
                return False
                
            logger.info("开始转换数据为 qlib 格式", symbols=len(data_dict))
            
            # 转换每个股票的数据
            all_data = []
            instruments = []
            
            for symbol, data in data_dict.items():
                logger.info("转换股票数据", symbol=symbol)
                
                # 标准化数据格式
                standardized_data = self._standardize_data(data, symbol)
                if standardized_data is not None:
                    all_data.append(standardized_data)
                    instruments.append(symbol)
            
            if not all_data:
                logger.error("没有有效的数据可以转换")
                return False
                
            # 合并所有数据
            if all_data:
                # 确保所有datetime列都没有时区信息
                for i, df in enumerate(all_data):
                    if 'datetime' in df.columns:
                        if hasattr(df['datetime'].dtype, 'tz') and df['datetime'].dtype.tz is not None:
                            all_data[i] = df.copy()
                            all_data[i]['datetime'] = pd.to_datetime(df['datetime']).dt.tz_localize(None)
                
                combined_data = pd.concat(all_data, ignore_index=True)
            else:
                combined_data = pd.DataFrame()
            
            # 保存为 qlib 格式
            self._save_qlib_data(combined_data, instruments)
            
            logger.info("数据转换完成", 
                       total_records=len(combined_data),
                       instruments_count=len(instruments))
            return True
            
        except Exception as e:
            logger.error("数据转换失败", error=str(e))
            return False
    
    def _load_data_from_files(self, file_pattern: str) -> Dict[str, pd.DataFrame]:
        """从文件加载数据。"""
        data_dict = {}
        csv_files = list(self.input_dir.glob(file_pattern))
        
        logger.info("加载数据文件", file_count=len(csv_files))
        
        for file_path in csv_files:
            try:
                # 从文件名提取股票代码
                symbol = file_path.stem.split('_')[0]
                
                data = pd.read_csv(file_path, index_col=0, parse_dates=True)
                
                # 确保索引没有时区信息
                if isinstance(data.index, pd.DatetimeIndex) and data.index.tz is not None:
                    data.index = data.index.tz_convert('UTC').tz_localize(None)
                
                # 标准化列名（转为小写并清理）
                data.columns = data.columns.str.lower().str.strip()
                
                data_dict[symbol] = data
                
                logger.debug("文件加载成功", file=file_path.name, symbol=symbol)
                
            except Exception as e:
                logger.warning("文件加载失败", file=file_path.name, error=str(e))
                
        return data_dict
    
    def _standardize_data(self, data: pd.DataFrame, symbol: str) -> Optional[pd.DataFrame]:
        """标准化单个股票的数据格式。"""
        try:
            # 确保索引是日期类型，并移除时区信息
            if not isinstance(data.index, pd.DatetimeIndex):
                data.index = pd.to_datetime(data.index, utc=True).tz_localize(None)
            elif data.index.tz is not None:
                data.index = data.index.tz_convert('UTC').tz_localize(None)
            
            # 确保所有列都没有时区信息
            for col in data.columns:
                if pd.api.types.is_datetime64_any_dtype(data[col]):
                    if hasattr(data[col].dtype, 'tz') and data[col].dtype.tz is not None:
                        data[col] = pd.to_datetime(data[col], utc=True).dt.tz_localize(None)
            
            # 标准化列名
            column_mapping = {
                'open': '$open',
                'high': '$high', 
                'low': '$low',
                'close': '$close',
                'volume': '$volume'
            }
            
            # 检查必需列
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in data.columns]
            
            if missing_columns:
                logger.warning("数据缺少必需列", symbol=symbol, missing=missing_columns)
                return None
            
            # 重命名列
            data_renamed = data[required_columns].rename(columns=column_mapping)
            
            # 添加元数据列
            data_renamed['instrument'] = symbol
            # 确保datetime列没有时区信息，并格式化为日期字符串
            datetime_series = pd.to_datetime(data_renamed.index, utc=True).tz_localize(None)
            # 只保留日期部分，去掉时间部分
            data_renamed['datetime'] = datetime_series.strftime('%Y-%m-%d')
            
            # 重新排列列顺序
            columns_order = ['instrument', 'datetime', '$open', '$high', '$low', '$close', '$volume']
            data_final = data_renamed[columns_order].copy()
            
            # 数据清洗
            data_final = data_final.dropna()
            data_final = data_final[data_final['$volume'] > 0]  # 过滤零成交量
            
            # 检查数据合理性
            price_cols = ['$open', '$high', '$low', '$close']
            for col in price_cols:
                data_final = data_final[data_final[col] > 0]  # 过滤负价格
            
            # 检查高低价逻辑
            data_final = data_final[
                (data_final['$high'] >= data_final['$low']) &
                (data_final['$high'] >= data_final['$open']) &
                (data_final['$high'] >= data_final['$close']) &
                (data_final['$low'] <= data_final['$open']) &
                (data_final['$low'] <= data_final['$close'])
            ]
            
            if len(data_final) == 0:
                logger.warning("数据清洗后无有效记录", symbol=symbol)
                return None
                
            logger.debug("数据标准化完成", 
                        symbol=symbol, 
                        records=len(data_final),
                        date_range=f"{data_final['datetime'].min()} to {data_final['datetime'].max()}")
            
            return data_final
            
        except Exception as e:
            logger.error("数据标准化失败", symbol=symbol, error=str(e))
            return None
    
    def _save_qlib_data(self, data: pd.DataFrame, instruments: List[str]):
        """保存数据为 qlib 格式。"""
        try:
            # 创建必要的目录结构
            (self.output_dir / "features").mkdir(exist_ok=True)
            (self.output_dir / "instruments").mkdir(exist_ok=True)
            (self.output_dir / "calendars").mkdir(exist_ok=True)
            
            # 按股票分组保存数据（qlib 标准格式）
            for symbol in instruments:
                symbol_data = data[data['instrument'] == symbol].copy()
                if len(symbol_data) == 0:
                    continue
                    
                # 创建股票目录
                symbol_dir = self.output_dir / "features" / symbol
                symbol_dir.mkdir(exist_ok=True)
                
                # 重新索引为日期
                symbol_data = symbol_data.set_index('datetime')
                symbol_data = symbol_data.drop(columns=['instrument'])
                
                # 保存为 qlib 格式
                symbol_file = symbol_dir / "1d.bin" 
                # 由于我们使用简化格式，先保存为CSV，然后qlib会自动处理
                csv_file = symbol_dir / "1d.csv"
                symbol_data.to_csv(csv_file)
                
                logger.debug("保存股票数据", symbol=symbol, records=len(symbol_data))
            
            # 保存主数据文件（备用）
            data_file = self.output_dir / "features" / "data.csv"
            data.to_csv(data_file, index=False)
            logger.info("主数据文件已保存", file=str(data_file))
            
            # 保存 instruments 列表
            instruments_file = self.output_dir / "instruments" / "all.txt"
            with open(instruments_file, 'w') as f:
                for instrument in sorted(instruments):
                    f.write(f"{instrument}\n")
            logger.info("股票列表已保存", file=str(instruments_file), count=len(instruments))
            
            # 创建日历文件
            self._create_calendar(data)
            
            # 创建简单的 qlib 配置
            config = {
                'provider_uri': str(self.output_dir),
                'region': 'custom',
                'market': 'custom',
                'calendar_provider': 'LocalCalendarProvider',
                'instrument_provider': 'LocalInstrumentProvider',
                'feature_provider': 'LocalFeatureProvider',
            }
            
            config_file = self.output_dir / "config.pkl"
            with open(config_file, 'wb') as f:
                pickle.dump(config, f)
            logger.info("配置文件已保存", file=str(config_file))
            
            # 保存数据统计信息
            stats = {
                'total_records': len(data),
                'instruments_count': len(instruments),
                'date_range': {
                    'start': data['datetime'].min(),
                    'end': data['datetime'].max()
                },
                'instruments': sorted(instruments)
            }
            
            stats_file = self.output_dir / "data_stats.pkl"
            with open(stats_file, 'wb') as f:
                pickle.dump(stats, f)
            logger.info("数据统计已保存", file=str(stats_file))
            
        except Exception as e:
            logger.error("保存 qlib 数据失败", error=str(e))
            raise
    
    def _create_calendar(self, data: pd.DataFrame):
        """创建交易日历文件。"""
        try:
            # 获取所有交易日期
            dates = sorted(data['datetime'].unique())
            
            # 保存日历文件
            calendar_file = self.output_dir / "calendars" / "day.txt"
            with open(calendar_file, 'w') as f:
                for date in dates:
                    f.write(f"{date}\n")
            
            logger.info("交易日历已保存", file=str(calendar_file), dates=len(dates))
            
        except Exception as e:
            logger.error("创建日历失败", error=str(e))
            raise
    
    def get_conversion_stats(self) -> Optional[Dict]:
        """获取转换统计信息。"""
        stats_file = self.output_dir / "data_stats.pkl"
        if stats_file.exists():
            try:
                with open(stats_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                logger.error("读取统计信息失败", error=str(e))
        return None
