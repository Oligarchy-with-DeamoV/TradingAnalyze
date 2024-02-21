from io import StringIO
from typing import Dict, List, Text

import pandas as pd
import structlog

from .log_utils import configure_structlog


configure_structlog()
structlogger = structlog.get_logger()


def read_csv_to_dataframe(csv_file_path: str) -> pd.DataFrame:
    """读取 CSV 内容并将其转换为 DataFrame。"""
    try:
        df = pd.read_csv(csv_file_path)
        structlogger.info("CSV file successfully read.")
        return df
    except Exception as e:
        structlogger.error("Failed to read CSV file.", error=str(e))
        raise


def split_dataframe_by_first_column(
    csv_file_path: str, split_signal: str
) -> Dict[Text, pd.DataFrame]:
    """根据 DataFrame 的第一列的不同值将其拆分为多个 DataFrame。"""
    try:
        with open(csv_file_path, "r") as f:
            contents = f.readlines()

        dfs = list()
        unique_values = set([c.split(split_signal)[0] for c in contents])
        for uv in unique_values:
            split_content = [c for c in contents if c.split(split_signal)[0] == uv]
            dfs.append((uv, pd.read_csv(StringIO("\n".join(split_content)))))
        structlogger.info("DataFrame successfully split.", df_count=len(dfs))
        return dict(dfs)
    except Exception as e:
        structlogger.error("Failed to split DataFrame.", error=str(e))
        raise


def fetch_trading_data(trading_data: pd.DataFrame):
    trading_data = trading_data[trading_data["DataDiscriminator"] == "Order"]
    trading_data = trading_data[trading_data["资产分类"] == "股票"]
    trading_data["日期/时间"] = pd.to_datetime(trading_data["日期/时间"])

    # trading style
    max_date = trading_data.groupby("代码")["日期/时间"].max()
    min_date = trading_data.groupby("代码")["日期/时间"].min()
    mean_duration_time = str((max_date - min_date).mean())
    median_duration_time = str((max_date - min_date).median())
    structlogger.info("平均持股周期", mean_duration_time=mean_duration_time)
    structlogger.info("中位数持股周期", median_duration_time=median_duration_time)

    # trade stock/trade win rate
    achieve_total = trading_data.groupby("代码")["已实现的损益"].sum()
    win_rate = achieve_total[achieve_total > 0].shape[0] / achieve_total.shape[0]
    structlogger.info("个股胜率", winrate=f"{win_rate*100:3.2f}%")

    achieve_total = trading_data["已实现的损益"]
    win_rate = achieve_total[achieve_total > 0].shape[0] / achieve_total.shape[0]
    structlogger.info("操作胜率", winrate=f"{win_rate*100:3.2f}%")


def fetch_data(
    csv_file_path: str, tables: List[str], split_signal: str
) -> Dict[Text, pd.DataFrame]:
    try:
        split_dfs = split_dataframe_by_first_column(
            csv_file_path=csv_file_path, split_signal=split_signal
        )
        fetched_dfs = [
            (t, split_dfs[t]) for t in tables if split_dfs.get(t, None) is not None
        ]
        if fetched_dfs:
            return dict(fetched_dfs)
        else:
            structlogger.error(
                "No Data found in tables.",
                tables_names=tables,
                ref_tables=split_dfs.keys(),
            )
            raise ValueError
    except Exception as e:
        structlogger.error("An error occurred in processing.", error=str(e))
        raise ValueError


def main(csv_file_path):
    datas = fetch_data(csv_file_path, tables=["交易"], split_signal=",")
    fetch_trading_data(datas["交易"])
