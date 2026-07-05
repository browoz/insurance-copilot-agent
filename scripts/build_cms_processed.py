from __future__ import annotations

import argparse
import csv
import re
import zipfile
from pathlib import Path
from typing import Iterable

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"


def first_existing(df: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    normalized = {c.lower(): c for c in df.columns}
    for candidate in candidates:
        found = normalized.get(candidate.lower())
        if found:
            return found
    return None


def read_zipped_csv(path: Path, nrows: int | None = None) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}. Run scripts/download_cms_pufs.py first.")
    with zipfile.ZipFile(path) as zf:
        members = [m for m in zf.namelist() if m.lower().endswith(".csv")]
        if not members:
            raise ValueError(f"No CSV found in {path}")
        with zf.open(members[0]) as handle:
            return pd.read_csv(handle, nrows=nrows, low_memory=False)


def pick(df: pd.DataFrame, *names: str, default: object = None) -> pd.Series:
    col = first_existing(df, names)
    if col:
        return df[col]
    return pd.Series([default] * len(df))


def money(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace("$", "", regex=False).str.replace(",", "", regex=False), errors="coerce")


def coalesce_text(df: pd.DataFrame, candidates: Iterable[str]) -> pd.Series:
    result = pd.Series([pd.NA] * len(df), index=df.index, dtype="object")
    for candidate in candidates:
        col = first_existing(df, [candidate])
        if not col:
            continue
        values = df[col].replace(["", "nan", "NaN"], pd.NA)
        result = result.fillna(values)
    return result


