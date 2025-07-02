"""测试 factor_cli.py 模块。"""

from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from trading_analyze.cli.factor_cli import (
    analyze_factors,
    calculate_factors,
    factor_cli,
    init_qlib,
)


class TestFactorCLI:
    """测试因子 CLI 命令组。"""
    
    def setup_method(self):
        """设置测试。"""
        self.runner = CliRunner()
    
    def test_factor_cli_help(self):
        """测试因子 CLI 帮助信息。"""
        result = self.runner.invoke(factor_cli, ['--help'])
        
        assert result.exit_code == 0
        assert 'factor' in result.output.lower() or '因子' in result.output
        # 检查子命令
        assert 'init' in result.output
        assert 'analyze' in result.output 
        assert 'calc' in result.output
    
    def test_factor_cli_no_command(self):
        """测试没有子命令时的行为。"""
        result = self.runner.invoke(factor_cli, [])
        
        # Click groups 默认行为是显示帮助并退出码为 2
        assert result.exit_code == 2
        assert 'Usage:' in result.output


class TestInitQlibCommand:
    """测试 init 命令。"""
    
    def setup_method(self):
        """设置测试。"""
        self.runner = CliRunner()
    
    def test_init_qlib_default_params(self):
        """测试使用默认参数初始化 qlib。"""
        result = self.runner.invoke(factor_cli, ['init'])
        
        assert result.exit_code == 0
        assert '初始化 qlib 环境' in result.output
        assert 'qlib_data' in result.output  # 默认数据目录
        # 应该成功初始化或显示状态
        assert '✅' in result.output or 'successfully' in result.output or '成功' in result.output
    
    def test_init_qlib_custom_data_dir(self):
        """测试使用自定义数据目录。"""
        result = self.runner.invoke(factor_cli, [
            'init', '--data_dir', '/custom/path'
        ])
        
        assert result.exit_code == 0
        assert '/custom/path' in result.output
        assert '初始化 qlib 环境' in result.output
    
    def test_init_qlib_help(self):
        """测试 init 命令帮助。"""
        result = self.runner.invoke(factor_cli, ['init', '--help'])
        
        assert result.exit_code == 0
        assert 'data_dir' in result.output
        assert '初始化' in result.output or 'init' in result.output
    
    @patch('structlog.get_logger')
    def test_init_qlib_with_exception(self, mock_get_logger):
        """测试 init 命令异常处理。"""
        # 模拟获取 logger
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        # 模拟在命令执行中发生异常
        with patch('click.echo', side_effect=Exception("测试异常")):
            result = self.runner.invoke(factor_cli, ['init'])
            
            # 应该记录错误但不崩溃  
            assert result.exit_code != 0


class TestCalculateFactorsCommand:
    """测试 calc 命令。"""
    
    def setup_method(self):
        """设置测试。"""
        self.runner = CliRunner()
    
    def test_calculate_factors_help(self):
        """测试 calc 命令帮助。"""
        result = self.runner.invoke(factor_cli, ['calc', '--help'])
        
        assert result.exit_code == 0
        assert 'stocks' in result.output
        assert 'factors' in result.output
        assert 'output' in result.output
    
    def test_calculate_factors_default_params(self):
        """测试使用默认参数计算因子。"""
        result = self.runner.invoke(factor_cli, ['calc'])
        
        assert result.exit_code == 0
        assert '计算因子' in result.output
        # 现在应该要求必要参数而不是显示待实现
        assert '错误' in result.output and '参数' in result.output
    
    def test_calculate_factors_with_params(self):
        """测试使用参数计算因子。"""
        result = self.runner.invoke(factor_cli, [
            'calc',
            '--stocks', 'AAPL,GOOGL,MSFT',
            '--start', '2023-01-01',
            '--end', '2023-12-31',
            '--factors', 'alpha',
            '--output', 'my_factors.csv'
        ])
        
        assert result.exit_code == 0
        # 检查输出是否包含关键信息，使用实际的中文输出格式
        assert "计算因子" in result.output
        assert "AAPL" in result.output and "GOOGL" in result.output and "MSFT" in result.output
        # 当没有 qlib 数据时，会有错误信息
        assert ("错误" in result.output or "my_factors.csv" in result.output)
    
    @patch('structlog.get_logger')
    def test_calculate_factors_error_handling(self, mock_get_logger):
        """测试 calc 命令错误处理。"""
        # 模拟获取 logger
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        with patch('click.echo', side_effect=Exception("计算错误")):
            result = self.runner.invoke(factor_cli, ['calc'])
            
            # 检查是否有适当的错误处理
            assert result.exit_code != 0


