"""测试数据转换器。"""

import pickle
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest

from trading_analyze.data_pipeline.converter import DataConverter


class TestDataConverter:
    """测试 DataConverter 类。"""
    
    def test_init(self, temp_dir: Path):
        """测试初始化。"""
        input_dir = temp_dir / "input"
        output_dir = temp_dir / "output"
        
        converter = DataConverter(str(input_dir), str(output_dir))
        
        assert converter.input_dir == input_dir
        assert converter.output_dir == output_dir
        assert output_dir.exists()
        assert (output_dir / "instruments").exists()
        assert (output_dir / "features").exists()
    
    def test_init_default_dirs(self):
        """测试默认目录。"""
        converter = DataConverter()
        assert str(converter.input_dir) == "raw_data"
        assert str(converter.output_dir) == "qlib_data"
    
    def test_load_data_from_files(self, temp_dir: Path, sample_multi_csv_files: dict):
        """测试从文件加载数据。"""
        converter = DataConverter(str(temp_dir), str(temp_dir / "output"))
        
        data_dict = converter._load_data_from_files("*.csv")
        
        # 由于文件名都以 STOCK 开头，所以只会有一个键 "STOCK"
        # (STOCK_A 和 STOCK_B 文件名的第一部分都是 STOCK)
        assert len(data_dict) == 1
        assert "STOCK" in data_dict
        
        # 检查数据格式
        data = data_dict["STOCK"]
        assert isinstance(data, pd.DataFrame)
        assert len(data) == 5
        assert isinstance(data.index, pd.DatetimeIndex)
    
    def test_load_data_from_files_no_files(self, temp_dir: Path):
        """测试没有找到文件的情况。"""
        converter = DataConverter(str(temp_dir), str(temp_dir / "output"))
        
        data_dict = converter._load_data_from_files("*.csv")
        
        assert data_dict == {}
    
    def test_standardize_data_valid(self, sample_ohlcv_data: pd.DataFrame):
        """测试标准化有效数据。"""
        converter = DataConverter()
        
        result = converter._standardize_data(sample_ohlcv_data, "TEST_STOCK")
        
        assert result is not None
        assert len(result) == 10
        
        expected_columns = ['instrument', 'datetime', '$open', '$high', '$low', '$close', '$volume']
        assert list(result.columns) == expected_columns
        
        # 检查数据内容
        assert all(result['instrument'] == "TEST_STOCK")
        assert result['$open'].iloc[0] == 100.0
        assert result['$close'].iloc[-1] == 113.0
    
    def test_standardize_data_missing_columns(self):
        """测试缺少必需列的数据。"""
        # 创建缺少 volume 列的数据
        data = pd.DataFrame({
            'open': [100, 101],
            'high': [105, 106],
            'low': [98, 99],
            'close': [104, 105]
        }, index=pd.date_range('2023-01-01', periods=2))
        
        converter = DataConverter()
        result = converter._standardize_data(data, "TEST_STOCK")
        
        assert result is None
    
    def test_standardize_data_invalid_prices(self):
        """测试包含无效价格的数据。"""
        # 创建包含负价格的数据
        data = pd.DataFrame({
            'open': [100, -50],  # 负价格
            'high': [105, 55],
            'low': [98, 48],
            'close': [104, 54],
            'volume': [1000000, 2000000]
        }, index=pd.date_range('2023-01-01', periods=2))
        
        converter = DataConverter()
        result = converter._standardize_data(data, "TEST_STOCK")
        
        # 应该过滤掉无效价格的行
        assert len(result) == 1
        assert result['$open'].iloc[0] == 100
    
    def test_standardize_data_invalid_ohlc_logic(self):
        """测试 OHLC 逻辑错误的数据。"""
        # 创建高价低于低价的数据
        data = pd.DataFrame({
            'open': [100, 101],
            'high': [95, 106],  # 高价低于开盘价
            'low': [98, 99],
            'close': [104, 105],
            'volume': [1000000, 1100000]
        }, index=pd.date_range('2023-01-01', periods=2))
        
        converter = DataConverter()
        result = converter._standardize_data(data, "TEST_STOCK")
        
        # 应该过滤掉逻辑错误的行
        assert len(result) == 1
        assert result['$high'].iloc[0] == 106  # 只保留第二行
    
    def test_standardize_data_zero_volume(self):
        """测试零成交量数据。"""
        data = pd.DataFrame({
            'open': [100, 101],
            'high': [105, 106],
            'low': [98, 99],
            'close': [104, 105],
            'volume': [0, 1100000]  # 零成交量
        }, index=pd.date_range('2023-01-01', periods=2))
        
        converter = DataConverter()
        result = converter._standardize_data(data, "TEST_STOCK")
        
        # 应该过滤掉零成交量的行
        assert len(result) == 1
        assert result['$volume'].iloc[0] == 1100000
    
    def test_standardize_data_all_invalid(self):
        """测试所有数据都无效的情况。"""
        data = pd.DataFrame({
            'open': [-100, -101],  # 全是负价格
            'high': [-95, -90],
            'low': [-105, -110],
            'close': [-98, -95],
            'volume': [1000000, 1100000]
        }, index=pd.date_range('2023-01-01', periods=2))
        
        converter = DataConverter()
        result = converter._standardize_data(data, "TEST_STOCK")
        
        assert result is None
    
    def test_save_qlib_data(self, temp_dir: Path, sample_multi_stock_data: dict):
        """测试保存 qlib 数据。"""
        converter = DataConverter(str(temp_dir), str(temp_dir / "output"))
        
        # 准备测试数据
        all_data = []
        instruments = []
        
        for symbol, data in sample_multi_stock_data.items():
            standardized = converter._standardize_data(data, symbol)
            if standardized is not None:
                all_data.append(standardized)
                instruments.append(symbol)
        
        combined_data = pd.concat(all_data, ignore_index=True)
        converter._save_qlib_data(combined_data, instruments)
        
        # 检查生成的文件
        output_dir = temp_dir / "output"
        assert (output_dir / "features" / "data.csv").exists()
        assert (output_dir / "instruments" / "all.txt").exists()
        assert (output_dir / "config.pkl").exists()
        assert (output_dir / "data_stats.pkl").exists()
        
        # 检查数据文件内容
        saved_data = pd.read_csv(output_dir / "features" / "data.csv")
        assert len(saved_data) == len(combined_data)
        assert list(saved_data.columns) == list(combined_data.columns)
        
        # 检查股票列表
        with open(output_dir / "instruments" / "all.txt", 'r') as f:
            saved_instruments = [line.strip() for line in f if line.strip()]
        assert sorted(saved_instruments) == sorted(instruments)
        
        # 检查配置文件
        with open(output_dir / "config.pkl", 'rb') as f:
            config = pickle.load(f)
        assert 'provider_uri' in config
        assert config['region'] == 'custom'
        
        # 检查统计文件
        with open(output_dir / "data_stats.pkl", 'rb') as f:
            stats = pickle.load(f)
        assert stats['total_records'] == len(combined_data)
        assert stats['instruments_count'] == len(instruments)
    
    def test_convert_to_qlib_format_with_data_dict(self, temp_dir: Path, sample_multi_stock_data: dict):
        """测试使用数据字典进行转换。"""
        converter = DataConverter(str(temp_dir), str(temp_dir / "output"))
        
        success = converter.convert_to_qlib_format(data_dict=sample_multi_stock_data)
        
        assert success is True
        
        # 检查输出文件
        output_dir = temp_dir / "output"
        assert (output_dir / "features" / "data.csv").exists()
        assert (output_dir / "instruments" / "all.txt").exists()
    
    def test_convert_to_qlib_format_from_files(self, temp_dir: Path, sample_multi_csv_files: dict):
        """测试从文件进行转换。"""
        converter = DataConverter(str(temp_dir), str(temp_dir / "output"))
        
        success = converter.convert_to_qlib_format()
        
        assert success is True
        
        # 检查输出文件
        output_dir = temp_dir / "output"
        assert (output_dir / "features" / "data.csv").exists()
        assert (output_dir / "instruments" / "all.txt").exists()
    
    def test_convert_to_qlib_format_no_data(self, temp_dir: Path):
        """测试没有数据的情况。"""
        converter = DataConverter(str(temp_dir), str(temp_dir / "output"))
        
        success = converter.convert_to_qlib_format()
        
        assert success is False
    
    def test_convert_to_qlib_format_invalid_data(self, temp_dir: Path):
        """测试无效数据的情况。"""
        # 创建全部无效的数据
        invalid_data = {
            'BAD_STOCK': pd.DataFrame({
                'open': [-100],  # 无效价格
                'high': [-95],
                'low': [-105],
                'close': [-98],
                'volume': [0]  # 零成交量
            }, index=pd.date_range('2023-01-01', periods=1))
        }
        
        converter = DataConverter(str(temp_dir), str(temp_dir / "output"))
        success = converter.convert_to_qlib_format(data_dict=invalid_data)
        
        assert success is False
    
    def test_get_conversion_stats_exists(self, temp_dir: Path, sample_multi_stock_data: dict):
        """测试获取转换统计信息（文件存在）。"""
        converter = DataConverter(str(temp_dir), str(temp_dir / "output"))
        converter.convert_to_qlib_format(data_dict=sample_multi_stock_data)
        
        stats = converter.get_conversion_stats()
        
        assert stats is not None
        assert 'total_records' in stats
        assert 'instruments_count' in stats
        assert 'date_range' in stats
        assert 'instruments' in stats
    
    def test_get_conversion_stats_not_exists(self, temp_dir: Path):
        """测试获取转换统计信息（文件不存在）。"""
        converter = DataConverter(str(temp_dir), str(temp_dir / "output"))
        
        stats = converter.get_conversion_stats()
        
        assert stats is None