def normalize_cost_text(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if not text or text.lower() in {"nan", "not applicable"}:
        return ""
    return re.sub(r"\s+", " ", text)


def cost_sort_key(value: str) -> tuple[int, float, str]:
    match = re.search(r"\$?\s*([0-9][0-9,]*(?:\.\d+)?)", value)
    if match:
        return (0, float(match.group(1).replace(",", "")), value)
    return (1, float("inf"), value)


def unique_cost_options(series: pd.Series) -> str:
    values = sorted({normalize_cost_text(value) for value in series if normalize_cost_text(value)}, key=cost_sort_key)
    return "; ".join(values)


def first_non_empty(series: pd.Series) -> object:
    for value in series:
        if normalize_cost_text(value):
            return value
    for value in series:
        if pd.notna(value) and str(value).strip():
            return value
    return pd.NA


def build_plans(year: int, sample_rows: int | None) -> pd.DataFrame:
    df = read_zipped_csv(RAW_DIR / f"cms_{year}" / "plan_attributes.zip", nrows=sample_rows)
    deductible = coalesce_text(
        df,
        [
            "MEHBDedInnTier1Individual",
            "TEHBDedInnTier1Individual",
            "MEHBDedCombInnOonIndividual",
            "TEHBDedCombInnOonIndividual",
        ],
    )
    oop_max = coalesce_text(
        df,
        [
            "MEHBInnTier1IndividualMOOP",
            "TEHBInnTier1IndividualMOOP",
            "MEHBCombInnOonIndividualMOOP",
            "TEHBCombInnOonIndividualMOOP",
        ],
    )
    raw_plans = pd.DataFrame(
        {
            "plan_id": pick(df, "StandardComponentId", "PlanId", "PlanID"),
            "year": year,
            "state": pick(df, "StateCode", "State"),
            "county": "",
            "issuer": pick(df, "IssuerMarketPlaceMarketingName", "IssuerName", "HIOSIssuerName", "Issuer"),
            "plan_name": pick(df, "PlanMarketingName", "PlanName"),
            "metal_level": pick(df, "MetalLevel"),
            "plan_type": pick(df, "PlanType"),
            "service_area_id": pick(df, "ServiceAreaId"),
            "monthly_premium": pd.NA,
            "deductible": deductible.map(normalize_cost_text),
            "out_of_pocket_max": oop_max.map(normalize_cost_text),
        }
    ).dropna(subset=["plan_id"])
    grouped = (
        raw_plans.groupby(["plan_id", "year"], as_index=False)
        .agg(
            {
                "state": first_non_empty,
                "county": first_non_empty,
                "issuer": first_non_empty,
                "plan_name": first_non_empty,
                "metal_level": first_non_empty,
                "plan_type": first_non_empty,
                "service_area_id": first_non_empty,
                "monthly_premium": first_non_empty,
                "deductible": unique_cost_options,
                "out_of_pocket_max": unique_cost_options,
            }
        )
    )
    grouped["deductible_source"] = grouped["deductible"].where(
        grouped["deductible"].eq(""), "Plan Attributes PUF tier-1 individual deductible options"
    )
    grouped["out_of_pocket_max_source"] = grouped["out_of_pocket_max"].where(
        grouped["out_of_pocket_max"].eq(""), "Plan Attributes PUF tier-1 individual MOOP options"
    )
    return grouped


def add_rates(plans: pd.DataFrame, year: int, sample_rows: int | None) -> pd.DataFrame:
    path = RAW_DIR / f"cms_{year}" / "rates.zip"
    if not path.exists():
        return plans
    state_filter = set(plans["state"].dropna().astype(str).unique())
    chunks = []
    with zipfile.ZipFile(path) as zf:
        member = [m for m in zf.namelist() if m.lower().endswith(".csv")][0]
        for chunk in pd.read_csv(zf.open(member), chunksize=250_000, low_memory=False):
            if "StateCode" in chunk.columns and state_filter:
                chunk = chunk[chunk["StateCode"].astype(str).isin(state_filter)]
            if chunk.empty:
                continue
            plan_id = pick(chunk, "PlanId", "PlanID", "StandardComponentId")
            age = pick(chunk, "Age")
            rate = money(pick(chunk, "IndividualRate", "Rate"))
            clean = pd.DataFrame({"plan_id": plan_id, "age": age, "monthly_premium": rate})
            adult = clean[clean["age"].astype(str).isin(["40", "Age 40"])]
            if not adult.empty:
                chunks.append(adult[["plan_id", "monthly_premium"]])
    if not chunks:
        return plans
    adult = pd.concat(chunks, ignore_index=True).dropna(subset=["monthly_premium"])
    adult = adult.groupby("plan_id", as_index=False)["monthly_premium"].min()
    return plans.drop(columns=["monthly_premium"]).merge(adult, on="plan_id", how="left")


def add_benefits(plans: pd.DataFrame, year: int, sample_rows: int | None) -> tuple[pd.DataFrame, pd.DataFrame]:
    benefits = read_zipped_csv(RAW_DIR / f"cms_{year}" / "benefits.zip", nrows=sample_rows)
    clean = pd.DataFrame(
        {
            "plan_id": pick(benefits, "StandardComponentId", "PlanId", "PlanID"),
            "year": year,
            "benefit_name": pick(benefits, "BenefitName", "Benefit"),
            "is_covered": pick(benefits, "IsCovered"),
            "copay": pick(benefits, "CopayInnTier1", "CopayInNet", "Copay"),
            "coinsurance": pick(benefits, "CoinsInnTier1", "CoinsuranceInNet", "Coinsurance"),
            "is_ehb": pick(benefits, "IsEHB"),
        }
    ).dropna(subset=["plan_id", "benefit_name"])

    return plans, clean


def build_service_areas(year: int) -> pd.DataFrame:
    path = RAW_DIR / f"cms_{year}" / "service_areas.zip"
    if not path.exists():
        return pd.DataFrame(
            columns=[
                "year",
                "state",
                "issuer_id",
                "service_area_id",
                "service_area_name",
                "cover_entire_state",
                "county_fips",
                "partial_county",
                "market_coverage",
                "dental_only_plan",
            ]
        )
    df = read_zipped_csv(path)
    county = pick(df, "County").astype("Int64").astype(str).replace("<NA>", "")
    return pd.DataFrame(
        {
            "year": year,
            "state": pick(df, "StateCode"),
            "issuer_id": pick(df, "IssuerId"),
            "service_area_id": pick(df, "ServiceAreaId"),
            "service_area_name": pick(df, "ServiceAreaName"),
            "cover_entire_state": pick(df, "CoverEntireState"),
            "county_fips": county,
            "partial_county": pick(df, "PartialCounty"),
            "market_coverage": pick(df, "MarketCoverage"),
            "dental_only_plan": pick(df, "DentalOnlyPlan"),
        }
    )


def build_docs(year: int) -> pd.DataFrame:
    rows = [
        {
            "source": "CMS Exchange Public Use Files",
            "title": "Plan Attributes PUF",
            "text": (
                "The Plan Attributes Public Use File contains plan-level attributes for qualified health plans, "
                "including issuer information, plan marketing name, plan type, metal level, and plan identifiers."
            ),
        },
        {
            "source": "CMS Exchange Public Use Files",
            "title": "Rate PUF",
            "text": (
                "The Rate Public Use File contains plan rate information used for structured premium lookup. "
                "In this project, age 40 rates are used as a simple comparable premium estimate when available."
            ),
        },
        {
            "source": "CMS Exchange Public Use Files",
            "title": "Benefits and Cost Sharing PUF",
            "text": (
                "The Benefits and Cost Sharing Public Use File contains benefit-level cost sharing details, "
                "including whether benefits are covered and in-network copay or coinsurance values."
            ),
        },
        {
            "source": "Health Insurance Glossary",
            "title": "Deductible",
            "text": "A deductible is the amount paid for covered health care services before the insurance plan starts to pay.",
        },
        {
            "source": "Health Insurance Glossary",
            "title": "Premium",
            "text": "A premium is the amount paid every month for health insurance coverage.",
        },
        {
            "source": "Health Insurance Glossary",
            "title": "Metal level",
            "text": "Bronze, Silver, Gold, and Platinum metal levels describe how plan costs are shared between the consumer and insurer.",
        },
    ]
    docs = pd.DataFrame(rows)
    docs["year"] = year
    return docs


def main() -> int:
    parser = argparse.ArgumentParser(description="Build processed CMS CSVs for the local insurance copilot.")
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--sample-rows", type=int, default=250_000, help="Rows to read from each CMS CSV. Use 0 for all rows.")
    args = parser.parse_args()
    sample_rows = None if args.sample_rows == 0 else args.sample_rows

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    plans = build_plans(args.year, sample_rows)
    plans = add_rates(plans, args.year, sample_rows)
    plans, benefits = add_benefits(plans, args.year, sample_rows)
    service_areas = build_service_areas(args.year)
    docs = build_docs(args.year)

    plans.to_csv(PROCESSED_DIR / "plans.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    benefits.to_csv(PROCESSED_DIR / "benefits.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    service_areas.to_csv(PROCESSED_DIR / "service_areas.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    docs.to_csv(PROCESSED_DIR / "docs.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    print(f"wrote {PROCESSED_DIR / 'plans.csv'} rows={len(plans):,}")
    print(f"wrote {PROCESSED_DIR / 'benefits.csv'} rows={len(benefits):,}")
    print(f"wrote {PROCESSED_DIR / 'service_areas.csv'} rows={len(service_areas):,}")
    print(f"wrote {PROCESSED_DIR / 'docs.csv'} rows={len(docs):,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
