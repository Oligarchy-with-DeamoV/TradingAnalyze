"""数据管道 CLI 命令。"""

from pathlib import Path

import click
import structlog

from ..data_pipeline import DataConverter, DataDownloader, DataValidator

logger = structlog.get_logger()


@click.group()
def data_cli():
    """数据管道相关命令。"""
    pass


@data_cli.command("download")
@click.option("--source", type=click.Choice(["yahoo", "csv"]), required=True, help="数据源类型")
@click.option("--symbols", help="股票代码列表，逗号分隔")
@click.option("--input", "input_file", help="输入 CSV 文件路径 (source=csv 时使用)")
@click.option("--start", "start_date", help="开始日期 (YYYY-MM-DD)")
@click.option("--end", "end_date", help="结束日期 (YYYY-MM-DD)")
@click.option("--output", "output_dir", default="./raw_data", help="输出目录")
def download_data(source, symbols, input_file, start_date, end_date, output_dir):
    """下载股票数据。"""
    try:
        downloader = DataDownloader(output_dir)
        
        if source == "yahoo":
            if not symbols or not start_date:
                click.echo("Yahoo Finance 数据源需要 --symbols 和 --start 参数", err=True)
                return
            
            symbol_list = [s.strip() for s in symbols.split(",")]
            click.echo(f"从 Yahoo Finance 下载 {len(symbol_list)} 只股票数据...")
            
            results = downloader.download_yahoo_finance(
                symbols=symbol_list,
                start_date=start_date,
                end_date=end_date
            )
            
            click.echo(f"下载完成: {len(results)} 只股票成功下载")
            
        elif source == "csv":
            if not input_file:
                click.echo("CSV 数据源需要 --input 参数", err=True)
                return
            
            if not Path(input_file).exists():
                click.echo(f"文件不存在: {input_file}", err=True)
                return
            
            click.echo(f"从 CSV 文件读取数据: {input_file}")
            results = downloader.download_from_csv(input_file)
            click.echo(f"读取完成: {len(results)} 只股票数据")
        
        # 列出下载的文件
        available_files = downloader.list_available_data()
        if available_files:
            click.echo(f"\n可用数据文件 ({len(available_files)} 个):")
            for file in available_files:
                click.echo(f"  - {file}")
                
    except Exception as e:
        logger.error("数据下载失败", error=str(e))
        click.echo(f"错误: {str(e)}", err=True)


@data_cli.command("convert")
@click.option("--input", "input_dir", default="./raw_data", help="原始数据目录")
@click.option("--output", "output_dir", default="./qlib_data", help="qlib 数据输出目录")
@click.option("--pattern", default="*.csv", help="文件匹配模式")
def convert_data(input_dir, output_dir, pattern):
    """转换数据为 qlib 格式。"""
    try:
        converter = DataConverter(input_dir, output_dir)
        
        click.echo(f"开始转换数据...")
        click.echo(f"输入目录: {input_dir}")
        click.echo(f"输出目录: {output_dir}")
        
        success = converter.convert_to_qlib_format(file_pattern=pattern)
        
        if success:
            click.echo("✓ 数据转换成功")
            
            # 显示转换统计
            stats = converter.get_conversion_stats()
            if stats:
                click.echo(f"\n转换统计:")
                click.echo(f"  总记录数: {stats['total_records']}")
                click.echo(f"  股票数量: {stats['instruments_count']}")
                click.echo(f"  日期范围: {stats['date_range']['start']} 至 {stats['date_range']['end']}")
                click.echo(f"  股票列表: {', '.join(stats['instruments'])}")
        else:
            click.echo("✗ 数据转换失败", err=True)
            
    except Exception as e:
        logger.error("数据转换失败", error=str(e))
        click.echo(f"错误: {str(e)}", err=True)


