import argparse
from .main import main


def run_entry():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv_file_path", help="IBKR bill path")
    args = parser.parse_args()
    main(csv_file_path=args.csv_file_path)
