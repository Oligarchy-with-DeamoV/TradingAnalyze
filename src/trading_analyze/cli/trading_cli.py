"""交易分析 CLI 命令。"""

import click
import structlog

from ..main import main as trading_main

logger = structlog.get_logger()


@click.group()
def trading_cli():
    """交易分析相关命令。"""
    pass


@trading_cli.command("analyze")
@click.option("--csv_file_path", required=True, help="IBKR 账单文件路径")
def analyze_trading(csv_file_path):
    """分析 IBKR 交易数据。"""
    try:
        click.echo(f"分析交易数据: {csv_file_path}")
        trading_main(csv_file_path)
        click.echo("✓ 交易分析完成")
        
    except Exception as e:
        logger.error("交易分析失败", error=str(e))
        click.echo(f"错误: {str(e)}", err=True)