@data_cli.command("validate")
@click.option("--data_dir", default="./qlib_data", help="qlib 数据目录")
@click.option("--output", "output_file", help="验证报告输出文件")
def validate_data(data_dir, output_file):
    """验证 qlib 数据质量。"""
    try:
        validator = DataValidator(data_dir)
        
        click.echo(f"开始验证数据: {data_dir}")
        results = validator.validate_qlib_data()
        
        # 显示验证结果
        if results['is_valid']:
            click.echo("✓ 数据验证通过")
        else:
            click.echo("✗ 数据验证失败", err=True)
        
        if results['errors']:
            click.echo(f"\n错误 ({len(results['errors'])}):")
            for error in results['errors']:
                click.echo(f"  - {error}")
        
        if results['warnings']:
            click.echo(f"\n警告 ({len(results['warnings'])}):")
            for warning in results['warnings']:
                click.echo(f"  - {warning}")
        
        if results['stats']:
            stats = results['stats']
            click.echo(f"\n数据统计:")
            click.echo(f"  总记录数: {stats.get('total_records', 'N/A')}")
            click.echo(f"  股票数量: {stats.get('instruments_count', 'N/A')}")
            if 'date_range' in stats:
                dr = stats['date_range']
                click.echo(f"  日期范围: {dr.get('start', 'N/A')} 至 {dr.get('end', 'N/A')}")
                click.echo(f"  交易日数: {dr.get('trading_days', 'N/A')}")
        
        # 数据质量信息
        quality = results['data_quality']
        if quality.get('critical_issues', 0) > 0:
            click.echo(f"\n⚠️  严重问题: {quality['critical_issues']} 个")
        if quality.get('warnings', 0) > 0:
            click.echo(f"⚠️  一般问题: {quality['warnings']} 个")
        
        click.echo(f"\n详细报告已保存至: {data_dir}/validation_report.txt")
        
        if output_file:
            # 复制报告到指定位置
            import shutil
            shutil.copy(f"{data_dir}/validation_report.txt", output_file)
            click.echo(f"报告已复制到: {output_file}")
            
    except Exception as e:
        logger.error("数据验证失败", error=str(e))
        click.echo(f"错误: {str(e)}", err=True)


@data_cli.command("check")
@click.option("--data_dir", default="./qlib_data", help="qlib 数据目录")
def quick_check(data_dir):
    """快速检查数据状态。"""
    try:
        validator = DataValidator(data_dir)
        
        click.echo(f"检查数据目录: {data_dir}")
        
        if validator.quick_check():
            click.echo("✓ 数据基本可用")
            
            # 显示基本信息
            try:
                import pandas as pd
                data_file = Path(data_dir) / "features" / "data.csv"
                data = pd.read_csv(data_file, nrows=0)  # 只读取列名
                
                instruments_file = Path(data_dir) / "instruments" / "all.txt"
                with open(instruments_file, 'r') as f:
                    instrument_count = len([line for line in f if line.strip()])
                
                click.echo(f"  数据列: {', '.join(data.columns)}")
                click.echo(f"  股票数量: {instrument_count}")
                
                # 显示前几只股票
                with open(instruments_file, 'r') as f:
                    first_instruments = [line.strip() for line in f if line.strip()][:5]
                click.echo(f"  前5只股票: {', '.join(first_instruments)}")
                
            except Exception:
                pass  # 忽略详细信息读取错误
                
        else:
            click.echo("✗ 数据不可用或格式错误", err=True)
            click.echo("建议运行 'validate' 命令获取详细信息")
            
    except Exception as e:
        logger.error("数据检查失败", error=str(e))
        click.echo(f"错误: {str(e)}", err=True)


@data_cli.command("list-files")
@click.option("--data_dir", default="./raw_data", help="数据目录")
def list_files(data_dir):
    """列出数据文件。"""
    try:
        downloader = DataDownloader(data_dir)
        files = downloader.list_available_data()
        
        if files:
            click.echo(f"数据目录 {data_dir} 中的文件 ({len(files)} 个):")
            for file in files:
                click.echo(f"  - {file}")
        else:
            click.echo(f"数据目录 {data_dir} 中没有找到数据文件")
            
    except Exception as e:
        logger.error("列出文件失败", error=str(e))
        click.echo(f"错误: {str(e)}", err=True)
