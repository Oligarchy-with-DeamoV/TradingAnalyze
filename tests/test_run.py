"""测试 run.py 模块 - CLI 入口点。"""

from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from trading_analyze.run import main, run_entry


class TestMainCLI:
    """测试主 CLI 命令组。"""
    
    def setup_method(self):
        """设置测试。"""
        self.runner = CliRunner()
    
    def test_main_help(self):
        """测试主 CLI 帮助信息。"""
        result = self.runner.invoke(main, ['--help'])
        
        assert result.exit_code == 0
        assert 'TradingAnalyze' in result.output
        # 应该显示子命令
        assert 'data' in result.output
        assert 'factor' in result.output
        assert 'trading' in result.output
    
    def test_main_no_command(self):
        """测试没有提供子命令时的行为。"""
        result = self.runner.invoke(main, [])
        
        # Click groups 默认行为是显示帮助并退出码为 2
        assert result.exit_code == 2
        assert 'Usage:' in result.output or 'Commands:' in result.output
    
    def test_main_invalid_command(self):
        """测试无效的子命令。"""
        result = self.runner.invoke(main, ['invalid_command'])
        
        assert result.exit_code != 0
        assert 'No such command' in result.output


class TestDataSubcommands:
    """测试 data 子命令组。"""
    
    def setup_method(self):
        """设置测试。"""
        self.runner = CliRunner()
    
    def test_data_help(self):
        """测试 data 子命令帮助。"""
        result = self.runner.invoke(main, ['data', '--help'])
        
        assert result.exit_code == 0
        assert 'data' in result.output.lower()


class TestFactorSubcommands:
    """测试 factor 子命令组。"""
    
    def setup_method(self):
        """设置测试。"""
        self.runner = CliRunner()
    
    def test_factor_help(self):
        """测试 factor 子命令帮助。"""
        result = self.runner.invoke(main, ['factor', '--help'])
        
        assert result.exit_code == 0
        assert 'factor' in result.output.lower()


class TestTradingSubcommands:
    """测试 trading 子命令组。"""
    
    def setup_method(self):
        """设置测试。"""
        self.runner = CliRunner()
    
    def test_trading_help(self):
        """测试 trading 子命令帮助。"""
        result = self.runner.invoke(main, ['trading', '--help'])
        
        assert result.exit_code == 0
        assert 'trading' in result.output.lower()


class TestRunEntry:
    """测试 run_entry 函数。"""
    
    @patch('trading_analyze.run.main')
    def test_run_entry_calls_main(self, mock_main):
        """测试 run_entry 调用主 CLI。"""
        run_entry()
        
        mock_main.assert_called_once()
    
    @patch('trading_analyze.run.main')
    def test_run_entry_exception_handling(self, mock_main):
        """测试 run_entry 异常处理。"""
        mock_main.side_effect = Exception("测试异常")
        
        # run_entry 不会捕获异常，所以应该抛出异常
        with pytest.raises(Exception, match="测试异常"):
            run_entry()


class TestCLIIntegration:
    """集成测试 - 测试 CLI 命令的整体流程。"""
    
    def setup_method(self):
        """设置测试。"""
        self.runner = CliRunner()
    
    def test_help_commands_completeness(self):
        """测试帮助命令的完整性。"""
        # 主命令帮助
        result = self.runner.invoke(main, ['--help'])
        assert result.exit_code == 0
        
        # 子命令帮助
        subcommands = ['data', 'factor', 'trading']
        for subcmd in subcommands:
            result = self.runner.invoke(main, [subcmd, '--help'])
            assert result.exit_code == 0
