"""数据验证器 - 验证数据质量和完整性。"""

import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import structlog

logger = structlog.get_logger()


class DataValidator:
    """数据验证器，检查数据质量和完整性。"""
    
    def __init__(self, data_dir: str = "./qlib_data"):
        """初始化验证器。
        
        Args:
            data_dir: qlib 数据目录
        """
        self.data_dir = Path(data_dir)
        
    def validate_qlib_data(self) -> Dict[str, any]:
        """验证 qlib 数据的完整性和质量。
        
        Returns:
            验证结果字典
        """
        logger.info("开始验证 qlib 数据", data_dir=str(self.data_dir))
        
        validation_results = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'stats': {},
            'data_quality': {},
        }
        
        try:
            # 检查目录结构
            structure_valid = self._validate_directory_structure()
            if not structure_valid:
                validation_results['is_valid'] = False
                validation_results['errors'].append("目录结构不完整")
            
            # 检查数据文件
            data_valid, data_stats = self._validate_data_files()
            if not data_valid:
                validation_results['is_valid'] = False
                validation_results['errors'].append("数据文件验证失败")
            else:
                validation_results['stats'] = data_stats
            
            # 数据质量检查
            quality_results = self._check_data_quality()
            validation_results['data_quality'] = quality_results
            
            if quality_results.get('critical_issues', 0) > 0:
                validation_results['is_valid'] = False
                
        except Exception as e:
            logger.error("数据验证过程出错", error=str(e))
            validation_results['is_valid'] = False
            validation_results['errors'].append(f"验证过程出错: {str(e)}")
        
        # 生成验证报告
        self._generate_validation_report(validation_results)
        
        logger.info("数据验证完成", 
                   is_valid=validation_results['is_valid'],
                   errors=len(validation_results['errors']),
                   warnings=len(validation_results['warnings']))
        
        return validation_results
    
    def _validate_directory_structure(self) -> bool:
        """验证目录结构。"""
        required_dirs = ['features', 'instruments']
        required_files = ['features/data.csv', 'instruments/all.txt']
        
        missing_dirs = []
        missing_files = []
        
        # 检查目录
        for dir_name in required_dirs:
            dir_path = self.data_dir / dir_name
            if not dir_path.exists():
                missing_dirs.append(dir_name)
        
        # 检查文件
        for file_path in required_files:
            full_path = self.data_dir / file_path
            if not full_path.exists():
                missing_files.append(file_path)
        
        if missing_dirs:
            logger.error("缺少必需目录", missing_dirs=missing_dirs)
        if missing_files:
            logger.error("缺少必需文件", missing_files=missing_files)
        
        return len(missing_dirs) == 0 and len(missing_files) == 0
    
    def _validate_data_files(self) -> Tuple[bool, Dict]:
        """验证数据文件。"""
        try:
            # 读取主数据文件
            data_file = self.data_dir / "features" / "data.csv"
            data = pd.read_csv(data_file)
            
            # 检查必需列
            required_columns = ['instrument', 'datetime', '$open', '$high', '$low', '$close', '$volume']
            missing_columns = [col for col in required_columns if col not in data.columns]
            
            if missing_columns:
                logger.error("数据文件缺少必需列", missing_columns=missing_columns)
                return False, {}
            
            # 读取股票列表
            instruments_file = self.data_dir / "instruments" / "all.txt"
            with open(instruments_file, 'r') as f:
                instruments_from_file = set(line.strip() for line in f if line.strip())
            
            # 检查数据中的股票与列表是否一致
            instruments_in_data = set(data['instrument'].unique())
            
            missing_in_data = instruments_from_file - instruments_in_data
            missing_in_file = instruments_in_data - instruments_from_file
            
            if missing_in_data:
                logger.warning("股票列表中有股票在数据中不存在", missing=list(missing_in_data))
            if missing_in_file:
                logger.warning("数据中有股票不在股票列表中", missing=list(missing_in_file))
            
            # 统计信息
            data['datetime'] = pd.to_datetime(data['datetime'])
            stats = {
                'total_records': len(data),
                'instruments_count': len(instruments_in_data),
                'date_range': {
                    'start': data['datetime'].min().isoformat(),
                    'end': data['datetime'].max().isoformat(),
                    'trading_days': len(data['datetime'].dt.date.unique())
                },
                'missing_in_data': len(missing_in_data),
                'missing_in_file': len(missing_in_file)
            }
            
            logger.info("数据文件验证完成", **stats)
            return True, stats
            
        except Exception as e:
            logger.error("数据文件验证失败", error=str(e))
            return False, {}
    
    def _check_data_quality(self) -> Dict:
        """检查数据质量。"""
        try:
            data_file = self.data_dir / "features" / "data.csv"
            data = pd.read_csv(data_file)
            data['datetime'] = pd.to_datetime(data['datetime'])
            
            quality_results = {
                'critical_issues': 0,
                'warnings': 0,
                'issues_detail': []
            }
            
            # 检查空值
            null_counts = data.isnull().sum()
            if null_counts.sum() > 0:
                quality_results['critical_issues'] += 1
                quality_results['issues_detail'].append({
                    'type': 'critical',
                    'issue': 'null_values',
                    'detail': null_counts[null_counts > 0].to_dict()
                })
            
            # 检查价格数据合理性
            price_columns = ['$open', '$high', '$low', '$close']
            
            # 负价格检查
            for col in price_columns:
                negative_count = (data[col] <= 0).sum()
                if negative_count > 0:
                    quality_results['critical_issues'] += 1
                    quality_results['issues_detail'].append({
                        'type': 'critical',
                        'issue': 'negative_prices',
                        'column': col,
                        'count': negative_count
                    })
            
            # 零成交量检查
            zero_volume_count = (data['$volume'] <= 0).sum()
            if zero_volume_count > 0:
                quality_results['warnings'] += 1
                quality_results['issues_detail'].append({
                    'type': 'warning',
                    'issue': 'zero_volume',
                    'count': zero_volume_count
                })
            
            # 高低价逻辑检查
            illogical_prices = (
                (data['$high'] < data['$low']) |
                (data['$high'] < data['$open']) |
                (data['$high'] < data['$close']) |
                (data['$low'] > data['$open']) |
                (data['$low'] > data['$close'])
            ).sum()
            
            if illogical_prices > 0:
                quality_results['critical_issues'] += 1
                quality_results['issues_detail'].append({
                    'type': 'critical',
                    'issue': 'illogical_ohlc',
                    'count': illogical_prices
                })
            
            # 数据连续性检查 (按股票)
            discontinuity_issues = []
            for instrument in data['instrument'].unique():
                instrument_data = data[data['instrument'] == instrument].copy()
                instrument_data = instrument_data.sort_values('datetime')
                
                # 检查日期间隔 (简单检查，假设工作日数据)
                date_diff = instrument_data['datetime'].diff().dt.days
                large_gaps = (date_diff > 7).sum()  # 超过一周的间隔
                
                if large_gaps > 0:
                    discontinuity_issues.append({
                        'instrument': instrument,
                        'large_gaps': large_gaps
                    })
            
            if discontinuity_issues:
                quality_results['warnings'] += 1
                quality_results['issues_detail'].append({
                    'type': 'warning',
                    'issue': 'data_discontinuity',
                    'instruments': discontinuity_issues
                })
            
            # 异常波动检查 (价格变化超过30%的情况)
            extreme_changes = []
            for instrument in data['instrument'].unique():
                instrument_data = data[data['instrument'] == instrument].copy()
                instrument_data = instrument_data.sort_values('datetime')
                
                price_change = instrument_data['$close'].pct_change().abs()
                extreme_count = (price_change > 0.3).sum()
                
                if extreme_count > 0:
                    extreme_changes.append({
                        'instrument': instrument,
                        'extreme_changes': extreme_count
                    })
            
            if extreme_changes:
                quality_results['warnings'] += 1
                quality_results['issues_detail'].append({
                    'type': 'warning',
                    'issue': 'extreme_price_changes',
                    'instruments': extreme_changes
                })
            
            logger.info("数据质量检查完成",
                       critical_issues=quality_results['critical_issues'],
                       warnings=quality_results['warnings'])
            
            return quality_results
            
        except Exception as e:
            logger.error("数据质量检查失败", error=str(e))
            return {
                'critical_issues': 1,
                'warnings': 0,
                'issues_detail': [{'type': 'critical', 'issue': 'quality_check_failed', 'error': str(e)}]
            }
    
    def _generate_validation_report(self, results: Dict):
        """生成验证报告。"""
        try:
            report_file = self.data_dir / "validation_report.txt"
            
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write("=== QLIB 数据验证报告 ===\n\n")
                f.write(f"验证时间: {pd.Timestamp.now()}\n")
                f.write(f"数据目录: {self.data_dir}\n\n")
                
                f.write(f"总体状态: {'✓ 通过' if results['is_valid'] else '✗ 失败'}\n")
                f.write(f"错误数量: {len(results['errors'])}\n")
                f.write(f"警告数量: {len(results['warnings'])}\n\n")
                
                if results['errors']:
                    f.write("=== 错误信息 ===\n")
                    for error in results['errors']:
                        f.write(f"- {error}\n")
                    f.write("\n")
                
                if results['warnings']:
                    f.write("=== 警告信息 ===\n")
                    for warning in results['warnings']:
                        f.write(f"- {warning}\n")
                    f.write("\n")
                
                if results['stats']:
                    f.write("=== 数据统计 ===\n")
                    stats = results['stats']
                    f.write(f"总记录数: {stats.get('total_records', 'N/A')}\n")
                    f.write(f"股票数量: {stats.get('instruments_count', 'N/A')}\n")
                    if 'date_range' in stats:
                        dr = stats['date_range']
                        f.write(f"日期范围: {dr.get('start', 'N/A')} 至 {dr.get('end', 'N/A')}\n")
                        f.write(f"交易日数: {dr.get('trading_days', 'N/A')}\n")
                    f.write("\n")
                
                if results['data_quality']['issues_detail']:
                    f.write("=== 数据质量详情 ===\n")
                    for issue in results['data_quality']['issues_detail']:
                        f.write(f"类型: {issue['type']}\n")
                        f.write(f"问题: {issue['issue']}\n")
                        if 'count' in issue:
                            f.write(f"数量: {issue['count']}\n")
                        if 'detail' in issue:
                            f.write(f"详情: {issue['detail']}\n")
                        f.write("\n")
            
            logger.info("验证报告已生成", report_file=str(report_file))
            
        except Exception as e:
            logger.error("生成验证报告失败", error=str(e))
    
    def quick_check(self) -> bool:
        """快速检查数据是否可用。
        
        Returns:
            数据是否基本可用
        """
        try:
            # 检查关键文件是否存在
            data_file = self.data_dir / "features" / "data.csv"
            instruments_file = self.data_dir / "instruments" / "all.txt"
            
            if not (data_file.exists() and instruments_file.exists()):
                return False
            
            # 简单读取测试
            data = pd.read_csv(data_file, nrows=10)
            required_columns = ['instrument', 'datetime', '$open', '$high', '$low', '$close', '$volume']
            
            return all(col in data.columns for col in required_columns)
            
        except Exception:
            return False
