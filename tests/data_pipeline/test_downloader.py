"""测试数据下载器。"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

from trading_analyze.data_pipeline.downloader import DataDownloader


class TestDataDownloader:
    """测试 DataDownloader 类。"""
    
    def test_init(self, temp_dir: Path):
        """测试初始化。"""
        downloader = DataDownloader(str(temp_dir / "raw_data"))
        assert downloader.output_dir.exists()
        assert downloader.output_dir.name == "raw_data"
    
    def test_init_default_output(self):
        """测试默认输出目录。"""
        downloader = DataDownloader()
        assert str(downloader.output_dir) == "raw_data"
    
    def test_download_from_csv_single_stock(self, temp_dir: Path, sample_csv_file: Path):
        """测试从 CSV 文件下载单只股票数据。"""
        downloader = DataDownloader(str(temp_dir / "output"))
        
        result = downloader.download_from_csv(str(sample_csv_file))
        
        assert len(result) == 1
        assert "test_stock" in result
        
        data = result["test_stock"]
        assert len(data) == 10
        assert list(data.columns) == ['open', 'high', 'low', 'close', 'volume']
        assert data.index.name == 'date'
        
        # 检查输出文件是否创建
        output_file = temp_dir / "output" / "test_stock_from_csv.csv"
        assert output_file.exists()
    
    def test_download_from_csv_multi_stock(self, temp_dir: Path):
        """测试从包含多只股票的 CSV 文件下载数据。"""
        # 创建多股票 CSV 文件
        csv_content = """symbol,date,open,high,low,close,volume
STOCK_A,2023-01-01,100,105,98,104,1000000
STOCK_A,2023-01-02,104,109,102,108,1100000
STOCK_B,2023-01-01,50,55,48,54,2000000
STOCK_B,2023-01-02,54,59,52,58,2100000"""
        
        csv_file = temp_dir / "multi_stock.csv"
        with open(csv_file, 'w') as f:
            f.write(csv_content)
        
        downloader = DataDownloader(str(temp_dir / "output"))
        result = downloader.download_from_csv(str(csv_file))
        
        assert len(result) == 2
        assert "STOCK_A" in result
        assert "STOCK_B" in result
        
        # 检查 STOCK_A 数据
        data_a = result["STOCK_A"]
        assert len(data_a) == 2
        assert data_a.iloc[0]['close'] == 104
        
        # 检查 STOCK_B 数据
        data_b = result["STOCK_B"]
        assert len(data_b) == 2
        assert data_b.iloc[0]['close'] == 54
    
    def test_download_from_csv_missing_columns(self, temp_dir: Path, incomplete_csv_data: str):
        """测试从缺少必需列的 CSV 文件下载数据。"""
        csv_file = temp_dir / "incomplete.csv"
        with open(csv_file, 'w') as f:
            f.write(incomplete_csv_data)
        
        downloader = DataDownloader(str(temp_dir / "output"))
        
        with pytest.raises(ValueError, match="CSV 文件缺少必需列"):
            downloader.download_from_csv(str(csv_file))
    
    def test_download_from_csv_file_not_found(self, temp_dir: Path):
        """测试文件不存在的情况。"""
        downloader = DataDownloader(str(temp_dir / "output"))
        
        with pytest.raises(Exception):
            downloader.download_from_csv(str(temp_dir / "nonexistent.csv"))
    
    @patch('trading_analyze.data_pipeline.downloader.yf.Ticker')
    def test_download_yahoo_finance_success(self, mock_ticker_class, temp_dir: Path):
        """测试成功从 Yahoo Finance 下载数据。"""
        # Mock yfinance Ticker
        mock_ticker = Mock()
        mock_data = pd.DataFrame({
            'Open': [100, 101, 102],
            'High': [105, 106, 107],
            'Low': [98, 99, 100],
            'Close': [104, 105, 106],
            'Volume': [1000000, 1100000, 1200000]
        }, index=pd.date_range('2023-01-01', periods=3))
        mock_data.index.name = 'Date'
        
        mock_ticker.history.return_value = mock_data
        mock_ticker_class.return_value = mock_ticker
        
        downloader = DataDownloader(str(temp_dir / "output"))
        result = downloader.download_yahoo_finance(
            symbols=["AAPL"],
            start_date="2023-01-01",
            end_date="2023-01-03"
        )
        
        assert len(result) == 1
        assert "AAPL" in result
        
        data = result["AAPL"]
        assert len(data) == 3
        assert 'open' in data.columns
        assert 'high' in data.columns
        assert 'low' in data.columns
        assert 'close' in data.columns
        assert 'volume' in data.columns
        
        # 检查输出文件
        output_file = temp_dir / "output" / "AAPL_2023-01-01_2023-01-03.csv"
        assert output_file.exists()
    
    @patch('trading_analyze.data_pipeline.downloader.yf.Ticker')
    def test_download_yahoo_finance_empty_data(self, mock_ticker_class, temp_dir: Path):
        """测试 Yahoo Finance 返回空数据。"""
        mock_ticker = Mock()
        mock_ticker.history.return_value = pd.DataFrame()
        mock_ticker_class.return_value = mock_ticker
        
        downloader = DataDownloader(str(temp_dir / "output"))
        result = downloader.download_yahoo_finance(
            symbols=["INVALID"],
            start_date="2023-01-01",
            end_date="2023-01-03"
        )
        
        assert len(result) == 0
    
    @patch('trading_analyze.data_pipeline.downloader.yf.Ticker')
    def test_download_yahoo_finance_exception(self, mock_ticker_class, temp_dir: Path):
        """测试 Yahoo Finance 下载异常。"""
        mock_ticker_class.side_effect = Exception("Network error")
        
        downloader = DataDownloader(str(temp_dir / "output"))
        result = downloader.download_yahoo_finance(
            symbols=["AAPL"],
            start_date="2023-01-01",
            end_date="2023-01-03"
        )
        
        assert len(result) == 0
    
    def test_download_yahoo_finance_default_end_date(self, temp_dir: Path):
        """测试默认结束日期。"""
        with patch('trading_analyze.data_pipeline.downloader.yf.Ticker') as mock_ticker_class:
            mock_ticker = Mock()
            mock_ticker.history.return_value = pd.DataFrame()
            mock_ticker_class.return_value = mock_ticker
            
            downloader = DataDownloader(str(temp_dir / "output"))
            downloader.download_yahoo_finance(
                symbols=["AAPL"],
                start_date="2023-01-01"
            )
            
            # 验证 history 被正确调用
            mock_ticker.history.assert_called_once()
            call_args = mock_ticker.history.call_args
            assert call_args[1]['start'] == "2023-01-01"
            assert call_args[1]['end'] is not None  # 应该有默认的结束日期
    
    def test_list_available_data_empty(self, temp_dir: Path):
        """测试空输出目录。"""
        downloader = DataDownloader(str(temp_dir / "output"))
        files = downloader.list_available_data()
        assert files == []
    
    def test_list_available_data_with_files(self, temp_dir: Path):
        """测试有文件的输出目录。"""
        output_dir = temp_dir / "output"
        output_dir.mkdir()
        
        # 创建一些测试文件
        (output_dir / "stock1.csv").touch()
        (output_dir / "stock2.csv").touch()
        (output_dir / "not_csv.txt").touch()
        
        downloader = DataDownloader(str(output_dir))
        files = downloader.list_available_data()
        
        assert len(files) == 2
        assert "stock1.csv" in files
        assert "stock2.csv" in files
        assert "not_csv.txt" not in files
