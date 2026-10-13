"""Optional standalone form utility, independent of the alarm application."""

import argparse
import json
import time
from pathlib import Path

import requests


def main(argv=None):
    parser = argparse.ArgumentParser(description="Submit form data from a JSON file")
    parser.add_argument("--url", required=True, help="Form submission endpoint")
    parser.add_argument("--data", type=Path, required=True, help="JSON mapping of form fields")
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--interval", type=float, default=1)
    args = parser.parse_args(argv)
    if args.count < 1 or args.interval < 0:
        parser.error("count must be positive and interval must be non-negative")
    with args.data.open(encoding="utf-8") as stream:
        data = json.load(stream)
    if not isinstance(data, dict):
        parser.error("data must contain a JSON object")
    with requests.Session() as session:
        for index in range(args.count):
            response = session.post(args.url, data=data, timeout=10)
            response.raise_for_status()
            print(f"Submitted {index + 1}; status: {response.status_code}")
            if index + 1 < args.count:
                time.sleep(args.interval)


if __name__ == "__main__":
    main()
