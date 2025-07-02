"""测试配置和通用 fixtures。"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Generator
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest
import structlog

from trading_analyze.log_utils import configure_structlog


@pytest.fixture(scope="session", autouse=True)
def configure_logging():
    """配置测试日志。"""
    configure_structlog(log_level=30)  # WARNING level for tests


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """创建临时目录。"""
    temp_path = Path(tempfile.mkdtemp())
    try:
        yield temp_path
    finally:
        shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_ohlcv_data() -> pd.DataFrame:
    """创建示例 OHLCV 数据。"""
    dates = pd.date_range('2023-01-01', periods=10, freq='D')
    data = {
        'open': [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0],
        'high': [105.0, 106.0, 107.0, 108.0, 109.0, 110.0, 111.0, 112.0, 113.0, 114.0],
        'low': [98.0, 99.0, 100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0],
        'close': [104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0, 111.0, 112.0, 113.0],
        'volume': [1000000, 1100000, 900000, 1200000, 800000, 1500000, 1300000, 1000000, 1100000, 950000]
    }
    df = pd.DataFrame(data, index=dates)
    df.index.name = 'date'
    return df


@pytest.fixture
def sample_multi_stock_data() -> Dict[str, pd.DataFrame]:
    """创建多只股票的示例数据。"""
    dates = pd.date_range('2023-01-01', periods=5, freq='D')
    
    # 股票 A
    data_a = {
        'open': [100.0, 101.0, 102.0, 103.0, 104.0],
        'high': [105.0, 106.0, 107.0, 108.0, 109.0],
        'low': [98.0, 99.0, 100.0, 101.0, 102.0],
        'close': [104.0, 105.0, 106.0, 107.0, 108.0],
        'volume': [1000000, 1100000, 900000, 1200000, 800000]
    }
    df_a = pd.DataFrame(data_a, index=dates)
    df_a.index.name = 'date'
    
    # 股票 B
    data_b = {
        'open': [50.0, 51.0, 52.0, 53.0, 54.0],
        'high': [55.0, 56.0, 57.0, 58.0, 59.0],
        'low': [48.0, 49.0, 50.0, 51.0, 52.0],
        'close': [54.0, 55.0, 56.0, 57.0, 58.0],
        'volume': [2000000, 2100000, 1900000, 2200000, 1800000]
    }
    df_b = pd.DataFrame(data_b, index=dates)
    df_b.index.name = 'date'
    
    return {
        'STOCK_A': df_a,
        'STOCK_B': df_b
    }


@pytest.fixture
def sample_csv_file(temp_dir: Path, sample_ohlcv_data: pd.DataFrame) -> Path:
    """创建示例 CSV 文件。"""
    csv_file = temp_dir / "test_stock.csv"
    sample_ohlcv_data.to_csv(csv_file)
    return csv_file


@pytest.fixture
def sample_multi_csv_files(temp_dir: Path, sample_multi_stock_data: Dict[str, pd.DataFrame]) -> Dict[str, Path]:
    """创建多个示例 CSV 文件。"""
    files = {}
    for symbol, data in sample_multi_stock_data.items():
        csv_file = temp_dir / f"{symbol}_2023-01-01_2023-01-05.csv"
        data.to_csv(csv_file)
        files[symbol] = csv_file
    return files


@pytest.fixture
def invalid_csv_data() -> str:
    """创建无效的 CSV 数据。"""
    return """date,price,amount
2023-01-01,100,1000
2023-01-02,invalid,1100
2023-01-03,102,abc"""


@pytest.fixture
def incomplete_csv_data() -> str:
    """创建不完整的 CSV 数据（缺少必需列）。"""
    return """date,open,close
2023-01-01,100,104
2023-01-02,101,105
2023-01-03,102,106"""


@pytest.fixture
def mock_structlog(monkeypatch):
    """Mock structlog logger。"""
    mock_logger = Mock()
    mock_logger.info = Mock()
    mock_logger.warning = Mock()
    mock_logger.error = Mock()
    mock_logger.debug = Mock()
    
    monkeypatch.setattr("trading_analyze.data_pipeline.downloader.logger", mock_logger)
    monkeypatch.setattr("trading_analyze.data_pipeline.converter.logger", mock_logger)
    monkeypatch.setattr("trading_analyze.data_pipeline.validator.logger", mock_logger)
    
    return mock_logger


@pytest.fixture
def qlib_data_structure(temp_dir: Path) -> Path:
    """创建标准的 qlib 数据结构。"""
    qlib_dir = temp_dir / "qlib_data"
    
    # 创建目录结构
    (qlib_dir / "features").mkdir(parents=True)
    (qlib_dir / "instruments").mkdir(parents=True)
    
    # 创建示例数据文件
    data_content = """instrument,datetime,$open,$high,$low,$close,$volume
