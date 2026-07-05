from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.request import urlretrieve


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"

CMS_PUF_URLS: dict[int, dict[str, str]] = {
    2026: {
        "plan_attributes": "https://download.cms.gov/marketplace-puf/2026/plan-attributes-puf.zip",
        "rates": "https://download.cms.gov/marketplace-puf/2026/rate-puf.zip",
        "benefits": "https://download.cms.gov/marketplace-puf/2026/benefits-and-cost-sharing-puf.zip",
        "service_areas": "https://download.cms.gov/marketplace-puf/2026/service-area-puf.zip",
        "networks": "https://download.cms.gov/marketplace-puf/2026/network-puf.zip",
    },
    2025: {
        "plan_attributes": "https://download.cms.gov/marketplace-puf/2025/plan-attributes-puf.zip",
        "rates": "https://download.cms.gov/marketplace-puf/2025/rate-puf.zip",
        "benefits": "https://download.cms.gov/marketplace-puf/2025/benefits-and-cost-sharing-puf.zip",
        "service_areas": "https://download.cms.gov/marketplace-puf/2025/service-area-puf.zip",
        "networks": "https://download.cms.gov/marketplace-puf/2025/network-puf.zip",
    },
}


def download_file(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size > 0:
        print(f"skip existing {target}")
        return
    print(f"download {url}")
    urlretrieve(url, target)
    print(f"saved {target} ({target.stat().st_size:,} bytes)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Download CMS Marketplace Public Use Files.")
    parser.add_argument("--year", type=int, default=2026, choices=sorted(CMS_PUF_URLS))
    parser.add_argument(
        "--datasets",
        nargs="+",
        default=["plan_attributes", "rates", "benefits", "service_areas", "networks"],
        choices=["plan_attributes", "rates", "benefits", "service_areas", "networks"],
    )
    args = parser.parse_args()

    year_urls = CMS_PUF_URLS[args.year]
    for dataset in args.datasets:
        url = year_urls[dataset]
        target = RAW_DIR / f"cms_{args.year}" / f"{dataset}.zip"
        download_file(url, target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

