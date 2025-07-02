"""测试 main.py 模块。"""

import os
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pandas as pd
import pytest

from trading_analyze.main import (
    fetch_data,
    fetch_trading_data,
    main,
    read_csv_to_dataframe,
    split_dataframe_by_first_column,
)


class TestReadCsvToDataframe:
    """测试 read_csv_to_dataframe 函数。"""
    
    def test_read_valid_csv(self, sample_csv_file):
        """测试读取有效的 CSV 文件。"""
        df = read_csv_to_dataframe(str(sample_csv_file))
        
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
    
    def test_read_nonexistent_file(self):
        """测试读取不存在的文件。"""
        with pytest.raises(FileNotFoundError):
            read_csv_to_dataframe("nonexistent_file.csv")
    
    @patch('trading_analyze.main.structlogger')
    def test_logging_on_success(self, mock_logger, sample_csv_file):
        """测试成功读取时的日志记录。"""
        read_csv_to_dataframe(str(sample_csv_file))
        mock_logger.info.assert_called_with("CSV file successfully read.")


class TestSplitDataframeByFirstColumn:
    """测试 split_dataframe_by_first_column 函数。"""
    
    def test_split_by_symbol(self, temp_dir):
        """测试按照股票代码分割数据。"""
        test_csv_content = """symbol,date,open,close,volume
AAPL,2023-01-01,100,105,1000
AAPL,2023-01-02,105,110,1100
GOOGL,2023-01-01,200,205,2000"""
        
        csv_file = temp_dir / "multi_stock.csv"
        with open(csv_file, 'w') as f:
            f.write(test_csv_content)
        
        # 使用逗号作为分隔符，因为 CSV 文件是逗号分隔的
        result = split_dataframe_by_first_column(str(csv_file), ",")
        
        assert isinstance(result, dict)
        assert "AAPL" in result
        assert "GOOGL" in result


@pytest.fixture
def sample_csv_content():
    """示例 CSV 内容。"""
    return """date,open,high,low,close,volume
2023-01-01,100,105,98,104,1000
2023-01-02,104,109,102,108,1100"""


@pytest.fixture  
def sample_csv_file(temp_dir, sample_csv_content):
    """创建示例 CSV 文件。"""
    csv_file = temp_dir / "test.csv"
    with open(csv_file, 'w') as f:
        f.write(sample_csv_content)
    return csv_file