TEST_A,2023-01-01,100.0,105.0,98.0,104.0,1000000
TEST_A,2023-01-02,104.0,109.0,102.0,108.0,1100000
TEST_B,2023-01-01,50.0,55.0,48.0,54.0,2000000
TEST_B,2023-01-02,54.0,59.0,52.0,58.0,2100000"""
    
    with open(qlib_dir / "features" / "data.csv", 'w') as f:
        f.write(data_content)
    
    # 创建股票列表
    with open(qlib_dir / "instruments" / "all.txt", 'w') as f:
        f.write("TEST_A\nTEST_B\n")
    
    return qlib_dir


@pytest.fixture
def factor_test_data() -> pd.DataFrame:
    """创建用于因子测试的模拟数据。"""
    import numpy as np
    
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=50, freq='D')
    
    data = []
    for i, date in enumerate(dates):
        # 生成多只股票的数据
        for stock in ['STOCK_A', 'STOCK_B', 'STOCK_C']:
            base_price = 100 if stock == 'STOCK_A' else (50 if stock == 'STOCK_B' else 200)
            price = base_price + i + np.random.normal(0, 2)
            
            # 生成因子值
            momentum = np.random.normal(0, 0.1)
            rsi = np.random.uniform(20, 80)
            volatility = np.random.uniform(0.1, 0.3)
            
            # 生成未来收益
            forward_return = np.random.normal(0.001, 0.02)
            
            data.append({
                'date': date,
                'stock': stock,
                'price': price,
                'momentum': momentum,
                'rsi': rsi,
                'volatility': volatility,
                'forward_return': forward_return,
                'market_cap': np.random.uniform(1e9, 1e11)
            })
    
    return pd.DataFrame(data)


@pytest.fixture
def performance_test_data() -> pd.DataFrame:
    """创建大数据集用于性能测试。"""
    import numpy as np
    
    np.random.seed(42)
    n_stocks = 20
    n_days = 100
    
    stocks = [f"STOCK_{i:03d}" for i in range(n_stocks)]
    dates = pd.date_range('2023-01-01', periods=n_days, freq='D')
    
    data = []
    for stock in stocks:
        for date in dates:
            data.append({
                'date': date,
                'stock': stock,
                'price': np.random.uniform(50, 200),
                'volume': np.random.uniform(1000000, 5000000),
                'factor1': np.random.normal(0, 1),
                'factor2': np.random.normal(0, 1),
                'returns': np.random.normal(0.001, 0.02)
            })
    
    return pd.DataFrame(data)


@pytest.fixture
def invalid_data_scenarios() -> Dict[str, str]:
    """创建各种无效数据场景。"""
    return {
        'missing_columns': """date,open,close
2023-01-01,100,105
2023-01-02,105,110""",
        
        'invalid_numbers': """date,open,high,low,close,volume
2023-01-01,100,105,98,104,1000
2023-01-02,invalid,110,102,108,1100""",
        
        'negative_prices': """date,open,high,low,close,volume
2023-01-01,100,105,98,104,1000
2023-01-02,-50,110,102,108,1100""",
        
        'zero_volume': """date,open,high,low,close,volume
2023-01-01,100,105,98,104,0
2023-01-02,101,106,99,105,0""",
        
        'empty_data': "",
        
        'header_only': "date,open,high,low,close,volume"
    }


@pytest.fixture
def cli_runner():
    """创建 Click CLI 测试运行器。"""
    from click.testing import CliRunner
    return CliRunner()


@pytest.fixture
def mock_yahoo_data():
    """创建模拟的 Yahoo Finance 数据。"""
    dates = pd.date_range('2023-01-01', periods=10, freq='D')
    data = {
        'Open': [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0],
        'High': [105.0, 106.0, 107.0, 108.0, 109.0, 110.0, 111.0, 112.0, 113.0, 114.0],
        'Low': [98.0, 99.0, 100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0],
        'Close': [104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0, 111.0, 112.0, 113.0],
        'Volume': [1000000, 1100000, 900000, 1200000, 800000, 1500000, 1300000, 1000000, 1100000, 950000]
    }
    df = pd.DataFrame(data, index=dates)
    return df


@pytest.fixture
def mock_yfinance_download(monkeypatch, mock_yahoo_data):
    """Mock yfinance download 函数。"""
    def mock_download(*args, **kwargs):
        return mock_yahoo_data
    
    monkeypatch.setattr("yfinance.download", mock_download)
    return mock_download


@pytest.fixture
def sample_config_file(temp_dir: Path) -> Path:
    """创建示例配置文件。"""
    import json
    
    config = {
        "data_sources": {
            "yahoo": {
                "enabled": True,
                "default_period": "1y"
            },
            "csv": {
                "enabled": True,
                "default_directory": "./raw_data"
            }
        },
        "qlib_config": {
            "provider_uri": "./qlib_data",
            "region": "us",
            "market": "nasdaq"
        },
        "factor_settings": {
            "lookback_window": 20,
            "rebalance_frequency": "monthly",
            "factors": ["momentum", "rsi", "volatility"]
        }
    }
    
    config_file = temp_dir / "config.json"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    return config_file


@pytest.fixture
def error_scenarios():
    """创建各种错误场景用于测试异常处理。"""
    return {
        'file_not_found': FileNotFoundError("文件不存在"),
        'permission_denied': PermissionError("权限不足"),
        'invalid_format': ValueError("数据格式无效"),
        'network_error': ConnectionError("网络连接失败"),
        'timeout_error': TimeoutError("请求超时"),
        'memory_error': MemoryError("内存不足"),
        'type_error': TypeError("类型错误"),
        'key_error': KeyError("键不存在")
    }


@pytest.fixture
def sample_backtest_results():
    """创建示例回测结果数据。"""
    dates = pd.date_range('2023-01-01', periods=30, freq='D')
    
    results = {
        'daily_returns': pd.Series(
            np.random.normal(0.001, 0.02, 30), 
            index=dates, 
            name='returns'
        ),
        'cumulative_returns': None,  # 将在测试中计算
        'sharpe_ratio': 1.5,
        'max_drawdown': -0.15,
        'total_return': 0.08,
        'volatility': 0.18,
        'win_rate': 0.52
    }
    
    # 计算累积收益
    results['cumulative_returns'] = (1 + results['daily_returns']).cumprod() - 1
    
    return results
