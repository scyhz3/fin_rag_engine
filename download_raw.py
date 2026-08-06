import argparse
import os
from datetime import date
from pathlib import Path

from finrag.companies import COMPANIES
from finrag.ingestion.downloader import EdinetDownloader
from finrag.ingestion.edinet_client import EdinetClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download raw EDINET filings.")
    parser.add_argument("start_date", nargs="?", type=date.fromisoformat)
    parser.add_argument("end_date", nargs="?", type=date.fromisoformat)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    end_date = args.end_date or date.today()
    start_date = args.start_date or end_date.replace(year=end_date.year - 5)

    client = EdinetClient(api_key=os.environ["EDINET_API"])
    downloader = EdinetDownloader(
        client=client,
        raw_dir=Path("data/raw/edinet"),
        edinet_codes=set(COMPANIES),
    )

    print(f"Searching from {start_date} to {end_date} for {len(COMPANIES)} companies.")

    try:
        downloaded_dirs = downloader.download_range(start_date, end_date)
    finally:
        client.close()

    if not downloaded_dirs:
        print("No matching filings were found.")
        return

    for directory in downloaded_dirs:
        print(directory)


if __name__ == "__main__":
    main()
