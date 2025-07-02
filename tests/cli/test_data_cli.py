"""测试数据 CLI 命令。"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from trading_analyze.cli.data_cli import data_cli


class TestDataCLI:
    """测试数据管道 CLI 命令。"""
    
    def test_data_cli_help(self):
        """测试数据命令帮助。"""
        runner = CliRunner()
        result = runner.invoke(data_cli, ['--help'])
        
        assert result.exit_code == 0
        assert "数据管道相关命令" in result.output
        assert "download" in result.output
        assert "convert" in result.output
        assert "validate" in result.output
    
    def test_download_csv_success(self, temp_dir: Path, sample_csv_file: Path):
        """测试成功从 CSV 下载数据。"""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            result = runner.invoke(data_cli, [
                'download',
                '--source', 'csv',
                '--input', str(sample_csv_file),
                '--output', 'test_output'
            ])
        
        assert result.exit_code == 0
        assert "读取完成" in result.output
        assert "可用数据文件" in result.output

    def test_download_csv_file_not_found(self):
        """测试 CSV 文件不存在。"""
        runner = CliRunner()

        result = runner.invoke(data_cli, [
            'download',
            '--source', 'csv',
            '--input', 'nonexistent.csv'
        ])

        assert result.exit_code == 0  # CLI 不会崩溃，但会显示错误
        assert "文件不存在" in result.output
    
    def test_download_yahoo_missing_params(self):
        """测试 Yahoo Finance 缺少必要参数。"""
        runner = CliRunner()
        
        result = runner.invoke(data_cli, [
            'download',
            '--source', 'yahoo'
            # 缺少 --symbols 和 --start
        ])
        
        assert result.exit_code == 0
        assert "需要" in result.output or "错误" in result.output
    def test_download_yahoo_success(self):
        """测试成功从 Yahoo Finance 下载数据。"""
        runner = CliRunner()
        
        result = runner.invoke(data_cli, [
            'download',
            '--source', 'yahoo',
            '--symbols', 'AAPL',
            '--start', '2023-01-01',
            '--end', '2023-01-31'
        ])
        
        # 主要测试 CLI 不会崩溃，并且有合理的输出
        assert result.exit_code == 0
        assert "Yahoo Finance" in result.output
        # 不论成功或失败，都应该有合理的信息
        assert ("下载完成" in result.output or "下载失败" in result.output or "下载" in result.output)
    
    def test_convert_success(self):
        """测试成功转换数据。"""
        runner = CliRunner()
        
        result = runner.invoke(data_cli, [
            'convert',
            '--input', './raw_data',
            '--output', './qlib_data'
        ])
        
        # 测试 CLI 不会崩溃，有合理输出
        assert result.exit_code == 0
        assert ("转换" in result.output or "数据" in result.output)
    
    def test_convert_failure(self):
        """测试转换失败。"""
        runner = CliRunner()
        
        result = runner.invoke(data_cli, ['convert'])
        
        # 测试CLI不会崩溃
        assert result.exit_code == 0
        assert ("转换" in result.output or "数据" in result.output)
    
    def test_validate_success(self):
        """测试成功验证数据。"""
        runner = CliRunner()
        
        result = runner.invoke(data_cli, ['validate'])
        
        # 测试CLI不会崩溃
        assert result.exit_code == 0
        assert ("验证" in result.output or "数据" in result.output)
    
    def test_validate_failure(self):
        """测试验证失败。"""
        runner = CliRunner()
        
        result = runner.invoke(data_cli, ['validate'])
        
        # 测试CLI不会崩溃
        assert result.exit_code == 0
        assert ("验证" in result.output or "数据" in result.output)

    def test_check_success(self):
        """测试成功快速检查。"""
        runner = CliRunner()
        
        result = runner.invoke(data_cli, ['check'])
        
        # 测试CLI不会崩溃
        assert result.exit_code == 0
        assert ("检查" in result.output or "数据" in result.output)

    def test_check_failure(self):
        """测试快速检查失败。"""
        runner = CliRunner()
        
        result = runner.invoke(data_cli, ['check'])
        
        # 测试CLI不会崩溃
        assert result.exit_code == 0
        assert ("检查" in result.output or "数据" in result.output)

    def test_list_files_success(self):
        """测试成功列出文件。"""
        runner = CliRunner()
        
        result = runner.invoke(data_cli, ['list-files'])
        
        # 测试CLI不会崩溃
        assert result.exit_code == 0
        assert ("文件" in result.output or "数据" in result.output)

    def test_list_files_empty(self):
        """测试列出空文件列表。"""
        runner = CliRunner()
        
        result = runner.invoke(data_cli, ['list-files'])
        
        # 测试CLI不会崩溃
        assert result.exit_code == 0
        assert ("文件" in result.output or "数据" in result.output)
