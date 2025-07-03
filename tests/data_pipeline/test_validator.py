"""测试数据验证器。"""

from pathlib import Path

import pandas as pd
import pytest

from trading_analyze.data_pipeline.validator import DataValidator


class TestDataValidator:
    """测试 DataValidator 类。"""
    
    def test_init(self, temp_dir: Path):
        """测试初始化。"""
        validator = DataValidator(str(temp_dir / "qlib_data"))
        assert validator.data_dir == temp_dir / "qlib_data"
    
    def test_init_default_dir(self):
        """测试默认目录。"""
        validator = DataValidator()
        assert str(validator.data_dir) == "qlib_data"
    
    def test_validate_directory_structure_valid(self, qlib_data_structure: Path):
        """测试有效的目录结构。"""
        validator = DataValidator(str(qlib_data_structure))
        
        result = validator._validate_directory_structure()
        
        assert result is True
    
    def test_validate_directory_structure_missing_dirs(self, temp_dir: Path):
        """测试缺少目录的情况。"""
        qlib_dir = temp_dir / "qlib_data"
        qlib_dir.mkdir()
        # 只创建一个目录
        (qlib_dir / "features").mkdir()
        
        validator = DataValidator(str(qlib_dir))
        result = validator._validate_directory_structure()
        
        assert result is False
    
    def test_validate_directory_structure_missing_files(self, temp_dir: Path):
        """测试缺少文件的情况。"""
        qlib_dir = temp_dir / "qlib_data"
        (qlib_dir / "features").mkdir(parents=True)
        (qlib_dir / "instruments").mkdir()
        # 只创建一个文件
        (qlib_dir / "features" / "data.csv").touch()
        
        validator = DataValidator(str(qlib_dir))
        result = validator._validate_directory_structure()
        
        assert result is False
    
    def test_validate_data_files_valid(self, qlib_data_structure: Path):
        """测试有效的数据文件。"""
        validator = DataValidator(str(qlib_data_structure))
        
        valid, stats = validator._validate_data_files()
        
        assert valid is True
        assert stats['total_records'] == 4
        assert stats['instruments_count'] == 2
        assert 'date_range' in stats
    
    def test_validate_data_files_missing_columns(self, temp_dir: Path):
        """测试缺少必需列的数据文件。"""
        qlib_dir = temp_dir / "qlib_data"
        (qlib_dir / "features").mkdir(parents=True)
        (qlib_dir / "instruments").mkdir()
        
        # 创建缺少列的数据文件
        data_content = """instrument,datetime,$open,$high,$low
TEST_A,2023-01-01,100.0,105.0,98.0"""
        
        with open(qlib_dir / "features" / "data.csv", 'w') as f:
            f.write(data_content)
        
        with open(qlib_dir / "instruments" / "all.txt", 'w') as f:
            f.write("TEST_A\n")
        
        validator = DataValidator(str(qlib_dir))
        valid, stats = validator._validate_data_files()
        
        assert valid is False
    
    def test_validate_data_files_inconsistent_instruments(self, temp_dir: Path):
        """测试股票列表与数据不一致的情况。"""
        qlib_dir = temp_dir / "qlib_data"
        (qlib_dir / "features").mkdir(parents=True)
        (qlib_dir / "instruments").mkdir()
        
        # 数据中只有 TEST_A
        data_content = """instrument,datetime,$open,$high,$low,$close,$volume
TEST_A,2023-01-01,100.0,105.0,98.0,104.0,1000000"""
        
        with open(qlib_dir / "features" / "data.csv", 'w') as f:
            f.write(data_content)
        
        # 但是股票列表包含 TEST_A 和 TEST_B
        with open(qlib_dir / "instruments" / "all.txt", 'w') as f:
            f.write("TEST_A\nTEST_B\n")
        
        validator = DataValidator(str(qlib_dir))
        valid, stats = validator._validate_data_files()
        
        assert valid is True  # 这种情况不是致命错误
        assert stats['missing_in_data'] == 1  # TEST_B 在数据中不存在
    
    def test_check_data_quality_valid(self, qlib_data_structure: Path):
        """测试有效数据的质量检查。"""
        validator = DataValidator(str(qlib_data_structure))
        
        quality_results = validator._check_data_quality()
        
        assert quality_results['critical_issues'] == 0
        assert quality_results['warnings'] >= 0  # 可能有警告但不是严重问题
    
    def test_check_data_quality_null_values(self, temp_dir: Path):
        """测试包含空值的数据质量检查。"""
        qlib_dir = temp_dir / "qlib_data"
        (qlib_dir / "features").mkdir(parents=True)
        (qlib_dir / "instruments").mkdir()
        
        # 创建包含空值的数据
        data_content = """instrument,datetime,$open,$high,$low,$close,$volume
TEST_A,2023-01-01,100.0,,98.0,104.0,1000000
TEST_A,2023-01-02,104.0,109.0,102.0,108.0,1100000"""
        
        with open(qlib_dir / "features" / "data.csv", 'w') as f:
            f.write(data_content)
        
        with open(qlib_dir / "instruments" / "all.txt", 'w') as f:
            f.write("TEST_A\n")
        
        validator = DataValidator(str(qlib_dir))
        quality_results = validator._check_data_quality()
        
        assert quality_results['critical_issues'] > 0
        # 检查是否有空值问题的详情
        issues = quality_results['issues_detail']
        null_issues = [i for i in issues if i['issue'] == 'null_values']
        assert len(null_issues) > 0
    
    def test_check_data_quality_negative_prices(self, temp_dir: Path):
        """测试包含负价格的数据质量检查。"""
        qlib_dir = temp_dir / "qlib_data"
        (qlib_dir / "features").mkdir(parents=True)
        (qlib_dir / "instruments").mkdir()
        
        # 创建包含负价格的数据
        data_content = """instrument,datetime,$open,$high,$low,$close,$volume
TEST_A,2023-01-01,-100.0,105.0,98.0,104.0,1000000
TEST_A,2023-01-02,104.0,109.0,102.0,108.0,1100000"""
        
        with open(qlib_dir / "features" / "data.csv", 'w') as f:
            f.write(data_content)
        
        with open(qlib_dir / "instruments" / "all.txt", 'w') as f:
            f.write("TEST_A\n")
        
        validator = DataValidator(str(qlib_dir))
        quality_results = validator._check_data_quality()
        
        assert quality_results['critical_issues'] > 0
        # 检查是否有负价格问题的详情
        issues = quality_results['issues_detail']
        negative_issues = [i for i in issues if i['issue'] == 'negative_prices']
        assert len(negative_issues) > 0
    
    def test_check_data_quality_zero_volume(self, temp_dir: Path):
        """测试包含零成交量的数据质量检查。"""
        qlib_dir = temp_dir / "qlib_data"
        (qlib_dir / "features").mkdir(parents=True)
        (qlib_dir / "instruments").mkdir()
        
        # 创建包含零成交量的数据
        data_content = """instrument,datetime,$open,$high,$low,$close,$volume
TEST_A,2023-01-01,100.0,105.0,98.0,104.0,0
TEST_A,2023-01-02,104.0,109.0,102.0,108.0,1100000"""
        
        with open(qlib_dir / "features" / "data.csv", 'w') as f:
            f.write(data_content)
        
        with open(qlib_dir / "instruments" / "all.txt", 'w') as f:
            f.write("TEST_A\n")
        
        validator = DataValidator(str(qlib_dir))
        quality_results = validator._check_data_quality()
        
        assert quality_results['warnings'] > 0
        # 检查是否有零成交量问题的详情
        issues = quality_results['issues_detail']
        volume_issues = [i for i in issues if i['issue'] == 'zero_volume']
        assert len(volume_issues) > 0
    
    def test_check_data_quality_illogical_ohlc(self, temp_dir: Path):
        """测试包含不合理 OHLC 的数据质量检查。"""
        qlib_dir = temp_dir / "qlib_data"
        (qlib_dir / "features").mkdir(parents=True)
        (qlib_dir / "instruments").mkdir()
        
        # 创建 OHLC 逻辑错误的数据（高价低于低价）
        data_content = """instrument,datetime,$open,$high,$low,$close,$volume
TEST_A,2023-01-01,100.0,95.0,98.0,104.0,1000000
TEST_A,2023-01-02,104.0,109.0,102.0,108.0,1100000"""
        
        with open(qlib_dir / "features" / "data.csv", 'w') as f:
            f.write(data_content)
        
        with open(qlib_dir / "instruments" / "all.txt", 'w') as f:
            f.write("TEST_A\n")
        
        validator = DataValidator(str(qlib_dir))
        quality_results = validator._check_data_quality()
        
        assert quality_results['critical_issues'] > 0
        # 检查是否有 OHLC 逻辑问题的详情
        issues = quality_results['issues_detail']
        ohlc_issues = [i for i in issues if i['issue'] == 'illogical_ohlc']
        assert len(ohlc_issues) > 0
    
    def test_validate_qlib_data_valid(self, qlib_data_structure: Path):
        """测试完整的数据验证（有效数据）。"""
        validator = DataValidator(str(qlib_data_structure))
        
        results = validator.validate_qlib_data()
        
        assert results['is_valid'] is True
        assert len(results['errors']) == 0
        assert 'stats' in results
        assert 'data_quality' in results
        
        # 检查是否生成了报告文件
        report_file = qlib_data_structure / "validation_report.txt"
        assert report_file.exists()
    
    def test_validate_qlib_data_invalid(self, temp_dir: Path):
        """测试完整的数据验证（无效数据）。"""
        qlib_dir = temp_dir / "qlib_data"
        qlib_dir.mkdir()
        # 不创建必需的目录结构
        
        validator = DataValidator(str(qlib_dir))
        results = validator.validate_qlib_data()
        
        assert results['is_valid'] is False
        assert len(results['errors']) > 0
    
    def test_quick_check_valid(self, qlib_data_structure: Path):
        """测试快速检查（有效数据）。"""
        validator = DataValidator(str(qlib_data_structure))
        
        result = validator.quick_check()
        
        assert result is True
    
    def test_quick_check_missing_files(self, temp_dir: Path):
        """测试快速检查（缺少文件）。"""
        qlib_dir = temp_dir / "qlib_data"
        qlib_dir.mkdir()
        
        validator = DataValidator(str(qlib_dir))
        result = validator.quick_check()
        
        assert result is False
    
    def test_quick_check_invalid_data_format(self, temp_dir: Path):
        """测试快速检查（数据格式错误）。"""
        qlib_dir = temp_dir / "qlib_data"
        (qlib_dir / "features").mkdir(parents=True)
        (qlib_dir / "instruments").mkdir()
        
        # 创建格式错误的数据文件
        with open(qlib_dir / "features" / "data.csv", 'w') as f:
            f.write("invalid,csv,format\n")
        
        with open(qlib_dir / "instruments" / "all.txt", 'w') as f:
            f.write("TEST_A\n")
        
        validator = DataValidator(str(qlib_dir))
        result = validator.quick_check()
        
        assert result is False
    
    def test_generate_validation_report(self, temp_dir: Path):
        """测试生成验证报告。"""
        qlib_dir = temp_dir / "qlib_data"
        qlib_dir.mkdir()
        
        validator = DataValidator(str(qlib_dir))
        
        # 创建测试结果
        test_results = {
            'is_valid': False,
            'errors': ['测试错误'],
            'warnings': ['测试警告'],
            'stats': {
                'total_records': 100,
                'instruments_count': 10,
                'date_range': {
                    'start': '2023-01-01T00:00:00',
                    'end': '2023-12-31T00:00:00',
                    'trading_days': 250
                }
            },
            'data_quality': {
                'issues_detail': [
                    {
                        'type': 'critical',
                        'issue': 'test_issue',
                        'count': 5
                    }
                ]
            }
        }
        
        validator._generate_validation_report(test_results)
        
        # 检查报告文件是否生成
        report_file = qlib_dir / "validation_report.txt"
        assert report_file.exists()
        
        # 检查报告内容
        with open(report_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "QLIB 数据验证报告" in content
        assert "测试错误" in content
        assert "测试警告" in content
        assert "总记录数: 100" in content
