"""测试数据 fixtures - 为测试提供标准化的测试数据。"""

import json
from pathlib import Path

import numpy as np
import pandas as pd


def create_sample_ohlcv_csv(file_path: Path, symbol: str = "TEST", days: int = 30):
    """创建示例 OHLCV CSV 文件。
    
    Args:
        file_path: 文件保存路径
        symbol: 股票代码
        days: 数据天数
    """
    np.random.seed(42)  # 确保可重现的测试数据
    
    # 生成日期序列
    dates = pd.date_range('2023-01-01', periods=days, freq='D')
    
    # 生成价格数据
    base_price = 100.0
    price_changes = np.random.normal(0, 0.02, days)  # 2% 日波动率
    
    close_prices = [base_price]
    for change in price_changes[1:]:
        close_prices.append(close_prices[-1] * (1 + change))
    
    # 生成 OHLC 数据
    data = []
    for i, (date, close) in enumerate(zip(dates, close_prices)):
        # 生成开盘价（基于前一日收盘价）
        if i == 0:
            open_price = close
        else:
            open_price = close_prices[i-1] * (1 + np.random.normal(0, 0.005))
        
        # 生成高低价
        daily_range = abs(np.random.normal(0, 0.01))
        high = max(open_price, close) * (1 + daily_range)
        low = min(open_price, close) * (1 - daily_range)
        
        # 生成成交量
        volume = int(np.random.uniform(800000, 2000000))
        
        data.append({
            'date': date.strftime('%Y-%m-%d'),
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close, 2),
            'volume': volume
        })
    
    # 保存为 CSV
    df = pd.DataFrame(data)
    df.to_csv(file_path, index=False)
    return df


def create_multi_stock_csv(base_dir: Path, symbols: list = None, days: int = 30):
    """创建多只股票的 CSV 文件。
    
    Args:
        base_dir: 基础目录
        symbols: 股票代码列表
        days: 数据天数
        
    Returns:
        Dict[str, Path]: 股票代码到文件路径的映射
    """
    if symbols is None:
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA']
    
    files = {}
    for symbol in symbols:
        file_path = base_dir / f"{symbol}_2023-01-01_2023-{1 + days//30:02d}-{days%30 + 1:02d}.csv"
        create_sample_ohlcv_csv(file_path, symbol, days)
        files[symbol] = file_path
    
    return files


def create_qlib_data_structure(base_dir: Path):
    """创建标准的 qlib 数据结构。
    
    Args:
        base_dir: 基础目录
        
    Returns:
        Path: qlib 数据目录路径
    """
    qlib_dir = base_dir / "qlib_data"
    
    # 创建目录结构
    (qlib_dir / "features").mkdir(parents=True, exist_ok=True)
    (qlib_dir / "instruments").mkdir(parents=True, exist_ok=True)
    
    # 创建示例数据
    symbols = ['TEST_A', 'TEST_B', 'TEST_C']
    dates = pd.date_range('2023-01-01', periods=10, freq='D')
    
    all_data = []
    for symbol in symbols:
        base_price = 100 if symbol == 'TEST_A' else (50 if symbol == 'TEST_B' else 200)
        
        for i, date in enumerate(dates):
            price = base_price + i * 2  # 简单的价格趋势
            
            all_data.append({
                'instrument': symbol,
                'datetime': date.strftime('%Y-%m-%d'),
                '$open': price,
                '$high': price * 1.02,
                '$low': price * 0.98,
                '$close': price * 1.01,
                '$volume': 1000000 + i * 100000
            })
    
    # 保存主数据文件
    data_df = pd.DataFrame(all_data)
    data_df.to_csv(qlib_dir / "features" / "data.csv", index=False)
    
    # 保存股票列表
    with open(qlib_dir / "instruments" / "all.txt", 'w') as f:
        for symbol in sorted(symbols):
            f.write(f"{symbol}\n")
    
    # 创建配置文件
    config = {
        'provider_uri': str(qlib_dir),
        'region': 'test',
        'market': 'test_market',
        'instruments_count': len(symbols),
        'data_range': {
            'start': '2023-01-01',
            'end': '2023-01-10'
        }
    }
    
    with open(qlib_dir / "config.json", 'w') as f:
        json.dump(config, f, indent=2)
    
    return qlib_dir


def create_invalid_csv_data():
    """创建各种无效的 CSV 数据用于测试。
    
    Returns:
        Dict[str, str]: 测试场景到 CSV 内容的映射
    """
    return {
        'missing_columns': """date,open,close
2023-01-01,100,105
2023-01-02,105,110""",
        
        'invalid_numbers': """date,open,high,low,close,volume
2023-01-01,100,105,98,104,1000
2023-01-02,invalid,110,102,108,1100
2023-01-03,102,abc,100,106,900""",
        
        'invalid_dates': """date,open,high,low,close,volume
invalid-date,100,105,98,104,1000
2023-02-30,101,106,99,105,1100
not-a-date,102,107,100,106,900""",
        
        'negative_prices': """date,open,high,low,close,volume
2023-01-01,100,105,98,104,1000
2023-01-02,-50,110,102,108,1100
2023-01-03,102,107,-10,106,900""",
        
        'zero_volume': """date,open,high,low,close,volume
2023-01-01,100,105,98,104,0
2023-01-02,101,106,99,105,0
2023-01-03,102,107,100,106,0""",
        
        'wrong_high_low': """date,open,high,low,close,volume
2023-01-01,100,95,98,104,1000
2023-01-02,101,106,110,105,1100
2023-01-03,102,107,108,106,900""",
        
        'empty_data': "",
        
        'header_only': "date,open,high,low,close,volume",
        
        'mixed_formats': """date,open,high,low,close,volume
2023-01-01,100.5,105.2,98.1,104.3,1000
01/02/2023,"101",106,99,"105",1100
2023-1-3,102.0,107,100,106,900"""
    }


