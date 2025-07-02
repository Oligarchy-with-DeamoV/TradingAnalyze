"""数据转换器 - 将原始数据转换为 qlib 格式。"""

import os
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd
import structlog

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
            combined_data = pd.concat(all_data, ignore_index=True)
            
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
                data_dict[symbol] = data
                
                logger.debug("文件加载成功", file=file_path.name, symbol=symbol)
                
            except Exception as e:
                logger.warning("文件加载失败", file=file_path.name, error=str(e))
                
        return data_dict
    
    def _standardize_data(self, data: pd.DataFrame, symbol: str) -> Optional[pd.DataFrame]:
        """标准化单个股票的数据格式。"""
        try:
            # 确保索引是日期类型
            if not isinstance(data.index, pd.DatetimeIndex):
                data.index = pd.to_datetime(data.index)
            
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
            data_renamed['datetime'] = data_renamed.index
            
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
            # 保存主数据文件
            data_file = self.output_dir / "features" / "data.csv"
            data.to_csv(data_file, index=False)
            logger.info("主数据文件已保存", file=str(data_file))
            
            # 保存 instruments 列表
            instruments_file = self.output_dir / "instruments" / "all.txt"
            with open(instruments_file, 'w') as f:
                for instrument in sorted(instruments):
                    f.write(f"{instrument}\n")
            logger.info("股票列表已保存", file=str(instruments_file), count=len(instruments))
            
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
                    'start': data['datetime'].min().isoformat(),
                    'end': data['datetime'].max().isoformat()
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
