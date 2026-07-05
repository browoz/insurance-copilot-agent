from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import Normalizer


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = ROOT / "data" / "sample"
PROCESSED_DIR = ROOT / "data" / "processed"


@dataclass
class SearchResult:
    plans: pd.DataFrame
    vector_results: list[dict[str, Any]]
    keyword_results: list[dict[str, Any]]


class InsuranceCopilot:
    def __init__(
        self,
        plans_path: Path | str | None = None,
        docs_path: Path | str | None = None,
    ) -> None:
        load_dotenv(ROOT / ".env")
        plans_path = plans_path or self._default_data_path("plans.csv")
        docs_path = docs_path or self._default_data_path("docs.csv")
        self.plans_df = pd.read_csv(plans_path)
        self.docs_df = pd.read_csv(docs_path)
        self.service_areas_df = self._load_optional_service_areas()
        self._normalize_plan_frame()
        self.chunks_df = self._build_chunks(self.docs_df)
        self.con = duckdb.connect(database=":memory:")
        self.con.register("plans_df", self.plans_df)
        self.con.execute("CREATE TABLE plans AS SELECT * FROM plans_df")
        self.con.register("service_areas_df", self.service_areas_df)
        self.con.execute("CREATE TABLE service_areas AS SELECT * FROM service_areas_df")
        self._build_retrievers()

    @staticmethod
    def _default_data_path(filename: str) -> Path:
        processed = PROCESSED_DIR / filename
        if processed.exists():
            return processed
        return SAMPLE_DIR / filename

    def _load_optional_service_areas(self) -> pd.DataFrame:
        path = PROCESSED_DIR / "service_areas.csv"
        if path.exists():
            return pd.read_csv(path, dtype=str).fillna("")
        return pd.DataFrame(
            columns=["state", "issuer_id", "service_area_id", "cover_entire_state", "county_fips"]
        )

    def _normalize_plan_frame(self) -> None:
        text_columns = ["plan_id", "state", "county", "issuer", "plan_name", "metal_level", "plan_type", "service_area_id"]
        for column in text_columns:
            if column not in self.plans_df.columns:
                self.plans_df[column] = ""
            self.plans_df[column] = self.plans_df[column].fillna("").astype(str)
        for column in ["monthly_premium", "deductible", "out_of_pocket_max"]:
            if column not in self.plans_df.columns:
                self.plans_df[column] = pd.NA

    @staticmethod
    def _build_chunks(docs_df: pd.DataFrame) -> pd.DataFrame:
        rows = []
        for idx, row in docs_df.iterrows():
            rows.append(
                {
                    "chunk_id": int(idx),
                    "source": row["source"],
                    "title": row["title"],
                    "chunk_text": row["text"],
                }
            )
        return pd.DataFrame(rows)

    def _build_retrievers(self) -> None:
        self.tfidf = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.tfidf_matrix = self.tfidf.fit_transform(self.chunks_df["chunk_text"])
        n_components = min(4, self.tfidf_matrix.shape[0] - 1, self.tfidf_matrix.shape[1] - 1)
        self.svd = TruncatedSVD(n_components=max(1, n_components), random_state=42)
        self.normalizer = Normalizer(copy=False)
        dense = self.svd.fit_transform(self.tfidf_matrix)
        self.chunk_embeddings = self.normalizer.fit_transform(dense)

    @staticmethod
    def _quote_sql(value: str) -> str:
        return str(value).replace("'", "''")

    @staticmethod
    def _county_to_fips(state: str | None, county: str | None) -> str | None:
        if not county:
            return None
        county_text = str(county).strip()
        if county_text.isdigit():
            return county_text.zfill(5)
        known = {
            ("TX", "dallas"): "48113",
            ("TX", "harris"): "48201",
            ("TX", "tarrant"): "48439",
            ("TX", "bexar"): "48029",
            ("FL", "miami-dade"): "12086",
        }
        return known.get(((state or "").upper(), county_text.lower().replace(" county", "")))

    def search_plans(
        self,
        state: str | None = None,
        county: str | None = None,
        metal_level: str | None = None,
        max_premium: float | None = None,
    ) -> pd.DataFrame:
        where = []
        if state:
            where.append(f"p.state = '{self._quote_sql(state.upper())}'")
        county_fips = self._county_to_fips(state, county)
        if metal_level:
            where.append(f"lower(CAST(p.metal_level AS VARCHAR)) = lower('{self._quote_sql(metal_level)}')")
        if max_premium is not None:
            where.append(f"p.monthly_premium <= {float(max_premium)}")

        sql = """
        SELECT
            DISTINCT p.plan_id,
            p.issuer,
            p.plan_name,
            p.metal_level,
            p.monthly_premium,
            p.deductible,
            p.out_of_pocket_max
        FROM plans
            p
        """
        if county_fips and len(self.service_areas_df):
            sql += """
            LEFT JOIN service_areas sa
              ON p.state = sa.state
             AND p.service_area_id = sa.service_area_id
            """
            where.append(
                f"(lower(sa.cover_entire_state) = 'yes' OR sa.county_fips = '{self._quote_sql(county_fips)}')"
            )
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY p.monthly_premium ASC NULLS LAST"
        return self.con.execute(sql).df()

    def vector_search(self, question: str, top_k: int = 3) -> list[dict[str, Any]]:
        query_tfidf = self.tfidf.transform([question])
        query_embedding = self.normalizer.transform(self.svd.transform(query_tfidf))
        similarities = cosine_similarity(query_embedding, self.chunk_embeddings)[0]
        top_indices = similarities.argsort()[::-1][:top_k]
        results = []
        for idx in top_indices:
            row = self.chunks_df.iloc[idx].to_dict()
            row["similarity"] = float(similarities[idx])
            results.append(row)
        return results

    def keyword_search(self, question: str, top_k: int = 3) -> list[dict[str, Any]]:
        query_vec = self.tfidf.transform([question])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix)[0]
        top_indices = similarities.argsort()[::-1][:top_k]
        results = []
        for idx in top_indices:
            row = self.chunks_df.iloc[idx].to_dict()
            row["keyword_score"] = float(similarities[idx])
            results.append(row)
        return results

    def hybrid_search(self, question: str, filters: dict[str, Any] | None = None) -> SearchResult:
        filters = filters or {}
        return SearchResult(
            plans=self.search_plans(
                state=filters.get("state"),
                county=filters.get("county"),
                metal_level=filters.get("metal_level"),
                max_premium=filters.get("max_premium"),
            ),
            vector_results=self.vector_search(question),
            keyword_results=self.keyword_search(question),
        )

    @staticmethod
    def build_prompt(question: str, search: SearchResult) -> str:
        plan_context = (
            search.plans.to_string(index=False)
            if len(search.plans)
            else "No structured plan results found."
        )
        doc_context_parts = []
        seen = set()
        for result in search.vector_results + search.keyword_results:
            key = result["chunk_id"]
            if key in seen:
                continue
            seen.add(key)
            doc_context_parts.append(
                f"Source: {result['source']}\n"
                f"Title: {result['title']}\n"
                f"Text: {result['chunk_text']}"
            )

        return f"""
User question:
{question}

Structured plan results:
{plan_context}

Retrieved explanation documents:
{chr(10).join(doc_context_parts)}

Instructions:
- Answer clearly for a beginner.
- Start with 2-3 bullets under "What the agents did" explaining that security checked the question, structured search found public CMS plans, retrieval found explanation documents, and synthesis combined them.
- Use structured plan results for plan names, premiums, deductibles, and out-of-pocket maximums.
- Use retrieved documents for definitions and explanations.
- When a metal level appears, explain in plain language that Bronze, Silver, Gold, and Platinum are cost-sharing categories, not quality ratings.
- If Silver appears, explain that it is a middle cost-sharing tier and can matter for cost-sharing reductions when a consumer is eligible.
- Explain why the shown plan matched the selected filters, including state, county, and metal level when available.
- Do not invent plan details.
- Include citations using source and title names.
- Keep the answer compact: use short sections and avoid more than 6 bullets total.
"""

    def call_mistral(self, prompt: str) -> str:
        api_key = os.getenv("MISTRAL_API_KEY")
        base_url = os.getenv("MISTRAL_BASE_URL", "https://api.mistral.ai/v1/chat/completions")
        model = os.getenv("MISTRAL_MODEL", "mistral-small-latest")
        if not api_key:
            return "MISTRAL_API_KEY is missing. Retrieval completed, but LLM generation is disabled."

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an insurance plan copilot. Use only the provided context. "
                        "If information is missing, say so. Cite source/title names."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        response = requests.post(
            base_url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def ask(self, question: str, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        search = self.hybrid_search(question, filters)
        prompt = self.build_prompt(question, search)
        try:
            answer = self.call_mistral(prompt)
        except Exception as exc:
            answer = f"LLM API call failed: {type(exc).__name__}: {exc}"
        return {
            "question": question,
            "answer": answer,
            "plans": search.plans,
            "retrieved_docs": pd.DataFrame(search.vector_results),
            "keyword_docs": pd.DataFrame(search.keyword_results),
        }