def create_factor_test_data(n_stocks: int = 5, n_days: int = 100):
    """创建用于因子测试的模拟数据。
    
    Args:
        n_stocks: 股票数量
        n_days: 天数
        
    Returns:
        pd.DataFrame: 包含股票价格和因子数据的 DataFrame
    """
    np.random.seed(42)
    
    # 生成股票代码
    stocks = [f"STOCK_{i:03d}" for i in range(n_stocks)]
    dates = pd.date_range('2023-01-01', periods=n_days, freq='D')
    
    data = []
    for stock in stocks:
        # 生成该股票的价格序列
        base_price = np.random.uniform(50, 200)
        returns = np.random.normal(0.001, 0.02, n_days)  # 日收益率
        
        prices = [base_price]
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        # 为每一天生成数据
        for i, (date, price) in enumerate(zip(dates, prices)):
            # 生成因子值
            momentum_5d = (price / prices[max(0, i-5)] - 1) if i >= 5 else 0
            momentum_20d = (price / prices[max(0, i-20)] - 1) if i >= 20 else 0
            
            # 计算波动率（过去10天的收益率标准差）
            if i >= 10:
                recent_returns = [prices[j]/prices[j-1] - 1 for j in range(i-9, i+1)]
                volatility = np.std(recent_returns)
            else:
                volatility = 0
            
            # 计算相对强弱指数 (简化版)
            if i >= 14:
                gains = [max(0, prices[j]/prices[j-1] - 1) for j in range(i-13, i+1)]
                losses = [max(0, -(prices[j]/prices[j-1] - 1)) for j in range(i-13, i+1)]
                avg_gain = np.mean(gains)
                avg_loss = np.mean(losses)
                rsi = 100 - (100 / (1 + avg_gain / (avg_loss + 1e-8)))
            else:
                rsi = 50
            
            # 计算未来收益（用于验证因子有效性）
            if i < n_days - 1:
                forward_return_1d = prices[i+1] / price - 1
            else:
                forward_return_1d = 0
            
            if i < n_days - 5:
                forward_return_5d = prices[i+5] / price - 1
            else:
                forward_return_5d = 0
            
            data.append({
                'date': date,
                'stock': stock,
                'price': price,
                'momentum_5d': momentum_5d,
                'momentum_20d': momentum_20d,
                'volatility': volatility,
                'rsi': rsi,
                'forward_return_1d': forward_return_1d,
                'forward_return_5d': forward_return_5d,
                'market_cap': np.random.uniform(1e9, 1e11)  # 市值
            })
    
    return pd.DataFrame(data)


def create_performance_test_data():
    """创建用于性能测试的大数据集。
    
    Returns:
        pd.DataFrame: 大型测试数据集
    """
    # 生成较大的数据集用于性能测试
    return create_factor_test_data(n_stocks=100, n_days=1000)


def save_test_fixtures(base_dir: Path):
    """保存所有测试 fixtures 到指定目录。
    
    Args:
        base_dir: 基础目录
    """
    fixtures_dir = base_dir / "fixtures"
    fixtures_dir.mkdir(exist_ok=True)
    
    # 1. 创建基础 OHLCV 数据
    create_sample_ohlcv_csv(fixtures_dir / "sample_stock.csv")
    
    # 2. 创建多股票数据
    multi_stock_dir = fixtures_dir / "multi_stocks"
    multi_stock_dir.mkdir(exist_ok=True)
    create_multi_stock_csv(multi_stock_dir)
    
    # 3. 创建 qlib 数据结构
    create_qlib_data_structure(fixtures_dir)
    
    # 4. 创建无效数据样本
    invalid_data = create_invalid_csv_data()
    invalid_dir = fixtures_dir / "invalid_data"
    invalid_dir.mkdir(exist_ok=True)
    
    for name, content in invalid_data.items():
        with open(invalid_dir / f"{name}.csv", 'w') as f:
            f.write(content)
    
    # 5. 创建因子测试数据
    factor_data = create_factor_test_data()
    factor_data.to_csv(fixtures_dir / "factor_test_data.csv", index=False)
    
    # 6. 创建性能测试数据（可选，较大）
    # perf_data = create_performance_test_data()
    # perf_data.to_csv(fixtures_dir / "performance_test_data.csv", index=False)
    
    print(f"测试 fixtures 已保存到: {fixtures_dir}")


if __name__ == "__main__":
    # 如果直接运行此脚本，创建测试 fixtures
    from pathlib import Path
    
    current_dir = Path(__file__).parent
    save_test_fixtures(current_dir)
