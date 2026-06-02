"""Bundled academic research MCP server.

Integrates Academix (metadata + citations), Paper Search (21+ sources + PDF/text),
and Paper Distill (curation pipeline) into one compact tool surface.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import random
import re
import sys
import time
from collections import OrderedDict, deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

import httpx

from publisher_apis import _get_client, search_scopus, search_springer, springer_resolve_oa

from fastmcp import FastMCP  # noqa: E402

from academix.aggregator import AcademicAggregator  # noqa: E402
from academix import server as academix_server  # noqa: E402
from paper_search_mcp import server as paper_search  # noqa: E402

# ID format patterns (used for source auto-detection in read_paper)
ARXIV_ID_RE = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$")
DOI_RE = re.compile(r"^10\.\d{4,}/\S+$")
PMID_RE = re.compile(r"^PMID:\d+$|^\d{4,9}$")

# Shared config
UNPAYWALL_EMAIL = os.environ.get("UNPAYWALL_EMAIL", "research@example.com")
PDF_MAGIC = b"%PDF-"

# Map of source name -> paper_search reader function (built once after import)
_READERS: dict[str, Any] = {}


def _get_reader(source: str):
    """Lazy-init reader registry; returns the reader callable or None."""
    if not _READERS:
        _READERS.update({
            "arxiv": paper_search.read_arxiv_paper,
            "semantic": paper_search.read_semantic_paper,
            "biorxiv": paper_search.read_biorxiv_paper,
            "medrxiv": paper_search.read_medrxiv_paper,
            "iacr": paper_search.read_iacr_paper,
            "openaire": paper_search.read_openaire_paper,
            "citeseerx": paper_search.read_citeseerx_paper,
            "doaj": paper_search.read_doaj_paper,
            "base": paper_search.read_base_paper,
            "zenodo": paper_search.read_zenodo_paper,
            "hal": paper_search.read_hal_paper,
        })
    return _READERS.get(source)

_academix: AcademicAggregator | None = None


@asynccontextmanager
async def lifespan(app: FastMCP) -> AsyncIterator[None]:
    global _academix
    _academix = AcademicAggregator(
        email=os.environ.get("ACADEMIX_EMAIL"),
        semantic_scholar_api_key=os.environ.get("SEMANTIC_SCHOLAR_API_KEY"),
    )
    academix_server._aggregator = _academix
    try:
        yield
    finally:
        if _academix is not None:
            await _academix.close()
        academix_server._aggregator = None
        _academix = None


mcp = FastMCP("research", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Caching layer
# ---------------------------------------------------------------------------

class _TTLCache:
    """Simple in-memory TTL cache with O(1) LRU eviction."""

    def __init__(self, ttl_seconds: int = 600, max_entries: int = 512):
        self._ttl = ttl_seconds
        self._max = max_entries
        self._store: OrderedDict[str, tuple[float, Any]] = OrderedDict()

    def _key(self, *args: Any, **kwargs: Any) -> str:
        blob = json.dumps(args, sort_keys=True, default=str) + json.dumps(
            kwargs, sort_keys=True, default=str
        )
        return hashlib.md5(blob.encode()).hexdigest()

    def get(self, *args: Any, **kwargs: Any) -> Any | None:
        k = self._key(*args, **kwargs)
        entry = self._store.get(k)
        if entry is None:
            return None
        ts, val = entry
        if time.monotonic() - ts > self._ttl:
            del self._store[k]
            return None
        # Mark as recently used
        self._store.move_to_end(k)
        return val

    def set(self, value: Any, *args: Any, **kwargs: Any) -> None:
        k = self._key(*args, **kwargs)
        if k in self._store:
            self._store.move_to_end(k)
        self._store[k] = (time.monotonic(), value)
        if len(self._store) > self._max:
            self._store.popitem(last=False)  # O(1) LRU eviction


_search_cache = _TTLCache(ttl_seconds=600, max_entries=256)
_lookup_cache = _TTLCache(ttl_seconds=3600, max_entries=1024)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _json_load(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {"raw": value}
    return value


def _authors(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        # Handle "Last, First" format: "Smith, John A.; Doe, Jane" -> ["John A. Smith", "Jane Doe"]
        if ";" in value:
            parts = [p.strip() for p in value.split(";") if p.strip()]
        elif "," in value:
            parts = [p.strip() for p in value.split(",") if p.strip()]
        else:
            return [value.strip()]
        # If exactly 2 parts, likely "Last, First"
        if len(parts) == 2:
            return [f"{parts[1]} {parts[0]}".strip()]
        return [p for p in parts if p]
    out = []
    for a in value:
        if isinstance(a, dict):
            name = (
                a.get("name")
                or a.get("author")
                or a.get("display_name")
                or a.get("givenName", "") + " " + a.get("familyName", "")
            ).strip()
            if name:
                out.append(name)
        elif a:
            out.append(str(a))
    return out


def _norm_id(value: Any) -> str:
    return str(value or "").strip().lower().removeprefix("https://doi.org/").removeprefix("http://doi.org/").removeprefix("doi:")


def _safe_filename(value: str) -> str:
    """Sanitize a string for use as a filename component (no path traversal)."""
    # Replace path separators and control chars with underscores; keep alnum, _, -, .
    s = re.sub(r"[^\w\-.]", "_", str(value or ""))
    # Strip leading dots (defeats ../ traversal even if / were not stripped)
    s = s.lstrip(".") or "paper"
    return s


def _save_pdf(content: bytes, paper_id: str, save_path: str) -> str:
    """Write PDF content to disk and return the path."""
    out_dir = Path(save_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{_safe_filename(paper_id)}.pdf"
    out_file.write_bytes(content)
    return str(out_file)


def _is_pdf_response(resp, content: bytes) -> bool:
    """Check if an HTTP response looks like a PDF."""
    return (
        "pdf" in resp.headers.get("content-type", "").lower()
        or content[:5] == PDF_MAGIC
    )


def _paper_key(paper: dict[str, Any]) -> str:
    doi = _norm_id(paper.get("doi"))
    if doi:
        return f"doi:{doi}"
    arxiv = _norm_id(paper.get("arxiv_id") or paper.get("arxiv"))
    if arxiv:
        return f"arxiv:{arxiv}"
    pmid = str(paper.get("pmid") or paper.get("paper_id") or "").strip()
    if pmid.startswith("PMID:"):
        return pmid.lower()
    # Title-based fallback: full normalized title + year for safer dedup
    title = re.sub(r"[^\w\s]", "", str(paper.get("title") or "").casefold())
    title = " ".join(title.split())
    year = str(paper.get("year") or paper.get("published_date") or "")[:4]
    return f"title:{title}:{year}" if title else ""


def _clean_abstract(value: Any) -> str:
    """Strip JATS/XML tags and clean up abstract text."""
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", " ", str(value))
    return re.sub(r"\s+", " ", text).strip()


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value or default)
    except (TypeError, ValueError):
        return default


def _normalize_paper(paper: dict[str, Any], source: str) -> dict[str, Any]:
    p = dict(paper)
    # Only merge from "raw" sub-dict if it actually exists (avoid self-iteration)
    raw = p.pop("raw", None)
    if isinstance(raw, dict):
        for k, v in raw.items():
            if k not in p or p[k] is None:
                p[k] = v
    authors = _authors(p.get("authors"))
    year_raw = p.get("year") or str(p.get("published_date") or "")[:4]
    # Detect OA status: explicit flag, or has pdf_url, or from OA sources
    is_oa = (
        p.get("is_open_access")
        or bool(p.get("pdf_url") or p.get("open_access_url"))
        or source in ("unpaywall", "doaj", "openaire", "base", "zenodo", "hal")
        or (p.get("arxiv_id") or p.get("arxiv"))
        or "biorxiv" in str(p.get("doi") or "")
        or "medrxiv" in str(p.get("doi") or "")
    )
    return {
        "title": p.get("title"),
        "authors": authors,
        "year": _to_int(year_raw, 0) or None,
        "venue": p.get("venue") or p.get("journal") or p.get("publisher"),
        "doi": p.get("doi"),
        "arxiv_id": p.get("arxiv_id") or p.get("arxiv"),
        "pmid": p.get("pmid"),
        "paper_id": p.get("id") or p.get("paper_id"),
        "url": p.get("url"),
        "pdf_url": p.get("pdf_url") or p.get("open_access_url"),
        "abstract": _clean_abstract(p.get("abstract")),
        "citation_count": _to_int(
            p.get("citation_count") or p.get("citations") or p.get("cited_by_count"), 0
        ),
        "keywords": p.get("keywords") or p.get("categories"),
        "is_open_access": bool(is_oa),
        "sources": sorted(set(s for s in [source, str(p.get("source") or source)] if s)),
    }


SOURCE_PRECISION_BONUS = {
    "openaire": 2,
    "academix": 1,
    "arxiv": 1,
    "semantic": 1,
    "scopus": 2,
    "springer": 2,
    "europepmc": 0,
    "pubmed": 0,
    "crossref": 0,
    "unpaywall": 0,
}


def _merge_papers(items: list[dict[str, Any]], limit: int, query: str | None = None) -> list[dict[str, Any]]:
    """Deduplicate and rank papers. Adds relevance_score when query is provided.

    relevance_score = term overlap between query and title (0-10 scale)
    + citation boost (1-3 points for 50+/100+/500+ citations).
    """
    # Extract query terms for relevance scoring
    query_terms: set[str] = set()
    if query:
        q_clean = re.sub(r"[^\w\s]", "", query.casefold())
        query_terms = {w for w in q_clean.split() if len(w) > 2}

    merged: dict[str, dict[str, Any]] = {}
    for item in items:
        key = _paper_key(item)
        if not key or key.startswith("title::"):
            continue
        existing = merged.get(key)
        if existing is None:
            raw_hits = len(set(item.get("sources") or []))
            precision_boost = 0
            for s in (item.get("sources") or []):
                precision_boost = max(precision_boost, SOURCE_PRECISION_BONUS.get(s, 0))
            item["source_hits"] = raw_hits + precision_boost
            # Compute relevance score from title term overlap + citation boost
            score = 0
            if query_terms and item.get("title"):
                title_clean = re.sub(r"[^\w\s]", "", item["title"].casefold())
                title_terms = set(title_clean.split())
                overlap = len(title_terms & query_terms)
                score = min(overlap * 3, 10)
            # Boost papers with high citation counts (top 10% of cited works get +3)
            cites = _to_int(item.get("citation_count"))
            if cites >= 500:
                score = min(score + 3, 10)
            elif cites >= 100:
                score = min(score + 2, 10)
            elif cites >= 50:
                score = min(score + 1, 10)
            item["relevance_score"] = score
            merged[key] = item
            continue
        new_sources = set(existing.get("sources") or []) | set(item.get("sources") or [])
        existing["sources"] = sorted(new_sources)
        raw_hits = len(new_sources)
        precision_boost = 0
        for s in new_sources:
            precision_boost = max(precision_boost, SOURCE_PRECISION_BONUS.get(s, 0))
        existing["source_hits"] = raw_hits + precision_boost
        for field in ("abstract", "doi", "arxiv_id", "pmid", "paper_id", "url", "pdf_url", "venue", "year", "keywords"):
            if not existing.get(field) and item.get(field):
                existing[field] = item[field]
        if not existing.get("authors") and item.get("authors"):
            existing["authors"] = item["authors"]
        existing["citation_count"] = max(
            _to_int(existing.get("citation_count")), _to_int(item.get("citation_count"))
        )
        # Take max of existing and new relevance_score (sources may differ in their scoring)
        existing["relevance_score"] = max(
            _to_int(existing.get("relevance_score")),
            _to_int(item.get("relevance_score")),
        )
    # Rank by: source_hits, relevance_score, has_abstract, citation_count, then year as tiebreaker
    ranked = sorted(
        merged.values(),
        key=lambda p: (
            _to_int(p.get("source_hits")),
            _to_int(p.get("relevance_score")),
            1 if p.get("abstract") else 0,
            min(_to_int(p.get("citation_count")), 5000),
            _to_int(p.get("year")),
        ),
        reverse=True,
    )
    # Only apply relevance-score floor when a query is given (walk_citations passes None)
    if query is not None:
        # Score 0 = zero query terms in title AND <50 citations (unrelated)
        # Score 1-2 = only from citation boost (rare but keep)
        ranked = [p for p in ranked if _to_int(p.get("relevance_score")) >= 1]
    return ranked[:limit]


BEST_SOURCES = "arxiv,semantic,crossref,openalex,pmc,europepmc,openaire,doaj,unpaywall"


def _expand_query(query: str) -> list[str]:
    """Generate query variations for broader recall."""
    expansions = [query]
    words = query.lower().split()
    acronyms = {
        "llm": ["large language model", "language models"],
        "nlp": ["natural language processing"],
        "ml": ["machine learning"],
        "dl": ["deep learning"],
        "cv": ["computer vision"],
        "rl": ["reinforcement learning"],
        "ai": ["artificial intelligence"],
        "bert": ["bidirectional encoder representations"],
        "gpt": ["generative pre-trained transformer"],
        "rag": ["retrieval augmented generation"],
        "mcp": ["model context protocol"],
        "iot": ["internet of things"],
    }
    expansions_added = 0
    for word in words:
        if word in acronyms and expansions_added < 2:
            for expansion in acronyms[word][:1]:  # Take only first expansion per acronym
                new_q = query.lower().replace(word, expansion)
                if new_q not in expansions:
                    expansions.append(new_q)
                    expansions_added += 1
                    break  # One expansion per acronym
    return expansions[:3]  # Original + up to 2 expansions


def _detect_source_from_paper(paper: dict[str, Any]) -> str:
    """Auto-detect the best source for full-text retrieval from paper metadata."""
    arxiv_id = paper.get("arxiv_id") or paper.get("arxiv") or ""
    if arxiv_id and ARXIV_ID_RE.match(arxiv_id):
        return "arxiv"
    doi = str(paper.get("doi") or "").lower()
    if "biorxiv" in doi:
        return "biorxiv"
    if "medrxiv" in doi:
        return "medrxiv"
    if doi and DOI_RE.match(doi):
        # Valid DOI but no bio/medrxiv prefix; let downstream OA fallbacks handle it
        return ""
    pmid = str(paper.get("pmid") or "")
    if pmid and PMID_RE.match(pmid):
        return "pmc"  # PMC has actual full text
    source_list = paper.get("sources") or []
    for s in source_list:
        if s in ("arxiv", "semantic", "biorxiv", "medrxiv", "iacr", "openaire",
                 "citeseerx", "doaj", "base", "zenodo", "hal", "pmc", "europepmc"):
            return s
    return ""


async def _resolve_oa_id(paper_id: str) -> str:
    """Resolve any paper ID (DOI, arXiv, OpenAlex W...) to OpenAlex work ID."""
    if not paper_id:
        return ""
    # Already an OpenAlex W... ID
    if paper_id.startswith("W"):
        return paper_id
    try:
        client = await _get_client()
        oa_email = UNPAYWALL_EMAIL

        # Try DOI lookup first
        if paper_id.startswith("10.") or paper_id.startswith("doi:"):
            doi = paper_id.removeprefix("doi:")
            resp = await client.get(
                f"https://api.openalex.org/works/doi:{doi}",
                params={"mailto": oa_email},
            )
            if resp.status_code == 200:
                return (resp.json().get("id") or "").split("/")[-1]

        # Try arXiv ID — handle both "arxiv:1706.03762" and "10.48550/arXiv.1706.03762"
        arxiv = ""
        if paper_id.startswith("arxiv:") or paper_id.startswith("arXiv:"):
            arxiv = paper_id.split(":", 1)[1]
        elif "arxiv" in paper_id.lower():
            arxiv = paper_id.split("/")[-1]
        if arxiv:
            resp = await client.get(
                "https://api.openalex.org/works",
                params={"filter": f"ids:arxiv:{arxiv}", "per_page": 1, "mailto": oa_email},
            )
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                if results:
                    return (results[0].get("id") or "").split("/")[-1]

        # Fallback: search by title/ID
        resp = await client.get(
            "https://api.openalex.org/works",
            params={"search": paper_id, "per_page": 1, "mailto": oa_email},
        )
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            if results:
                return (results[0].get("id") or "").split("/")[-1]

        return ""
    except Exception:
        return ""


async def _search_openalex_direct(query: str, max_results: int = 50, year_from: int | None = None, year_to: int | None = None) -> list[dict[str, Any]]:
    """Direct OpenAlex API search with full metadata. Returns normalized papers."""
    try:
        client = await _get_client()
        oa_email = UNPAYWALL_EMAIL
        filters = []
        if year_from:
            filters.append(f"from_publication_date:{year_from}-01-01")
        if year_to:
            filters.append(f"to_publication_date:{year_to}-12-31")
        params: dict[str, Any] = {
            "search": query,
            "per_page": min(max_results, 200),
            "mailto": oa_email,
        }
        if filters:
            params["filter"] = ",".join(filters)
        resp = await client.get("https://api.openalex.org/works", params=params)
        if resp.status_code != 200:
            return []
        data = resp.json()
        papers = [_parse_oa_work(r, include_pdf=True) for r in data.get("results", [])[:max_results]]
        return [_normalize_paper(p, "openalex-direct") for p in papers]
    except Exception:
        return []


def _parse_oa_work(r: dict[str, Any], include_pdf: bool = True) -> dict[str, Any]:
    """Parse a single OpenAlex work into our normalized paper format."""
    authors = []
    for a in (r.get("authorships") or [])[:8]:
        name = (a.get("author") or {}).get("display_name", "")
        if name:
            authors.append(name)
    abstract = ""
    abstract_inv = r.get("abstract_inverted_index")
    if abstract_inv:
        positions = []
        for word, pos_list in abstract_inv.items():
            for pos in pos_list:
                positions.append((pos, word))
        positions.sort()
        abstract = " ".join(w for _, w in positions)
    paper = {
        "title": r.get("title", ""),
        "authors": authors,
        "year": (r.get("publication_date") or "")[:4] or None,
        "doi": (r.get("doi") or "").removeprefix("https://doi.org/"),
        "abstract": abstract,
        "citation_count": _to_int(r.get("cited_by_count")),
        "url": r.get("id", ""),
    }
    if include_pdf:
        oa_info = r.get("open_access", {}) or {}
        paper["pdf_url"] = oa_info.get("oa_url") or (r.get("primary_location") or {}).get("pdf_url")
        paper["is_open_access"] = bool(oa_info.get("is_oa"))
    return paper


async def _openalex_citations(doi: str, direction: str = "cited_by", limit: int = 10) -> list[dict[str, Any]]:
    """Fetch forward (cited_by) or backward (references) citations via OpenAlex."""
    oa_id = await _resolve_oa_id(doi)
    if not oa_id:
        return []
    return await _fetch_oa_by_id(oa_id, direction, limit)


async def _fetch_oa_by_id(oa_id: str, direction: str, limit: int) -> list[dict[str, Any]]:
    """Fetch citations from OpenAlex using a resolved W... work ID."""
    try:
        client = await _get_client()
        oa_email = UNPAYWALL_EMAIL

        if direction == "cited_by":
            resp = await client.get(
                "https://api.openalex.org/works",
                params={"filter": f"cites:{oa_id}", "per_page": limit, "mailto": oa_email},
            )
        else:
            resp = await client.get(
                f"https://api.openalex.org/works/{oa_id}",
                params={"mailto": oa_email},
            )
            if resp.status_code != 200:
                return []
            refs = (resp.json() or {}).get("referenced_works", [])
            if not refs:
                return []
            ids_param = "|".join(refs[:limit])
            resp = await client.get(
                "https://api.openalex.org/works",
                params={"filter": f"ids:{ids_param}", "per_page": limit, "mailto": oa_email},
            )
        if resp.status_code != 200:
            return []
        results = resp.json().get("results", [])
        papers = [_parse_oa_work(r, include_pdf=False) for r in results[:limit]]
        return [_normalize_paper(p, f"openalex-{direction}") for p in papers]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Core tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def search_literature(
    query: str,
    max_results: int = 25,
    year_from: int | None = None,
    year_to: int | None = None,
    expand_queries: bool = True,
) -> dict[str, Any]:
    """Search academic papers across 8 sources (arXiv, Semantic Scholar, OpenAlex, CrossRef, Unpaywall, OpenAIRE, Scopus, Springer). Returns deduplicated results with abstracts and citation counts."""
    # Check cache
    cache_key = (query, max_results, year_from, year_to, expand_queries)
    cached = _search_cache.get(*cache_key)
    if cached is not None:
        return cached

    year = None
    if year_from and year_to:
        year = f"{year_from}-{year_to}"
    elif year_from:
        year = f"{year_from}-"
    elif year_to:
        year = f"-{year_to}"

    queries = _expand_query(query) if expand_queries else [query]
    has_scopus = bool(os.environ.get("ELSEVIER_API_KEY"))
    has_springer = bool(os.environ.get("SPRINGER_API_KEY"))
    tasks_per_query = 2 + int(has_scopus) + int(has_springer)

    # Per-task: (coro, source_label)
    task_specs: list[tuple[Any, str]] = []
    for q in queries:
        task_specs.append((academix_server.academic_search_papers(
            query=q,
            year_from=year_from,
            year_to=year_to,
            sort="relevance",
            limit=min(max(max_results, 1), 100),
            response_format="json",
        ), "academix"))
        task_specs.append((paper_search.search_papers(
            query=q,
            max_results_per_source=max(10, min(max_results, 50)),
            sources=BEST_SOURCES,
            year=year,
        ), "paper-search"))
        if has_scopus:
            task_specs.append((search_scopus(q, max_results=max_results, year_from=str(year_from) if year_from else None, year_to=str(year_to) if year_to else None), "scopus"))
        if has_springer:
            task_specs.append((search_springer(q, max_results=max_results, year_from=str(year_from) if year_from else None, year_to=str(year_to) if year_to else None), "springer"))

    try:
        outputs = await asyncio.wait_for(
            asyncio.gather(*[t[0] for t in task_specs], return_exceptions=True),
            timeout=30.0,
        )
    except asyncio.TimeoutError:
        outputs = [Exception("search timed out")] * len(task_specs)

    papers: list[dict[str, Any]] = []
    errors: dict[str, str] = {}

    def _extract_papers(out: Any, source: str) -> list[dict[str, Any]]:
        """Extract papers from a backend response, tagged with source name."""
        data = _json_load(out)
        raw_papers = data.get("papers", []) if isinstance(data, dict) else (out if isinstance(out, list) else [])
        return [_normalize_paper(p, source) for p in raw_papers]

    # Use modular arithmetic on iteration index (works regardless of which tasks errored)
    for i, (out, source) in enumerate(zip(outputs, [t[1] for t in task_specs])):
        q_idx = min(i // tasks_per_query, len(queries) - 1)
        if isinstance(out, Exception):
            errors[f"{source}_{queries[q_idx]}"] = str(out)
        else:
            papers.extend(_extract_papers(out, source))

    merged = _merge_papers(papers, max_results, query)

    # Direct OpenAlex search (separate from paper_search wrapper for full metadata)
    try:
        oa_papers = await asyncio.wait_for(
            _search_openalex_direct(query, max_results=max_results, year_from=year_from, year_to=year_to),
            timeout=15.0,
        )
        if oa_papers:
            all_with_oa = merged + oa_papers
            merged = _merge_papers(all_with_oa, max_results, query)
    except asyncio.TimeoutError:
        pass

    result = {
        "query": query,
        "queries_used": queries,
        "total_before_dedupe": len(papers),
        "returned": len(merged),
        "errors": errors,
        "papers": merged,
    }

    _search_cache.set(result, *cache_key)
    return result


@mcp.tool()
async def walk_citations(
    paper_id: str,
    direction: Literal["forward", "backward", "both"] = "forward",
    depth: int = 1,
    max_papers_per_hop: int = 10,
    max_total: int = 200,
) -> dict[str, Any]:
    """Follow citation graphs forward (who cites) or backward (what it cites), multi-hop. Uses OpenAlex (highest success rate). Only walks most-cited papers for deeper hops."""
    visited: set[str] = set()
    all_papers: list[dict[str, Any]] = []
    queue: deque[tuple[str, int]] = deque([(paper_id, 0)])
    visited.add(paper_id)
    truncated = False

    while queue:
        if len(all_papers) >= max_total:
            truncated = True
            break
        current_id, current_depth = queue.popleft()
        if current_depth >= depth:
            continue

        # Resolve any paper ID to OpenAlex work ID
        oa_id = await _resolve_oa_id(current_id)
        if not oa_id:
            continue

        # Fetch forward + backward from OpenAlex in parallel
        cite_tasks = []
        if direction in ("forward", "both"):
            cite_tasks.append(_fetch_oa_by_id(oa_id, "cited_by", max_papers_per_hop))
        if direction in ("backward", "both"):
            cite_tasks.append(_fetch_oa_by_id(oa_id, "references", max_papers_per_hop))

        try:
            cite_results = await asyncio.wait_for(
                asyncio.gather(*cite_tasks, return_exceptions=True),
                timeout=15.0,
            )
        except asyncio.TimeoutError:
            continue

        for r in cite_results:
            if isinstance(r, Exception) or not isinstance(r, list):
                continue
            for paper in r[:max_papers_per_hop]:
                if not isinstance(paper, dict):
                    continue
                if len(all_papers) >= max_total:
                    truncated = True
                    break
                pid = paper.get("doi") or paper.get("arxiv_id") or paper.get("paper_id") or ""
                if not pid or pid in visited:
                    continue
                visited.add(pid)
                paper["hop"] = current_depth + 1
                paper["via"] = current_id
                all_papers.append(paper)
                # Only queue highly-cited papers for deeper hops
                if current_depth + 1 < depth and _to_int(paper.get("citation_count")) >= 10:
                    queue.append((pid, current_depth + 1))
            if truncated:
                break
        if truncated:
            break

    deduped = _merge_papers(all_papers, len(all_papers))
    return {
        "root_paper": paper_id,
        "truncated": truncated,
        "max_total": max_total,
        "direction": direction,
        "depth": depth,
        "total_found": len(deduped),
        "papers": deduped,
    }


@mcp.tool()
async def read_paper(
    paper_id: str,
    source: str = "auto",
    doi: str = "",
    title: str = "",
    save_path: str = "./downloads",
    use_scihub: bool = True,
) -> dict[str, Any]:
    """Download and extract full text from a paper. Falls back through OA repositories, Unpaywall, Sci-Hub."""
    if source == "auto":
        # Only pass an ID field if the value actually matches its expected format
        # (e.g. a DOI like "10.1234/foo" must not be passed as arxiv_id).
        source = _detect_source_from_paper({
            "arxiv_id": paper_id if ARXIV_ID_RE.match(paper_id) else "",
            "doi": paper_id if DOI_RE.match(paper_id) else doi,
            "pmid": paper_id if PMID_RE.match(paper_id) else "",
        })

    result: dict[str, Any] = {"paper_id": paper_id, "source": source}

    reader = _get_reader(source)
    if reader:
        try:
            text = await reader(paper_id, save_path=save_path)
            result["text"] = text
            result["success"] = bool(text)
            return result
        except Exception as exc:
            result["reader_error"] = str(exc)

    try:
        path = await paper_search.download_with_fallback(
            source=source, paper_id=paper_id, doi=doi, title=title,
            save_path=save_path, use_scihub=use_scihub,
        )
        result["download_path"] = path
        result["success"] = path is not None
    except Exception as exc:
        result["download_error"] = str(exc)
        result["success"] = False

    # Additional OA fallbacks (if DOI provided and main download failed)
    if not result.get("success") and doi:
        client = await _get_client()

        # Try OpenAlex OA URL (has open_access.oa_url for many papers)
        try:
            oa_url = None
            resp = await client.get(
                f"https://api.openalex.org/works/doi:{doi}",
                params={"mailto": UNPAYWALL_EMAIL},
            )
            if resp.status_code == 200:
                data = resp.json()
                oa_info = data.get("open_access", {})
                oa_url = oa_info.get("oa_url")
                if not oa_url:
                    primary = data.get("primary_location", {})
                    if primary and primary.get("pdf_url"):
                        oa_url = primary["pdf_url"]
            if oa_url:
                pdf_resp = await client.get(oa_url, timeout=30.0)
                if pdf_resp.status_code == 200 and _is_pdf_response(pdf_resp, pdf_resp.content):
                    result["download_path"] = _save_pdf(pdf_resp.content, paper_id, save_path)
                    result["success"] = True
                    result["oa_source"] = "openalex"
                    return result
        except Exception:
            pass

        # Try Springer OA
        try:
            oa_url = await springer_resolve_oa(doi)
            if oa_url:
                pdf_resp = await client.get(oa_url, timeout=30.0)
                if pdf_resp.status_code == 200 and _is_pdf_response(pdf_resp, pdf_resp.content):
                    result["download_path"] = _save_pdf(pdf_resp.content, paper_id, save_path)
                    result["success"] = True
                    result["oa_source"] = "springer"
                    return result
        except Exception:
            pass

        # Try multi-mirror Sci-Hub (if enabled). Uses a fresh client with
        # follow_redirects=True because the shared client may not allow it.
        if use_scihub:
            env_mirrors = os.environ.get("SCI_HUB_MIRRORS", "").strip()
            sci_hub_urls = (
                [m.strip() for m in env_mirrors.split(",") if m.strip()]
                if env_mirrors
                else ["https://sci-hub.se", "https://sci-hub.st", "https://sci-hub.ru"]
            )
            async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as sc:
                for mirror in sci_hub_urls:
                    try:
                        resp = await sc.get(f"{mirror}/{doi}")
                        if resp.status_code == 200 and _is_pdf_response(resp, resp.content):
                            result["download_path"] = _save_pdf(resp.content, paper_id, save_path)
                            result["success"] = True
                            result["oa_source"] = f"scihub:{mirror}"
                            return result
                    except Exception:
                        continue

    return result


# ---------------------------------------------------------------------------
# Curation tools
# ---------------------------------------------------------------------------

def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
