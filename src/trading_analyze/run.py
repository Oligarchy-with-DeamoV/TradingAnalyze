import click

from .cli import data_cli, factor_cli, trading_cli


@click.group()
def main():
    """TradingAnalyze - 交易分析和因子挖掘工具。"""
    pass


# 添加子命令组
main.add_command(data_cli, name="data")
main.add_command(factor_cli, name="factor") 
main.add_command(trading_cli, name="trading")


def run_entry():
    """程序入口点。"""
    main()