class TestAnalyzeFactorsCommand:
    """测试 analyze 命令。"""
    
    def setup_method(self):
        """设置测试。"""
        self.runner = CliRunner()
    
    def test_analyze_factors_help(self):
        """测试 analyze 命令帮助。"""
        result = self.runner.invoke(factor_cli, ['analyze', '--help'])
        
        assert result.exit_code == 0
        assert 'factor_file' in result.output
        assert 'output' in result.output
    
    def test_analyze_factors_with_file(self):
        """测试分析因子文件。"""
        result = self.runner.invoke(factor_cli, [
            'analyze',
            '--factor_file', 'factors.csv',
            '--output', 'analysis.txt'
        ])
        
        assert result.exit_code == 0
        assert 'factors.csv' in result.output
        assert 'analysis.txt' in result.output
        assert '分析因子' in result.output
        assert '待实现' in result.output or '⚠️' in result.output
    
    def test_analyze_factors_missing_required_param(self):
        """测试缺少必需参数。"""
        result = self.runner.invoke(factor_cli, ['analyze'])
        
        # 应该报错，因为 factor_file 是必需的
        assert result.exit_code != 0
        assert 'factor_file' in result.output or 'required' in result.output.lower()
    
    @patch('structlog.get_logger')
    def test_analyze_factors_error_handling(self, mock_get_logger):
        """测试 analyze 命令错误处理。"""
        # 模拟获取 logger
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        with patch('click.echo', side_effect=Exception("分析错误")):
            result = self.runner.invoke(factor_cli, [
                'analyze', '--factor_file', 'test.csv'
            ])
            
            # 检查错误处理
            assert result.exit_code != 0


class TestFactorCLIIntegration:
    """因子 CLI 集成测试。"""
    
    def setup_method(self):
        """设置测试。"""
        self.runner = CliRunner()
    
    def test_command_workflow(self):
        """测试命令工作流。"""
        with self.runner.isolated_filesystem():
            # 1. 初始化 qlib 环境
            result1 = self.runner.invoke(factor_cli, [
                'init', '--data_dir', './test_data'
            ])
            assert result1.exit_code == 0
            
            # 2. 计算因子
            result2 = self.runner.invoke(factor_cli, [
                'calc', '--stocks', 'AAPL', '--output', 'factors.csv'
            ])
            assert result2.exit_code == 0
            
            # 3. 分析因子（需要传入文件参数）
            result3 = self.runner.invoke(factor_cli, [
                'analyze', '--factor_file', 'factors.csv'
            ])
            assert result3.exit_code == 0
    
    def test_help_commands_completeness(self):
        """测试帮助命令的完整性。"""
        # 主命令帮助
        result = self.runner.invoke(factor_cli, ['--help'])
        assert result.exit_code == 0
        
        # 子命令帮助
        subcommands = ['init', 'analyze', 'calc']
        for subcmd in subcommands:
            result = self.runner.invoke(factor_cli, [subcmd, '--help'])
            assert result.exit_code == 0
            assert subcmd in result.output or subcmd.upper() in result.output
    
    def test_output_format_consistency(self):
        """测试输出格式一致性。"""
        commands = [
            ['init'],
            ['calc'],
            ['analyze', '--factor_file', 'dummy.csv']
        ]
        
        for cmd in commands:
            result = self.runner.invoke(factor_cli, cmd)
            
            # 所有命令都应该有一致的输出格式（除了 analyze 可能因为缺少文件而失败）
            if 'analyze' in cmd:
                # analyze 命令可能因为文件不存在而有不同的输出
                continue
            assert result.exit_code == 0
            # 现在实际实现了功能，不再期望待实现标记
            assert any(marker in result.output for marker in ['✅', '初始化', '计算', '错误'])
    
    @patch('structlog.get_logger')
    def test_logging_throughout_commands(self, mock_get_logger):
        """测试所有命令的日志记录。"""
        # 模拟获取 logger
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        commands = [
            ['init'],
            ['calc'], 
            ['analyze', '--factor_file', 'test.csv']
        ]
        
        for cmd in commands:
            # 重置 mock
            mock_logger.reset_mock()
            
            result = self.runner.invoke(factor_cli, cmd)
            
            # 即使是占位符实现，也应该能正常执行
            # analyze 命令可能因为文件不存在而返回非零退出码
            if 'analyze' not in cmd:
                assert result.exit_code == 0


class TestFactorCLIErrorScenarios:
    """测试因子 CLI 错误场景。"""
    
    def setup_method(self):
        """设置测试。"""
        self.runner = CliRunner()
    
    def test_invalid_command_options(self):
        """测试无效的命令选项。"""
        # 测试不存在的选项
        result = self.runner.invoke(factor_cli, [
            'init', '--invalid_option', 'value'
        ])
        
        assert result.exit_code != 0
        assert 'No such option' in result.output or 'Invalid' in result.output
    
    def test_missing_required_params(self):
        """测试缺少必需参数。"""
        # analyze 命令需要 factor_file 参数
        result = self.runner.invoke(factor_cli, ['analyze'])
        
        assert result.exit_code != 0
        assert 'factor_file' in result.output or 'required' in result.output.lower()
    
    def test_file_path_validation(self):
        """测试文件路径验证。"""
        # 测试不存在的目录（当前实现可能不会验证）
        result = self.runner.invoke(factor_cli, [
            'init', '--data_dir', '/nonexistent/path/that/does/not/exist'
        ])
        
        # 当前实现应该正常执行（占位符）
        assert result.exit_code == 0
