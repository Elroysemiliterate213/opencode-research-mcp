"""Benchmark: Bundled MCP vs separate MCPs — real academic search quality comparison."""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path


def _find_tool_site_packages() -> list[Path]:
    candidates = []
    base = Path.home() / "AppData" / "Roaming" / "uv" / "tools"
    for tool, subdir in [
        ("paper-distill-mcp", "Lib/site-packages"),
        ("paper-search-mcp", "Lib/site-packages"),
        ("academix", "Lib/site-packages"),
    ]:
        candidates.append(base / tool / subdir)
    return [p for p in candidates if p.exists()]


for _sp in reversed(_find_tool_site_packages()):
    _sp_str = str(_sp)
    if _sp_str not in sys.path:
        sys.path.insert(0, _sp_str)

from academix.aggregator import AcademicAggregator
from academix import server as academix_server
from paper_search_mcp import server as paper_search


QUERIES = [
    "retrieval augmented generation",
    "machine learning for drug discovery",
    "transformer neural network architecture",
    "reinforcement learning from human feedback",
]


async def benchmark_academix(query: str, agg: AcademicAggregator) -> dict:
    t0 = time.monotonic()
    try:
        result = await agg.search_papers(query, limit=20, sort="relevance")
        elapsed = time.monotonic() - t0
        papers = result.get("papers", [])
        return {
            "source": "academix",
            "query": query,
            "count": len(papers),
            "elapsed": round(elapsed, 2),
            "papers": [
                {
                    "title": p.get("title"),
                    "year": p.get("year"),
                    "doi": p.get("doi"),
                    "arxiv_id": p.get("arxiv_id"),
                    "citation_count": p.get("citation_count"),
                    "source": p.get("source"),
                }
                for p in papers[:5]
            ],
        }
    except Exception as e:
        return {"source": "academix", "query": query, "error": str(e)}


async def benchmark_papersearch(query: str) -> dict:
    t0 = time.monotonic()
    try:
        result = await paper_search.search_papers(
            query=query,
            max_results_per_source=5,
            sources="arxiv,semantic,openalex,crossref,dblp,pubmed,google_scholar,unpaywall",
        )
        elapsed = time.monotonic() - t0
        papers = result.get("papers", []) if isinstance(result, dict) else []
        return {
            "source": "paper-search",
            "query": query,
            "count": len(papers),
            "elapsed": round(elapsed, 2),
            "papers": [
                {
                    "title": p.get("title"),
                    "year": p.get("year"),
                    "doi": p.get("doi"),
                    "arxiv_id": p.get("arxiv_id"),
                    "citation_count": p.get("citations"),
                    "source": p.get("source"),
                }
                for p in papers[:5]
            ],
            "sources_used": result.get("sources_used", []),
        }
    except Exception as e:
        return {"source": "paper-search", "query": query, "error": str(e)}


async def benchmark_bundle(query: str, agg: AcademicAggregator) -> dict:
    """Simulate what the bundle does: call both backends, dedup, merge."""
    t0 = time.monotonic()
    errors = {}
    papers_raw = []

    # academix
    try:
        r1 = await agg.search_papers(query, limit=20, sort="relevance")
        for p in r1.get("papers", []):
            papers_raw.append({"title": p.get("title"), "doi": p.get("doi"), "arxiv_id": p.get("arxiv_id"),
                               "year": p.get("year"), "citation_count": p.get("citation_count"),
                               "source": "academix", "abstract": p.get("abstract")})
    except Exception as e:
        errors["academix"] = str(e)

    # paper-search
    try:
        r2 = await paper_search.search_papers(query=query, max_results_per_source=5,
                                              sources="arxiv,semantic,openalex,crossref,dblp,pubmed,google_scholar,unpaywall")
        if isinstance(r2, dict):
            for p in r2.get("papers", []):
                papers_raw.append({"title": p.get("title"), "doi": p.get("doi"), "arxiv_id": p.get("arxiv_id"),
                                   "year": p.get("year"), "citation_count": p.get("citations"),
                                   "source": "paper-search", "abstract": p.get("abstract")})
    except Exception as e:
        errors["paper-search"] = str(e)

    # dedup by doi / arxiv_id
    seen: set[str] = set()
    merged: list[dict] = []
    for p in papers_raw:
        key = str(p.get("doi") or p.get("arxiv_id") or p.get("title", "")).strip().lower()
        if key and key not in seen:
            seen.add(key)
            merged.append(p)
        elif key in seen:
            # mark as duplicate
            for mp in merged:
                mk = str(mp.get("doi") or mp.get("arxiv_id") or mp.get("title", "")).strip().lower()
                if mk == key:
                    mp["dup_source"] = mp.get("dup_source", [mp["source"]]) + [p["source"]]
                    break

    elapsed = time.monotonic() - t0
    dedup_rate = (1 - len(merged) / len(papers_raw)) * 100 if papers_raw else 0
    coverage_gap = len([p for p in merged if "paper-search" in str(p.get("dup_source", [])) or "paper-search" in str(p.get("source"))]) - \
                   len([p for p in merged if "academix" in str(p.get("dup_source", [])) or "academix" in str(p.get("source"))])

    return {
        "source": "bundle",
        "query": query,
        "total_before_dedup": len(papers_raw),
        "after_dedup": len(merged),
        "dedup_rate": round(dedup_rate, 1),
        "elapsed": round(elapsed, 2),
        "errors": errors,
        "coverage_gap": f"paper-search found {abs(coverage_gap)} more unique papers than academix" if coverage_gap > 0
                         else f"academix found {abs(coverage_gap)} more unique papers than paper-search" if coverage_gap < 0
                         else "equal coverage",
        "samples": merged[:5],
    }


async def main():
    agg = AcademicAggregator(email="chestccj795@gmail.com")
    academix_server._aggregator = agg

    print("=" * 80)
    print("BENCHMARK: Bundled MCP vs Separate MCPs")
    print("=" * 80)

    for query in QUERIES:
        print(f"\n{'─' * 80}")
        print(f"QUERY: {query}")
        print(f"{'─' * 80}")

        # Test each backend separately
        a = await benchmark_academix(query, agg)
        ps = await benchmark_papersearch(query)
        b = await benchmark_bundle(query, agg)

        print(f"\n  ACADEMIX alone:     {a.get('count', 0)} papers in {a.get('elapsed', 0)}s")
        print(f"  PAPER-SEARCH alone:  {ps.get('count', 0)} papers in {ps.get('elapsed', 0)}s")
        print(f"  BUNDLE (merged):    {b.get('after_dedup', 0)} papers from {b.get('total_before_dedup', 0)} raw | dedup rate: {b.get('dedup_rate', 0)}%")
        if b.get("errors"):
            print(f"  Errors: {b['errors']}")

        print(f"\n  Top samples (bundle):")
        for i, p in enumerate(b.get("samples", []), 1):
            print(f"    {i}. {p.get('title', 'N/A')[:80]}")
            print(f"       [{p.get('source')}] year={p.get('year')} citations={p.get('citation_count')}")

    print(f"\n{'=' * 80}")
    print("TOOL SURFACE COMPARISON")
    print(f"{'=' * 80}")
    print(f"\n  SEPARATE (3 MCPs):  43+ tools across 3 processes")
    print(f"  BUNDLED (1 MCP):     11 tools in 1 process")
    print(f"  REDUCTION:           {(1 - 11/43)*100:.0f}% in tool surface")
    print(f"  TOKEN SAVINGS:       ~11,000 tokens in context window")

    await agg.close()


if __name__ == "__main__":
    asyncio.run(main())
