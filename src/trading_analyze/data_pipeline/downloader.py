"""数据下载器 - 从各种数据源下载股票数据。"""

import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import structlog
import yfinance as yf

logger = structlog.get_logger()


class DataDownloader:
    """数据下载器，支持多种数据源。"""
    
    def __init__(self, output_dir: str = "./raw_data"):
        """初始化下载器。
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def download_yahoo_finance(
        self,
        symbols: List[str],
        start_date: str,
        end_date: Optional[str] = None,
        interval: str = "1d"
    ) -> Dict[str, pd.DataFrame]:
        """从 Yahoo Finance 下载数据。
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)，默认为今天
            interval: 数据间隔 (1d, 1h 等)
            
        Returns:
            下载的数据字典 {symbol: DataFrame}
        """
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
            
        logger.info("开始下载 Yahoo Finance 数据", 
                   symbols=symbols, start=start_date, end=end_date)
        
        results = {}
        failed_symbols = []
        
        for symbol in symbols:
            max_retries = 3
            retry_delay = 2  # 秒
            
            for attempt in range(max_retries):
                try:
                    logger.info("下载股票数据", symbol=symbol, attempt=attempt+1)
                    ticker = yf.Ticker(symbol)
                    data = ticker.history(
                        start=start_date,
                        end=end_date,
                        interval=interval,
                        auto_adjust=True,  # 自动调整分红配股
                        prepost=False     # 不包含盘前盘后
                    )
                    
                    if data.empty:
                        logger.warning("无数据", symbol=symbol)
                        failed_symbols.append(symbol)
                        break
                        
                    # 清理数据
                    data = data.dropna()
                    data.index.name = "date"
                    
                    # 重命名列为标准格式
                    data.columns = [col.lower() for col in data.columns]
                    if 'adj close' in data.columns:
                        data = data.drop(columns=['adj close'])
                        
                    results[symbol] = data
                    
                    # 保存到文件
                    output_file = self.output_dir / f"{symbol}_{start_date}_{end_date}.csv"
                    data.to_csv(output_file)
                    logger.info("数据已保存", symbol=symbol, file=str(output_file), records=len(data))
                    break  # 成功，退出重试循环
                    
                except Exception as e:
                    error_msg = str(e)
                    if "rate limit" in error_msg.lower() or "too many requests" in error_msg.lower():
                        if attempt < max_retries - 1:
                            logger.warning("遇到限流，等待重试", symbol=symbol, attempt=attempt+1, delay=retry_delay)
                            time.sleep(retry_delay)
                            retry_delay *= 2  # 指数退避
                            continue
                    
                    logger.error("下载失败", symbol=symbol, error=error_msg, attempt=attempt+1)
                    if attempt == max_retries - 1:
                        failed_symbols.append(symbol)
            
            # 请求间添加小延迟避免限流
            if len(symbols) > 1:
                time.sleep(1)
                
        if failed_symbols:
            logger.warning("部分股票下载失败", failed_symbols=failed_symbols)
            
        logger.info("下载完成", 
                   total=len(symbols), 
                   success=len(results), 
                   failed=len(failed_symbols))
        
        return results
    
    def download_from_csv(self, csv_file: str) -> Dict[str, pd.DataFrame]:
        """从 CSV 文件读取数据。
        
        Args:
            csv_file: CSV 文件路径
            
        Returns:
            读取的数据字典
        """
        logger.info("从 CSV 文件读取数据", file=csv_file)
        
        try:
            data = pd.read_csv(csv_file)
            
            # 基本数据验证
            required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
            if 'symbol' in data.columns:
                # 多股票格式
                results = {}
                for symbol in data['symbol'].unique():
                    symbol_data = data[data['symbol'] == symbol].copy()
                    symbol_data = symbol_data.set_index('date')
                    symbol_data = symbol_data[required_columns[1:]]  # 除了 date
                    results[symbol] = symbol_data
                    
                    # 保存单独文件
                    output_file = self.output_dir / f"{symbol}_from_csv.csv"
                    symbol_data.to_csv(output_file)
                    
                logger.info("CSV 数据读取完成", symbols=len(results))
                return results
            else:
                # 单股票格式
                if not all(col in data.columns for col in required_columns):
                    missing = [col for col in required_columns if col not in data.columns]
                    raise ValueError(f"CSV 文件缺少必需列: {missing}")
                    
                data = data.set_index('date')
                data = data[required_columns[1:]]  # 除了 date
                
                # 使用文件名作为股票代码
                symbol = Path(csv_file).stem
                results = {symbol: data}
                
                # 保存标准化文件
                output_file = self.output_dir / f"{symbol}_from_csv.csv"
                data.to_csv(output_file)
                
                logger.info("CSV 数据读取完成", symbol=symbol, records=len(data))
                return results
                
        except Exception as e:
            logger.error("CSV 文件读取失败", file=csv_file, error=str(e))
            raise
    
    def list_available_data(self) -> List[str]:
        """列出已下载的数据文件。
        
        Returns:
            数据文件列表
        """
        if not self.output_dir.exists():
            return []
            
        csv_files = list(self.output_dir.glob("*.csv"))
        return [f.name for f in csv_files]
